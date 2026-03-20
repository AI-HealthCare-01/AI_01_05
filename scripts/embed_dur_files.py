"""DUR 안전정보 파일을 ChromaDB dur_safety 컬렉션에 임베딩하는 스크립트.

Usage:
    uv run python scripts/embed_dur_files.py
"""

import csv
import hashlib
import os
import sys

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DUR_DIR = "data/dur"
CHROMA_DIR = os.getenv("CHROMA_PERSIST_DIR", "data/embeddings")
COLLECTION_NAME = "dur_safety"
EMBEDDING_MODEL = "jhgan/ko-sroberta-multitask"

# 병용금기 필터링용 정신과 관련 키워드
PSYCH_KEYWORDS = [
    "리스페리돈",
    "올란자핀",
    "쿠에티아핀",
    "아리피프라졸",
    "할로페리돌",
    "클로자핀"
    "팔리페리돈",
    "졸피뎀",
    "에스조피클론",
    "트리아졸람",
    "플루옥세틴",
    "설트랄린",
    "파록세틴",
    "에스시탈로프람",
    "벤라팍신",
    "미르타자핀",
    "둘록세틴",
    "아미트리프틸린",
    "이미프라민",
    "알프라졸람",
    "로라제팜",
    "디아제팜",
    "클로나제팜",
    "리튬",
    "발프로산",
    "카르바마제핀",
    "라모트리진",
    "메틸페니데이트",
    "아토목세틴",
    "부프로피온",
    "트라마돌",
    "모르핀",
    "옥시코돈",
    "와파린",
    "아스피린",
    "이부프로펜",
    "나프록센",
]

# 새 CSV 컬럼 인덱스
COL_DUR_TYPE = 1       # DUR유형
COL_INGREDIENT = 5     # DUR성분명
COL_EFFICACY = 9       # 효능군
COL_CONTENT = 11       # 금기내용
COL_AGE = 13           # 연령기준
COL_MAX_PERIOD = 14    # 최대투여기간
COL_MAX_DOSE = 15      # 1일최대용량
COL_GRADE = 16         # 등급
COL_COMBO_INGREDIENT = 20  # 병용금기DUR성분명
COL_STATUS = 25        # 상태
COL_SERIES = 26        # 계열명


def read_csv(filepath: str) -> list[list[str]]:
    """CSV 파일을 utf-8-bom → cp949 → utf-8 순서로 읽기 시도."""
    # 필드 크기 제한 확장 (병용금기 등 대용량 필드 대응)
    csv.field_size_limit(10 * 1024 * 1024)  # 10MB

    for enc in ("utf-8-sig", "cp949", "utf-8"):
        try:
            with open(filepath, encoding=enc) as f:
                return list(csv.reader(f))
        except (UnicodeDecodeError, UnicodeError):
            continue
    raise RuntimeError(f"인코딩 감지 실패: {filepath}")


def make_id(text: str) -> str:
    """텍스트 해시 기반 고유 ID 생성."""
    return hashlib.md5(text.encode()).hexdigest()


def _safe_get(row: list[str], idx: int) -> str:
    """인덱스 범위 초과 방지."""
    return row[idx].strip() if idx < len(row) else ""


def process_pregnancy_csv() -> list[dict]:
    """임부금기 CSV 처리."""
    filepath = os.path.join(DUR_DIR, "DUR_임부금기.csv")
    if not os.path.exists(filepath):
        print(f"  [SKIP] 파일 없음: {filepath}")
        return []

    rows = read_csv(filepath)[1:]  # 헤더 제외
    seen = set()
    results = []

    for row in rows:
        if len(row) < 27:
            continue
        ingredient = _safe_get(row, COL_INGREDIENT)
        grade = _safe_get(row, COL_GRADE)
        content = _safe_get(row, COL_CONTENT)
        status = _safe_get(row, COL_STATUS)

        if not ingredient or status != "정상":
            continue
        if ingredient in seen:
            continue
        seen.add(ingredient)

        text = f"{ingredient}은(는) 임부금기 {grade} 성분입니다."
        if grade == "1등급":
            text += " 사람에서 태아에 대한 위해성이 명확하여 원칙적으로 사용이 금지됩니다."
        elif grade == "2등급":
            text += " 태아에 대한 위해성이 나타날 수 있어 원칙적으로 사용이 금지됩니다."
        if content:
            text += f" {content}"

        results.append({
            "text": text,
            "metadata": {
                "source": "식약처_임부금기",
                "type": "임부금기",
                "성분명": ingredient,
                "등급": grade,
            },
        })

    return results


