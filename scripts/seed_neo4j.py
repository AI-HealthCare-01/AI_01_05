#!/usr/bin/env python
"""Neo4j 정신과 약물 지식그래프 시드 스크립트.

Drug 노드 → HAS_COMPONENT → Component 노드 → INTERACTS_WITH → Component 노드
severity: "DANGER" (생명 위협, red_alert=True) / "CAUTION" (주의 필요)

실행: uv run python scripts/seed_neo4j.py
"""

from __future__ import annotations

import asyncio
import logging
import os

from neo4j import AsyncGraphDatabase

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# ── 정신과 약물 정의 ────────────────────────────────────────────
PSYCHIATRIC_DRUGS = [
    # 항정신병약
    {"name": "리스페리돈", "generic": "risperidone", "category": "항정신병약"},
    {"name": "올란자핀", "generic": "olanzapine", "category": "항정신병약"},
    {"name": "쿠에티아핀", "generic": "quetiapine", "category": "항정신병약"},
    {"name": "아리피프라졸", "generic": "aripiprazole", "category": "항정신병약"},
    {"name": "할로페리돌", "generic": "haloperidol", "category": "항정신병약"},
    {"name": "클로자핀", "generic": "clozapine", "category": "항정신병약"},
    {"name": "팔리페리돈", "generic": "paliperidone", "category": "항정신병약"},
    # 수면제
    {"name": "졸피뎀", "generic": "zolpidem", "category": "수면제"},
    {"name": "트리아졸람", "generic": "triazolam", "category": "수면제"},
    {"name": "에스조피클론", "generic": "eszopiclone", "category": "수면제"},
    # 항우울제 - SSRI
    {"name": "플루옥세틴", "generic": "fluoxetine", "category": "항우울제-SSRI"},
    {"name": "설트랄린", "generic": "sertraline", "category": "항우울제-SSRI"},
    {"name": "파록세틴", "generic": "paroxetine", "category": "항우울제-SSRI"},
    {"name": "에스시탈로프람", "generic": "escitalopram", "category": "항우울제-SSRI"},
    # 항우울제 - 기타
    {"name": "벤라팍신", "generic": "venlafaxine", "category": "항우울제-SNRI"},
    {"name": "미르타자핀", "generic": "mirtazapine", "category": "항우울제-NaSSA"},
    {"name": "아미트리프틸린", "generic": "amitriptyline", "category": "항우울제-TCA"},
    {"name": "부프로피온", "generic": "bupropion", "category": "항우울제-NDRI"},
    # 항불안제 - 벤조디아제핀
    {"name": "알프라졸람", "generic": "alprazolam", "category": "항불안제-벤조"},
    {"name": "로라제팜", "generic": "lorazepam", "category": "항불안제-벤조"},
    {"name": "디아제팜", "generic": "diazepam", "category": "항불안제-벤조"},
    {"name": "클로나제팜", "generic": "clonazepam", "category": "항불안제-벤조"},
    # 기분안정제
    {"name": "리튬", "generic": "lithium", "category": "기분안정제"},
    {"name": "발프로산", "generic": "valproic acid", "category": "기분안정제"},
    {"name": "카르바마제핀", "generic": "carbamazepine", "category": "기분안정제"},
    {"name": "라모트리진", "generic": "lamotrigine", "category": "기분안정제"},
    # ADHD 약물
    {"name": "메틸페니데이트", "generic": "methylphenidate", "category": "ADHD"},
    {"name": "아토목세틴", "generic": "atomoxetine", "category": "ADHD"},
    # 진통제/오피오이드
    {"name": "트라마돌", "generic": "tramadol", "category": "진통제"},
    {"name": "모르핀", "generic": "morphine", "category": "오피오이드"},
    {"name": "옥시코돈", "generic": "oxycodone", "category": "오피오이드"},
    # 기타 약물/물질
    {"name": "알코올", "generic": "alcohol", "category": "물질"},
    {"name": "MAO억제제", "generic": "MAOI", "category": "항우울제-MAOI"},
    {"name": "이부프로펜", "generic": "ibuprofen", "category": "NSAID"},
    {"name": "나프록센", "generic": "naproxen", "category": "NSAID"},
    {"name": "아스피린", "generic": "aspirin", "category": "NSAID"},
    {"name": "와파린", "generic": "warfarin", "category": "항응고제"},
]

