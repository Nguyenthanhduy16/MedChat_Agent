"""
Final Answer Handler - Tạo câu trả lời cuối cùng trực tiếp từ các AnswerQuery.
Đã gộp Summary + Final Answer thành một bước duy nhất.
"""
from typing import List
from langchain_core.prompts import ChatPromptTemplate
from .core import get_llm, FinalAnswer, SummaryAnswer, AnswerQuery
from .prompt_templates import FINAL_ANSWER_SYSTEM_PROMPT, FINAL_ANSWER_HUMAN_PROMPT

import logging

logger = logging.getLogger(__name__)

# Prompt mới cho việc tạo final answer trực tiếp từ nhiều answers
DIRECT_FINAL_SYSTEM_PROMPT = """Bạn là một trợ lý dược chuyên nghiệp. Nhiệm vụ của bạn là tổng hợp các câu trả lời từ nhiều nguồn và trình bày câu trả lời cuối cùng cho người dùng.

Nguyên tắc:
- Tổng hợp thông tin từ TẤT CẢ các nguồn một cách logic và mạch lạc
- Loại bỏ thông tin trùng lặp, giữ lại thông tin quan trọng nhất
- Trình bày câu trả lời một cách tự nhiên, dễ hiểu
- Đảm bảo thông tin chính xác và đầy đủ
- Sử dụng ngôn ngữ phù hợp với người dùng Việt Nam
- Nếu các nguồn có thông tin mâu thuẫn, ưu tiên nguồn đáng tin cậy hơn

LƯU Ý: Trả lời trực tiếp câu hỏi của người dùng, không cần giới thiệu dài dòng.
"""

DIRECT_FINAL_HUMAN_PROMPT = """Câu hỏi của người dùng: {query}

Các câu trả lời từ các nguồn:
{answers}

Hãy tổng hợp và trình bày câu trả lời cuối cùng một cách rõ ràng, đầy đủ và chuyên nghiệp.
"""


class FinalAnswerHandler:
    """
    Tạo câu trả lời cuối cùng cho người dùng.
    Hỗ trợ 2 cách:
    1. generate_from_answers(): Trực tiếp từ list AnswerQuery (đã gộp Summary)
    2. generate(): Từ SummaryAnswer (legacy, để tương thích ngược)
    """
    
    def __init__(self):
        self.llm = get_llm()
        self.structured_llm = self.llm.with_structured_output(FinalAnswer)
        
        # Prompt cho cách mới (trực tiếp từ answers)
        self.direct_prompt = ChatPromptTemplate.from_messages([
            ("system", DIRECT_FINAL_SYSTEM_PROMPT),
            ("human", DIRECT_FINAL_HUMAN_PROMPT),
        ])
        self.direct_chain = self.direct_prompt | self.structured_llm
        
        # Prompt cho cách cũ (từ summary) - legacy
        self.legacy_prompt = ChatPromptTemplate.from_messages([
            ("system", FINAL_ANSWER_SYSTEM_PROMPT),
            ("human", FINAL_ANSWER_HUMAN_PROMPT),
        ])
        self.legacy_chain = self.legacy_prompt | self.structured_llm
    
    def generate_from_answers(self, query: str, answers: List[AnswerQuery]) -> FinalAnswer:
        """
        Tạo câu trả lời cuối cùng TRỰC TIẾP từ danh sách AnswerQuery.
        Đã gộp Summary + Final Answer thành một bước.
        
        Args:
            query: Câu hỏi gốc của người dùng
            answers: Danh sách các câu trả lời từ RAG/Web search
            
        Returns:
            FinalAnswer: Câu trả lời cuối cùng
        """
        try:
            # Format các answers thành text
            answers_text = []
            all_sources = []
            
            for i, answer in enumerate(answers, 1):
                source = answer.source if hasattr(answer, 'source') else f"Nguồn {i}"
                answers_text.append(f"[Nguồn {i}: {source}]\n{answer.answer}")
                all_sources.append(source)
            
            answers_formatted = "\n\n---\n\n".join(answers_text)
            
            result = self.direct_chain.invoke({
                "query": query,
                "answers": answers_formatted
            })
            
            # Đảm bảo sources được set đúng
            if not result.sources:
                result.sources = all_sources
            
            logger.info(f"Generated final answer from {len(answers)} sources")
            return result
            
        except Exception as e:
            logger.error(f"Error generating final answer: {e}")
            # Fallback: lấy answer đầu tiên
            if answers:
                return FinalAnswer(
                    answer=answers[0].answer,
                    sources=[answers[0].source] if hasattr(answers[0], 'source') else [],
                    confidence=0.6
                )
            return FinalAnswer(
                answer="Xin lỗi, không thể tạo câu trả lời.",
                sources=[],
                confidence=0.0
            )
    
    def generate(self, query: str, summary: SummaryAnswer) -> FinalAnswer:
        """
        [Legacy] Tạo câu trả lời cuối cùng từ SummaryAnswer.
        Giữ lại để tương thích ngược với code cũ.
        
        Args:
            query: Câu hỏi gốc của người dùng
            summary: Câu trả lời đã được tổng hợp từ Summary
            
        Returns:
            FinalAnswer: Câu trả lời cuối cùng với confidence score
        """
        try:
            sources_text = ", ".join(summary.sources) if summary.sources else "Không có nguồn"
            
            result = self.legacy_chain.invoke({
                "query": query,
                "summary": summary.summary,
                "sources": sources_text
            })
            
            logger.info(f"Generated final answer with {len(summary.sources)} sources")
            return result
        except Exception as e:
            logger.error(f"Error in generating final answer: {e}")
            return FinalAnswer(
                answer=summary.summary,
                sources=summary.sources,
                confidence=0.7
            )
    
    def generate_simple(self, query: str, summary: SummaryAnswer) -> str:
        """
        [Legacy] Tạo câu trả lời cuối cùng dạng đơn giản (chỉ trả về text).
        
        Args:
            query: Câu hỏi gốc của người dùng
            summary: Câu trả lời đã được tổng hợp
            
        Returns:
            str: Câu trả lời cuối cùng dạng text
        """
        final_result = self.generate(query, summary)
        return final_result.answer
