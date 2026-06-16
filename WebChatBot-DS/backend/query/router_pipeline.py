"""
Pipeline router tích hợp hai nhánh:
1. RAG (MedicalQueryPipeline) - cho câu hỏi về kiến thức y tế
2. Database Search (StorePipeline) - cho câu hỏi về kho hàng, giá cả, tồn kho
"""
from typing import Union
from .router import Router
from .medical_query_pipeline import MedicalQueryPipeline
from .store.store_pipeline import StorePipeline
from .core import FinalAnswer

import logging

logger = logging.getLogger(__name__)


class RouterPipeline:
    """
    Pipeline chính sử dụng Router để quyết định nhánh xử lý:
    - medical_knowledge -> MedicalQueryPipeline (RAG)
    - store_database -> StorePipeline (Database Search)
    """
    
    def __init__(self, max_retries: int = 2):
        """
        Khởi tạo router pipeline.
        
        Args:
            max_retries: Số lần thử tối đa cho Final Answer evaluation
        """
        self.router = Router()
        self.medical_pipeline = MedicalQueryPipeline(max_retries=max_retries)
        
        # Khởi tạo StorePipeline với xử lý lỗi
        try:
            self.store_pipeline = StorePipeline()
            self.store_pipeline_available = True
            logger.info("StorePipeline initialized successfully")
        except Exception as e:
            logger.warning(f"Không thể khởi tạo StorePipeline: {e}")
            logger.warning("Hệ thống sẽ chỉ sử dụng RAG pipeline. Vui lòng tạo database bằng cách chạy:")
            logger.warning("  cd sqlite-db/src && python main.py")
            self.store_pipeline = None
            self.store_pipeline_available = False
        
        logger.info("RouterPipeline initialized")
    
    def process_query(self, user_query: str) -> Union[FinalAnswer, dict]:
        """
        Xử lý câu hỏi người dùng bằng cách routing đến pipeline phù hợp.
        
        Args:
            user_query: Câu hỏi từ người dùng
            
        Returns:
            FinalAnswer: Nếu route đến medical_knowledge (RAG)
            dict: Nếu route đến store_database (Database search)
                - text: str - Câu trả lời
                - is_image: bool - Có phải hình ảnh không
                - image: Optional - Hình ảnh nếu có
        """
        logger.info(f"Processing query: {user_query}")
        
        # Bước 1: Router quyết định nhánh
        route_result = self.router.route(user_query)
        logger.info(f"Routed to: {route_result.datasource} - {route_result.reasoning}")
        
        # Bước 2: Xử lý theo nhánh được chọn
        if route_result.datasource == "medical_knowledge":
            # Nhánh RAG - xử lý câu hỏi y tế
            logger.info("Using MedicalQueryPipeline (RAG)")
            result = self.medical_pipeline.process_query(user_query)
            return result
        
        elif route_result.datasource == "store_database":
            # Nhánh Database Search - xử lý câu hỏi về kho hàng
            if not self.store_pipeline_available:
                logger.warning("StorePipeline không khả dụng, fallback sang RAG")
                result = self.medical_pipeline.process_query(user_query)
                return result
            
            logger.info("Using StorePipeline (Database Search)")
            try:
                result = self.store_pipeline.query(user_query)
                return result
            except Exception as e:
                logger.error(f"Lỗi khi query database: {e}")
                logger.info("Fallback sang RAG pipeline")
                result = self.medical_pipeline.process_query(user_query)
                return result
        
        else:
            # Fallback: mặc định dùng RAG
            logger.warning(f"Unknown datasource: {route_result.datasource}, falling back to RAG")
            result = self.medical_pipeline.process_query(user_query)
            return result
    
    def process_query_unified(self, user_query: str) -> dict:
        """
        Xử lý câu hỏi và trả về format thống nhất.
        
        Args:
            user_query: Câu hỏi từ người dùng
            
        Returns:
            dict: Kết quả thống nhất với format:
                - answer: str - Câu trả lời
                - sources: list[str] - Danh sách nguồn
                - confidence: float - Độ tin cậy (0.0-1.0)
                - is_image: bool - Có phải hình ảnh không (mặc định False)
                - image: Optional - Hình ảnh nếu có (mặc định None)
                - steps: list[str] - Danh sách các bước xử lý
        """
        steps = []
        
        # Bước 1: Router phân loại
        route_result = self.router.route(user_query)
        steps.append(f"1. Router: Phan loai cau hoi -> {route_result.datasource}")
        steps.append(f"   Ly do: {route_result.reasoning}")
        
        result = self.process_query(user_query)
        
        # Nếu là FinalAnswer (từ RAG)
        if isinstance(result, FinalAnswer):
            # Lấy steps từ result nếu có
            if hasattr(result, 'steps') and result.steps:
                steps.extend(result.steps)
            return {
                "answer": result.answer,
                "sources": result.sources,
                "confidence": result.confidence,
                "is_image": False,
                "image": None,
                "steps": steps
            }
        
        # Nếu là dict (từ StorePipeline)
        elif isinstance(result, dict):
            # Lấy steps từ result nếu có
            if "steps" in result:
                steps.extend(result["steps"])
            return {
                "answer": result.get("text", ""),
                "sources": ["Database"],
                "confidence": 0.9 if result.get("is_image", False) else 0.85,
                "is_image": result.get("is_image", False),
                "image": result.get("image", None),
                "steps": steps
            }
        
        # Fallback
        else:
            return {
                "answer": "Xin lỗi, không thể xử lý câu hỏi của bạn.",
                "sources": [],
                "confidence": 0.0,
                "is_image": False,
                "image": None,
                "steps": steps
            }

