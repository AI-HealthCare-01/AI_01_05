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
    "리스페리돈", "올란자핀", "쿠에티아핀", "아리피프라졸", "할로페리돌",
    "클로자핀", "팔리페리돈", "졸피뎀", "에스조피클론", "트리아졸람",
    "플루옥세틴", "설트랄린", "파록세틴", "에스시탈로프람", "벤라팍신",
    "미르타자핀", "둘록세틴", "아미트리프틸린", "이미프라민",
    "알프라졸람", "로라제팜", "디아제팜", "클로나제팜",
    "리튬", "발프로산", "카르바마제핀", "라모트리진",
    "메틸페니데이트", "아토목세틴", "부프로피온",
    "트라마돌", "모르핀", "옥시코돈",
    "와파린", "아스피린", "이부프로펜", "나프록센",
]


def read_csv(filepath: str) -> list[list[str]]:
    """CSV 파일을 cp949 → utf-8-sig 순서로 읽기 시도."""
    for enc in ("cp949", "utf-8-sig", "utf-8"):
        try:
            with open(filepath, encoding=enc) as f:
                return list(csv.reader(f))
        except (UnicodeDecodeError, UnicodeError):
            continue
    raise RuntimeError(f"인코딩 감지 실패: {filepath}")


def make_id(text: str) -> str:
    """텍스트 해시 기반 고유 ID 생성."""
    return hashlib.md5(text.encode()).hexdigest()


def _parse_pregnancy_grade(grade_raw: str) -> str:
    """임부금기 등급 파싱."""
    if "1등급" in grade_raw:
        return "1등급"
    if "2등급" in grade_raw:
        return "2등급"
    return ""


def _build_pregnancy_text(ingredient: str, grade: str, grade_raw: str, detail: str, note: str) -> str:
    """임부금기 텍스트 생성."""
    text = f"{ingredient}은(는) 임부금기 {grade} 성분입니다."
    if grade == "1등급":
        text += " 사람에서 태아에 대한 위해성이 명확하여 원칙적으로 사용이 금지됩니다."
    elif grade == "2등급":
        text += " 태아에 대한 위해성이 나타날 수 있어 원칙적으로 사용이 금지됩니다."
    if grade_raw and grade_raw != grade:
        text += f" 세부사항: {grade_raw}"
    if detail:
        text += f" {detail}"
    if note:
        text += f" 비고: {note}"
    return text


def process_pregnancy_xlsx() -> list[dict]:
    """임부금기 성분리스트 xlsx 처리 (skiprows=1, 실제 데이터는 row 2부터)."""
    import openpyxl

    filepath = os.path.join(DUR_DIR, "임부금기 성분리스트_251223.xlsx")
    if not os.path.exists(filepath):
        print(f"  [SKIP] 파일 없음: {filepath}")
        return []

    wb = openpyxl.load_workbook(filepath, read_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(min_row=3, values_only=True))
    wb.close()

    results = []
    for row in rows:
        if not row or not row[1]:
            continue
        ingredient = str(row[1]).strip()
        grade_raw = str(row[2]).strip() if row[2] else ""
        note = str(row[3]).strip() if row[3] else ""
        detail = str(row[4]).strip() if row[4] else ""

        grade = _parse_pregnancy_grade(grade_raw)
        text = _build_pregnancy_text(ingredient, grade, grade_raw, detail, note)

        results.append({
            "text": text,
            "metadata": {
                "source": "식약처_임부금기",
                "type": "임부금기",
                "성분명": ingredient,
                "등급": grade or grade_raw,
            },
        })

    return results


