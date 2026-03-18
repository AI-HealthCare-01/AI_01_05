"""Neo4j 지식그래프 서비스.
약물-성분-상호작용-부작용 관계를 그래프로 저장하고 조회한다.
"""
from __future__ import annotations

import logging
import os

from neo4j import AsyncGraphDatabase

logger = logging.getLogger("dodaktalk.graph")


class GraphService:
    def __init__(self) -> None:
        uri = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
        user = os.getenv("NEO4J_USER", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "dodaktalk1234")
        self._driver = AsyncGraphDatabase.driver(uri, auth=(user, password))
        logger.info("Neo4j 연결 완료: %s", uri)

    async def close(self) -> None:
        await self._driver.close()

    async def init_schema(self) -> None:
        """기본 약물 지식그래프 스키마 초기화."""
        async with self._driver.session() as session:
            # 인덱스 생성
            await session.run("CREATE INDEX drug_name IF NOT EXISTS FOR (d:Drug) ON (d.name)")
            await session.run("CREATE INDEX component_name IF NOT EXISTS FOR (c:Component) ON (c.name)")
            logger.info("Neo4j 스키마 초기화 완료")

    async def seed_drug_data(self) -> None:
        """기본 약물 데이터 삽입."""
        async with self._driver.session() as session:
            # 약물 노드 생성
            await session.run("""
                MERGE (d:Drug {name: '타이레놀'})
                SET d.generic_name = '아세트아미노펜', d.category = '해열진통제'
                MERGE (c:Component {name: '아세트아미노펜', category: '해열진통제'})
                MERGE (d)-[:HAS_COMPONENT]->(c)
            """)
            await session.run("""
                MERGE (d:Drug {name: '탁센연질캡슐'})
                SET d.generic_name = '나프록센', d.category = 'NSAID'
                MERGE (c:Component {name: '나프록센', category: 'NSAID'})
                MERGE (d)-[:HAS_COMPONENT]->(c)
            """)
            await session.run("""
                MERGE (d:Drug {name: '탁센400이부프로펜연질캡슐'})
                SET d.generic_name = '이부프로펜', d.category = 'NSAID'
                MERGE (c:Component {name: '이부프로펜', category: 'NSAID'})
                MERGE (d)-[:HAS_COMPONENT]->(c)
            """)
            # NSAID 카테고리 관계
            await session.run("""
                MERGE (cat:Category {name: 'NSAID'})
                WITH cat
                MATCH (c:Component) WHERE c.category = 'NSAID'
                MERGE (c)-[:BELONGS_TO]->(cat)
            """)
            # 상호작용 관계
            await session.run("""
                MATCH (a:Component {name: '나프록센'})
                MATCH (b:Component {name: '이부프로펜'})
                MERGE (a)-[:INTERACTS_WITH {
                    severity: 'DANGER',
                    description: '두 NSAID 계열 약물 동시 복용 시 위장출혈, 신장 손상 위험 증가',
                    recommendation: '동시 복용 금지'
                }]->(b)
            """)
            await session.run("""
                MATCH (a:Component {name: '아세트아미노펜'})
                MATCH (b:Component {name: '나프록센'})
                MERGE (a)-[:INTERACTS_WITH {
                    severity: 'CAUTION',
                    description: '함께 복용 가능하나 각각의 최대 용량을 초과하지 않도록 주의',
                    recommendation: '용량 준수 필요'
                }]->(b)
            """)
            logger.info("기본 약물 데이터 삽입 완료")

    async def get_drug_interactions(self, drug_names: list[str]) -> str:
        """복용 중인 약물들의 상호작용 정보를 조회한다."""
        if not drug_names:
            return ""
        async with self._driver.session() as session:
            result = await session.run("""
                MATCH (d:Drug)-[:HAS_COMPONENT]->(c:Component)
                WHERE d.name IN $drug_names OR any(name IN $drug_names WHERE d.name CONTAINS name)
                WITH collect(c.name) AS components
                MATCH (a:Component)-[r:INTERACTS_WITH]->(b:Component)
                WHERE a.name IN components AND b.name IN components
                RETURN a.name AS drug_a, b.name AS drug_b,
                       r.severity AS severity, r.description AS description,
                       r.recommendation AS recommendation
            """, drug_names=drug_names)
            records = await result.data()
            if not records:
                return ""
            lines = ["[약물 상호작용 정보]"]
            for r in records:
                severity_label = "⚠️ 위험" if r["severity"] == "DANGER" else "⚡ 주의"
                lines.append(
                    f"{severity_label}: {r['drug_a']} + {r['drug_b']} - {r['description']} ({r['recommendation']})"
                )
            return "\n".join(lines)

    async def search_drug_by_name(self, name: str) -> dict | None:
        """약물명으로 약물 정보 조회."""
        async with self._driver.session() as session:
            result = await session.run("""
                MATCH (d:Drug)-[:HAS_COMPONENT]->(c:Component)
                WHERE d.name CONTAINS $name
                RETURN d.name AS name, d.category AS category,
                       collect(c.name) AS components
                LIMIT 1
            """, name=name)
            record = await result.single()
            if not record:
                return None
            return dict(record)

    async def check_drug_combination(self, drugs: list[str]) -> dict:
        """사용자 복용약 목록 전체 교차 검사.

        Args:
            drugs: 약물명 목록

        Returns:
            {
                "has_danger": bool,    # DANGER 관계 발견 시 True → red_alert
                "has_caution": bool,   # CAUTION 관계 발견 시 True
                "interactions": [...]  # 발견된 상호작용 목록
            }
        """
        if not drugs or len(drugs) < 1:
            return {"has_danger": False, "has_caution": False, "interactions": []}

        async with self._driver.session() as session:
            # 약물명에서 성분 추출 후 상호작용 검색
            # 한글/영문 모두 검색 (name, generic_name)
            result = await session.run(
                """
                MATCH (d:Drug)-[:HAS_COMPONENT]->(c:Component)
                WHERE any(drug IN $drugs WHERE
                    d.name CONTAINS drug OR
                    d.generic_name CONTAINS drug OR
                    c.name CONTAINS drug OR
                    c.generic_name CONTAINS drug
                )
                WITH collect(DISTINCT c.name) AS components
                MATCH (a:Component)-[r:INTERACTS_WITH]->(b:Component)
                WHERE a.name IN components AND b.name IN components
                RETURN DISTINCT
                    a.name AS drug_a,
                    b.name AS drug_b,
                    r.severity AS severity,
                    r.description AS description,
                    r.recommendation AS recommendation
                """,
                drugs=drugs,
            )
            records = await result.data()

            has_danger = False
            has_caution = False
            interactions = []

            for r in records:
                severity = r["severity"]
                if severity == "DANGER":
                    has_danger = True
                elif severity == "CAUTION":
                    has_caution = True

                interactions.append({
                    "drug_a": r["drug_a"],
                    "drug_b": r["drug_b"],
                    "severity": severity,
                    "description": r["description"],
                    "recommendation": r["recommendation"],
                })

            return {
                "has_danger": has_danger,
                "has_caution": has_caution,
                "interactions": interactions,
            }

    async def search_interaction(self, query_drug: str, user_drugs: list[str]) -> dict:
        """질문 약물과 사용자 복용약 간 상호작용 검사.

        Args:
            query_drug: 질문에 언급된 약물 (예: "졸피뎀", "술")
            user_drugs: 사용자 복용 중인 약물 목록

        Returns:
            {
                "has_danger": bool,
                "has_caution": bool,
                "interactions": [...]
            }
        """
        async with self._driver.session() as session:
            # 질문 약물의 성분 찾기
            result = await session.run(
                """
                MATCH (d:Drug)-[:HAS_COMPONENT]->(c:Component)
                WHERE d.name CONTAINS $query OR
                      d.generic_name CONTAINS $query OR
                      c.name CONTAINS $query OR
                      c.generic_name CONTAINS $query
                RETURN collect(DISTINCT c.name) AS query_components
                """,
                query=query_drug,
            )
            query_record = await result.single()
            query_components = query_record["query_components"] if query_record else []

            # 사용자 약물의 성분 찾기
            result = await session.run(
                """
                MATCH (d:Drug)-[:HAS_COMPONENT]->(c:Component)
                WHERE any(drug IN $drugs WHERE
                    d.name CONTAINS drug OR
                    d.generic_name CONTAINS drug OR
                    c.name CONTAINS drug OR
                    c.generic_name CONTAINS drug
                )
                RETURN collect(DISTINCT c.name) AS user_components
                """,
                drugs=user_drugs,
            )
            user_record = await result.single()
            user_components = user_record["user_components"] if user_record else []

            # 질문 약물과 사용자 약물 간 상호작용 검색
            if not query_components and not user_components:
                return {"has_danger": False, "has_caution": False, "interactions": []}

            result = await session.run(
                """
                MATCH (a:Component)-[r:INTERACTS_WITH]->(b:Component)
                WHERE (a.name IN $query_comps AND b.name IN $user_comps)
                   OR (a.name IN $user_comps AND b.name IN $query_comps)
                RETURN DISTINCT
                    a.name AS drug_a,
                    b.name AS drug_b,
                    r.severity AS severity,
                    r.description AS description,
                    r.recommendation AS recommendation
                """,
                query_comps=query_components,
                user_comps=user_components,
            )
            records = await result.data()

            has_danger = False
            has_caution = False
            interactions = []

            for r in records:
                severity = r["severity"]
                if severity == "DANGER":
                    has_danger = True
                elif severity == "CAUTION":
                    has_caution = True

                interactions.append({
                    "drug_a": r["drug_a"],
                    "drug_b": r["drug_b"],
                    "severity": severity,
                    "description": r["description"],
                    "recommendation": r["recommendation"],
                })

            return {
                "has_danger": has_danger,
                "has_caution": has_caution,
                "interactions": interactions,
            }

    async def format_interaction_result(self, result: dict) -> str:
        """상호작용 검색 결과를 텍스트로 포맷팅."""
        if not result["interactions"]:
            return ""

        lines = ["[Neo4j 약물 상호작용 검색 결과]"]

        if result["has_danger"]:
            lines.append("!! DANGER 상호작용 발견 - red_alert=True 권고 !!")

        for interaction in result["interactions"]:
            severity = interaction["severity"]
            emoji = "🚨" if severity == "DANGER" else "⚠️"
            lines.append(
                f"{emoji} [{severity}] {interaction['drug_a']} + {interaction['drug_b']}: "
                f"{interaction['description']} ({interaction['recommendation']})"
            )

        return "\n".join(lines)


_graph_service: GraphService | None = None


async def get_graph_service() -> GraphService:
    global _graph_service
    if _graph_service is None:
        _graph_service = GraphService()
        await _graph_service.init_schema()
        await _graph_service.seed_drug_data()
    return _graph_service
