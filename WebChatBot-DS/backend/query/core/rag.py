import os
from xmlrpc import client
from qdrant_client import QdrantClient, models
from dotenv import load_dotenv

# Tìm file .env trong thư mục MedAgent (thư mục gốc của project)
env_path = os.path.join(os.path.dirname(__file__), "../../.env")
load_dotenv(dotenv_path=env_path)

def get_rag_client():
    """
    Khởi tạo Qdrant client từ biến môi trường.
    
    Returns:
        QdrantClient: Client kết nối đến Qdrant
    """
    qdrant_url = os.getenv("QDRANT_URL")
    qdrant_api_key = os.getenv("QDRANT_API_KEY")
    
    if not qdrant_url:
        raise ValueError(
            "QDRANT_URL không được tìm thấy trong file .env. "
            "Vui lòng kiểm tra file .env trong thư mục MedAgent/"
        )
    
    if not qdrant_api_key:
        raise ValueError(
            "QDRANT_API_KEY không được tìm thấy trong file .env. "
            "Vui lòng kiểm tra file .env trong thư mục MedAgent/"
        )
    
    client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key, timeout=60)
    return client

if __name__ == "__main__":
    rag_client = get_rag_client()
    
    print(rag_client.get_collections())