def process_pregnancy_csv() -> list[dict]:
    """임부금기 품목리스트 csv 처리 — 성분명 기준 중복 제거."""
    filepath = os.path.join(DUR_DIR, "의약품안전사용서비스(DUR)_임부금기 품목리스트 2025.6.csv")
    if not os.path.exists(filepath):
        print(f"  [SKIP] 파일 없음: {filepath}")
        return []

    rows = read_csv(filepath)
    # 컬럼: 성분명, 성분코드, 제품코드, 제품명, 업체명, 고시일자, 고시번호, 금기등급, 상세정보, 급여여부
    data = rows[1:]

    seen_ingredients = set()
    results = []
    for row in data:
        if len(row) < 9:
            continue
        ingredient = row[0].strip()
        if not ingredient or ingredient in seen_ingredients:
            continue
        seen_ingredients.add(ingredient)

        grade_raw = row[7].strip()
        detail = row[8].strip()

        grade = f"{grade_raw}등급" if grade_raw in ("1", "2") else grade_raw

        text = f"{ingredient}은(는) 임부금기 {grade} 성분입니다."
        if grade_raw == "1":
            text += " 사람에서 태아에 대한 위해성이 명확하여 원칙적으로 사용이 금지됩니다."
        elif grade_raw == "2":
            text += " 태아에 대한 위해성이 나타날 수 있어 원칙적으로 사용이 금지됩니다."
        if detail:
            text += f" {detail}"

        results.append({
            "text": text,
            "metadata": {
                "source": "심평원_임부금기",
                "type": "임부금기",
                "성분명": ingredient,
                "등급": grade,
            },
        })

    return results


def process_elderly_csv() -> list[dict]:
    """노인주의 품목리스트 csv 처리."""
    filepath = os.path.join(DUR_DIR, "의약품안전사용서비스(DUR)_노인주의 품목리스트 2025.6.csv")
    if not os.path.exists(filepath):
        print(f"  [SKIP] 파일 없음: {filepath}")
        return []

    rows = read_csv(filepath)
    # 컬럼: 성분명, 성분코드, 제품코드, 제품명, 업소명, 공고일자, 공고번호, 약품상세정보, 비고, 급여여부
    data = rows[1:]

    seen = set()
    results = []
    for row in data:
        if len(row) < 8:
            continue
        ingredient = row[0].strip()
        product = row[3].strip()
        detail = row[7].strip()

        key = f"{ingredient}|{product}"
        if not ingredient or key in seen:
            continue
        seen.add(key)

        text = f"{ingredient}({product})은(는) 노인 투여 시 주의가 필요한 의약품입니다."
        if detail:
            text += f" {detail}"

        results.append({
            "text": text,
            "metadata": {
                "source": "심평원_노인주의",
                "type": "노인주의",
                "성분명": ingredient,
            },
        })

    return results


def process_elderly_nsaid_csv() -> list[dict]:
    """노인주의(해열진통소염제) 품목리스트 csv 처리."""
    filepath = os.path.join(DUR_DIR, "의약품안전사용서비스(DUR)_노인주의(해열진통소염제) 품목리스트 2025.6.csv")
    if not os.path.exists(filepath):
        print(f"  [SKIP] 파일 없음: {filepath}")
        return []

    rows = read_csv(filepath)
    # 컬럼: 성분코드, 성분명, 제품코드, 제품명, 업소명, 약품상세정보, 급여여부
    data = rows[1:]

    seen = set()
    results = []
    for row in data:
        if len(row) < 6:
            continue
        ingredient = row[1].strip()
        product = row[3].strip()
        detail = row[5].strip()

        key = f"{ingredient}|{product}"
        if not ingredient or key in seen:
            continue
        seen.add(key)

        text = f"{ingredient}({product})은(는) 노인에게 투여 시 주의가 필요한 해열진통소염제입니다."
        if detail:
            text += f" {detail}"

        results.append({
            "text": text,
            "metadata": {
                "source": "심평원_노인주의",
                "type": "노인주의",
                "성분명": ingredient,
            },
        })

    return results


def process_age_csv() -> list[dict]:
    """연령금기 품목리스트 csv 처리."""
    filepath = os.path.join(DUR_DIR, "의약품안전사용서비스(DUR)_연령금기 품목리스트 2025.6.csv")
    if not os.path.exists(filepath):
        print(f"  [SKIP] 파일 없음: {filepath}")
        return []

    rows = read_csv(filepath)
    # 컬럼: 성분명, 성분코드, 제품코드, 제품명, 업체명, 특정연령, 특정연령단위, 연령처리조건, 고시번호, 고시일자, 상세정보, 급여여부
    data = rows[1:]

    seen = set()
    results = []
    for row in data:
        if len(row) < 11:
            continue
        ingredient = row[0].strip()
        product = row[3].strip()
        age = row[5].strip()
        age_unit = row[6].strip()
        condition = row[7].strip()
        detail = row[10].strip()

        key = f"{ingredient}|{product}"
        if not ingredient or key in seen:
            continue
        seen.add(key)

        # 연령 조건 텍스트 구성
        age_text = f"{age}{age_unit}"
        cond_map = {"미만 (1)": "미만", "이하 (2)": "이하", "초과 (3)": "초과", "이상 (4)": "이상"}
        cond_text = cond_map.get(condition, condition.split("(")[0].strip() if condition else "")

        text = f"{ingredient}({product})은(는) {age_text} {cond_text} 환자에게 투여 금기입니다."
        if detail:
            text += f" {detail}"

        results.append({
            "text": text,
            "metadata": {
                "source": "심평원_연령금기",
                "type": "연령금기",
                "성분명": ingredient,
            },
        })

    return results


