"""FAISS 기반 의약품/질병/DUR 검색 서비스."""
import logging
import os
import pickle
from dataclasses import dataclass

logger = logging.getLogger("dodaktalk.faiss")

FAISS_DIR = os.getenv("FAISS_DATA_DIR", "data/faiss")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
EMBEDDING_MODEL = "text-embedding-ada-002"


@dataclass
class SearchResult:
    text: str
    metadata: dict
    score: float


class FAISSService:
    def __init__(self) -> None:
        self._available = False
        self._indexes = {}
        self._sentences = {}
        self._metadata = {}
        self._adverse_lookup = {}

        try:
            import faiss
            from openai import OpenAI

            self._faiss = faiss
            self._openai = OpenAI(api_key=OPENAI_API_KEY)

            index_configs = [
                ("disease", "disease.index", "disease_meta.pkl"),
                ("drug_info", "drug_info.index", "drug_info_meta.pkl"),
                ("safety", "safety.index", "safety_meta.pkl"),
            ]

            loaded = []
            for name, index_file, meta_file in index_configs:
                index_path = os.path.join(FAISS_DIR, index_file)
                meta_path = os.path.join(FAISS_DIR, meta_file)

                if not os.path.exists(index_path) or not os.path.exists(meta_path):
                    logger.warning("FAISS 파일 없음: %s 또는 %s", index_path, meta_path)
                    continue

                self._indexes[name] = faiss.read_index(index_path)
                with open(meta_path, "rb") as f:
                    meta = pickle.load(f)
                self._sentences[name] = meta["sentences"]
                self._metadata[name] = meta["metadata"]
                loaded.append(name)
                logger.info("FAISS 인덱스 로드 완료: %s (%d개)", name, len(meta["sentences"]))

            adverse_path = os.path.join(FAISS_DIR, "adverse_lookup.pkl")
            if os.path.exists(adverse_path):
                with open(adverse_path, "rb") as f:
                    self._adverse_lookup = pickle.load(f)
                logger.info("성분 룩업 로드 완료: %d개", len(self._adverse_lookup))

            if loaded:
                self._available = True
                logger.info("FAISS 서비스 초기화 완료: %s", loaded)
            else:
                logger.warning("로드된 FAISS 인덱스 없음. FAISS 서비스 비활성화.")

        except ImportError as e:
            logger.warning("faiss-cpu 또는 openai 미설치. FAISS 서비스 비활성화: %s", e)
        except Exception as e:
            logger.warning("FAISS 서비스 초기화 실패: %s", e)

    @property
    def available(self) -> bool:
        return self._available

    def _embed(self, text: str) -> list[float]:
        response = self._openai.embeddings.create(
            input=text,
            model=EMBEDDING_MODEL,
        )
        return response.data[0].embedding

    def _search_index(self, index_name: str, query: str, n_results: int = 3) -> list[SearchResult]:
        if index_name not in self._indexes:
            return []

        import numpy as np

        query_vector = np.array([self._embed(query)], dtype="float32")
        scores, indices = self._indexes[index_name].search(query_vector, n_results)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:
                continue
            results.append(
                SearchResult(
                    text=self._sentences[index_name][idx],
                    metadata=self._metadata[index_name][idx],
                    score=float(score),
                )
            )
        return results

    async def search_drug(self, query: str, n_results: int = 3) -> list[SearchResult]:
        if not self._available:
            return []
        try:
            return self._search_index("drug_info", query, n_results)
        except Exception as e:
            logger.warning("약물 검색 실패: %s", e)
            return []

    async def search_disease(self, query: str, n_results: int = 3) -> list[SearchResult]:
        if not self._available:
            return []
        try:
            return self._search_index("disease", query, n_results)
        except Exception as e:
            logger.warning("질병 검색 실패: %s", e)
            return []

    async def search_safety(self, query: str, n_results: int = 3) -> list[SearchResult]:
        if not self._available:
            return []
        try:
            return self._search_index("safety", query, n_results)
        except Exception as e:
            logger.warning("DUR 검색 실패: %s", e)
            return []

    async def search_all(self, query: str, n_results: int = 3) -> dict[str, list[SearchResult]]:
        if not self._available:
            return {"drug": [], "disease": [], "safety": []}
        return {
            "drug": await self.search_drug(query, n_results),
            "disease": await self.search_disease(query, n_results),
            "safety": await self.search_safety(query, n_results),
        }

    def lookup_ingredient(self, name: str) -> dict | None:
        return self._adverse_lookup.get(name)

    def format_results_for_gpt(self, results: dict[str, list[SearchResult]]) -> str:
        lines = []

        if results.get("safety"):
            lines.append("=== DUR 병용금기 정보 ===")
            for r in results["safety"]:
                lines.append(f"- {r.text}")

        if results.get("drug"):
            lines.append("\n=== 약물 정보 ===")
            for r in results["drug"]:
                lines.append(f"- {r.text}")

        if results.get("disease"):
            lines.append("\n=== 질병 정보 ===")
            for r in results["disease"]:
                lines.append(f"- {r.text}")

        return "\n".join(lines) if lines else ""


# faiss_service = FAISSService()  # drug_agent.py로 대체