def process_elderly_csv() -> list[dict]:
    """노인주의 CSV 처리."""
    filepath = os.path.join(DUR_DIR, "DUR_노인주의.csv")
    if not os.path.exists(filepath):
        print(f"  [SKIP] 파일 없음: {filepath}")
        return []

    rows = read_csv(filepath)[1:]
    seen = set()
    results = []

    for row in rows:
        if len(row) < 27:
            continue
        ingredient = _safe_get(row, COL_INGREDIENT)
        content = _safe_get(row, COL_CONTENT)
        status = _safe_get(row, COL_STATUS)

        if not ingredient or status != "정상":
            continue
        if ingredient in seen:
            continue
        seen.add(ingredient)

        text = f"{ingredient}은(는) 노인 투여 시 주의가 필요한 의약품입니다."
        if content:
            text += f" {content}"

        results.append({
            "text": text,
            "metadata": {
                "source": "식약처_노인주의",
                "type": "노인주의",
                "성분명": ingredient,
            },
        })

    return results


def process_age_csv() -> list[dict]:
    """특정연령대금기 CSV 처리."""
    filepath = os.path.join(DUR_DIR, "DUR_특정연령대금기.csv")
    if not os.path.exists(filepath):
        print(f"  [SKIP] 파일 없음: {filepath}")
        return []

    rows = read_csv(filepath)[1:]
    seen = set()
    results = []

    for row in rows:
        if len(row) < 27:
            continue
        ingredient = _safe_get(row, COL_INGREDIENT)
        age = _safe_get(row, COL_AGE)
        content = _safe_get(row, COL_CONTENT)
        status = _safe_get(row, COL_STATUS)

        if not ingredient or status != "정상":
            continue
        key = f"{ingredient}|{age}"
        if key in seen:
            continue
        seen.add(key)

        text = f"{ingredient}은(는)"
        if age:
            text += f" {age} 환자에게 투여 금기입니다."
        else:
            text += " 특정 연령대에 투여 금기입니다."
        if content:
            text += f" {content}"

        results.append({
            "text": text,
            "metadata": {
                "source": "식약처_특정연령대금기",
                "type": "연령금기",
                "성분명": ingredient,
            },
        })

    return results


def process_combination_csv() -> list[dict]:
    """병용금기 CSV 처리 — 정신과 관련 키워드만 필터링."""
    filepath = os.path.join(DUR_DIR, "DUR_병용금기.csv")
    if not os.path.exists(filepath):
        print(f"  [SKIP] 파일 없음: {filepath}")
        return []

    rows = read_csv(filepath)[1:]
    seen = set()
    results = []

    for row in rows:
        if len(row) < 27:
            continue
        ingredient_a = _safe_get(row, COL_INGREDIENT)
        ingredient_b = _safe_get(row, COL_COMBO_INGREDIENT)
        content = _safe_get(row, COL_CONTENT)
        status = _safe_get(row, COL_STATUS)

        if not ingredient_a or not ingredient_b or status != "정상":
            continue

        # 정신과 키워드 필터링
        combined = f"{ingredient_a} {ingredient_b}"
        if not any(kw in combined for kw in PSYCH_KEYWORDS):
            continue

        # 성분쌍 기준 중복 제거
        pair = tuple(sorted([ingredient_a, ingredient_b]))
        if pair in seen:
            continue
        seen.add(pair)

        text = f"{ingredient_a}과(와) {ingredient_b}은(는) 병용 금기입니다."
        if content:
            text += f" {content}"

        results.append({
            "text": text,
            "metadata": {
                "source": "식약처_병용금기",
                "type": "병용금기",
                "성분명": f"{ingredient_a}, {ingredient_b}",
            },
        })

    return results


