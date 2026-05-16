from langchain_core.prompts import ChatPromptTemplate
from .core import get_llm, SplitQuery
from .prompt_templates import SPLIT_QUERY_SYSTEM_PROMPT, SPLIT_QUERY_HUMAN_PROMPT

import logging

logger = logging.getLogger(__name__)


class SplitQueryHandler:
    """
    Chia một câu hỏi người dùng thành K câu hỏi con để tìm kiếm hiệu quả hơn.
    Dựa trên kiến trúc: User Query -> Split Query -> K Queries
    """
    
    def __init__(self):
        self.llm = get_llm()
        self.structured_llm = self.llm.with_structured_output(SplitQuery)
        self.prompt = self._create_prompt()
        self.split_chain = self.prompt | self.structured_llm
    
    def _create_prompt(self):
        """Tạo prompt template cho việc chia câu hỏi."""
        return ChatPromptTemplate.from_messages([
            ("system", SPLIT_QUERY_SYSTEM_PROMPT),
            ("human", SPLIT_QUERY_HUMAN_PROMPT),
        ])
    
    def split(self, query: str) -> SplitQuery:
        """
        Chia câu hỏi người dùng thành K câu hỏi con.
        
        Args:
            query: Câu hỏi gốc từ người dùng
            
        Returns:
            SplitQuery: Đối tượng chứa danh sách các câu hỏi con và lý do chia
        """
        try:
            result = self.split_chain.invoke({"query": query})
            logger.info(f"Split query into {len(result.queries)} sub-queries: {result.reasoning}")
            return result
        except Exception as e:
            logger.error(f"Error in splitting query: {e}")
            # Fallback: trả về chính câu hỏi gốc nếu có lỗi
            return SplitQuery(
                queries=[query],
                reasoning="Fallback due to splitting error - using original query"
            )
    
    def get_queries(self, query: str) -> list[str]:
        """
        Lấy danh sách các câu hỏi con từ câu hỏi gốc.
        Phương thức tiện ích để lấy trực tiếp danh sách queries.
        
        Args:
            query: Câu hỏi gốc từ người dùng
            
        Returns:
            list[str]: Danh sách các câu hỏi con
        """
        split_result = self.split(query)
        return split_result.queries

