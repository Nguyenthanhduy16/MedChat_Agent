from langchain_core.prompts import ChatPromptTemplate

from ..core import get_llm, get_embedding_model, AnswerQuery, RephraseQuery
from .medical_rag import MedicalRAG
from .medical_search import MedicalSearch
from ..prompt_templates import MEDICAL_REPHRASE_PROMPT, MEDICAL_ANSWER_PROMPT, MEDICAL_SYSTEM_PROMPT, MEDICAL_HISTORY_PROMPT



class MedicalPipeline:
    def __init__(self):
        self.llm = get_llm()
        self.similarity_threshold = 0.55
        self.embedder = get_embedding_model()  # Sử dụng model mặc định của Google
        self.medical_rag = MedicalRAG(embedder=self.embedder)
        self.medical_search = MedicalSearch(max_results=3)
        self._init_prompt()
        self._init_chains()
    
    def _init_prompt(self):
        self.rephrase_prompt = ChatPromptTemplate.from_messages([
                ("system", MEDICAL_SYSTEM_PROMPT),
                ("human", MEDICAL_REPHRASE_PROMPT),
            ])
        self.answer_prompt = ChatPromptTemplate.from_messages([
                ("system", MEDICAL_SYSTEM_PROMPT),
                ("human", MEDICAL_ANSWER_PROMPT),
            ])
    
    def _init_chains(self):
        self.structured_llm_answer = self.llm.with_structured_output(AnswerQuery)
        self.structured_llm_rephrase = self.llm.with_structured_output(RephraseQuery)
        self.rephrase_chain = self.rephrase_prompt | self.structured_llm_rephrase
        self.answer_chain = self.answer_prompt | self.structured_llm_answer

    def process_medical_answer(self, query: str, context: str = "") -> AnswerQuery:
        results = self.answer_chain.invoke({"query": query, "context": context})
        return results

    def process_medical_rephrase(self, query: str) -> str:
        results = self.rephrase_chain.invoke({"query": query})
        return results.rephrased_question

    def query(self, user_query, max_attempts: int = 3) -> AnswerQuery:
        query = user_query
        for attempt in range(max_attempts):
            # 1. Query RAG to extract relevant documents
            results = self.medical_rag.query(query)
            thresholded_results = [res.payload["text"] for res in results if res.score >= self.similarity_threshold]
            # 2. If threshold is met → run RAG
            if thresholded_results:
                context = "\n\n".join(thresholded_results)
                result = self.process_medical_answer(query, context=context)
                return result

            # 3. If not met → rephrase question
            rephrased = self.process_medical_rephrase(query)
            print(f"DEBUG: Rephrased: {rephrased}")
            query = rephrased

        result = self.medical_search.answer(user_query)
        # 4. If still not met after 3 attempts
        return result