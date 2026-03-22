"""
약물 정보 임베딩 파이프라인 v2
12개 CSV → 문장화 → OpenAI 임베딩 → FAISS .index 저장

개선사항 (v2):
  1. e약은요 문장에 성분명·브랜드 동의어 동시 삽입 → 브랜드명 검색 정확도 향상
  2. 이상사례_성분 데이터를 safety.index에서 분리 → adverse_lookup.pkl 로 저장
     (성분 식별자 역할이므로 벡터 검색 불필요, 병용금기 노이즈 제거)
  3. DUR 병용금기 문장에 NSAIDs·진통제 등 약효군 키워드 보강
  4. 낱알식별에 분할선(+/-/없음) 정보 추가 → "분할해서 먹어도 되나요" 대응
  5. 음식·음주·카페인 상호작용 키워드 태그 추가 → "술과 먹어도 되나요" 대응
  6. 졸음·운전 주의 키워드 태그 추가 → "운전해도 되나요" 대응

인덱스 구조:
  drug_info.index    : 낱알식별 + e약은요
  safety.index       : DUR 8종
  disease.index      : 상병분류기호
  adverse_lookup.pkl : 이상사례 성분 lookup (exact match용, FAISS 아님)

실행:
  pip install openai faiss-cpu pandas numpy tqdm
  export OPENAI_API_KEY=sk-...
  python embedding_pipeline.py --index all
  python embedding_pipeline.py --test
  python embedding_pipeline.py --search
  python embedding_pipeline.py -q "타이레놀 해열" -t drug_info
"""

import os
import re
import pickle
import numpy as np
import pandas as pd
from tqdm import tqdm
from openai import OpenAI

# ── 설정 ──────────────────────────────────────────────
DATA_DIR        = "./data"
OUTPUT_DIR      = "./indexes"
MODEL           = "text-embedding-3-small"   # large 권한 없을 경우 small 사용
BATCH_SIZE      = 512          # 한 배치 최대 문장 수
MAX_TOKENS_BATCH = 250_000     # OpenAI 한도 300K, 여유분 확보
MAX_CHARS_PER_TEXT = 6_000     # 단일 문장 최대 글자 수 (약 1,500토큰)

os.makedirs(OUTPUT_DIR, exist_ok=True)
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))


# ══════════════════════════════════════════════════════
# 공통 유틸
# ══════════════════════════════════════════════════════

def read_csv(filename: str) -> pd.DataFrame:
    path = os.path.join(DATA_DIR, filename)
    for enc in ["utf-8-sig", "utf-8", "cp949", "euc-kr"]:
        try:
            df = pd.read_csv(path, encoding=enc, engine="python", on_bad_lines="skip")
            df = df.loc[:, ~df.columns.str.startswith("Unnamed")]
            return df
        except (UnicodeDecodeError, ValueError):
            continue
    raise ValueError(f"인코딩 감지 실패: {filename}")


def read_excel(filename: str) -> pd.DataFrame:
    path = os.path.join(DATA_DIR, filename)
    df = pd.read_excel(path)
    df = df.loc[:, ~df.columns.str.startswith("Unnamed")]
    return df


def clean(val) -> str:
    if pd.isna(val):
        return ""
    s = str(val).strip()
    if s in ("-", "nan", "NaN", "None"):
        return ""
    s = s.replace("|", ", ")
    s = s.replace("&nbsp;", " ")   # nedrug HTML 엔티티 제거
    s = re.sub(r"\s+", " ", s)
    return s


def _estimate_tokens(text: str) -> int:
    """간단한 토큰 수 추정 (한국어: 글자당 ~1.5토큰, 영어: 단어당 ~1.3토큰)"""
    return int(len(text) * 1.5)


