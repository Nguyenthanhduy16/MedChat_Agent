"""
Script để embedding dữ liệu thuốc và upload lên Qdrant
Sử dụng Google Generative AI Embeddings (text-embedding-004)
"""
import os
import json
from pathlib import Path
from typing import List, Dict, Any
from dotenv import load_dotenv
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
import time


env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    # Thử load từ thư mục hiện tại
    load_dotenv()

# Configuration
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
COLLECTION_NAME = "embedding_data"
EMBEDDING_MODEL = "models/text-embedding-004"

# Đường dẫn đến thư mục data
# Tự động detect Kaggle environment
if Path("/kaggle/working").exists():
    # Đang chạy trên Kaggle
    BASE_DIR = Path("/kaggle/working/Project3")
    DATA_DIR = BASE_DIR / "drugs-data-main" / "data" / "details"
else:
    # Chạy local
    DATA_DIR = Path(__file__).parent.parent / "drugs-data-main" / "data" / "details"

# Cấu hình chunking
# Google text-embedding-004 có giới hạn ~2048 tokens
# Ước tính: 1 token ≈ 4 ký tự (tiếng Việt)
# Chunk size: 1500 ký tự ≈ 375 tokens (an toàn, để lại buffer)
# Chunk overlap: 200 ký tự để giữ ngữ cảnh giữa các chunks
CHUNK_SIZE = 1500
CHUNK_OVERLAP = 200

# Cấu hình cho Kaggle (không cần input)
# Set KAGGLE_MODE=True để tự động xóa collection cũ và bỏ qua input()
KAGGLE_MODE = os.getenv("KAGGLE_MODE", "False").lower() == "true"


def create_documents_from_json(json_file: Path) -> List[Document]:
    """
    Tạo documents từ một file JSON thuốc
    Mỗi file JSON sẽ tạo ra một document tổng hợp
    """
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Lấy tên file (không có extension) làm ID
        file_name = json_file.stem
        
        # Lấy category từ đường dẫn (tên folder cha)
        category = json_file.parent.name
        
        # Tạo nội dung tổng hợp từ các trường
        content_parts = []
        
        # Thêm mô tả
        if data.get("describe"):
            content_parts.append(f"Danh mục:\n{category}\n\nTên thuốc:\n{file_name}\n\nMô tả:\n{data['describe']}")
        
        # Thêm thành phần
        if data.get("ingredient"):
            content_parts.append(f"\nThành phần:\n{data['ingredient']}")
        
        # Thêm công dụng
        if data.get("usage"):
            content_parts.append(f"\nCông dụng:\n{data['usage']}")
        
        # Thêm liều dùng
        if data.get("dosage"):
            content_parts.append(f"\nLiều dùng:\n{data['dosage']}")
        
        # Thêm tác dụng phụ
        if data.get("adverse_effect"):
            content_parts.append(f"\nTác dụng phụ:\n{data['adverse_effect']}")
        
        # Thêm lưu ý
        if data.get("careful"):
            content_parts.append(f"\nLưu ý:\n{data['careful']}")
        
        # Thêm bảo quản
        if data.get("preservation"):
            content_parts.append(f"\nBảo quản:\n{data['preservation']}")
        
        # Tạo document
        page_content = "\n".join(content_parts)
        
        # Metadata
        metadata = {
            "id": file_name,
            "category": category,
            "file_name": file_name,
        }
        
        return [Document(page_content=page_content, metadata=metadata)]
    
    except Exception as e:
        print(f"Lỗi khi đọc file {json_file}: {e}")
        return []


