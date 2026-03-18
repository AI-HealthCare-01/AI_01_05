"""ChromaDB 기반 RAG 서비스 (HyDE + Cross-Encoder Re-ranking).

Design spec: chat-core.design.md §5.5
의학 가이드라인 PDF를 임베딩하여 벡터 검색 기반 컨텍스트를 제공한다.
DUR 안전정보 컬렉션(dur_safety)도 지원한다.

Pipeline (v2):
Query → HyDE 가설 생성 → Vector Search Top-20 → Cross-Encoder Re-ranking → Top-5

Note: chromadb와 sentence-transformers가 설치되지 않은 환경에서도
      graceful degradation으로 빈 결과를 반환한다.
"""

from __future__ import annotations

import hashlib
import logging
import os
from abc import ABC, abstractmethod

logger = logging.getLogger("dodaktalk.rag")

CHROMA_DIR = os.getenv("CHROMA_PERSIST_DIR", "data/embeddings")
EMBEDDING_MODEL = "jhgan/ko-sroberta-multitask"

# 파이프라인 설정
HYDE_ENABLED = os.getenv("RAG_HYDE_ENABLED", "true").lower() == "true"
RERANK_ENABLED = os.getenv("RAG_RERANK_ENABLED", "true").lower() == "true"
VECTOR_SEARCH_TOP_K = 20  # 벡터 검색 후보 수
FINAL_TOP_K = 5  # 최종 반환 수


# ── 추상 인터페이스 ────────────────────────────────────────────
class VectorSearchTool(ABC):
    """벡터 검색 도구 추상 인터페이스.

    ChromaDB, FAISS 등 다양한 백엔드를 교체 가능하게 함.
    """

    @abstractmethod
    async def search(self, query: str, top_k: int) -> list[str]:
        """벡터 검색을 수행합니다.

        Args:
            query: 검색 쿼리 (임베딩할 텍스트)
            top_k: 반환할 결과 수

        Returns:
            관련 텍스트 청크 리스트
        """
        raise NotImplementedError

    @abstractmethod
    def embed(self, text: str) -> list[float]:
        """텍스트를 임베딩 벡터로 변환."""
        raise NotImplementedError


class ChromaDBSearchTool(VectorSearchTool):
    """ChromaDB 기반 벡터 검색 도구."""

    def __init__(self, client, collection, embedder) -> None:
        self._client = client
        self._collection = collection
        self._embedder = embedder

    async def search(self, query: str, top_k: int) -> list[str]:
        """ChromaDB에서 벡터 검색."""
        try:
            if self._collection.count() == 0:
                return []
            query_embedding = self._embedder.encode(query).tolist()
            results = self._collection.query(
                query_embeddings=[query_embedding],
                n_results=min(top_k, self._collection.count()),
            )
            documents = results.get("documents", [[]])
            return documents[0] if documents else []
        except Exception as e:
            logger.warning("ChromaDB 검색 실패: %s", e)
            return []

    def embed(self, text: str) -> list[float]:
        """텍스트 임베딩."""
        return self._embedder.encode(text).tolist()


