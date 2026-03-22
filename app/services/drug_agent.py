"""
drug_agent.py — 약물 정보 ReAct Agent
embedding_pipeline.py와 같은 디렉토리에 위치시켜 실행

실행:
  python drug_agent.py
  python drug_agent.py -q "타이레놀과 술 같이 먹어도 되나요"
"""

import json
import os
import pickle

import faiss
import numpy as np
from openai import OpenAI

# embedding_pipeline의 설정값 재사용
DATA_DIR = "data/faiss"
OUTPUT_DIR = "data/faiss"
MODEL_EMB = "text-embedding-3-small"
MODEL_LLM = "gpt-4o-mini"

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))


# ── 인덱스 로딩 (최초 1회) ──────────────────────────────
_indexes: dict = {}
_stores: dict = {}


def _load(name: str):
    if name in _indexes:
        return
    idx_path = os.path.join(OUTPUT_DIR, f"{name}.index")
    meta_path = os.path.join(OUTPUT_DIR, f"{name}_meta.pkl")
    if not os.path.exists(idx_path):
        return
    _indexes[name] = faiss.read_index(idx_path)
    with open(meta_path, "rb") as f:
        _stores[name] = pickle.load(f)


def _load_adverse():
    path = os.path.join(OUTPUT_DIR, "adverse_lookup.pkl")
    if not os.path.exists(path):
        return {}
    with open(path, "rb") as f:
        return pickle.load(f)


# 시작 시 전체 로드
for n in ["drug_info", "safety", "disease", "drug_meta"]:
    _load(n)
_adverse = _load_adverse()


# ── 색상 동의어 매핑 ────────────────────────────────────────
COLOR_ALIASES = {
    "흰색": ["하양", "하얀", "백색", "흰"],
    "하양": ["흰색", "하얀", "백색", "흰"],
    "노란색": ["노랑", "황색"],
    "분홍색": ["핑크", "분홍"],
}


# ── 핵심 검색 함수 ────────────────────────────────────────
def _keyword_search(query: str, index_name: str, top_k: int = 5) -> list[dict]:
    """메타데이터의 품목명/제품명/브랜드명 + sentence에서 키워드 exact match 검색"""
    if index_name not in _stores:
        return []
    store = _stores[index_name]

    # 쿼리에서 질문 패턴 제거 → 약물명 키워드 추출
    q = query.strip()
    for suffix in [
        "성분이 뭐야?",
        "성분이 뭐야",
        "성분이",
        "성분 알려줘",
        "효능이 뭐야",
        "부작용이 뭐야",
        "뭐야?",
        "뭐야",
        "알려줘",
        "어떤 약",
        "어떤약",
    ]:
        q = q.replace(suffix, " ")
    # 공백 기준 분리 후 1글자 조사만 제거 (단어 내부 글자 손상 방지)
    tokens = q.split()
    keywords = []
    for t in tokens:
        t = t.strip()
        if len(t) < 2:
            continue
        # 끝 1글자가 조사이고 나머지가 2글자 이상이면 조사 제거
        if len(t) >= 3 and t[-1] in "은는이가의을를에도과와":
            keywords.append(t[:-1])
        else:
            keywords.append(t)
    if not keywords:
        return []

    # 색상 동의어 확장
    expanded_keywords = list(keywords)
    for kw in keywords:
        for alias_key, aliases in COLOR_ALIASES.items():
            if kw == alias_key or kw in aliases:
                expanded_keywords.extend([alias_key] + aliases)
    keywords = list(set(expanded_keywords))

    # 매칭 점수 기반 검색: 더 많은 키워드가 매칭될수록 높은 점수
    scored_matches = []
    for i, meta in enumerate(store["metadata"]):
        name = meta.get("품목명", "") or meta.get("제품명", "") or ""
        brand = meta.get("브랜드명", "") or ""
        sentence = store["sentences"][i] if i < len(store["sentences"]) else ""
        target = f"{name} {brand} {sentence}"

        # 각 키워드별 매칭 여부 확인
        match_count = sum(1 for kw in keywords if kw in target)

        if match_count > 0:
            scored_matches.append({
                "score": match_count / len(keywords),  # 매칭 비율 (1.0 = 전부 매칭)
                "type": meta.get("type", ""),
                "sentence": store["sentences"][i][:300],
                "match_count": match_count,
            })

    # 매칭 점수 높은 순으로 정렬
    scored_matches.sort(key=lambda x: x["match_count"], reverse=True)

    # match_count 기반 필터: 키워드 2개 이상이면 최소 2개 매칭된 결과만 반환
    if len(keywords) >= 2:
        filtered = [m for m in scored_matches if m["match_count"] >= 2]
        if filtered:
            scored_matches = filtered

    # match_count 필드 제거 후 반환
    results = []
    for m in scored_matches[:top_k]:
        results.append({
            "score": m["score"],
            "type": m["type"],
            "sentence": m["sentence"],
        })

    return results


