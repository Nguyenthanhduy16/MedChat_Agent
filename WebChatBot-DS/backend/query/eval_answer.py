from langchain_core.prompts import ChatPromptTemplate
from .core import get_llm, EvalAnswer
from .prompt_templates import EVAL_ANSWER_SYSTEM_PROMPT, EVAL_ANSWER_HUMAN_PROMPT

import logging

logger = logging.getLogger(__name__)


class EvalAnswerHandler:
    """
    Đánh giá chất lượng câu trả lời từ RAG + Answer.
    Dựa trên kiến trúc: RAG + Answer -> Eval Answer -> (loop back nếu try < M) hoặc (Web search nếu try >= M hoặc not satisfactory)
    """
    
    def __init__(self, max_tries: int = 3):
        """
        Khởi tạo EvalAnswerHandler.
        
        Args:
            max_tries: Số lần thử tối đa (M) trước khi chuyển sang web search
        """
        self.llm = get_llm()
        self.structured_llm = self.llm.with_structured_output(EvalAnswer)
        self.prompt = self._create_prompt()
        self.eval_chain = self.prompt | self.structured_llm
        self.max_tries = max_tries
    
    def _create_prompt(self):
        """Tạo prompt template cho việc đánh giá câu trả lời."""
        return ChatPromptTemplate.from_messages([
            ("system", EVAL_ANSWER_SYSTEM_PROMPT),
            ("human", EVAL_ANSWER_HUMAN_PROMPT),
        ])
    
    def evaluate(self, query: str, answer: str, try_count: int) -> EvalAnswer:
        """
        Đánh giá chất lượng câu trả lời.
        
        Args:
            query: Câu hỏi gốc của người dùng
            answer: Câu trả lời từ RAG + Answer
            try_count: Số lần đã thử (bắt đầu từ 1)
            
        Returns:
            EvalAnswer: Đối tượng chứa kết quả đánh giá và quyết định
        """
        try:
            result = self.eval_chain.invoke({
                "query": query,
                "answer": answer,
                "try_count": try_count,
                "max_tries": self.max_tries
            })
            
            # Logic bổ sung: nếu đã thử quá M lần, không nên retry nữa
            if try_count >= self.max_tries:
                result.should_retry = False
                logger.info(f"Max tries ({self.max_tries}) reached, should not retry")
            
            logger.info(
                f"Answer evaluation - Satisfactory: {result.is_satisfactory}, "
                f"Score: {result.score:.2f}, Should retry: {result.should_retry}, "
                f"Try: {try_count}/{self.max_tries}"
            )
            return result
        except Exception as e:
            logger.error(f"Error in evaluating answer: {e}")
            # Fallback: nếu đã thử quá nhiều lần, không retry
            should_retry = try_count < self.max_tries
            return EvalAnswer(
                is_satisfactory=False,
                score=0.0,
                reasoning=f"Fallback due to evaluation error. Try count: {try_count}",
                should_retry=should_retry
            )
    
    def should_retry(self, query: str, answer: str, try_count: int) -> bool:
        """
        Kiểm tra xem có nên thử lại hay không.
        Phương thức tiện ích để lấy trực tiếp quyết định retry.
        
        Args:
            query: Câu hỏi gốc của người dùng
            answer: Câu trả lời từ RAG + Answer
            try_count: Số lần đã thử
            
        Returns:
            bool: True nếu nên thử lại, False nếu nên chuyển sang web search
        """
        eval_result = self.evaluate(query, answer, try_count)
        return eval_result.should_retry
    
    def is_satisfactory(self, query: str, answer: str, try_count: int) -> bool:
        """
        Kiểm tra xem câu trả lời có đạt yêu cầu hay không.
        Phương thức tiện ích để lấy trực tiếp kết quả đánh giá.
        
        Args:
            query: Câu hỏi gốc của người dùng
            answer: Câu trả lời từ RAG + Answer
            try_count: Số lần đã thử
            
        Returns:
            bool: True nếu câu trả lời đạt yêu cầu, False nếu không
        """
        eval_result = self.evaluate(query, answer, try_count)
        return eval_result.is_satisfactory