# ── 약물 상호작용 정의 ────────────────────────────────────────────
INTERACTIONS = [
    # === 항정신병약 + 알코올/수면제 ===
    ("리스페리돈", "알코올", "DANGER", "과진정 및 호흡억제", "절대 금지"),
    ("리스페리돈", "졸피뎀", "DANGER", "과진정 및 호흡억제", "동시 복용 금지"),
    ("올란자핀", "알코올", "DANGER", "과진정 및 호흡억제", "절대 금지"),
    ("올란자핀", "졸피뎀", "DANGER", "과진정 및 호흡억제", "동시 복용 금지"),
    ("쿠에티아핀", "알코올", "DANGER", "과진정 및 저혈압", "절대 금지"),
    ("쿠에티아핀", "리튬", "CAUTION", "QT 연장 위험", "모니터링 필요"),
    ("아리피프라졸", "알코올", "DANGER", "과진정", "절대 금지"),
    ("할로페리돌", "알코올", "DANGER", "과진정", "절대 금지"),
    ("할로페리돌", "리튬", "CAUTION", "신경독성 위험", "모니터링 필요"),
    ("클로자핀", "알코올", "DANGER", "과진정 및 호흡억제", "절대 금지"),
    ("클로자핀", "로라제팜", "DANGER", "호흡억제 및 심정지 위험", "동시 복용 금지"),
    ("팔리페리돈", "알코올", "DANGER", "과진정", "절대 금지"),
    # === 수면제 + 알코올/벤조 ===
    ("졸피뎀", "알코올", "DANGER", "호흡억제 및 사망 위험", "절대 금지"),
    ("졸피뎀", "로라제팜", "DANGER", "과진정 및 호흡억제", "동시 복용 금지"),
    ("졸피뎀", "알프라졸람", "DANGER", "과진정 및 호흡억제", "동시 복용 금지"),
    ("졸피뎀", "디아제팜", "DANGER", "과진정 및 호흡억제", "동시 복용 금지"),
    ("졸피뎀", "클로나제팜", "DANGER", "과진정 및 호흡억제", "동시 복용 금지"),
    ("트리아졸람", "알코올", "DANGER", "호흡억제", "절대 금지"),
    ("에스조피클론", "알코올", "DANGER", "호흡억제", "절대 금지"),
    # === 항우울제 + MAOI/기타 ===
    ("플루옥세틴", "MAO억제제", "DANGER", "세로토닌 증후군 - 생명위협", "14일 간격 필요"),
    ("플루옥세틴", "트라마돌", "DANGER", "세로토닌 증후군", "동시 복용 금지"),
    ("플루옥세틴", "리튬", "CAUTION", "세로토닌 증후군 위험", "모니터링 필요"),
    ("설트랄린", "MAO억제제", "DANGER", "세로토닌 증후군 - 생명위협", "14일 간격 필요"),
    ("설트랄린", "트라마돌", "DANGER", "세로토닌 증후군", "동시 복용 금지"),
    ("파록세틴", "MAO억제제", "DANGER", "세로토닌 증후군 - 생명위협", "14일 간격 필요"),
    ("에스시탈로프람", "MAO억제제", "DANGER", "세로토닌 증후군 - 생명위협", "14일 간격 필요"),
    ("에스시탈로프람", "리튬", "CAUTION", "세로토닌 증후군 위험", "모니터링 필요"),
    ("벤라팍신", "MAO억제제", "DANGER", "세로토닌 증후군 - 생명위협", "14일 간격 필요"),
    ("미르타자핀", "MAO억제제", "DANGER", "세로토닌 증후군", "14일 간격 필요"),
    ("아미트리프틸린", "MAO억제제", "DANGER", "세로토닌 증후군", "14일 간격 필요"),
    ("아미트리프틸린", "알코올", "CAUTION", "과진정 증가", "음주 피할 것"),
    ("부프로피온", "MAO억제제", "DANGER", "고혈압 위기", "동시 복용 금지"),
    ("부프로피온", "알코올", "CAUTION", "경련 위험 증가", "음주 피할 것"),
    # === 벤조디아제핀 + 알코올/오피오이드 ===
    ("알프라졸람", "알코올", "DANGER", "호흡억제 및 사망 위험", "절대 금지"),
    ("알프라졸람", "트라마돌", "DANGER", "호흡억제", "동시 복용 금지"),
    ("알프라졸람", "모르핀", "DANGER", "호흡억제 및 사망 위험", "동시 복용 금지"),
    ("알프라졸람", "옥시코돈", "DANGER", "호흡억제 및 사망 위험", "동시 복용 금지"),
    ("로라제팜", "알코올", "DANGER", "호흡억제 및 사망 위험", "절대 금지"),
    ("로라제팜", "트라마돌", "DANGER", "호흡억제", "동시 복용 금지"),
    ("로라제팜", "모르핀", "DANGER", "호흡억제 및 사망 위험", "동시 복용 금지"),
    ("디아제팜", "알코올", "DANGER", "호흡억제 및 사망 위험", "절대 금지"),
    ("디아제팜", "트라마돌", "DANGER", "호흡억제", "동시 복용 금지"),
    ("클로나제팜", "알코올", "DANGER", "호흡억제 및 사망 위험", "절대 금지"),
    ("클로나제팜", "트라마돌", "DANGER", "호흡억제", "동시 복용 금지"),
    # === 기분안정제 ===
    ("리튬", "이부프로펜", "DANGER", "리튬 독성 - 신장 배설 감소", "동시 복용 금지"),
    ("리튬", "나프록센", "DANGER", "리튬 독성 - 신장 배설 감소", "동시 복용 금지"),
    ("리튬", "아스피린", "CAUTION", "리튬 농도 변화 가능", "모니터링 필요"),
    ("리튬", "알코올", "DANGER", "리튬 독성 및 탈수 위험", "절대 금지"),
    ("발프로산", "아스피린", "CAUTION", "출혈 위험 증가", "모니터링 필요"),
    ("발프로산", "라모트리진", "DANGER", "라모트리진 독성 2배 증가", "용량 조절 필수"),
    ("카르바마제핀", "MAO억제제", "DANGER", "고혈압 위기", "동시 복용 금지"),
    ("라모트리진", "발프로산", "DANGER", "라모트리진 독성 증가", "용량 감량 필요"),
    # === ADHD 약물 ===
    ("메틸페니데이트", "MAO억제제", "DANGER", "고혈압 위기", "14일 간격 필요"),
    ("메틸페니데이트", "알코올", "CAUTION", "심혈관 부담 증가", "음주 피할 것"),
    ("아토목세틴", "MAO억제제", "DANGER", "고혈압 위기", "14일 간격 필요"),
    # === 오피오이드 + 알코올/벤조 ===
    ("트라마돌", "알코올", "DANGER", "호흡억제 및 발작 위험", "절대 금지"),
    ("모르핀", "알코올", "DANGER", "호흡억제 및 사망 위험", "절대 금지"),
    ("옥시코돈", "알코올", "DANGER", "호흡억제 및 사망 위험", "절대 금지"),
    # === 항응고제 ===
    ("와파린", "아스피린", "DANGER", "출혈 위험 현저히 증가", "동시 복용 금지"),
    ("와파린", "이부프로펜", "DANGER", "출혈 위험 현저히 증가", "동시 복용 금지"),
    ("와파린", "나프록센", "DANGER", "출혈 위험 현저히 증가", "동시 복용 금지"),
    ("와파린", "알코올", "CAUTION", "출혈 위험 증가 및 대사 변화", "음주 제한"),
    # === 추가 상호작용 (100개 목표) ===
    ("리스페리돈", "로라제팜", "CAUTION", "진정 효과 증가", "모니터링 필요"),
    ("리스페리돈", "트라마돌", "CAUTION", "발작 역치 저하", "모니터링 필요"),
    ("올란자핀", "로라제팜", "CAUTION", "과진정 및 저혈압", "주의 필요"),
    ("올란자핀", "리튬", "CAUTION", "신경독성 위험", "모니터링 필요"),
    ("쿠에티아핀", "디아제팜", "CAUTION", "진정 효과 증가", "용량 조절"),
    ("쿠에티아핀", "트라마돌", "CAUTION", "발작 위험", "모니터링 필요"),
    ("할로페리돌", "로라제팜", "CAUTION", "과진정", "용량 조절"),
    ("클로자핀", "발프로산", "CAUTION", "혈액학적 부작용 증가", "혈액검사 필요"),
    ("플루옥세틴", "알프라졸람", "CAUTION", "알프라졸람 농도 증가", "용량 감량"),
    ("플루옥세틴", "할로페리돌", "CAUTION", "할로페리돌 농도 증가", "모니터링"),
    ("설트랄린", "알코올", "CAUTION", "중추신경억제 증가", "음주 피할 것"),
    ("파록세틴", "트라마돌", "DANGER", "세로토닌 증후군", "동시 복용 금지"),
    ("파록세틴", "알코올", "CAUTION", "부작용 증가", "음주 피할 것"),
    ("벤라팍신", "트라마돌", "DANGER", "세로토닌 증후군", "동시 복용 금지"),
    ("벤라팍신", "알코올", "CAUTION", "부작용 증가", "음주 피할 것"),
    ("미르타자핀", "알코올", "CAUTION", "진정 효과 증가", "음주 피할 것"),
    ("미르타자핀", "트라마돌", "DANGER", "세로토닌 증후군", "동시 복용 금지"),
    ("아미트리프틸린", "트라마돌", "DANGER", "세로토닌 증후군 및 발작", "동시 복용 금지"),
    ("카르바마제핀", "와파린", "CAUTION", "와파린 대사 증가", "INR 모니터링"),
    ("카르바마제핀", "알코올", "CAUTION", "중추신경억제 증가", "음주 피할 것"),
    ("발프로산", "알코올", "CAUTION", "간독성 및 진정 증가", "음주 피할 것"),
    ("라모트리진", "알코올", "CAUTION", "중추신경억제 증가", "음주 피할 것"),
    ("메틸페니데이트", "할로페리돌", "CAUTION", "운동장애 위험", "모니터링 필요"),
    ("트라마돌", "에스시탈로프람", "DANGER", "세로토닌 증후군", "동시 복용 금지"),
    ("트라마돌", "설트랄린", "DANGER", "세로토닌 증후군", "동시 복용 금지"),
    ("트라마돌", "벤라팍신", "DANGER", "세로토닌 증후군", "동시 복용 금지"),
    ("모르핀", "로라제팜", "DANGER", "호흡억제", "동시 복용 금지"),
    ("모르핀", "디아제팜", "DANGER", "호흡억제", "동시 복용 금지"),
    ("모르핀", "클로나제팜", "DANGER", "호흡억제", "동시 복용 금지"),
    ("옥시코돈", "로라제팜", "DANGER", "호흡억제", "동시 복용 금지"),
    ("옥시코돈", "디아제팜", "DANGER", "호흡억제", "동시 복용 금지"),
    ("옥시코돈", "클로나제팜", "DANGER", "호흡억제", "동시 복용 금지"),
]