def _vector_search(query: str, index_name: str, top_k: int = 5) -> list[dict]:
    """키워드 사전 필터링 + 벡터 검색 하이브리드"""
    import logging
    logger = logging.getLogger("dodaktalk.drug_agent")
    logger.info(f"[_vector_search] index={index_name}, query={query}, top_k={top_k}")

    if index_name not in _indexes:
        return []

    # 1단계: 키워드 exact match
    kw_results = _keyword_search(query, index_name, top_k)
    if kw_results:
        logger.info(f"[_keyword_search] {index_name}: {len(kw_results)}건 매칭")
        return kw_results

    # 2단계: 벡터 검색 fallback
    logger.info(f"[_vector_search] {index_name}: 키워드 매칭 없음, 벡터 검색 실행")
    resp = client.embeddings.create(model=MODEL_EMB, input=[query])
    q_vec = np.array([resp.data[0].embedding], dtype="float32")
    faiss.normalize_L2(q_vec)

    scores, ids = _indexes[index_name].search(q_vec, top_k)
    store = _stores[index_name]

    results = []
    for score, idx in zip(scores[0], ids[0], strict=False):
        if idx == -1:
            continue
        results.append(
            {
                "score": round(float(score), 4),
                "type": store["metadata"][idx].get("type", ""),
                "sentence": store["sentences"][idx][:300],
            }
        )
    logger.info(f"[_vector_search] {index_name}: {len(results)}건 반환, top_score={results[0]['score'] if results else 'N/A'}")
    return results


# ── Tool 함수들 ───────────────────────────────────────────
def search_drug_info(query: str, top_k: int = 5) -> str:
    """낱알식별·e약은요·nedrug PIL 검색 (효능, 용법, 주의사항, 이상반응, 외형)"""
    results = _vector_search(query, "drug_info", top_k)
    if not results:
        return "drug_info 인덱스 없음"
    return json.dumps(results, ensure_ascii=False, indent=2)


def search_safety(query: str, top_k: int = 5) -> str:
    """DUR 검색 (병용금기, 임부금기, 노인주의, 용량주의 등)"""
    results = _vector_search(query, "safety", top_k)
    if not results:
        return "safety 인덱스 없음"
    return json.dumps(results, ensure_ascii=False, indent=2)


def search_disease(query: str, top_k: int = 3) -> str:
    """상병분류기호 검색 (질환명 → ICD 코드)"""
    results = _vector_search(query, "disease", top_k)
    if not results:
        return "disease 인덱스 없음"
    return json.dumps(results, ensure_ascii=False, indent=2)


def search_drug_meta(query: str, top_k: int = 5) -> str:
    """의약품허가정보 검색 (브랜드명↔성분명 매핑, 마약류, 희귀의약품, ATC코드)"""
    results = _vector_search(query, "drug_meta", top_k)
    if not results:
        return "drug_meta 인덱스 없음"
    return json.dumps(results, ensure_ascii=False, indent=2)


def lookup_adverse(ingredient: str) -> str:
    """이상사례보고 성분 exact match 조회"""
    result = _adverse.get(ingredient)
    if result:
        return json.dumps({"성분명": ingredient, **result}, ensure_ascii=False)
    # 부분 매칭 시도
    matches = [k for k in _adverse if ingredient in k or k in ingredient]
    if matches:
        return json.dumps([{"성분명": m, **_adverse[m]} for m in matches[:3]], ensure_ascii=False)
    return f"'{ingredient}' 이상사례 데이터 없음"


