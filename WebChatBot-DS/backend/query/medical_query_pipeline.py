"""
Pipeline tích hợp hoàn chỉnh cho nhánh RAG.
Luồng: User Query -> Split Query -> K Queries -> RAG + Answer -> Eval Answer 
-> (loop back nếu try < M) hoặc (Web search nếu try >= M hoặc not satisfied) -> Final Answer

Đã bỏ bước Summary - đưa thẳng các answers vào Final Answer.
"""
from typing import Optional, List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from .split_query import SplitQueryHandler
from .medical.medical_pipeline import MedicalPipeline
from .medical.medical_search import MedicalSearch
from .eval_answer import EvalAnswerHandler
from .final_answer import FinalAnswerHandler
from .core import AnswerQuery, FinalAnswer

import logging

logger = logging.getLogger(__name__)


class MedicalQueryPipeline:
    """
    Pipeline hoàn chỉnh xử lý câu hỏi y tế theo kiến trúc:
    User Query -> Split Query -> K Queries -> RAG + Answer -> Eval Answer 
    -> (loop back nếu try < M) hoặc (Web search nếu try >= M) -> Final Answer
    
    Đã bỏ bước Summary - Final Answer nhận trực tiếp các answers đã eval.
    """
    
    def __init__(self, max_retries: int = 1, max_workers: int = 1):
        """
        Khởi tạo pipeline.
        
        Args:
            max_retries: Số lần thử tối đa (M) cho RAG + Answer trước khi chuyển sang web search
            max_workers: Số thread tối đa cho xử lý song song
        """
        self.split_handler = SplitQueryHandler()
        self.medical_pipeline = MedicalPipeline()
        self.medical_search = MedicalSearch(max_results=3)
        self.eval_handler = EvalAnswerHandler(max_tries=max_retries)
        self.final_handler = FinalAnswerHandler()
        self.max_retries = max_retries
        self.max_workers = max_workers
    
    def process_query(self, user_query: str) -> FinalAnswer:
        """
        Xử lý câu hỏi người dùng theo pipeline hoàn chỉnh.
        
        Args:
            user_query: Câu hỏi từ người dùng
            
        Returns:
            FinalAnswer: Câu trả lời cuối cùng
        """
        logger.info(f"Processing query: {user_query}")
        steps = []
        
        # Bước 1: Split Query thành K Queries
        split_result = self.split_handler.split(user_query)
        k_queries = split_result.queries
        logger.info(f"Split into {len(k_queries)} sub-queries")
        steps.append(f"2. Split Query: Tach thanh {len(k_queries)} cau hoi con")
        if len(k_queries) > 1:
            steps.append(f"   Cac cau hoi: {', '.join([f'Q{i+1}' for i in range(len(k_queries))])}")
        
        # Bước 2: Xử lý từng query bằng RAG + Answer + Eval (song song nếu nhiều queries)
        all_answers = self._process_queries_parallel(k_queries, steps)
        
        # Bước 3: Nếu không có answer nào, trả về câu trả lời mặc định
        if not all_answers:
            return FinalAnswer(
                answer="Xin lỗi, tôi không tìm thấy thông tin phù hợp để trả lời câu hỏi của bạn.",
                sources=[],
                confidence=0.0,
                steps=steps
            )
        
        # Bước 4: Final Answer - trực tiếp từ các answers (bỏ Summary)
        steps.append(f"{len(steps) + 1}. Final Answer: Tong hop ket qua tu {len(all_answers)} nguon")
        final_answer = self.final_handler.generate_from_answers(user_query, all_answers)
        logger.info("Generated final answer")
        final_answer.steps = steps
        
        return final_answer
    
    def _process_queries_parallel(self, queries: List[str], steps: List[str]) -> List[AnswerQuery]:
        """
        Xử lý nhiều queries SONG SONG, mỗi query qua RAG + Answer + Eval.
        
        Args:
            queries: Danh sách các câu hỏi cần xử lý
            steps: Danh sách các bước xử lý để cập nhật
            
        Returns:
            List[AnswerQuery]: Danh sách các câu trả lời đã được eval
        """
        all_answers = []
        step_num = len(steps) + 1
        
        # Nếu chỉ có 1 query, xử lý trực tiếp
        if len(queries) == 1:
            steps.append(f"{step_num}. Xu ly cau hoi: RAG + Answer + Eval")
            answer, query_steps = self._process_single_query(queries[0])
            if answer:
                all_answers.append(answer)
                if query_steps:
                    steps.extend(query_steps)
            return all_answers
        
        # Xử lý song song nhiều queries
        steps.append(f"{step_num}. Xu ly {len(queries)} cau hoi song song")
        with ThreadPoolExecutor(max_workers=min(len(queries), self.max_workers)) as executor:
            future_to_query = {
                executor.submit(self._process_single_query, query): query 
                for query in queries
            }
            
            for idx, future in enumerate(as_completed(future_to_query), 1):
                query = future_to_query[future]
                try:
                    answer, query_steps = future.result()
                    if answer:
                        all_answers.append(answer)
                        if query_steps:
                            steps.append(f"   Q{idx}: {query_steps[-1] if query_steps else 'Hoan thanh'}")
                        logger.info(f"Got answer for: {query[:50]}...")
                except Exception as e:
                    logger.error(f"Error processing query '{query}': {e}")
                    steps.append(f"   Q{idx}: Loi - {str(e)[:50]}")
        
        return all_answers
    
    def _process_single_query(self, query: str) -> Tuple[Optional[AnswerQuery], List[str]]:
        """
        Xử lý một câu hỏi: RAG + Answer -> Eval Answer -> (loop back hoặc Web search).
        
        Args:
            query: Câu hỏi
            
        Returns:
            tuple: (AnswerQuery hoặc None, danh sách các bước xử lý)
        """
        query_steps = []
        
        # Thử RAG + Answer với retry logic
        for try_count in range(1, self.max_retries + 1):
            logger.info(f"Attempt {try_count}/{self.max_retries} for RAG + Answer")
            
            # RAG + Answer
            rag_answer = self._get_rag_answer(query)
            
            if not rag_answer:
                # Nếu không có kết quả từ RAG, chuyển sang web search ngay
                logger.info("No RAG results, switching to web search")
                query_steps.append("   - RAG: Khong co ket qua -> Chuyen sang Web Search")
                answer = self._get_web_search_answer(query)
                query_steps.append("   - Web Search: Hoan thanh")
                return answer, query_steps
            
            query_steps.append(f"   - RAG (lan {try_count}): Tim thay {len(rag_answer.source.split(',')) if hasattr(rag_answer, 'source') else 1} nguon")
            
            # Eval Answer
            eval_result = self.eval_handler.evaluate(query, rag_answer.answer, try_count)
            logger.info(f"Evaluation: satisfactory={eval_result.is_satisfactory}, score={eval_result.score:.2f}")
            query_steps.append(f"   - Eval: Diem {eval_result.score:.2f}, {'Dat' if eval_result.is_satisfactory else 'Chua dat'}")
            
            # Nếu đạt yêu cầu (satisfied), trả về
            if eval_result.is_satisfactory:
                logger.info("Answer is satisfactory, returning RAG answer")
                query_steps.append("   - Ket qua: Su dung cau tra loi tu RAG")
                return rag_answer, query_steps
            
            # Nếu không đạt và không nên retry (try >= M hoặc not satisfied), chuyển sang web search
            if not eval_result.should_retry:
                logger.info("Should not retry, switching to web search")
                query_steps.append("   - Chuyen sang Web Search (khong retry)")
                answer = self._get_web_search_answer(query)
                query_steps.append("   - Web Search: Hoan thanh")
                return answer, query_steps
            
            # Nếu nên retry và chưa đạt max (try < M), tiếp tục loop
            logger.info(f"Retrying RAG + Answer (try {try_count}/{self.max_retries})")
            query_steps.append(f"   - Retry lan {try_count + 1}")
        
        # Nếu đã thử hết max_retries mà vẫn không đạt, chuyển sang web search
        logger.info("Max retries reached, switching to web search")
        query_steps.append(f"   - Da thu het {self.max_retries} lan -> Chuyen sang Web Search")
        answer = self._get_web_search_answer(query)
        query_steps.append("   - Web Search: Hoan thanh")
        return answer, query_steps
    
    def _get_rag_answer(self, query: str) -> Optional[AnswerQuery]:
        """
        Lấy câu trả lời từ RAG.
        
        Args:
            query: Câu hỏi
            
        Returns:
            AnswerQuery hoặc None nếu không tìm thấy hoặc có lỗi
        """
        try:
            # Query RAG để lấy documents
            results = self.medical_pipeline.medical_rag.query(query)
            
            # Nếu không có kết quả (có thể do collection không tồn tại hoặc lỗi)
            if not results:
                logger.info("RAG không trả về kết quả, sẽ fallback sang web search")
                return None
            
            thresholded_results = [
                res.payload.get("text", "") 
                for res in results 
                if res.score >= self.medical_pipeline.similarity_threshold
            ]
            
            if thresholded_results:
                context = "\n\n".join(thresholded_results)
                answer = self.medical_pipeline.process_medical_answer(query, context=context)
                return answer
            
            return None
        except Exception as e:
            logger.error(f"Error in RAG query: {e}")
            return None
    
    def _get_web_search_answer(self, query: str) -> Optional[AnswerQuery]:
        """
        Lấy câu trả lời từ Web search.
        
        Args:
            query: Câu hỏi
            
        Returns:
            AnswerQuery: Câu trả lời từ web search
        """
        try:
            answer = self.medical_search.answer(query)
            return answer
        except Exception as e:
            logger.error(f"Error in web search: {e}")
            return AnswerQuery(
                answer="Xin lỗi, không thể tìm kiếm thông tin trên web.",
                source="Lỗi hệ thống"
            )