def embed_batch(texts: list) -> np.ndarray:
    """
    토큰 기반 배치로 OpenAI 임베딩 호출.
    - 배치당 최대 MAX_TOKENS_BATCH 토큰 이하로 자동 분할
    - 단일 텍스트가 MAX_CHARS_PER_TEXT 초과 시 앞부분만 사용
    """
    # 긴 텍스트 선제 자름
    truncated = [t[:MAX_CHARS_PER_TEXT] for t in texts]

    all_vecs = []
    batch: list = []
    batch_tokens = 0

    def flush(b):
        if not b:
            return []
        resp = client.embeddings.create(model=MODEL, input=b)
        return [d.embedding for d in resp.data]

    for text in truncated:
        tok = _estimate_tokens(text)

        # 단일 텍스트가 한도 초과 → 강제 자름 (이미 위에서 자름, 보험용)
        if tok > MAX_TOKENS_BATCH:
            text = text[:MAX_CHARS_PER_TEXT // 2]
            tok  = _estimate_tokens(text)

        # 현재 배치에 추가하면 한도 초과 또는 문장 수 초과 → flush
        if batch and (batch_tokens + tok > MAX_TOKENS_BATCH or len(batch) >= BATCH_SIZE):
            all_vecs.extend(flush(batch))
            batch, batch_tokens = [], 0

        batch.append(text)
        batch_tokens += tok

    # 마지막 배치
    all_vecs.extend(flush(batch))

    return np.array(all_vecs, dtype="float32")


def save_index(sentences: list, metadata: list, index_name: str):
    import faiss

    print(f"\n[{index_name}] 임베딩 중... ({len(sentences):,}개 문장)")
    vecs = embed_batch(sentences)
    faiss.normalize_L2(vecs)
    dim = vecs.shape[1]

    # IndexFlatIP: 정확한 전체 탐색 (브루트포스)
    # IndexIVFFlat은 nprobe=1 기본값으로 일부 클러스터만 탐색 → 검색 누락 발생
    # 69K 문장 기준 FlatIP 검색 속도 ~10ms 이하로 충분히 빠름
    index = faiss.IndexFlatIP(dim)
    index.add(vecs)

    index_path = os.path.join(OUTPUT_DIR, f"{index_name}.index")
    meta_path  = os.path.join(OUTPUT_DIR, f"{index_name}_meta.pkl")

    faiss.write_index(index, index_path)
    with open(meta_path, "wb") as f:
        pickle.dump({"sentences": sentences, "metadata": metadata}, f)

    print(f"  ✅ {index_path}  ({index.ntotal:,}개 벡터)")
    print(f"  ✅ {meta_path}")


# ══════════════════════════════════════════════════════
# 낱알식별 보완용 성분 정보 사전 (v3)
# e약은요에 없는 약의 성분명 → 효능·주의 텍스트 매핑
# DUR 노인주의/수면진정제 계열 정보를 여기서 추가 기술
# ══════════════════════════════════════════════════════

# 성분명(또는 성분명 일부) → {"효능": ..., "주의": ..., "계열": ...}
# 낱알식별 문장에 해당 정보가 없을 때 보완 텍스트로 삽입됨
_INGREDIENT_SUPPLEMENT: dict = {
    "졸피뎀": {
        "효능": "불면증 단기치료",
        "주의": "졸음유발 수면제, 복용후운전및기계조작금지, 다음날까지졸음지속가능, 음주병용금지",
        "계열": "수면진정제 벤조디아제핀유사체",
    },
    "트라조돈": {
        "효능": "우울증 항우울제",
        "주의": "졸음유발 진정작용, 운전주의, 기립성저혈압, 알코올병용주의",
        "계열": "항우울제 SARI",
    },
    "알프라졸람": {
        "효능": "불안장애 공황장애",
        "주의": "졸음유발 진정작용, 운전주의, 의존성위험, 갑자기중단금지 임의중단금지",
        "계열": "수면진정제 벤조디아제핀",
    },
    "디아제팜": {
        "효능": "불안 근이완 항경련",
        "주의": "졸음유발, 운전주의, 의존성위험, 노인투여주의, 갑자기중단금지 임의중단금지",
        "계열": "수면진정제 벤조디아제핀",
    },
    "클로나제팜": {
        "효능": "뇌전증 공황장애",
        "주의": "졸음유발, 운전주의, 의존성위험, 갑자기중단금지 임의중단금지",
        "계열": "수면진정제 벤조디아제핀",
    },
    "이부프로펜": {
        "효능": "해열 진통 소염 NSAIDs",
        "주의": "공복복용주의 위장장애, 알코올병용주의, 아스피린등NSAIDs중복금지, 임부말기금기",
        "계열": "NSAIDs 진통소염제",
    },
    "아세트아미노펜": {
        "효능": "해열 진통 두통 감기",
        "주의": "음주시간독성위험 알코올병용주의, 간질환주의, 하루최대용량초과금지",
        "계열": "해열진통제",
    },
}

def _get_supplement(품목명: str) -> dict:
    """품목명에서 성분명을 추출해 보완 정보 반환"""
    for 성분키, info in _INGREDIENT_SUPPLEMENT.items():
        if 성분키 in 품목명:
            return info
    return {}


# ══════════════════════════════════════════════════════
# 1. 낱알식별
#    v2: 분할선 정보 추가 → "알약 분할해서 먹어도 되나요" 검색 대응
#    v3: 성분 보완 정보 삽입 → e약은요 미수록 약 검색 대응
# ══════════════════════════════════════════════════════

def process_nalgal() -> tuple:
    df = read_csv("낱알식별.csv")
    sentences, metadata = [], []

    for _, row in tqdm(df.iterrows(), total=len(df), desc="낱알식별"):
        품목명   = clean(row.get("품목명", ""))
        성상     = clean(row.get("성상", ""))
        색상앞   = clean(row.get("색상앞", ""))
        색상뒤   = clean(row.get("색상뒤", ""))
        모양     = clean(row.get("의약품제형", ""))
        표시앞   = clean(row.get("표시앞", "")) or clean(row.get("표기내용앞", ""))
        표시뒤   = clean(row.get("표시뒤", "")) or clean(row.get("표기내용뒤", ""))
        분류명   = clean(row.get("분류명", ""))
        업소명   = clean(row.get("업소명", ""))
        제형     = clean(row.get("제형코드명", ""))
        보험코드  = clean(row.get("보험코드", ""))
        분할선앞  = clean(row.get("분할선앞", ""))

        # v2: 분할 가능 여부 판단
        if 분할선앞 and 분할선앞 not in ("-", "없음", ""):
            분할정보 = f"분할선 있음({분할선앞}) 분할복용가능"
        else:
            분할정보 = "분할선없음 분할복용주의"

        색상 = 색상앞
        if 색상뒤 and 색상뒤 != 색상앞:
            색상 = f"{색상앞}/{색상뒤}"

        각인_parts = []
        if 표시앞: 각인_parts.append(f"앞면 '{표시앞}'")
        if 표시뒤: 각인_parts.append(f"뒷면 '{표시뒤}'")
        각인 = ", ".join(각인_parts) if 각인_parts else "각인없음"

        parts = ["[낱알식별]"]
        if 색상:        parts.append(f"{색상}색")
        if 모양:        parts.append(모양)
        if 제형:        parts.append(f"({제형})")
        if 각인_parts:  parts.append(f"각인: {각인}")
        if 성상:        parts.append(f"성상: {성상}")
        if 품목명:      parts.append(f"제품명: {품목명}")
        if 분류명:      parts.append(f"약효분류: {분류명}")
        if 업소명:      parts.append(f"제조사: {업소명}")
        parts.append(분할정보)

        # v3: e약은요 미수록 약 보완 — 성분 정보 사전에서 효능·주의·계열 추가
        supp = _get_supplement(품목명)
        if supp.get("효능"):  parts.append(f"효능: {supp['효능']}")
        if supp.get("주의"):  parts.append(f"주의: {supp['주의']}")
        if supp.get("계열"):  parts.append(f"약물계열: {supp['계열']}")

        sentence = " / ".join(parts)
        if len(sentence) < 20:
            continue

        sentences.append(sentence)
        metadata.append({
            "type":       "낱알식별",
            "품목명":     품목명,
            "업소명":     업소명,
            "분류명":     분류명,
            "보험코드":   보험코드,
            "분할가능":   분할정보,
            "품목일련번호": str(row.get("품목일련번호", "")),
            "원문":       sentence,
        })

    return sentences, metadata


# ══════════════════════════════════════════════════════
# 2. e약은요
#    v2: 성분명 병기, 음식/음주/카페인/졸음/운전 키워드 태그 추가
# ══════════════════════════════════════════════════════

_INGREDIENT_RE = re.compile(r"[\(（]([가-힣a-zA-Z·\s]+?)[\)）]")

def extract_ingredient(품목명: str) -> str:
    m = _INGREDIENT_RE.search(품목명)
    return m.group(1).strip() if m else ""


# 음식 상호작용 키워드 → 태그명
_FOOD_KEYWORDS = {
    "알코올음주": ["술", "음주", "알코올", "주류"],
    "카페인커피":  ["커피", "카페인", "녹차", "에너지드링크", "홍차"],
    "유제품":     ["우유", "유제품", "칼슘", "치즈", "요구르트"],
    "자몽":       ["자몽", "그레이프프루트"],
}

# 졸음·운전 관련 키워드
_DROWSY_KEYWORDS = [
    "졸음", "졸림", "기면", "진정", "수면", "최면", "항히스타민",
    "벤조디아제핀", "졸피뎀", "트라조돈", "알프라졸람", "클로나제팜",
    "디아제팜", "로라제팜", "졸음을 유발", "운전 주의", "기계조작 주의",
]

# 임의 중단 위험 키워드
_DISCONTINUE_KEYWORDS = [
    "임의로중단", "갑자기중단", "중단하지마십시오", "끊지마십시오",
    "의사와상의없이", "중단시", "반드시복용", "지속복용",
]


def process_eya() -> tuple:
    df = read_csv("e약은요.csv")

    col_map = {
        "효능":     "이 약의 효능은 무엇입니까?",
        "용법":     "이 약은 어떻게 사용합니까?",
        "사전주의":  "이 약을 사용하기 전에 반드시 알아야 할 내용은 무엇입니까?",
        "주의사항":  "이 약의 사용상 주의사항은 무엇입니까?",
        "상호작용":  "이 약을 사용하는 동안 주의해야 할 약 또는 음식은 무엇입니까?",
        "이상반응":  "이 약은 어떤 이상반응이 나타날 수 있습니까?",
        "보관":     "이 약은 어떻게 보관해야 합니까?",
    }

    sentences, metadata = [], []

    # ── v4: 중복 제거 (개선) ──────────────────────────────────
    # 문제: 기존 (성분명+섹션) 기준은 타이레놀처럼 고유 브랜드명을 가진 제품도
    #       동일 성분의 앞 제품에 의해 스킵되는 오류가 있었음.
    #
    # 해결: 제거 대상을 "제네릭 그룹"으로 한정.
    #   - 제네릭 그룹 = 제품명이 "XXX(성분명)" 패턴, 즉 괄호 안에 성분명이 명시된 경우
    #     → 이 경우만 (성분명, 섹션, content앞80자) 중복 제거 적용
    #   - 고유 브랜드명 제품 = 제품명에 괄호 성분명이 없거나 제품명 자체가 브랜드
    #     → 중복 제거 미적용 (항상 임베딩)
    #
    # 예) 알마게이트(알마겔정)  → 제네릭, 중복 제거 대상
    #     타이레놀정500밀리그람(아세트아미노펜) → 괄호 성분명 있지만
    #       제품명 앞부분 "타이레놀정500밀리그람"이 성분명과 다름 → 고유 브랜드 취급
    _seen: dict = {}
    _GENERIC_RE = re.compile(r'^[^(（]+[(（]([가-힣a-zA-Z·\s]+?)[)）]')

    def _is_generic_duplicate(제품명: str, 성분명: str, section: str, content: str) -> bool:
        """제네릭 제품의 중복 문장만 제거. 고유 브랜드(타이레놀 등)는 항상 통과.

        제네릭 판단 기준:
          - 제품명 앞부분(괄호 전, 제형/용량 제거 후)이 성분명과 exact match인 경우
          - 예) 알마게이트정(알마게이트) → 앞부분"알마게이트" == 성분명"알마게이트" → 제네릭
          - 예) 타이레놀정500(아세트아미노펜) → 앞부분"타이레놀" ≠ "아세트아미노펜" → 고유 브랜드
        """
        if not 성분명:
            return False
        m = _GENERIC_RE.match(제품명)
        if not m:
            return False
        앞부분 = re.sub(r'\d+[\s]*(밀리그램|mg|mL|g|mcg|ml|%)', '', 제품명.split('(')[0]).strip()
        앞부분 = re.sub(r'(정|캡슐|시럽|주사|액|산|현탁|과립|연질|필름코팅|서방)$', '', 앞부분).strip()
        성분명_정제 = 성분명.replace(" ", "")
        앞부분_정제 = 앞부분.replace(" ", "")

        # exact match이거나, 앞부분이 3자 이하 단어로 성분명 안에 포함되면 제네릭
        is_generic = (
            앞부분_정제 == 성분명_정제 or
            (len(앞부분_정제) <= 3 and 앞부분_정제 in 성분명_정제)
        )
        if is_generic:
            key = (성분명.strip(), section)
            sig = content.replace(" ", "")[:80]
            seen = _seen.setdefault(key, set())
            if sig in seen:
                return True
            seen.add(sig)
        return False
    # ────────────────────────────────────────────────────────

    for _, row in tqdm(df.iterrows(), total=len(df), desc="e약은요"):
        제품명   = clean(row.get("제품명", ""))
        업체명   = clean(row.get("업체명", ""))
        일련번호  = str(row.get("품목일련번호", ""))
        성분명   = extract_ingredient(제품명)

        # v2: 성분명(브랜드명) 병기 prefix
        prefix_str = f"{성분명}({제품명})" if 성분명 else 제품명

        for section_label, col in col_map.items():
            content = clean(row.get(col, ""))
            if not content or content == "-":
                continue

            # v3: 중복 문장 스킵
            if _is_generic_duplicate(제품명, 성분명, section_label, content):
                continue

            sentence = f"[e약은요/{section_label}] {prefix_str} / {section_label}: {content}"

            # v2: 음식 상호작용 태그
            extra_tags = []
            content_no_space = content.replace(" ", "")
            if section_label == "상호작용":
                for tag, synonyms in _FOOD_KEYWORDS.items():
                    if any(kw in content_no_space for kw in synonyms):
                        extra_tags.append(tag)
                if extra_tags:
                    sentence += f" / 음식주의: {' '.join(extra_tags)}"

            # v2: 졸음·운전 태그
            drowsy = any(kw in content_no_space for kw in _DROWSY_KEYWORDS)
            if drowsy and section_label in ("주의사항", "이상반응", "사전주의"):
                sentence += " / 졸음유발가능 운전기계조작주의"

            # v2: 임의 중단 태그
            discontinue_risk = any(kw in content_no_space for kw in _DISCONTINUE_KEYWORDS)
            if discontinue_risk and section_label in ("주의사항", "사전주의", "용법"):
                sentence += " / 임의중단금지 반드시의사상담"

            sentences.append(sentence)
            metadata.append({
                "type":       "e약은요",
                "section":    section_label,
                "제품명":     제품명,
                "성분명":     성분명,
                "업체명":     업체명,
                "품목일련번호": 일련번호,
                "졸음주의":   drowsy,
                "음식태그":   extra_tags,
                "원문":       sentence,
            })

    return sentences, metadata


# ══════════════════════════════════════════════════════
# 3. DUR 처리
#    v2: 병용금기에 약효군(NSAIDs 등) 키워드 보강
# ══════════════════════════════════════════════════════

_DRUG_CLASS_MAP = {
    "NSAIDs진통소염제": ["이부프로펜", "아스피린", "나프록센", "케토프로펜",
                        "디클로페낙", "인도메타신", "멜록시캄", "셀레콕시브",
                        "케토롤락", "피록시캄"],
    "스타틴":           ["아토르바스타틴", "로수바스타틴", "심바스타틴", "프라바스타틴",
                        "플루바스타틴", "피타바스타틴"],
    "항응고제":         ["와파린", "아픽사반", "리바록사반", "다비가트란", "에독사반"],
    "혈압강하제":       ["암로디핀", "발사르탄", "올메사르탄", "로사르탄", "텔미사르탄"],
    "항우울제":         ["파록세틴", "플루옥세틴", "세르트랄린", "에스시탈로프람"],
    "수면진정제":       ["졸피뎀", "트리아졸람", "알프라졸람", "디아제팜", "로라제팜"],
}

def get_drug_class(성분명: str) -> str:
    for class_name, members in _DRUG_CLASS_MAP.items():
        if any(m in 성분명 for m in members):
            return class_name
    return ""


def process_dur_병용금기(df: pd.DataFrame) -> tuple:
    sentences, metadata = [], []

    for _, row in df.iterrows():
        성분A    = clean(row.get("DUR성분명", ""))
        성분A_영 = clean(row.get("DUR성분명영문", ""))
        성분B    = clean(row.get("병용금기DUR성분명", ""))
        성분B_영 = clean(row.get("병용금기DUR성분영문명", ""))
        금기내용 = clean(row.get("금기내용", ""))
        약효분류 = clean(row.get("약효분류코드", ""))

        if not 성분A or not 성분B:
            continue

        사유     = 금기내용 if 금기내용 else "병용 시 위험 증가"
        class_A  = get_drug_class(성분A)
        class_B  = get_drug_class(성분B)

        for (주성분, 주영문, 주계열), (대상, 대상영문, 대상계열) in [
            ((성분A, 성분A_영, class_A), (성분B, 성분B_영, class_B)),
            ((성분B, 성분B_영, class_B), (성분A, 성분A_영, class_A)),
        ]:
            parts = [
                "[DUR/병용금기]",
                f"성분A: {주성분}",
                f"성분B: {대상}",
                f"병용금기사유: {사유}",
            ]
            if 주계열:   parts.append(f"성분A약효군: {주계열}")
            if 대상계열:  parts.append(f"성분B약효군: {대상계열}")
            if 약효분류:  parts.append(f"약효분류: {약효분류}")

            sentence = " / ".join(parts)
            sentences.append(sentence)
            metadata.append({
                "type":   "DUR_병용금기",
                "성분A":  주성분,
                "성분B":  대상,
                "금기내용": 사유,
                "원문":   sentence,
            })

    return sentences, metadata


def process_dur_단일성분(df: pd.DataFrame, dur_type: str) -> tuple:
    sentences, metadata = [], []

    for _, row in df.iterrows():
        성분명   = clean(row.get("DUR성분명", ""))
        성분영문  = clean(row.get("DUR성분명영문", ""))
        금기내용  = clean(row.get("금기내용", ""))
        효능군   = clean(row.get("효능군", ""))
        연령기준  = clean(row.get("연령기준", ""))
        최대기간  = clean(row.get("최대투여기간", ""))
        최대용량  = clean(row.get("1일최대용량", ""))
        등급     = clean(row.get("등급", ""))
        계열명   = clean(row.get("계열명", ""))
        제형     = clean(row.get("제형", ""))
        비고     = clean(row.get("비고", ""))

        if not 성분명:
            continue

        parts = [f"[DUR/{dur_type}]", f"성분명: {성분명}"]
        if 성분영문: parts.append(f"({성분영문})")

        if dur_type == "노인주의":
            parts.append(f"노인주의사항: {금기내용}" if 금기내용 else "노인투여시주의필요")
            if 제형: parts.append(f"해당제형: {제형}")

        elif dur_type == "임부금기":
            parts.append(f"임부금기사유: {금기내용}" if 금기내용 else "임부에게투여금지")
            if 등급: parts.append(f"위험등급: {등급}")
            if 비고: parts.append(f"비고: {비고}")

        elif dur_type == "특정연령대금기":
            if 연령기준: parts.append(f"금기연령: {연령기준}세미만")
            parts.append(f"사유: {금기내용}" if 금기내용 else "해당연령대안전성미확립")
            if 제형: parts.append(f"해당제형: {제형}")

        elif dur_type == "용량주의":
            if 최대용량: parts.append(f"1일최대용량: {최대용량}")
            if 금기내용: parts.append(f"주의사항: {금기내용}")

        elif dur_type == "투여기간주의":
            if 최대기간: parts.append(f"최대투여기간: {최대기간}")
            if 비고:     parts.append(f"적용범위: {비고}")

        elif dur_type == "효능군중복주의":
            if 효능군:   parts.append(f"효능군: {효능군}")
            if 계열명:   parts.append(f"계열: {계열명}")
            parts.append(f"주의사항: {금기내용}" if 금기내용 else "동일효능군중복투여주의")

        elif dur_type == "첨가제주의":
            if 금기내용: parts.append(f"첨가제주의사항: {금기내용}")
            if 비고:     parts.append(f"적용범위: {비고}")

        sentence = " / ".join(parts)
        sentences.append(sentence)
        metadata.append({
            "type":    f"DUR_{dur_type}",
            "성분명":  성분명,
            "성분코드": str(row.get("DUR성분코드", "")),
            "연령기준": 연령기준,
            "등급":    등급,
            "원문":    sentence,
        })

    return sentences, metadata


# ══════════════════════════════════════════════════════
# 3-2. 신규 DUR 3종 처리
#   - 동일성분중복: 제품별 DUR 성분코드 조합 → "같은 성분 중복투여 주의"
#   - 분할주의:     분할/분쇄/씹기 금지 제형 목록
#   - 수유부주의:   수유 중 주의 성분 목록
# ══════════════════════════════════════════════════════

def process_dur_동일성분중복() -> tuple:
    """DUR_동일성분중복.xlsx → 제품별 동일성분 중복투여 주의 문장"""
    try:
        df = read_excel("DUR_동일성분중복.xlsx")
    except FileNotFoundError:
        print("  ⚠️  DUR_동일성분중복.xlsx 없음 — 건너뜀")
        return [], []

    sentences, metadata = [], []
    # 성분코드 컬럼 목록
    성분코드_cols = [c for c in df.columns if c.startswith("DUR성분코드")]
    성분명_cols   = [c for c in df.columns if c.startswith("DUR성분명")]

    for _, row in df.iterrows():
        제품명 = clean(str(row.get("제품명", "") or ""))
        업소명 = clean(str(row.get("업소명", "") or ""))
        제품코드 = clean(str(row.get("제품코드", "") or ""))

        # 유효한 성분명만 수집
        성분들 = []
        for col in 성분명_cols:
            v = clean(str(row.get(col, "") or ""))
            if v and v not in ("nan", "-"):
                성분들.append(v)

        if not 제품명 or not 성분들:
            continue

        성분_str = ", ".join(성분들)
        sentence = (
            f"[DUR/동일성분중복] 제품명: {제품명} / "
            f"동일성분중복주의: {성분_str} / "
            f"동일 성분이 포함된 다른 약과 함께 복용하지 마십시오"
        )
        sentences.append(sentence)
        metadata.append({
            "type":    "DUR_동일성분중복",
            "제품명":  제품명,
            "업소명":  업소명,
            "제품코드": 제품코드,
            "성분목록": 성분_str,
            "원문":    sentence,
        })

    return sentences, metadata


def process_dur_분할주의() -> tuple:
    """DUR_분할주의.xlsx → 분할·분쇄·씹기 금지 제품 문장"""
    try:
        df = read_excel("DUR_분할주의.xlsx")
    except FileNotFoundError:
        print("  ⚠️  DUR_분할주의.xlsx 없음 — 건너뜀")
        return [], []

    sentences, metadata = [], []
    성분명_col = [c for c in df.columns if "성분명" in c]
    성분명_col = 성분명_col[0] if 성분명_col else "성분명"

    for _, row in df.iterrows():
        제품명 = clean(str(row.get("제품명", "") or ""))
        성분명 = clean(str(row.get(성분명_col, "") or ""))
        제형   = clean(str(row.get("제형", "") or ""))
        업체명 = clean(str(row.get("업체명", "") or ""))

        if not 제품명:
            continue

        sentence = (
            f"[DUR/분할주의] 제품명: {제품명} / 성분: {성분명} / "
            f"제형: {제형} / "
            f"분할·분쇄·씹기 금지 — 통째로 삼켜야 하는 약"
        )
        sentences.append(sentence)
        metadata.append({
            "type":   "DUR_분할주의",
            "제품명": 제품명,
            "성분명": 성분명,
            "제형":   제형,
            "업체명": 업체명,
            "원문":   sentence,
        })

    return sentences, metadata


def process_dur_수유부주의() -> tuple:
    """DUR_수유부주의.xlsx → 수유 중 주의 성분 문장"""
    try:
        df = read_excel("DUR_수유부주의.xlsx")
    except FileNotFoundError:
        print("  ⚠️  DUR_수유부주의.xlsx 없음 — 건너뜀")
        return [], []

    sentences, metadata = [], []
    _seen = set()  # 동일 성분 중복 제거

    for _, row in df.iterrows():
        성분명 = clean(str(row.get("성분명", "") or ""))
        제품명 = clean(str(row.get("제품명", "") or ""))
        비고   = clean(str(row.get("비고", "") or ""))

        if not 성분명:
            continue

        # 성분명 기준 대표 1개만
        if 성분명 not in _seen:
            _seen.add(성분명)
            sentence = (
                f"[DUR/수유부주의] 성분명: {성분명} / "
                f"수유 중 주의 — 모유를 통해 영아에게 전달될 수 있음"
            )
            if 비고 and 비고 != "-":
                sentence += f" / 비고: {비고}"
            sentences.append(sentence)
            metadata.append({
                "type":   "DUR_수유부주의",
                "성분명": 성분명,
                "비고":   비고,
                "원문":   sentence,
            })

    return sentences, metadata


# ══════════════════════════════════════════════════════
# 4. 이상사례보고 → adverse_lookup.pkl (FAISS 제외)
# ══════════════════════════════════════════════════════

def process_adverse_lookup() -> dict:
    df = read_csv("이상사례보고_성분정보.csv")
    lookup = {}

    for _, row in df.iterrows():
        한  = clean(row.get("성분명(한)", ""))
        영  = clean(row.get("성분명(영)", ""))
        코드 = str(row.get("성분코드", ""))
        if 한:
            lookup[한] = {"성분코드": 코드, "성분명영": 영}

    out_path = os.path.join(OUTPUT_DIR, "adverse_lookup.pkl")
    with open(out_path, "wb") as f:
        pickle.dump(lookup, f)

    print(f"  ✅ adverse_lookup.pkl 저장 ({len(lookup):,}개 성분)")
    return lookup


# ══════════════════════════════════════════════════════
# 5. 상병분류기호
# ══════════════════════════════════════════════════════

def process_disease() -> tuple:
    df = read_csv("상병분류기호.csv")
    df.columns = [c.replace("\n", "") for c in df.columns]

    if "완전코드구분" in df.columns:
        df = df[df["완전코드구분"] == "완전코드"]

    df = df.drop_duplicates(subset=["상병기호", "한글명칭"])
    sentences, metadata = [], []

    for _, row in tqdm(df.iterrows(), total=len(df), desc="상병분류기호"):
        코드   = clean(row.get("상병기호", ""))
        한글명  = clean(row.get("한글명칭", ""))
        영문명  = clean(row.get("영문명칭", ""))

        if not 코드 or not 한글명:
            continue

        sentence = f"[상병분류] 상병코드: {코드} / 질환명: {한글명}"
        if 영문명:
            sentence += f" ({영문명})"

        sentences.append(sentence)
        metadata.append({
            "type":   "상병분류",
            "상병코드": 코드,
            "한글명칭": 한글명,
            "영문명칭": 영문명,
            "원문":   sentence,
        })

    return sentences, metadata


# ══════════════════════════════════════════════════════
# 6. nedrug PIL (process_nedrug_pil)
#    nedrug_pil.csv → e약은요와 동일한 섹션별 문장화
#    크롤러(nedrug_crawler.py)로 생성한 파일 사용
# ══════════════════════════════════════════════════════

def process_nedrug_pil() -> tuple:
    path = os.path.join(DATA_DIR, "nedrug_pil.csv")
    if not os.path.exists(path):
        print("  ⚠️  nedrug_pil.csv 없음 — 건너뜀")
        return [], []

    df = pd.read_csv(path, encoding="utf-8-sig")
    sentences, metadata = [], []

    col_map = {
        "효능효과": "효능효과",
        "용법용량": "용법용량",
        "주의사항": "주의사항",
    }

    for _, row in tqdm(df.iterrows(), total=len(df), desc="nedrug PIL"):
        품목명   = clean(str(row.get("품목명",  "") or ""))
        주성분명_raw = clean(str(row.get("주성분명","") or ""))
        일련번호  = str(row.get("품목일련번호", ""))

        # 주성분명 파싱: "[M040353]아세트아미노펜|[M050058]구아이페네신" → "아세트아미노펜, 구아이페네신"
        성분명_list = re.findall(r'\]([^|\[]+)', 주성분명_raw)
        # 각 성분명에서 끝 쉼표/공백 제거 (원본에 쉼표가 붙어있는 경우 대비)
        성분명_list = [re.sub(r',\s*$', '', s.strip()) for s in 성분명_list if s.strip()]
        성분명_list = [s for s in 성분명_list if s]
        성분명_정제 = ", ".join(성분명_list) if 성분명_list else (
            extract_ingredient(품목명) or 주성분명_raw.split(",")[0].strip()
        )

        # prefix: 브랜드명 앞에 + 성분명 최대 3개 병기
        # 성분이 많은 복합제의 경우 prefix가 너무 길어지면 브랜드명이 희석됨
        브랜드명 = re.sub(r'[\(（].*', '', 품목명).strip()
        if not 브랜드명:
            브랜드명 = 품목명
        성분명_short = ", ".join(성분명_list[:3])   # 최대 3개
        if len(성분명_list) > 3:
            성분명_short += " 외"
        prefix = f"{브랜드명} {성분명_short}" if 성분명_short else 브랜드명

        for section_label, col in col_map.items():
            content = clean(str(row.get(col, "") or ""))
            if not content:
                continue

            sentence = f"[nedrug/{section_label}] {prefix} / {section_label}: {content}"

            # 음식 상호작용 태그
            content_ns = content.replace(" ", "")
            extra_tags = []
            if section_label == "주의사항":
                for tag, synonyms in _FOOD_KEYWORDS.items():
                    if any(kw in content_ns for kw in synonyms):
                        extra_tags.append(tag)
                if extra_tags:
                    sentence += f" / 음식주의: {' '.join(extra_tags)}"

            # 졸음·운전 태그 — 모든 섹션에서 감지 (용법용량에도 운전 주의 언급 가능)
            drowsy = any(kw in content_ns for kw in _DROWSY_KEYWORDS)
            if drowsy:
                sentence += " / 졸음유발가능 운전기계조작주의"

            # 임의 중단 태그
            discontinue = any(kw in content_ns for kw in _DISCONTINUE_KEYWORDS)
            if discontinue and section_label == "주의사항":
                sentence += " / 임의중단금지 반드시의사상담"

            sentences.append(sentence)
            metadata.append({
                "type":      "nedrug_PIL",
                "section":   section_label,
                "품목명":    품목명,
                "브랜드명":  브랜드명,
                "성분명":    성분명_정제,
                "품목일련번호": 일련번호,
                "원문":      sentence,
            })

    print(f"  nedrug PIL: {len(sentences):,}문장")
    return sentences, metadata


# ══════════════════════════════════════════════════════
# 인덱스 구축
# ══════════════════════════════════════════════════════

def build_drug_info_index():
    print("\n" + "="*60)
    print("📦 drug_info.index 구축")
    print("="*60)
    s1, m1 = process_nalgal()
    s2, m2 = process_eya()
    s3, m3 = process_nedrug_pil()
    all_s = s1 + s2 + s3
    all_m = m1 + m2 + m3
    print(f"\n  낱알식별: {len(s1):,} / e약은요: {len(s2):,} / nedrug: {len(s3):,} / 합계: {len(all_s):,}")
    save_index(all_s, all_m, "drug_info")


def build_safety_index():
    print("\n" + "="*60)
    print("🚨 safety.index 구축  (DUR 8종)")
    print("="*60)
    all_s, all_m = [], []

    df_byg = read_csv("DUR_병용금기.csv")
    s, m = process_dur_병용금기(df_byg)
    print(f"  DUR_병용금기: {len(s):,}문장 (양방향)")
    all_s += s; all_m += m

    for dur_type, fname in {
        "노인주의":      "DUR_노인주의.csv",
        "임부금기":      "DUR_임부금기.csv",
        "특정연령대금기": "DUR_특정연령대금기.csv",
        "용량주의":      "DUR_용량주의.csv",
        "투여기간주의":   "DUR_투여기간주의.csv",
        "효능군중복주의": "DUR_효능군중복주의.csv",
        "첨가제주의":    "DUR_첨가제주의.csv",
    }.items():
        df = read_csv(fname)
        s, m = process_dur_단일성분(df, dur_type)
        print(f"  DUR_{dur_type}: {len(s):,}문장")
        all_s += s; all_m += m

    # 신규 DUR 3종 (xlsx)
    s, m = process_dur_동일성분중복()
    print(f"  DUR_동일성분중복: {len(s):,}문장")
    all_s += s; all_m += m

    s, m = process_dur_분할주의()
    print(f"  DUR_분할주의: {len(s):,}문장")
    all_s += s; all_m += m

    s, m = process_dur_수유부주의()
    print(f"  DUR_수유부주의: {len(s):,}문장")
    all_s += s; all_m += m

    print("\n  이상사례 성분 → adverse_lookup.pkl (FAISS 제외)")
    process_adverse_lookup()

    print(f"\n  합계: {len(all_s):,}문장")
    save_index(all_s, all_m, "safety")


def build_disease_index():
    print("\n" + "="*60)
    print("🏥 disease.index 구축")
    print("="*60)
    s, m = process_disease()
    print(f"\n  합계: {len(s):,}문장")
    save_index(s, m, "disease")


# ══════════════════════════════════════════════════════
# 6. 의약품허가상세정보 (drug_meta.index)  v4 신규
#
#  효능효과·용법용량·주의사항은 전부 PDF URL → 텍스트 없음
#  활용 가능한 컬럼:
#    품목명, 주성분명, 원료성분, 영문성분명, ATC코드,
#    성상, 전문일반, 저장방법, 마약류분류, 희귀의약품여부
#
#  문장화 전략:
#    - 브랜드명(품목명) + 성분명 + ATC코드 + 특수분류 → 품목 식별 문장
#    - 동일 주성분명 그룹에서 중복 성분 문장 1개만 유지
#    - 취소·유효기간만료 품목 제외(정상만 포함)
#
#  근본 원인 해결 기여:
#    원인2(브랜드명 검색): 품목명-성분명 매핑으로 drug_info 보완 ✅ 부분
#    원인3(스틸녹스 등):  품목 식별 문장으로 기본 약물 정보 제공  ✅ 부분
# ══════════════════════════════════════════════════════

# ATC코드 → 한글 약효군 매핑 (주요 코드만)
_ATC_MAP: dict = {
    # 수면진정제 — 졸피뎀(N05CF02), 트리아졸람(N05CD05) 등 커버
    "N05C":  "수면진정제",
    "N05CD": "수면진정제 벤조디아제핀",
    "N05CF": "수면제 비벤조디아제핀",   # 졸피뎀(N05CF02) 상위
    "N05CF02": "수면제 졸피뎀",
    "N05CH": "멜라토닌수용체작용제",
    # 항우울제 — 트라조돈(N06AX05) 커버
    "N06A":  "항우울제",
    "N06AB": "항우울제 SSRI",
    "N06AX": "항우울제 기타",           # 트라조돈(N06AX05) 상위
    "N06AX05": "항우울제 트라조돈",
    "N06AA": "항우울제 삼환계",
    # 진통제
    "N02A":  "마약성진통제",
    "N02B":  "비마약성진통제",
    "N02BE": "아세트아미노펜계 해열진통제",
    "N02BE01": "아세트아미노펜 해열진통제",
    # NSAIDs
    "M01A":  "NSAIDs 소염진통제",
    "M01AB": "NSAIDs 아세트산계",
    "M01AE": "NSAIDs 프로피온산계",     # 이부프로펜(M01AE01) 상위
    "M01AE01": "이부프로펜 NSAIDs",
    "M01AE02": "나프록센 NSAIDs",
    # 기타
    "C10A":  "스타틴 고지혈증",
    "C10AA": "스타틴",
    "B01A":  "항응고제·혈소판억제제",
    "B01AC": "혈소판억제제",
    "B01AF": "항응고제 경구",
    "C09A":  "ACE억제제",
    "C09C":  "ARB 혈압강하제",
    "A10B":  "경구혈당강하제",
    "A10A":  "인슐린",
    "J01":   "항생제",
    "R03":   "호흡기계약물",
    # 항불안제
    "N05B":  "항불안제",
    "N05BA": "항불안제 벤조디아제핀",
    # 향정신성 계열
    "N05A":  "항정신병약",
    "N03":   "항뇌전증약",
}

def _atc_to_korean(atc: str) -> str:
    """ATC 코드를 한글 약효군으로 변환 (7→6→5→4→3→2자리 순 fallback)"""
    if not atc:
        return ""
    for length in (7, 6, 5, 4, 3, 2):
        if length <= len(atc):
            match = _ATC_MAP.get(atc[:length], "")
            if match:
                return match
    return ""

def _parse_주성분명(raw: str) -> str:
    """[M040702]포도당|[M040426]염화나트륨 → 포도당, 염화나트륨"""
    import re
    names = re.findall(r']([^|]+)', str(raw))
    return ", ".join(n.strip() for n in names if n.strip())


def process_drug_meta() -> tuple:
    """의약품허가상세정보 → 품목 식별 문장 생성"""
    try:
        df = pd.read_excel(
            os.path.join(DATA_DIR, "의약품허가상세정보.xls"),
            sheet_name="Sheet0"
        )
    except FileNotFoundError:
        print("  ⚠️  의약품허가상세정보.xls 없음 — drug_meta 건너뜀")
        return [], []

    # 정상 품목만
    df = df[df["취소상태"] == "정상"].copy()
    print(f"  정상 품목: {len(df):,}건")

    sentences, metadata = [], []
    # 동일 주성분 그룹에서 성분 대표 문장 중복 방지
    _seen_성분: set = set()

    for _, row in tqdm(df.iterrows(), total=len(df), desc="의약품허가상세정보"):
        품목명   = clean(str(row.get("품목명", "") or ""))
        주성분명  = _parse_주성분명(row.get("주성분명", ""))
        원료성분  = clean(str(row.get("원료성분", "") or ""))
        영문성분  = clean(str(row.get("영문성분명", "") or ""))
        atc     = clean(str(row.get("ATC코드", "") or ""))
        성상     = clean(str(row.get("성상", "") or ""))
        전문일반  = clean(str(row.get("전문일반", "") or ""))
        마약류   = clean(str(row.get("마약류분류", "") or ""))
        희귀     = clean(str(row.get("희귀의약품여부", "") or ""))
        일련번호  = str(row.get("품목일련번호", ""))

        if not 품목명:
            continue

        atc_kor  = _atc_to_korean(atc)
        특수분류  = []
        if 마약류 and 마약류 not in ("NaN", "N"):
            특수분류.append(f"마약류({마약류})")
        if 희귀 == "Y":
            특수분류.append("희귀의약품")

        # ── 문장 1: 품목 식별 문장 (브랜드명 + 성분 + 분류) ──
        # 마약류·희귀의약품은 prefix로 분리해 검색 가중치 확보
        if 마약류 and 마약류 not in ("NaN", "N", ""):
            tag_prefix = f"[의약품허가/마약류]"
            parts = [tag_prefix, f"마약류분류: {마약류}", f"품목명: {품목명}"]
        elif 희귀 == "Y":
            tag_prefix = f"[의약품허가/희귀의약품]"
            parts = [tag_prefix, "희귀의약품", f"품목명: {품목명}"]
        else:
            parts = ["[의약품허가]", f"품목명: {품목명}"]

        if 주성분명:  parts.append(f"주성분: {주성분명}")
        if 영문성분:  parts.append(f"({영문성분})")
        if atc_kor:   parts.append(f"약효군: {atc_kor}")
        if atc:       parts.append(f"ATC: {atc}")
        if 전문일반:  parts.append(전문일반)
        if 성상:      parts.append(f"성상: {성상[:60]}")

        sentence = " / ".join(parts)
        sentences.append(sentence)
        metadata.append({
            "type":     "의약품허가",
            "품목명":   품목명,
            "주성분명": 주성분명,
            "ATC코드":  atc,
            "약효군":   atc_kor,
            "전문일반": 전문일반,
            "마약류":   마약류,
            "희귀":     희귀,
            "품목일련번호": 일련번호,
            "원문":     sentence,
        })

        # ── 문장 2: 성분 대표 문장 (동일 성분 첫 번째만) ──
        # 동일 주성분의 수백 개 제네릭을 대표하는 단일 성분 문장
        성분_key = 주성분명.replace(" ", "")[:40]
        if 성분_key and 성분_key not in _seen_성분:
            _seen_성분.add(성분_key)
            s2_parts = ["[의약품허가/성분]", f"성분명: {주성분명}"]
            if 영문성분:  s2_parts.append(f"({영문성분})")
            if atc_kor:   s2_parts.append(f"약효군: {atc_kor}")
            if atc:       s2_parts.append(f"ATC: {atc}")
            s2 = " / ".join(s2_parts)
            sentences.append(s2)
            metadata.append({
                "type":     "의약품허가_성분",
                "주성분명": 주성분명,
                "ATC코드":  atc,
                "약효군":   atc_kor,
                "원문":     s2,
            })

    return sentences, metadata


def build_drug_meta_index():
    print("\n" + "="*60)
    print("💊 drug_meta.index 구축  (의약품허가상세정보)")
    print("="*60)
    s, m = process_drug_meta()
    if not s:
        return
    print(f"\n  합계: {len(s):,}문장")
    save_index(s, m, "drug_meta")


# ══════════════════════════════════════════════════════
# 검색
# ══════════════════════════════════════════════════════

def search(query: str, index_name: str, top_k: int = 5):
    import faiss

    index_path = os.path.join(OUTPUT_DIR, f"{index_name}.index")
    meta_path  = os.path.join(OUTPUT_DIR, f"{index_name}_meta.pkl")

    if not os.path.exists(index_path):
        print(f"  ⚠️  {index_name}.index 없음")
        return

    index = faiss.read_index(index_path)
    with open(meta_path, "rb") as f:
        store = pickle.load(f)

    resp  = client.embeddings.create(model=MODEL, input=[query])
    q_vec = np.array([resp.data[0].embedding], dtype="float32")
    faiss.normalize_L2(q_vec)

    scores, ids = index.search(q_vec, top_k)

    print(f'\n🔍 "{query}" → {index_name}')
    print("-" * 70)
    for rank, (score, idx) in enumerate(zip(scores[0], ids[0]), 1):
        if idx == -1:
            continue
        meta = store["metadata"][idx]
        print(f"  [{rank}] score={score:.4f}  type={meta.get('type','')}")
        print(f"       {store['sentences'][idx][:130]}")


def run_test_suite(top_k: int = 3):
    print("\n\n" + "="*70)
    print("🧪 검색 품질 테스트 v4")
    print("="*70)

    cases = [
        # (쿼리, 인덱스, 설명)
        ("흰색 원형 정제 각인 RS",                           "drug_info",  "낱알 외형 검색"),
        ("타이레놀 효능 해열",                                "drug_info",  "브랜드명 효능 검색"),
        ("이부프로펜 아스피린 같이 먹어도 되나요",             "safety",     "병용금기 검색"),
        ("타이레놀과 술 같이 먹어도 되나요",                  "drug_info",  "음주 상호작용"),
        ("타이레놀과 커피 같이 먹어도 되나요",                "drug_info",  "카페인 상호작용"),
        ("스틸녹스 먹었는데 속이 쓰린 증상이 나타났어",        "drug_info",  "이상반응 검색"),
        ("트리티코정은 어떤 약이야",                          "drug_info",  "약물 정보 검색"),
        ("알약을 분할해서 먹어도 되는지",                      "drug_info",  "분할 복용 가능 여부"),
        ("부루펜시럽 알러지 어떤 성분 주의해야",              "drug_info",  "알러지 성분 확인"),
        ("운전해야 하는데 스틸녹스정 먹어도 될까",             "drug_info",  "졸음·운전 주의"),
        ("처방받은 약을 그만 먹어도 될까",                    "drug_info",  "임의 중단 주의"),
        ("임산부 금기 약물",                                  "safety",     "임부금기 DUR"),
        ("노인 주의 수면제",                                  "safety",     "노인주의 DUR"),
        ("당뇨병 상병코드",                                   "disease",    "상병코드 검색"),
        # v4 신규: drug_meta 검색 케이스
        ("스틸녹스 졸피뎀 수면제",                            "drug_meta",  "★v4 약물 식별 — 스틸녹스"),
        ("트리티코 트라조돈 항우울제",                         "drug_meta",  "★v4 약물 식별 — 트리티코"),
        ("아세트아미노펜 타이레놀",                            "drug_meta",  "★v4 성분-브랜드 매핑"),
        ("이부프로펜 부루펜 NSAIDs",                          "drug_meta",  "★v4 NSAIDs 성분 검색"),
        ("희귀의약품 목록",                                   "drug_meta",  "★v4 희귀의약품 검색"),
        ("마약류 수면제",                                     "drug_meta",  "★v4 마약류 분류 검색"),
    ]

    INDEX_ALL_V4 = ["drug_info", "safety", "disease", "drug_meta"]
    for query, index_name, desc in cases:
        idx_path = os.path.join(OUTPUT_DIR, f"{index_name}.index")
        if not os.path.exists(idx_path):
            print(f"\n  ── [{desc}]  ⚠️  {index_name}.index 없음 — 건너뜀")
            continue
        print(f"\n  ── [{desc}]")
        search(query, index_name, top_k=top_k)


# ══════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse
    import glob

    parser = argparse.ArgumentParser(
        description="약물 임베딩 파이프라인 v2",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog=(
            "사용 예시:\n"
            "  # 1. 최초 구축 (전체)\n"
            "  python embedding_pipeline.py --index all\n\n"
            "  # 2. 기존 인덱스 삭제 후 재구축 (코드 변경 후)\n"
            "  python embedding_pipeline.py --rebuild all\n\n"
            "  # 3. 특정 인덱스만 재구축\n"
            "  python embedding_pipeline.py --rebuild drug_info\n\n"
            "  # 4. 구축 직후 테스트\n"
            "  python embedding_pipeline.py --rebuild all --test\n\n"
            "  # 5. 테스트만 (인덱스 이미 있을 때)\n"
            "  python embedding_pipeline.py --test\n\n"
            "  # 6. 단일 쿼리 검색\n"
            "  python embedding_pipeline.py -q '타이레놀 효능' -t drug_info\n\n"
            "  # 7. 대화형 검색\n"
            "  python embedding_pipeline.py --search\n"
        ),
    )

    parser.add_argument(
        "--index",
        choices=["drug_info", "safety", "disease", "all"],
        default=None,
        help="인덱스 구축 (기존 파일 있으면 건너뜀)",
    )
    parser.add_argument(
        "--rebuild",
        choices=["drug_info", "safety", "disease", "drug_meta", "all"],
        default=None,
        help="기존 .index/.pkl 파일 삭제 후 재구축 (코드 변경 후 사용)",
    )
    parser.add_argument("--test",   action="store_true", help="14개 테스트 케이스 실행")
    parser.add_argument("--search", action="store_true", help="대화형 검색 모드")
    parser.add_argument("--query",  "-q", type=str,  default=None, help="단일 쿼리 검색")
    parser.add_argument(
        "--target", "-t",
        choices=["drug_info", "safety", "disease", "drug_meta"],
        default=None,
        help="--query 검색 대상 인덱스 (생략 시 전체 검색)",
    )
    parser.add_argument("--top-k", "-k", type=int, default=5, help="결과 수 (기본 5)")
    args = parser.parse_args()

    INDEX_ALL = ["drug_info", "safety", "disease", "drug_meta"]

    # ── --rebuild: 기존 파일 삭제 후 재구축 ──────────────
    if args.rebuild:
        targets = INDEX_ALL if args.rebuild == "all" else [args.rebuild]
        print(f"\n🗑️  기존 인덱스 삭제: {targets}")
        for t in targets:
            for ext in [".index", "_meta.pkl"]:
                fp = os.path.join(OUTPUT_DIR, f"{t}{ext}")
                if os.path.exists(fp):
                    os.remove(fp)
                    print(f"   삭제: {fp}")
        # adverse_lookup도 safety 재구축 시 삭제
        if args.rebuild in ("safety", "all"):
            lp = os.path.join(OUTPUT_DIR, "adverse_lookup.pkl")
            if os.path.exists(lp):
                os.remove(lp)
                print(f"   삭제: {lp}")

        # 삭제 후 바로 구축
        if args.rebuild in ("drug_info", "all"):  build_drug_info_index()
        if args.rebuild in ("safety",    "all"):  build_safety_index()
        if args.rebuild in ("disease",   "all"):  build_disease_index()
        if args.rebuild in ("drug_meta", "all"):  build_drug_meta_index()

    # ── --index: 없는 인덱스만 구축 ──────────────────────
    elif args.index:
        if args.index in ("drug_info", "all"):  build_drug_info_index()
        if args.index in ("safety",    "all"):  build_safety_index()
        if args.index in ("disease",   "all"):  build_disease_index()
        if args.index in ("drug_meta", "all"):  build_drug_meta_index()

    # ── 인덱스 현황 출력 ─────────────────────────────────
    if args.rebuild or args.index:
        print("\n📂 인덱스 현황")
        for t in INDEX_ALL:
            fp = os.path.join(OUTPUT_DIR, f"{t}.index")
            if os.path.exists(fp):
                size_mb = os.path.getsize(fp) / 1024 / 1024
                print(f"   ✅ {t}.index  ({size_mb:.1f} MB)")
            else:
                print(f"   ❌ {t}.index  없음")

    # ── --test: 14개 테스트 케이스 ───────────────────────
    if args.test:
        run_test_suite(top_k=args.top_k)
        raise SystemExit(0)

    # ── --query: 단일 쿼리 검색 ──────────────────────────
    if args.query:
        targets = [args.target] if args.target else INDEX_ALL
        for t in targets:
            search(args.query, t, top_k=args.top_k)
        raise SystemExit(0)

    # 대화형 검색 모드
    if args.search or args.index is None:
        INDEX_ALL = ["drug_info", "safety", "disease", "drug_meta"]
        available = [
            t for t in INDEX_ALL
            if os.path.exists(os.path.join(OUTPUT_DIR, f"{t}.index"))
        ]
        if not available:
            print("❌ 구축된 인덱스가 없습니다. 먼저 --index all 을 실행하세요.")
            raise SystemExit(1)

        print("\n" + "="*60)
        print("🔍 대화형 검색 모드       종료: q 또는 Ctrl+C")
        print("="*60)
        print(f"  사용 가능 인덱스 : {', '.join(available)}")
        print(f"  결과 수          : {args.top_k}개  (--top-k 로 변경)")
        print()
        print("  입력 형식")
        print("  ┌─ 특정 인덱스 지정  :  safety: 이부프로펜 아스피린")
        print("  ├─ 전체 인덱스 검색  :  all: 타이레놀")
        print("  └─ 인덱스 생략       :  타이레놀   ← 직전 인덱스 재사용")
        print()

        last_target = available[0]

        while True:
            try:
                raw = input("검색 >> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n👋 종료")
                break

            if not raw or raw.lower() in ("q", "quit", "exit"):
                print("👋 종료")
                break

            if ":" in raw:
                prefix, query = raw.split(":", 1)
                prefix = prefix.strip().lower()
                query  = query.strip()
            else:
                prefix = last_target
                query  = raw

            if not query:
                continue

            if prefix == "all":
                targets = available
            elif prefix in INDEX_ALL:
                targets = [prefix]
                last_target = prefix
            else:
                targets = [last_target]
                query   = raw

            for t in targets:
                if t not in available:
                    print(f"  ⚠️  {t}.index 없음")
                    continue
                search(query, t, top_k=args.top_k)