def process_dose_csv() -> list[dict]:
    """용량주의 CSV 처리."""
    filepath = os.path.join(DUR_DIR, "DUR_용량주의.csv")
    if not os.path.exists(filepath):
        print(f"  [SKIP] 파일 없음: {filepath}")
        return []

    rows = read_csv(filepath)[1:]
    seen = set()
    results = []

    for row in rows:
        if len(row) < 27:
            continue
        ingredient = _safe_get(row, COL_INGREDIENT)
        content = _safe_get(row, COL_CONTENT)
        max_dose = _safe_get(row, COL_MAX_DOSE)
        status = _safe_get(row, COL_STATUS)

        if not ingredient or status != "정상":
            continue
        if ingredient in seen:
            continue
        seen.add(ingredient)

        text = f"{ingredient}은(는) 용량 주의 의약품입니다."
        if max_dose:
            text += f" 1일 최대 용량: {max_dose}."
        if content:
            text += f" {content}"

        results.append({
            "text": text,
            "metadata": {
                "source": "식약처_용량주의",
                "type": "용량주의",
                "성분명": ingredient,
                "1일최대용량": max_dose,
            },
        })

    return results


def process_period_csv() -> list[dict]:
    """투여기간주의 CSV 처리."""
    filepath = os.path.join(DUR_DIR, "DUR_투여기간주의.csv")
    if not os.path.exists(filepath):
        print(f"  [SKIP] 파일 없음: {filepath}")
        return []

    rows = read_csv(filepath)[1:]
    seen = set()
    results = []

    for row in rows:
        if len(row) < 27:
            continue
        ingredient = _safe_get(row, COL_INGREDIENT)
        content = _safe_get(row, COL_CONTENT)
        max_period = _safe_get(row, COL_MAX_PERIOD)
        status = _safe_get(row, COL_STATUS)

        if not ingredient or status != "정상":
            continue
        if ingredient in seen:
            continue
        seen.add(ingredient)

        text = f"{ingredient}은(는) 투여기간 주의 의약품입니다."
        if max_period:
            text += f" 최대 투여 기간: {max_period}."
        if content:
            text += f" {content}"

        results.append({
            "text": text,
            "metadata": {
                "source": "식약처_투여기간주의",
                "type": "투여기간주의",
                "성분명": ingredient,
                "최대투여기간": max_period,
            },
        })

    return results


def process_additive_csv() -> list[dict]:
    """첨가제주의 CSV 처리."""
    filepath = os.path.join(DUR_DIR, "DUR_첨가제주의.csv")
    if not os.path.exists(filepath):
        print(f"  [SKIP] 파일 없음: {filepath}")
        return []

    rows = read_csv(filepath)[1:]
    seen = set()
    results = []

    for row in rows:
        if len(row) < 27:
            continue
        ingredient = _safe_get(row, COL_INGREDIENT)
        content = _safe_get(row, COL_CONTENT)
        status = _safe_get(row, COL_STATUS)

        if not ingredient or status != "정상":
            continue
        if ingredient in seen:
            continue
        seen.add(ingredient)

        text = f"{ingredient}은(는) 첨가제 주의 성분입니다."
        if content:
            text += f" {content}"

        results.append({
            "text": text,
            "metadata": {
                "source": "식약처_첨가제주의",
                "type": "첨가제주의",
                "성분명": ingredient,
            },
        })

    return results


