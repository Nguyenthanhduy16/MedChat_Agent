from typing import Literal
from langchain_core.prompts import ChatPromptTemplate
from ..core import get_llm, RouteQuery
from ..prompt_templates import ROUTER_SYSTEM_PROMPT, ROUTER_HUMAN_PROMPT

import logging

logger = logging.getLogger(__name__)

class Router:
    """
    Router quyết định câu hỏi nên được xử lý bởi:
    - medical_knowledge: RAG cho câu hỏi về y tế, thuốc, sức khỏe
    - store_database: Database cho câu hỏi về kho, thống kê, biểu đồ
    """
    
    def __init__(self, model: str = "gpt-4o-mini"):
        """
        Khởi tạo Router với GPT model.
        
        Args:
            model: Loại model sử dụng (mặc định: gpt-4o-mini)
        """
        self.llm = get_llm(model)
        self.structured_llm = self.llm.with_structured_output(RouteQuery)
        self.prompt = self._create_prompt()
        self.router_chain = self.prompt | self.structured_llm
        logger.info(f"Router initialized with {model}")

    def _create_prompt(self):

        return ChatPromptTemplate.from_messages(
            [
                ("system", ROUTER_SYSTEM_PROMPT),
                ("human", ROUTER_HUMAN_PROMPT),
            ]
        )

    def route(self, question: str) -> RouteQuery:
        try:
            result = self.router_chain.invoke({"question": question})
            logger.info(f"Routed question to: {result.datasource} - {result.reasoning}")
            return result
        except Exception as e:
            logger.error(f"Error in routing: {e}")
            # Default to medical knowledge if routing fails
            return RouteQuery(
                datasource="medical_knowledge",
                reasoning="Fallback due to routing error",
            )
