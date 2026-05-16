import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from ..prompt_templates.base import SUMMARIZE_HISTORY_PROMPT, SUMMARIZE_SYSTEM_PROMPT
from ..core.structure import SummarizeQuery

# Tìm file .env trong thư mục MedAgent (thư mục gốc của project)
env_path = os.path.join(os.path.dirname(__file__), "../../.env")
load_dotenv(dotenv_path=env_path)

def get_llm(type_model="gpt-4o-mini", temperature: float = 0.3):
    """
    Lấy LLM model theo loại được chỉ định.
    
    Args:
        type_model: Loại model ("gpt", "gpt-4o", "gpt-4o-mini", "gemini", "openai-oss", "llama3", "qwen3")
        temperature: Độ ngẫu nhiên của output (0.0 - 1.0)
    
    Returns:
        ChatOpenAI hoặc ChatGoogleGenerativeAI instance
    """
    # GPT Models (OpenAI) - Mặc định
    if type_model == "gpt" or type_model == "gpt-4o":
        return ChatOpenAI(
            model="gpt-4o",
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            temperature=temperature,
        )
    elif type_model == "gpt-4o-mini":
        return ChatOpenAI(
            model="gpt-4o-mini",
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            temperature=temperature,
        )
    elif type_model == "gpt-3.5":
        return ChatOpenAI(
            model="gpt-3.5-turbo",
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            temperature=temperature,
        )
    # Gemini Models (Google)
    elif type_model == "gemini":
        return ChatGoogleGenerativeAI(
            model="gemini-2.5-flash-lite",
            temperature=temperature,
            google_api_key=os.getenv("GOOGLE_API_KEY"),
        )
    # Cerebras Models (OpenAI compatible)
    elif type_model == "openai-oss":
        return ChatOpenAI(
            model="gpt-oss-120b",
            openai_api_base="https://api.cerebras.ai/v1",
            openai_api_key=os.getenv("CEREBRAS_API_KEY"),
            temperature=temperature,
        )
    elif type_model == "llama3":
        return ChatOpenAI(
            model="llama-3.3-70b",
            openai_api_base="https://api.cerebras.ai/v1",
            openai_api_key=os.getenv("CEREBRAS_API_KEY"),
            temperature=temperature,
        )
    elif type_model == 'qwen3':
        return ChatOpenAI(
            model="qwen-3-32b",
            openai_api_base="https://api.cerebras.ai/v1",
            openai_api_key=os.getenv("CEREBRAS_API_KEY"),
            temperature=temperature,
        )
    else:
        # Fallback to GPT-4o-mini nếu không nhận ra model
        return ChatOpenAI(
            model="gpt-4o-mini",
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            temperature=temperature,
        )

class HistoryManager:
    def __init__(self, llm, max_length: int = 500):
        self.history = {}
        self.llm = llm
        self._init_prompt()
        self._init_chain()
        self.max_length = max_length
    
    def _init_prompt(self):
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", SUMMARIZE_SYSTEM_PROMPT),
            ("user", SUMMARIZE_HISTORY_PROMPT),
        ])
    
    def _init_chain(self):
        self.structured_llm = self.llm.with_structured_output(SummarizeQuery)
        self.history_chain = self.prompt | self.structured_llm
 
    
    def put_history(self, user_id: str, role: str, message: str):
        if user_id not in self.history:
            self.history[user_id] = []
        self.history[user_id].append({"role": role, "content": message})
        
        # Nếu hội thoại quá dài, tự động tóm tắt lại
        full_text = self._history_to_text(user_id)
        if len(full_text) > self.max_length:
            summary = self.summarize_history(user_id)
            self.history[user_id] = [{"role": "system", "content": f"Tóm tắt hội thoại: {summary}"}]
        
    def _history_to_text(self, user_id: str) -> str:
        if user_id not in self.history:
            return ""
        return "\n".join([f"{entry['role']}: {entry['content']}" for entry in self.history[user_id]])

    def get_history(self, user_id: str) -> str:
        if user_id not in self.history:
            return ""
        return self._history_to_text(user_id)        

    def summarize_history(self, user_id: str) -> str:

        if user_id not in self.history or not self.history[user_id]:
            return "No history available."

        history_text = self.get_history(user_id)
        
        result = self.history_chain.invoke({"history": history_text})
        return result.summary
    
    
if __name__ == "__main__":
    # Test the LLM setup
    history = HistoryManager(get_llm())
    history.put_history("user1", "user", "Hello, how are you?")
    history.put_history("user1", "assistant", "I'm fine, thank you!")
    print(history.get_history("user1"))
