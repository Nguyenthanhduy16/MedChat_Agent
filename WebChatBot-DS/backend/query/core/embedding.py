import os
from typing import List
import numpy as np
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from dotenv import load_dotenv

# Tìm file .env trong thư mục MedAgent (thư mục gốc của project)
env_path = os.path.join(os.path.dirname(__file__), "../../.env")
load_dotenv(dotenv_path=env_path)


class GoogleEmbeddingWrapper:
    """
    Wrapper để tương thích GoogleGenerativeAIEmbeddings với interface của SentenceTransformer.
    Cho phép sử dụng method .encode() giống như SentenceTransformer.
    """
    def __init__(self, model_name: str = "models/text-embedding-004"):
        """
        Khởi tạo Google embedding model.
        
        Args:
            model_name: Tên model embedding của Google (mặc định: "models/text-embedding-004")
        """
        self.google_embeddings = GoogleGenerativeAIEmbeddings(
            model=model_name,
            google_api_key=os.getenv("GOOGLE_API_KEY"),
        )
        self.model_name = model_name
    
    def encode(self, texts: List[str], convert_to_numpy: bool = True, **kwargs):
        """
        Encode danh sách texts thành embeddings.
        Tương thích với interface của SentenceTransformer.
        
        Args:
            texts: Danh sách các text cần encode
            convert_to_numpy: Có chuyển đổi sang numpy array không (mặc định True)
            **kwargs: Các tham số bổ sung (không sử dụng cho Google embedding)
            
        Returns:
            numpy array hoặc list chứa embeddings
        """
        # Google embedding trả về list of lists
        embeddings = self.google_embeddings.embed_documents(texts)
        
        if convert_to_numpy:
            return np.array(embeddings)
        return embeddings


def get_embedding_model(model_name: str = None):
    """
    Lấy embedding model mặc định của Google.
    
    Args:
        model_name: Tên model (mặc định None sẽ dùng model mặc định của Google)
        
    Returns:
        GoogleEmbeddingWrapper: Wrapper cho Google embedding model
    """
    # Sử dụng model mặc định của Google nếu không chỉ định
    if model_name is None:
        model_name = "models/text-embedding-004"
    
    return GoogleEmbeddingWrapper(model_name=model_name)