def chunk_documents(documents: List[Document]) -> List[Document]:
    """
    Chia nhỏ documents thành các chunks nhỏ hơn để phù hợp với giới hạn embedding
    """
    print(f"\nĐang chunking {len(documents)} documents...")
    print(f"Chunk size: {CHUNK_SIZE} ký tự, Overlap: {CHUNK_OVERLAP} ký tự")
    
    # Khởi tạo text splitter
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""]  # Ưu tiên tách theo đoạn, câu, từ
    )
    
    chunked_documents = []
    total_chunks = 0
    
    for doc in documents:
        # Chunk document
        chunks = text_splitter.split_documents([doc])
        
        # Cập nhật metadata cho mỗi chunk
        for chunk_idx, chunk in enumerate(chunks):
            # Thêm thông tin chunk vào metadata
            chunk.metadata["chunk_index"] = chunk_idx
            chunk.metadata["total_chunks"] = len(chunks)
            # Tạo unique ID cho chunk (file_name + chunk_index)
            chunk.metadata["chunk_id"] = f"{doc.metadata['file_name']}_chunk_{chunk_idx}"
        
        chunked_documents.extend(chunks)
        total_chunks += len(chunks)
    
    print(f"Tổng số chunks sau khi chia nhỏ: {total_chunks}")
    print(f"Trung bình: {total_chunks/len(documents):.2f} chunks/document")
    
    return chunked_documents


def load_all_documents(data_dir: Path) -> List[Document]:
    """
    Load tất cả documents từ các file JSON trong thư mục data
    Sau đó chunk các documents để phù hợp với giới hạn embedding
    """
    documents = []
    json_files = list(data_dir.rglob("*.json"))
    total_files = len(json_files)
    
    print(f"Tìm thấy {total_files} file JSON")
    print("Đang load documents...\n")
    
    for idx, json_file in enumerate(json_files, 1):
        docs = create_documents_from_json(json_file)
        documents.extend(docs)
        
        if idx % 100 == 0:
            print(f"Đã load {idx}/{total_files} files...")
    
    print(f"\nTổng số documents trước khi chunking: {len(documents)}")
    
    # Chunk documents
    chunked_documents = chunk_documents(documents)
    
    return chunked_documents


def setup_qdrant_collection(client: QdrantClient, collection_name: str, embedding_dim: int = 768, auto_delete: bool = False):
    """
    Tạo collection trên Qdrant nếu chưa tồn tại
    text-embedding-004 có dimension là 768
    
    Args:
        auto_delete: Nếu True, tự động xóa collection cũ nếu tồn tại (dùng cho Kaggle)
    """
    try:
        # Kiểm tra collection đã tồn tại chưa
        collections = client.get_collections()
        collection_exists = any(col.name == collection_name for col in collections.collections)
        
        if collection_exists:
            print(f"Collection '{collection_name}' đã tồn tại.")
            if auto_delete:
                print("Tự động xóa collection cũ (Kaggle mode)...")
                client.delete_collection(collection_name)
                print(f"Đã xóa collection '{collection_name}'")
            else:
                response = input("Bạn có muốn xóa và tạo lại collection? (yes/no): ")
                if response.lower() in ['yes', 'y', 'có', 'c']:
                    client.delete_collection(collection_name)
                    print(f"Đã xóa collection '{collection_name}'")
                else:
                    print("Sử dụng collection hiện có.")
                    return
        
        # Tạo collection mới
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=embedding_dim,
                distance=Distance.COSINE
            )
        )
        print(f"Đã tạo collection '{collection_name}' với dimension {embedding_dim}")
    
    except Exception as e:
        print(f"Lỗi khi setup collection: {e}")
        raise