def process_efficacy_csv() -> list[dict]:
    """효능군중복주의 CSV 처리."""
    filepath = os.path.join(DUR_DIR, "DUR_효능군중복주의.csv")
    if not os.path.exists(filepath):
        print(f"  [SKIP] 파일 없음: {filepath}")
        return []

    rows = read_csv(filepath)[1:]
    seen = set()
    results = []

    for row in rows:
        if len(row) < 27:
            continue
        ingredient = _safe_get(row, COL_INGREDIENT)
        efficacy = _safe_get(row, COL_EFFICACY)
        series = _safe_get(row, COL_SERIES)
        content = _safe_get(row, COL_CONTENT)
        status = _safe_get(row, COL_STATUS)

        if not ingredient or status != "정상":
            continue
        if ingredient in seen:
            continue
        seen.add(ingredient)

        text = f"{ingredient}은(는) 효능군 중복 주의 의약품입니다."
        if series:
            text += f" 계열: {series}."
        if efficacy:
            text += f" 효능군: {efficacy}."
        if content:
            text += f" {content}"

        results.append({
            "text": text,
            "metadata": {
                "source": "식약처_효능군중복주의",
                "type": "효능군중복주의",
                "성분명": ingredient,
                "계열명": series,
            },
        })

    return results


def embed_to_chromadb(documents: list[dict], batch_label: str) -> int:
    """문서 리스트를 ChromaDB dur_safety 컬렉션에 저장."""
    if not documents:
        print(f"  [{batch_label}] 저장할 문서 없음")
        return 0

    import chromadb
    from sentence_transformers import SentenceTransformer

    client = chromadb.PersistentClient(path=CHROMA_DIR)
    collection = client.get_or_create_collection(COLLECTION_NAME)
    embedder = SentenceTransformer(EMBEDDING_MODEL)

    texts = [doc["text"] for doc in documents]
    metadatas = [doc["metadata"] for doc in documents]
    ids = [make_id(t) for t in texts]

    # 배치 처리 (ChromaDB 제한: 한번에 5461건)
    batch_size = 5000
    total = 0
    for i in range(0, len(texts), batch_size):
        batch_texts = texts[i : i + batch_size]
        batch_ids = ids[i : i + batch_size]
        batch_meta = metadatas[i : i + batch_size]

        print(f"  [{batch_label}] 임베딩 중... ({i + 1}~{min(i + batch_size, len(texts))}/{len(texts)})")
        embeddings = embedder.encode(batch_texts, show_progress_bar=True).tolist()

        collection.upsert(
            documents=batch_texts,
            embeddings=embeddings,
            metadatas=batch_meta,
            ids=batch_ids,
        )
        total += len(batch_texts)

    return total


def main():
    print("=" * 60)
    print("DUR 안전정보 ChromaDB 임베딩 시작")
    print(f"저장 경로: {CHROMA_DIR}/{COLLECTION_NAME}")
    print(f"임베딩 모델: {EMBEDDING_MODEL}")
    print("=" * 60)

    tasks = [
        ("임부금기",       process_pregnancy_csv),
        ("노인주의",       process_elderly_csv),
        ("특정연령대금기", process_age_csv),
        ("병용금기",       process_combination_csv),
        ("용량주의",       process_dose_csv),
        ("투여기간주의",   process_period_csv),
        ("첨가제주의",     process_additive_csv),
        ("효능군중복주의", process_efficacy_csv),
    ]

    stats = {}
    for i, (label, func) in enumerate(tasks, 1):
        print(f"\n[{i}/{len(tasks)}] {label} 처리 중...")
        docs = func()
        print(f"  파싱 완료: {len(docs)}건")
        stats[label] = embed_to_chromadb(docs, label)

    print("\n" + "=" * 60)
    print("임베딩 완료 결과")
    print("=" * 60)
    total = 0
    for name, count in stats.items():
        print(f"  {name}: {count}건")
        total += count
    print(f"\n  총 저장 건수: {total}건")
    print(f"  ChromaDB 경로: {CHROMA_DIR}")
    print(f"  컬렉션 이름: {COLLECTION_NAME}")
    print("=" * 60)


if __name__ == "__main__":
    main()