def process_combination_csv() -> list[dict]:
    """병용금기 품목리스트 csv 처리 — 정신과 관련 키워드만 필터링."""
    filepath = os.path.join(DUR_DIR, "의약품안전사용서비스(DUR)_병용금기 품목리스트 2025.6.csv")
    if not os.path.exists(filepath):
        print(f"  [SKIP] 파일 없음: {filepath}")
        return []

    rows = read_csv(filepath)
    # 컬럼: 성분명A, 성분코드A, 제품코드A, 제품명A, 업체명A, 급여여부A,
    #       성분명B, 성분코드B, 제품코드B, 제품명B, 업체명B, 급여여부B,
    #       고시번호, 고시일자, 상세정보, 비고
    data = rows[1:]

    seen = set()
    results = []
    for row in data:
        if len(row) < 15:
            continue
        ingredient_a = row[0].strip()
        product_a = row[3].strip()
        ingredient_b = row[6].strip()
        product_b = row[9].strip()
        detail = row[14].strip()

        # 정신과 키워드 필터링 (제품명A/B에서 검색)
        combined = f"{product_a} {product_b} {ingredient_a} {ingredient_b}"
        if not any(kw in combined for kw in PSYCH_KEYWORDS):
            continue

        # 성분쌍 기준 중복 제거
        pair = tuple(sorted([ingredient_a, ingredient_b]))
        if pair in seen:
            continue
        seen.add(pair)

        text = f"{ingredient_a}과(와) {ingredient_b}은(는) 병용 금기입니다."
        if detail:
            text += f" {detail}"

        results.append({
            "text": text,
            "metadata": {
                "source": "심평원_병용금기",
                "type": "병용금기",
                "성분명": f"{ingredient_a}, {ingredient_b}",
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

        print(f"  [{batch_label}] 임베딩 중... ({i+1}~{min(i+batch_size, len(texts))}/{len(texts)})")
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

    stats = {}

    # 1. 임부금기 xlsx
    print("\n[1/6] 임부금기 성분리스트 (xlsx)...")
    docs = process_pregnancy_xlsx()
    print(f"  파싱 완료: {len(docs)}건")
    stats["임부금기_xlsx"] = embed_to_chromadb(docs, "임부금기_xlsx")

    # 2. 임부금기 csv
    print("\n[2/6] 임부금기 품목리스트 (csv, 성분 중복제거)...")
    docs = process_pregnancy_csv()
    print(f"  파싱 완료: {len(docs)}건")
    stats["임부금기_csv"] = embed_to_chromadb(docs, "임부금기_csv")

    # 3. 노인주의
    print("\n[3/6] 노인주의 품목리스트...")
    docs = process_elderly_csv()
    print(f"  파싱 완료: {len(docs)}건")
    stats["노인주의"] = embed_to_chromadb(docs, "노인주의")

    # 4. 노인주의 해열진통소염제
    print("\n[4/6] 노인주의(해열진통소염제) 품목리스트...")
    docs = process_elderly_nsaid_csv()
    print(f"  파싱 완료: {len(docs)}건")
    stats["노인주의_해열"] = embed_to_chromadb(docs, "노인주의_해열")

    # 5. 연령금기
    print("\n[5/6] 연령금기 품목리스트...")
    docs = process_age_csv()
    print(f"  파싱 완료: {len(docs)}건")
    stats["연령금기"] = embed_to_chromadb(docs, "연령금기")

    # 6. 병용금기 (정신과 키워드 필터링)
    print("\n[6/6] 병용금기 품목리스트 (정신과 키워드 필터링)...")
    docs = process_combination_csv()
    print(f"  파싱 완료: {len(docs)}건")
    stats["병용금기"] = embed_to_chromadb(docs, "병용금기")

    # 결과 출력
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
