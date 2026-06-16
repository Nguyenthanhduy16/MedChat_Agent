import numpy as np
from qdrant_client import models
from qdrant_client.http.models import ScoredPoint
from qdrant_client.http.exceptions import UnexpectedResponse
from ..core import get_rag_client
import logging

logger = logging.getLogger(__name__)

class MedicalRAG:
    def __init__(self, embedder):
        self.rag_client = get_rag_client()
        self.collection_name = "embedding_data"
        # self.model_name = cfg.RAG_EMBEDDING_MODEL_NAME
        self.model = embedder
        self.limit = 5
        self._check_collection_exists()
        
    def _check_collection_exists(self):
        """Kiểm tra xem collection có tồn tại không."""
        try:
            collections = self.rag_client.get_collections()
            collection_names = [col.name for col in collections.collections]
            if self.collection_name not in collection_names:
                logger.warning(
                    f"Collection '{self.collection_name}' không tồn tại trong Qdrant. "
                    f"Các collection có sẵn: {collection_names}. "
                    "Hệ thống sẽ fallback sang web search khi RAG không khả dụng."
                )
        except Exception as e:
            logger.warning(f"Không thể kiểm tra collections: {e}. Hệ thống sẽ fallback sang web search.")
        
    def query(self, query: str):
        """
        Query RAG database.
        
        Returns:
            List[ScoredPoint]: Danh sách kết quả tìm kiếm, hoặc empty list nếu có lỗi
        """
        try:
            embeddings = self.model.encode([query], convert_to_numpy=True).tolist()[0]
            hits = self.rag_client.search(
                collection_name=self.collection_name,
                query_vector=embeddings,
                limit=self.limit
            )
            return hits
        except UnexpectedResponse as e:
            if "doesn't exist" in str(e) or "404" in str(e):
                logger.warning(
                    f"Collection '{self.collection_name}' không tồn tại. "
                    "Vui lòng tạo collection hoặc cập nhật dữ liệu RAG."
                )
            else:
                logger.error(f"Lỗi khi query RAG: {e}")
            return []
        except Exception as e:
            logger.error(f"Lỗi không mong đợi khi query RAG: {e}")
            return []
