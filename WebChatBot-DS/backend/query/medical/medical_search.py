import requests
import numpy as np
from ddgs import DDGS
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, TimeoutError, Error as PlaywrightError
from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings
import os
from dotenv import load_dotenv

# Tìm file .env trong thư mục MedAgent (thư mục gốc của project)
env_path = os.path.join(os.path.dirname(__file__), "../../../.env")
load_dotenv(dotenv_path=env_path)
from langchain_core.prompts import ChatPromptTemplate
from langchain_text_splitters import RecursiveCharacterTextSplitter
from query.core.structure import RouteQuery

from ..core import AnswerQuery, get_llm
from ..prompt_templates import MEDICAL_ANSWER_PROMPT, MEDICAL_SYSTEM_PROMPT

def web_search(query: str, max_results: int = 5):
    with DDGS() as ddgs:
        results = ddgs.text(query, max_results=max_results)
    urls = [r.get("href") for r in results if r.get("href")]
    return urls

def clean_text(soup):
    # soup là list các <p> hoặc bs4 element
    raw_text = "\n".join([p.get_text() for p in soup])

    # tách từng dòng, loại bỏ các dòng trắng
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]

    # nối lại với 1 newline giữa các dòng
    clean = "\n".join(lines)
    return clean

def crawl_page(url: str, timeout: int = 10000) -> str:
    """
    Crawl một trang web và trả về text content.
    
    Args:
        url: URL cần crawl
        timeout: Timeout cho việc load trang (ms)
        
    Returns:
        str: Text content của trang, hoặc empty string nếu có lỗi
    """
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, timeout=timeout)
            content = page.content()
            browser.close()
            
            # Dùng BeautifulSoup để extract text
            soup = BeautifulSoup(content, "html.parser")
            text = clean_text(soup)
            return text
    except (PlaywrightError, TimeoutError) as e:
        print(f"[WARN] Không thể truy cập {url}: {e}")
        return ""
    except Exception as e:
        print(f"[WARN] Lỗi khi crawl {url}: {e}")
        return ""

class WebSearchCrawler:
    def __init__(self, max_results: int = 5):
        self.max_results = max_results

    def search(self, query: str):
        results = web_search(query, self.max_results)
        return results

    def crawl(self, results):
        crawled_texts = {}
        for url in results:
            text = crawl_page(url)
            crawled_texts[url] = text
        return crawled_texts

    def search_and_crawl(self, query: str):
        results = self.search(query)
        if not results:
            print("No search results found.")
            return {}
        crawled_texts = self.crawl(results)
        return crawled_texts
    
class WebInfoRetriever:
    def __init__(self, top_k: int = 5, threshold: float = 0.1):
        self.splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=50)
        # Sử dụng model embedding text-embedding-004 của Google
        self.embedder = GoogleGenerativeAIEmbeddings(
            model="models/text-embedding-004",
            google_api_key=os.getenv("GOOGLE_API_KEY"),
        )
        self.top_k = top_k
        self.threshold = threshold

    def chunk_text(self, text: str):
        chunks = self.splitter.split_text(text)
        return chunks
    
    def retrieve(self, contexts: dict):
        relevant_chunks = []
        for url, text in contexts.items():
            chunks = self.chunk_text(text)
            for i, chunk in enumerate(chunks):
                doc = Document(
                    page_content=chunk,
                    metadata={"source": url, "chunk_id": i}
                )
                relevant_chunks.append(doc)
        if not relevant_chunks:
            print("No relevant chunks found.")
            return None
        vectorstore = FAISS.from_documents(relevant_chunks, self.embedder)
        retriever = vectorstore.as_retriever(search_kwargs={"k": self.top_k})
        return retriever



class MedicalSearch:
    def __init__(self, max_results: int = 3):
        self.llm = get_llm()
        self.prompt = self._create_prompt()
        self.structured_llm = self.llm.with_structured_output(AnswerQuery)
        self.max_results = max_results
        self.web_crawler = WebSearchCrawler(max_results=self.max_results)
        self.info_retriever = WebInfoRetriever()
        self.search_chain = self.prompt | self.structured_llm
        
    def _create_prompt(self):
        return ChatPromptTemplate.from_messages([
                ("system", MEDICAL_SYSTEM_PROMPT),
                ("human", MEDICAL_ANSWER_PROMPT),
            ])

    def answer_query(self, query: str, context: str):
        print("Answering query...")
        response = self.search_chain.invoke({"query": query, "context": context})
        return response


    def answer(self, query: str):
        web_infos = self.web_crawler.search_and_crawl(query)
        retriever = self.info_retriever.retrieve(web_infos)
        if not retriever:
            return AnswerQuery(answer="Xin lỗi, tôi không tìm thấy thông tin phù hợp để trả lời câu hỏi của bạn.", source="Không có nguồn.")
        relevant_docs = retriever.invoke(query)
        print(f"Found {len(relevant_docs)} relevant documents.")
        combined_context = "\n\n".join(
            f"[Nguồn: {doc.metadata.get('source', 'unknown')}] {doc.page_content}"
            for doc in relevant_docs
        )
        return self.answer_query(query, combined_context)

if __name__ == "__main__":
    medical_search = MedicalSearch(max_results=3)
    query = "thông tin thuốc Xương Khớp?"
    results = medical_search.answer(query)
    print("Kết quả tìm kiếm và trả lời:")
    print(results.answer)
    print("Nguồn:")
    print(results.source)