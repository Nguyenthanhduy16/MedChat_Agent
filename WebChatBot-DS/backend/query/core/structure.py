from typing import Literal
from pydantic import BaseModel, Field
from typing import Optional

class RouteQuery(BaseModel):
    """Route a user query to the appropriate data source."""

    datasource: Literal["medical_knowledge", "store_database"] = Field(
        ...,
        description="Route to store_database for sales-related queries or medical_knowledge for medical queries",
    )
    reasoning: str = Field(..., description="Brief for the decision")

class AnswerQuery(BaseModel):
    """Answer a user query with context."""

    answer: str = Field(..., description="The answer to the user's query based on the provided context")
    source: str = Field(..., description="The source of the information used to answer the query")

class RephraseQuery(BaseModel):
    """Rephrase a user query for better retrieval."""

    rephrased_question: str = Field(..., description="The rephrased version of the user's query")

class SummarizeQuery(BaseModel):
    """Summarize a long text into a concise summary."""

    summary: str = Field(..., description="A concise summary of the provided text")

class SplitQuery(BaseModel):
    """Split a user query into multiple sub-queries."""

    queries: list[str] = Field(..., description="List of K sub-queries split from the original query")
    reasoning: str = Field(..., description="Brief explanation of why the query was split this way")

class EvalAnswer(BaseModel):
    """Evaluate the quality of an answer."""

    is_satisfactory: bool = Field(..., description="Whether the answer is satisfactory (True) or needs improvement (False)")
    score: float = Field(..., description="Quality score from 0.0 to 1.0")
    reasoning: str = Field(..., description="Explanation of the evaluation")
    should_retry: bool = Field(..., description="Whether to retry generating the answer (True) or proceed to web search (False)")

class SummaryAnswer(BaseModel):
    """Summarize multiple answers into a single comprehensive answer."""

    summary: str = Field(..., description="The summarized and consolidated answer from multiple sources")
    sources: list[str] = Field(..., description="List of sources used in the summary")

class FinalAnswer(BaseModel):
    """Final answer to return to the user."""

    answer: str = Field(..., description="The final answer to the user's query")
    sources: list[str] = Field(..., description="List of sources used")
    confidence: float = Field(..., description="Confidence score from 0.0 to 1.0")
    steps: Optional[list[str]] = Field(default=None, description="List of processing steps")
    

class FaithfulnessEval(BaseModel):
    """
    Đánh giá mức độ câu trả lời có dựa trên context hay không.
    """
    faithfulness: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Mức độ trung thực so với ngữ cảnh, từ 0 (hallucination) đến 1 (hoàn toàn dựa trên context)"
    )
    reason: str = Field(
        ...,
        description="Giải thích ngắn gọn lý do chấm điểm"
    )
    
class ContextRelevanceEval(BaseModel):
    """
    Đánh giá mức độ liên quan và đầy đủ của context.
    """
    context_relevance: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Context có liên quan và đủ thông tin để trả lời câu hỏi hay không"
    )
    reason: str = Field(
        ...,
        description="Nhận xét ngắn gọn"
    )

class AnswerCorrectnessEval(BaseModel):
    """
    Đánh giá độ chính xác về mặt y khoa của câu trả lời.
    """
    correctness: int = Field(
        ...,
        ge=1,
        le=5,
        description="Độ chính xác y khoa: 1 (sai/nguy hiểm) đến 5 (đúng và đầy đủ)"
    )
    reason: str = Field(
        ...,
        description="Giải thích vì sao câu trả lời được chấm mức này"
    )
    
class LLMEvalResult(BaseModel):
    """
    Kết quả đánh giá LLM cho một câu hỏi.
    """
    faithfulness: FaithfulnessEval
    context_relevance: ContextRelevanceEval
    correctness: AnswerCorrectnessEval
    
class SplitQueryEval(BaseModel):
    """Viết lại query của user, tách thành các câu nhỏ hơn nếu cần thiếu"""

    queries: list[str] = Field(..., description="Danh sách các câu trích xuất từ query của người dùng")
    reasoning: str = Field(..., description="Giải thích lý do chia tách")

class QueryPlan(BaseModel):
    sql: str
    need_chart: bool
    chart_type: Optional[str] = None   # line | bar | pie
    x: Optional[str] = None
    y: Optional[str] = None
    title: Optional[str] = None
    