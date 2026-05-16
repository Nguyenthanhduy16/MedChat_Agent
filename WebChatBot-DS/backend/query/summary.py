from langchain_core.prompts import ChatPromptTemplate
from .core import get_llm, SummaryAnswer, AnswerQuery
from .prompt_templates import SUMMARY_SYSTEM_PROMPT, SUMMARY_HUMAN_PROMPT

import logging

logger = logging.getLogger(__name__)


class SummaryHandler:
    """
    Tổng hợp các câu trả lời từ nhiều nguồn (Web search + Answer, Database + Answer) 
    thành một câu trả lời toàn diện.
    Dựa trên kiến trúc: Web search + Answer -> Summary -> Final Answer
    """
    
    def __init__(self):
        self.llm = get_llm()
        self.structured_llm = self.llm.with_structured_output(SummaryAnswer)
        self.prompt = self._create_prompt()
        self.summary_chain = self.prompt | self.structured_llm
    
    def _create_prompt(self):
        """Tạo prompt template cho việc tổng hợp."""
        return ChatPromptTemplate.from_messages([
            ("system", SUMMARY_SYSTEM_PROMPT),
            ("human", SUMMARY_HUMAN_PROMPT),
        ])
    
    def summarize(self, original_query: str, answers: list[AnswerQuery]) -> SummaryAnswer:
        """
        Tổng hợp nhiều câu trả lời thành một câu trả lời toàn diện.
        
        Args:
            original_query: Câu hỏi gốc của người dùng
            answers: Danh sách các câu trả lời từ các nguồn khác nhau
            
        Returns:
            SummaryAnswer: Câu trả lời đã được tổng hợp và danh sách nguồn
        """
        try:
            # Format các câu trả lời thành chuỗi
            answers_text = []
            for i, answer in enumerate(answers, 1):
                answer_text = f"[Nguồn {i}: {answer.source}]\n{answer.answer}"
                answers_text.append(answer_text)
            
            answers_formatted = "\n\n---\n\n".join(answers_text)
            
            result = self.summary_chain.invoke({
                "original_query": original_query,
                "answers": answers_formatted
            })
            
            logger.info(f"Summarized {len(answers)} answers into one comprehensive answer")
            return result
        except Exception as e:
            logger.error(f"Error in summarizing answers: {e}")
            # Fallback: lấy câu trả lời đầu tiên nếu có lỗi
            if answers:
                return SummaryAnswer(
                    summary=answers[0].answer,
                    sources=[answers[0].source]
                )
            return SummaryAnswer(
                summary="Xin lỗi, không thể tổng hợp câu trả lời.",
                sources=[]
            )
    
    def summarize_single(self, original_query: str, answer: AnswerQuery) -> SummaryAnswer:
        """
        Tổng hợp một câu trả lời duy nhất (trường hợp chỉ có một nguồn).
        Phương thức tiện ích khi chỉ có một câu trả lời.
        
        Args:
            original_query: Câu hỏi gốc của người dùng
            answer: Câu trả lời duy nhất
            
        Returns:
            SummaryAnswer: Câu trả lời và nguồn
        """
        return SummaryAnswer(
            summary=answer.answer,
            sources=[answer.source]
        )