# ── RAG 서비스 ─────────────────────────────────────────────────
class RAGService:
    """ChromaDB 벡터 검색 기반 RAG 서비스 (HyDE + Re-ranking)."""

    def __init__(self) -> None:
        self._available = False
        self._chromadb = None
        self._search_tool: VectorSearchTool | None = None

        try:
            import chromadb
            from sentence_transformers import SentenceTransformer

            self._chromadb = chromadb
            self._client = chromadb.PersistentClient(path=CHROMA_DIR)
            self._collection = self._client.get_or_create_collection("guidelines")
            self._embedder = SentenceTransformer(EMBEDDING_MODEL)

            # VectorSearchTool 인터페이스 구현
            self._search_tool = ChromaDBSearchTool(self._client, self._collection, self._embedder)

            self._available = True
            logger.info(
                "RAG 서비스 초기화 완료 (ChromaDB: %s, HyDE=%s, Rerank=%s)",
                CHROMA_DIR,
                HYDE_ENABLED,
                RERANK_ENABLED,
            )
        except ImportError:
            logger.warning("chromadb 또는 sentence-transformers 미설치. RAG 비활성화.")
        except Exception as e:
            logger.warning("RAG 서비스 초기화 실패: %s", e)

    @property
    def available(self) -> bool:
        return self._available

    def _get_collection(self, collection: str):
        """컬렉션 이름으로 ChromaDB 컬렉션 객체 반환."""
        if collection == "guidelines":
            return self._collection
        return self._client.get_or_create_collection(collection)

    async def _apply_hyde(self, query: str) -> str:
        """HyDE 가설 생성 적용."""
        if not HYDE_ENABLED:
            return query
        try:
            from app.services.hyde_service import get_hyde_service

            hyde = get_hyde_service()
            if hyde.available:
                hypothesis = await hyde.generate_hypothesis(query)
                if hypothesis and hypothesis != query:
                    logger.debug("HyDE 적용: %s... → %s...", query[:30], hypothesis[:30])
                    return hypothesis
        except Exception as e:
            logger.warning("HyDE 실패, 원본 질문 사용: %s", e)
        return query

    async def _apply_reranking(self, query: str, candidates: list[str], n_results: int) -> list[str]:
        """Cross-Encoder Re-ranking 적용."""
        if not RERANK_ENABLED or len(candidates) <= n_results:
            return candidates[:n_results]
        try:
            from app.services.reranker_service import get_reranker_service

            reranker = get_reranker_service()
            if reranker.available:
                reranked = await reranker.rerank(query, candidates, top_k=n_results)
                logger.debug("Re-ranking 적용: %d → %d", len(candidates), len(reranked))
                return reranked
        except Exception as e:
            logger.warning("Re-ranking 실패, 벡터 검색 결과 반환: %s", e)
        return candidates[:n_results]

    async def search(
        self,
        query: str,
        n_results: int = 5,
        collection: str = "guidelines",
    ) -> list[str]:
        """HyDE + Re-ranking 파이프라인으로 벡터 검색."""
        if not self._available:
            return []

        try:
            coll = self._get_collection(collection)
            if coll.count() == 0:
                return []

            search_query = await self._apply_hyde(query)

            vector_top_k = VECTOR_SEARCH_TOP_K if RERANK_ENABLED else n_results
            query_embedding = self._embedder.encode(search_query).tolist()
            results = coll.query(
                query_embeddings=[query_embedding],
                n_results=min(vector_top_k, coll.count()),
            )
            candidates = results.get("documents", [[]])[0] if results.get("documents") else []

            if not candidates:
                return []

            return await self._apply_reranking(query, candidates, n_results)

        except Exception as e:
            logger.warning("RAG 검색 실패 (collection=%s): %s", collection, e)
            return []

    async def search_simple(
        self,
        query: str,
        n_results: int = 3,
        collection: str = "guidelines",
    ) -> list[str]:
        """단순 벡터 검색 (HyDE/Re-ranking 미적용).

        빠른 검색이 필요하거나 파이프라인 비교용.
        """
        if not self._available:
            return []

        try:
            coll = self._get_collection(collection)
            if coll.count() == 0:
                return []
            query_embedding = self._embedder.encode(query).tolist()
            results = coll.query(
                query_embeddings=[query_embedding],
                n_results=min(n_results, coll.count()),
            )
            documents = results.get("documents", [[]])
            return documents[0] if documents else []
        except Exception as e:
            logger.warning("단순 RAG 검색 실패 (collection=%s): %s", collection, e)
            return []

    def ingest_text(
        self,
        text: str,
        source: str,
        collection: str = "guidelines",
        metadata: dict | None = None,
    ) -> int:
        """텍스트를 청크 분할하여 ChromaDB에 저장합니다.

        Args:
            text: 임베딩할 텍스트
            source: 출처 식별자
            collection: 저장할 컬렉션 이름
            metadata: 각 청크에 첨부할 메타데이터

        Returns:
            저장된 청크 수. 비활성 시 0.
        """
        if not self._available:
            logger.warning("RAG 비활성 상태. 텍스트 수집 불가.")
            return 0

        try:
            from langchain_text_splitters import RecursiveCharacterTextSplitter

            splitter = RecursiveCharacterTextSplitter(
                chunk_size=500,
                chunk_overlap=50,
            )
            chunks = splitter.split_text(text)

            if not chunks:
                return 0

            coll = self._get_collection(collection)
            embeddings = self._embedder.encode(chunks).tolist()
            base_meta = {"source": source, **(metadata or {})}
            ids = [hashlib.md5(f"{source}_{i}_{c[:50]}".encode()).hexdigest() for i, c in enumerate(chunks)]
            metadatas = [base_meta for _ in chunks]

            coll.upsert(
                documents=chunks,
                embeddings=embeddings,
                metadatas=metadatas,
                ids=ids,
            )

            logger.info("텍스트 수집 완료: %s (%d 청크, collection=%s)", source, len(chunks), collection)
            return len(chunks)
        except Exception as e:
            logger.warning("텍스트 수집 실패 (%s): %s", source, e)
            return 0

    def ingest_pdf(self, pdf_path: str) -> int:
        """PDF를 청크 분할하여 ChromaDB에 저장합니다.

        Args:
            pdf_path: PDF 파일 경로

        Returns:
            저장된 청크 수. 비활성 시 0.
        """
        if not self._available:
            logger.warning("RAG 비활성 상태. PDF 수집 불가.")
            return 0

        try:
            from langchain_text_splitters import RecursiveCharacterTextSplitter

            with open(pdf_path, "rb") as f:
                try:
                    import pdfplumber

                    pdf = pdfplumber.open(f)
                    text = "\n".join(page.extract_text() or "" for page in pdf.pages)
                    pdf.close()
                except ImportError:
                    logger.warning("pdfplumber 미설치. PDF 수집 불가.")
                    return 0

            splitter = RecursiveCharacterTextSplitter(
                chunk_size=500,
                chunk_overlap=50,
            )
            chunks = splitter.split_text(text)

            if not chunks:
                return 0

            embeddings = self._embedder.encode(chunks).tolist()
            ids = [f"{pdf_path}_{i}" for i in range(len(chunks))]

            self._collection.add(
                documents=chunks,
                embeddings=embeddings,
                ids=ids,
            )

            logger.info("PDF 수집 완료: %s (%d 청크)", pdf_path, len(chunks))
            return len(chunks)
        except Exception as e:
            logger.warning("PDF 수집 실패 (%s): %s", pdf_path, e)
            return 0