def upload_to_qdrant(documents: List[Document], batch_size: int = 100):
    """
    Upload documents lên Qdrant với embedding
    """
    # Khởi tạo embeddings
    # GoogleGenerativeAIEmbeddings sẽ tự động lấy GOOGLE_API_KEY từ environment variable
    print("\nĐang khởi tạo Google Generative AI Embeddings...")
    embeddings = GoogleGenerativeAIEmbeddings(
        model=EMBEDDING_MODEL
    )
    
    # Khởi tạo Qdrant client
    print("Đang kết nối với Qdrant...")
    client = QdrantClient(
        url=QDRANT_URL,
        api_key=QDRANT_API_KEY,
        timeout=300
    )
    
    # Setup collection
    print("\nĐang setup collection...")
    setup_qdrant_collection(client, COLLECTION_NAME, embedding_dim=768, auto_delete=KAGGLE_MODE)
    
    # Khởi tạo vector store
    print("\nĐang khởi tạo vector store...")
    vector_store = QdrantVectorStore(
        client=client,
        collection_name=COLLECTION_NAME,
        embedding=embeddings
    )
    
    # Upload documents theo batch
    total_docs = len(documents)
    print(f"\nBắt đầu upload {total_docs} documents lên Qdrant...")
    print(f"Batch size: {batch_size}\n")
    
    start_time = time.time()
    
    for i in range(0, total_docs, batch_size):
        batch = documents[i:i + batch_size]
        batch_num = (i // batch_size) + 1
        total_batches = (total_docs + batch_size - 1) // batch_size
        
        try:
            # Upload batch
            vector_store.add_documents(batch)
            
            elapsed_time = time.time() - start_time
            avg_time_per_batch = elapsed_time / batch_num
            remaining_batches = total_batches - batch_num
            estimated_remaining = avg_time_per_batch * remaining_batches
            
            print(f"Batch {batch_num}/{total_batches}: Đã upload {min(i + batch_size, total_docs)}/{total_docs} documents "
                  f"(Ước tính còn lại: {estimated_remaining/60:.1f} phút)")
        
        except Exception as e:
            print(f"Lỗi khi upload batch {batch_num}: {e}")
            continue
    
    total_time = time.time() - start_time
    print(f"\n{'='*60}")
    print(f"Hoàn thành!")
    print(f"Tổng số documents: {total_docs}")
    print(f"Thời gian: {total_time/60:.2f} phút")
    print(f"{'='*60}")


def main():
    """
    Hàm chính
    """
    print("="*60)
    print("Script Embedding và Upload lên Qdrant")
    print("="*60)
    print(f"Data directory: {DATA_DIR}")
    print(f"Collection name: {COLLECTION_NAME}")
    print(f"Embedding model: {EMBEDDING_MODEL}")
    print()
    
    # Kiểm tra environment variables
    if not QDRANT_URL or not QDRANT_API_KEY:
        print("Lỗi: Thiếu QDRANT_URL hoặc QDRANT_API_KEY trong file .env")
        print("Vui lòng tạo file .env trong thư mục gốc của project với các biến sau:")
        print("QDRANT_URL=your_qdrant_url")
        print("QDRANT_API_KEY=your_qdrant_api_key")
        print("GOOGLE_API_KEY=your_google_api_key")
        return
    
    if not GOOGLE_API_KEY:
        print("Lỗi: Thiếu GOOGLE_API_KEY trong file .env")
        print("Vui lòng thêm GOOGLE_API_KEY vào file .env")
        return
    
    # Kiểm tra thư mục data
    if not DATA_DIR.exists():
        print(f"Lỗi: Thư mục {DATA_DIR} không tồn tại!")
        return
    
    # Load documents
    documents = load_all_documents(DATA_DIR)
    
    if not documents:
        print("Không tìm thấy documents nào!")
        return
    
    # Xác nhận trước khi upload (bỏ qua nếu KAGGLE_MODE)
    if not KAGGLE_MODE:
        print(f"\nBạn sắp upload {len(documents)} documents lên Qdrant.")
        response = input("Bạn có chắc chắn muốn tiếp tục? (yes/no): ")
        if response.lower() not in ['yes', 'y', 'có', 'c']:
            print("Đã hủy bỏ.")
            return
    else:
        print(f"\nBắt đầu upload {len(documents)} documents lên Qdrant (Kaggle mode)...")
    
    # Upload lên Qdrant
    upload_to_qdrant(documents)


if __name__ == "__main__":
    main()

