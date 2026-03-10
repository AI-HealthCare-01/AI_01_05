"""ChromaDB 기반 RAG 서비스.

Design spec: chat-core.design.md §5.5
의학 가이드라인 PDF를 임베딩하여 벡터 검색 기반 컨텍스트를 제공한다.

Note: chromadb와 sentence-transformers가 설치되지 않은 환경에서도
      graceful degradation으로 빈 결과를 반환한다.
"""

import logging
import os

logger = logging.getLogger("dodaktalk.rag")

CHROMA_DIR = os.getenv("CHROMA_PERSIST_DIR", "data/embeddings")
EMBEDDING_MODEL = "jhgan/ko-sroberta-multitask"


class RAGService:
    """ChromaDB 벡터 검색 기반 RAG 서비스."""

    def __init__(self) -> None:
        self._available = False
        try:
            import chromadb
            from sentence_transformers import SentenceTransformer

            self._client = chromadb.PersistentClient(path=CHROMA_DIR)
            self._collection = self._client.get_or_create_collection("guidelines")
            self._embedder = SentenceTransformer(EMBEDDING_MODEL)
            self._available = True
            logger.info("RAG 서비스 초기화 완료 (ChromaDB: %s)", CHROMA_DIR)
        except ImportError:
            logger.warning("chromadb 또는 sentence-transformers 미설치. RAG 비활성화.")
        except Exception as e:
            logger.warning("RAG 서비스 초기화 실패: %s", e)

    @property
    def available(self) -> bool:
        return self._available

    async def search(self, query: str, n_results: int = 3) -> list[str]:
        """의학 가이드라인에서 관련 문맥을 검색합니다.

        Args:
            query: 검색 쿼리 (사용자 질문)
            n_results: 반환할 결과 수

        Returns:
            관련 텍스트 청크 리스트. 비활성 또는 실패 시 빈 리스트.
        """
        if not self._available:
            return []

        try:
            query_embedding = self._embedder.encode(query).tolist()
            results = self._collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
            )
            documents = results.get("documents", [[]])
            return documents[0] if documents else []
        except Exception as e:
            logger.warning("RAG 검색 실패: %s", e)
            return []

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
                # PyPDF2 or pdfplumber로 텍스트 추출
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