# ── Tool 스펙 정의 ────────────────────────────────────────
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_drug_info",
            "description": (
                "약물의 효능, 용법용량, 주의사항, 이상반응, 외형(낱알식별), "
                "음식/음주 상호작용, 졸음·운전 주의 정보를 검색합니다. "
                "브랜드명(타이레놀, 부루펜, 스틸녹스 등)이나 증상으로 검색 가능합니다."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "검색할 약물명, 증상, 또는 질문 내용"},
                    "top_k": {"type": "integer", "description": "반환할 결과 수 (기본 5, 최대 10)", "default": 5},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_safety",
            "description": (
                "DUR(의약품 안전 사용 서비스) 데이터를 검색합니다. "
                "병용금기(두 약을 함께 먹으면 안 되는 경우), 임부금기, "
                "노인 주의 약물, 용량 주의, 첨가제 주의 정보를 포함합니다."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "성분명, 약물 계열, 또는 안전 관련 질문"},
                    "top_k": {"type": "integer", "default": 5},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_disease",
            "description": "질환명으로 ICD 상병분류기호(상병코드)를 검색합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "질환명 또는 증상명"},
                    "top_k": {"type": "integer", "default": 3},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_drug_meta",
            "description": (
                "의약품허가정보에서 브랜드명↔성분명 매핑, ATC 약효군 분류, "
                "마약류 여부, 희귀의약품 여부를 검색합니다. "
                "예: '타이레놀의 성분명은?', '졸피뎀 수면제 종류'"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "브랜드명, 성분명, 약효군, 또는 분류 관련 질문"},
                    "top_k": {"type": "integer", "default": 5},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "lookup_adverse",
            "description": (
                "이상사례보고 데이터에서 성분명으로 코드를 조회합니다. 성분명 exact match 또는 부분 매칭을 지원합니다."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "ingredient": {"type": "string", "description": "한글 성분명 (예: 아세트아미노펜, 이부프로펜)"}
                },
                "required": ["ingredient"],
            },
        },
    },
]

TOOL_MAP = {
    "search_drug_info": search_drug_info,
    "search_safety": search_safety,
    "search_disease": search_disease,
    "search_drug_meta": search_drug_meta,
    "lookup_adverse": lookup_adverse,
}

SYSTEM_PROMPT = """당신은 약물 정보를 안내하는 전문 AI 어시스턴트입니다.
사용자의 질문에 답하기 위해 제공된 Tool을 적극적으로 활용하세요.

Tool 사용 가이드:
- 약물 효능/용법/주의사항/이상반응/성분 → search_drug_info (가장 먼저 호출)
- 브랜드명↔성분명 매핑, ATC코드, 마약류/희귀의약품 → search_drug_meta
- 병용금기/임부금기/노인주의 → search_safety
- 질환명/상병코드 → search_disease
- 성분 관련 질문은 반드시 search_drug_info를 먼저 호출한 후 필요 시 search_drug_meta도 호출하세요
- 복잡한 질문은 여러 Tool을 순서대로 호출하세요

중요 원칙:
- 검색 결과가 확실하지 않으면 반드시 의사·약사 상담을 권장하세요
- 의학적 진단이나 처방은 하지 마세요
- 검색 결과의 score가 0.35 미만이면 "관련 정보를 찾지 못했습니다"로 안내하세요"""


# ── ReAct Agent 루프 ──────────────────────────────────────
def run_agent(user_message: str, max_turns: int = 5, verbose: bool = True) -> str:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]

    for _turn in range(max_turns):
        response = client.chat.completions.create(
            model=MODEL_LLM,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
        )
        msg = response.choices[0].message

        # Tool 호출 없으면 최종 응답
        if not msg.tool_calls:
            return msg.content

        # Tool 호출 처리
        messages.append(msg.model_dump(exclude_unset=True))

        for tc in msg.tool_calls:
            fn_name = tc.function.name
            fn_args = json.loads(tc.function.arguments)

            if verbose:
                print(f"  🔧 [{fn_name}] {fn_args}")

            fn_result = TOOL_MAP[fn_name](**fn_args)

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": fn_result,
                }
            )

    return "최대 턴 수 초과"


# ── CLI ────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="약물 정보 ReAct Agent")
    parser.add_argument("-q", "--query", type=str, default=None)
    parser.add_argument("--no-verbose", action="store_true")
    args = parser.parse_args()

    verbose = not args.no_verbose

    if args.query:
        print(f"\n질문: {args.query}\n")
        answer = run_agent(args.query, verbose=verbose)
        print(f"\n답변:\n{answer}")
    else:
        # 대화형 모드
        print("\n💊 약물 정보 Agent  (종료: q)")
        print("=" * 50)
        while True:
            q = input("\n질문 >> ").strip()
            if not q or q.lower() in ("q", "quit"):
                break
            answer = run_agent(q, verbose=verbose)
            print(f"\n{answer}")