async def seed_psychiatric_data():
    """정신과 약물 데이터를 Neo4j에 삽입."""
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "dodaktalk1234")

    driver = AsyncGraphDatabase.driver(uri, auth=(user, password))
    logger.info("Neo4j 연결: %s", uri)

    try:
        async with driver.session() as session:
            # 스키마/인덱스 생성
            logger.info("인덱스 생성 중...")
            await session.run("CREATE INDEX drug_name IF NOT EXISTS FOR (d:Drug) ON (d.name)")
            await session.run("CREATE INDEX drug_generic IF NOT EXISTS FOR (d:Drug) ON (d.generic_name)")
            await session.run("CREATE INDEX component_name IF NOT EXISTS FOR (c:Component) ON (c.name)")

            # 약물 노드 생성
            logger.info("약물 노드 생성 중... (%d개)", len(PSYCHIATRIC_DRUGS))
            for drug in PSYCHIATRIC_DRUGS:
                await session.run(
                    """
                    MERGE (d:Drug {name: $name})
                    SET d.generic_name = $generic, d.category = $category
                    MERGE (c:Component {name: $name, generic_name: $generic, category: $category})
                    MERGE (d)-[:HAS_COMPONENT]->(c)
                    """,
                    name=drug["name"],
                    generic=drug["generic"],
                    category=drug["category"],
                )
            logger.info("약물 노드 생성 완료")

            # 상호작용 관계 생성
            logger.info("상호작용 관계 생성 중... (%d개)", len(INTERACTIONS))
            created = 0
            for drug_a, drug_b, severity, description, recommendation in INTERACTIONS:
                result = await session.run(
                    """
                    MATCH (a:Component {name: $drug_a})
                    MATCH (b:Component {name: $drug_b})
                    MERGE (a)-[r:INTERACTS_WITH]->(b)
                    SET r.severity = $severity,
                        r.description = $description,
                        r.recommendation = $recommendation
                    RETURN count(r) AS cnt
                    """,
                    drug_a=drug_a,
                    drug_b=drug_b,
                    severity=severity,
                    description=description,
                    recommendation=recommendation,
                )
                record = await result.single()
                if record and record["cnt"] > 0:
                    created += 1

            logger.info("상호작용 관계 생성 완료: %d개", created)

            # 카테고리 노드 생성
            categories = set(d["category"] for d in PSYCHIATRIC_DRUGS)
            for cat in categories:
                await session.run(
                    """
                    MERGE (cat:Category {name: $cat})
                    WITH cat
                    MATCH (c:Component {category: $cat})
                    MERGE (c)-[:BELONGS_TO]->(cat)
                    """,
                    cat=cat,
                )
            logger.info("카테고리 노드 생성 완료: %d개", len(categories))

            # 통계 출력
            result = await session.run("MATCH (d:Drug) RETURN count(d) AS drug_count")
            drug_count = (await result.single())["drug_count"]

            result = await session.run("MATCH (c:Component) RETURN count(c) AS comp_count")
            comp_count = (await result.single())["comp_count"]

            result = await session.run("MATCH ()-[r:INTERACTS_WITH]->() RETURN count(r) AS rel_count")
            rel_count = (await result.single())["rel_count"]

            logger.info("=== 시드 완료 ===")
            logger.info("Drug 노드: %d", drug_count)
            logger.info("Component 노드: %d", comp_count)
            logger.info("INTERACTS_WITH 관계: %d", rel_count)

    finally:
        await driver.close()
        logger.info("Neo4j 연결 종료")


if __name__ == "__main__":
    asyncio.run(seed_psychiatric_data())
