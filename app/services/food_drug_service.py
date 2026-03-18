"""음식-약물 상호작용 검색 서비스.

data/faiss/food_drug.index + food_drug_meta.pkl + food_aliases.json 기반
internal(규칙) 검색 + pubmed(논문) 벡터 검색 하이브리드.
"""

import json
import logging
import os
import pickle
import re

import faiss
import numpy as np
from openai import AsyncOpenAI

logger = logging.getLogger("dodaktalk.food_drug")

DATA_DIR = "data/faiss"
MODEL_EMB = "text-embedding-3-small"

# ── 데이터 로드 ─────────────────────────────────────────
_index = None
_metadata: list[dict] = []
_aliases: dict[str, list[str]] = {}
_available = False

try:
    idx_path = os.path.join(DATA_DIR, "food_drug.index")
    meta_path = os.path.join(DATA_DIR, "food_drug_meta.pkl")
    alias_path = os.path.join(DATA_DIR, "food_aliases.json")

    if os.path.exists(idx_path) and os.path.exists(meta_path):
        _index = faiss.read_index(idx_path)
        with open(meta_path, "rb") as f:
            _meta_raw = pickle.load(f)
        _metadata = _meta_raw.get("metadata", [])
        logger.info("음식-약물 인덱스 로드 완료: %d건", len(_metadata))

        if os.path.exists(alias_path):
            with open(alias_path, "r", encoding="utf-8") as f:
                _aliases = json.load(f)
            logger.info("음식 별칭 로드 완료: %d개 카테고리", len(_aliases))

        _available = True
    else:
        logger.warning("음식-약물 데이터 파일 없음. 서비스 비활성화.")
except Exception as e:
    logger.warning("음식-약물 서비스 초기화 실패: %s", e)


# ── 유틸 함수 ───────────────────────────────────────────
def normalize_food(text: str) -> list[str]:
    """사용자 메시지에서 음식 키워드를 정규화된 카테고리로 변환."""
    normalized = text.replace(" ", "")
    matched = []
    for category, aliases in _aliases.items():
        for alias in aliases:
            if alias.replace(" ", "") in normalized:
                matched.append(category)
                break
    return matched


def _clean_drug_name(name: str) -> str:
    """약물명에서 괄호 안 성분명 제거하여 비교용 이름 추출."""
    return re.sub(r"\s*\(.*\)", "", name).strip()


# ── 검색 함수 ───────────────────────────────────────────
def search_internal_rules(
    food_categories: list[str],
    user_drugs: list[str],
) -> list[dict]:
    """internal 규칙 기반 검색: 음식 카테고리 × 사용자 복용약 매칭."""
    if not _available or not _metadata:
        return []

    results = []
    drug_names_lower = [d.lower() for d in user_drugs]

    for meta in _metadata:
        if meta.get("source") != "internal":
            continue
        if meta["food_name"] not in food_categories:
            continue

        meta_drug = _clean_drug_name(meta["drug_name"]).lower()
        for user_drug in drug_names_lower:
            user_clean = re.sub(r"\s*\(.*", "", user_drug).strip().lower()
            if user_clean in meta_drug or meta_drug in user_clean:
                results.append({
                    "food": meta["food_name"],
                    "drug": meta["drug_name"],
                    "severity": meta.get("severity", "unknown"),
                    "recommendation": meta.get("recommendation", ""),
                    "source": "internal",
                })
                break

    return results


async def search_literature(
    query: str,
    top_k: int = 3,
) -> list[dict]:
    """벡터 검색으로 pubmed 논문 기반 음식-약물 상호작용 검색."""
    if not _available or _index is None:
        return []

    try:
        client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        resp = await client.embeddings.create(model=MODEL_EMB, input=[query])
        q_vec = np.array([resp.data[0].embedding], dtype="float32")
        faiss.normalize_L2(q_vec)

        scores, ids = _index.search(q_vec, top_k * 2)

        results = []
        for score, idx in zip(scores[0], ids[0]):
            if idx == -1 or idx >= len(_metadata):
                continue
            meta = _metadata[idx]
            if meta.get("source") != "pubmed":
                continue
            results.append({
                "food": meta.get("food_name", ""),
                "drug": meta.get("drug_name", ""),
                "evidence": (meta.get("evidence_text") or meta.get("recommendation", ""))[:200],
                "score": round(float(score), 4),
                "source": "pubmed",
            })
            if len(results) >= top_k:
                break

        return results
    except Exception as e:
        logger.warning("음식-약물 논문 검색 실패: %s", e)
        return []


# ── 통합 검색 함수 (chatbot_service에서 호출) ───────────
async def search_food_drug(query: str, user_drugs: list[str]) -> str:
    """음식-약물 상호작용을 검색하여 GPT 프롬프트용 텍스트 반환."""
    if not _available:
        return ""

    # 1) 음식 카테고리 추출
    food_categories = normalize_food(query)

    parts = []

    # 2) internal 규칙 검색 (사용자 복용약과 음식 매칭)
    if food_categories and user_drugs:
        rules = search_internal_rules(food_categories, user_drugs)
        if rules:
            severity_order = {"major": 0, "moderate": 1, "minor": 2, "unknown": 3}
            rules.sort(key=lambda r: severity_order.get(r["severity"], 3))
            lines = []
            for r in rules[:5]:
                sev = {"major": "위험", "moderate": "주의", "minor": "경미"}.get(r["severity"], "미분류")
                lines.append(f"- [{sev}] {r['food']} + {r['drug']}: {r['recommendation']}")
            parts.append("=== 음식-약물 상호작용 (규칙) ===\n" + "\n".join(lines))

    # 3) 논문 벡터 검색
    literature = await search_literature(query, top_k=2)
    if literature:
        lines = []
        for r in literature:
            lines.append(f"- {r['food']} 관련: {r['evidence']}")
        parts.append("=== 음식-약물 상호작용 (논문) ===\n" + "\n".join(lines))

    return "\n\n".join(parts)
