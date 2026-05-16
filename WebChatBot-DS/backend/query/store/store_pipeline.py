"""
Store Pipeline - Xử lý các câu hỏi về kho hàng, thống kê và vẽ biểu đồ.
Sử dụng GPT để tạo SQL query và vẽ biểu đồ thống kê.
"""
from query.core import get_llm
from pydantic import BaseModel
from typing import Optional
import io
import logging
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_DIR = BASE_DIR / 'sqlite-db' / "database"
DB_PATH = DB_DIR / "drug-warehouse.db"

# Tạo thư mục database nếu chưa tồn tại
DB_DIR.mkdir(parents=True, exist_ok=True)

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib

# Cấu hình matplotlib để hiển thị tiếng Việt
matplotlib.rcParams['font.family'] = ['DejaVu Sans', 'Arial Unicode MS', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False

# Optional import for cv2, fallback to PIL if not available
try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False
    try:
        from PIL import Image
        HAS_PIL = True
    except ImportError:
        HAS_PIL = False

from langchain_core.prompts import ChatPromptTemplate
from langchain_community.utilities import SQLDatabase
from langchain_core.tools import tool
from sqlalchemy import text
from ..prompt_templates import SYSTEM_STORE_PLAN_PROMPT, SYSTEM_STORE_ANSWER_PROMPT, USER_STORE_ANSWER_PROMPT
from ..core import AnswerQuery, QueryPlan

# Cấu hình logger
logger = logging.getLogger(__name__)


def create_chart(chart_type: str, df: pd.DataFrame, x: str, y: str, title: str = "Biểu đồ") -> np.ndarray:
    """
    Tạo biểu đồ từ DataFrame với nhiều loại biểu đồ hỗ trợ.
    
    Args:
        chart_type: Loại biểu đồ (line, bar, pie, horizontal_bar, area)
        df: DataFrame chứa dữ liệu
        x: Tên cột trục x
        y: Tên cột trục y
        title: Tiêu đề biểu đồ
    
    Returns:
        numpy array của hình ảnh
    """
    # Tạo figure với kích thước phù hợp
    fig, ax = plt.subplots(figsize=(12, 7))
    
    # Chuẩn bị dữ liệu
    x_data = df[x].astype(str) if x in df.columns else df.iloc[:, 0].astype(str)
    y_data = pd.to_numeric(df[y], errors='coerce') if y in df.columns else pd.to_numeric(df.iloc[:, 1], errors='coerce')
    
    # Màu sắc chuyên nghiệp
    colors = ['#0d9488', '#14b8a6', '#2dd4bf', '#5eead4', '#99f6e4',
              '#0ea5e9', '#38bdf8', '#7dd3fc', '#bae6fd', '#e0f2fe']
    
    if chart_type == "line":
        ax.plot(x_data, y_data, marker='o', linewidth=2.5, markersize=8, color=colors[0])
        ax.fill_between(range(len(x_data)), y_data, alpha=0.3, color=colors[0])
        
    elif chart_type == "bar":
        bars = ax.bar(x_data, y_data, color=colors[:len(x_data)], edgecolor='white', linewidth=1.2)
        # Thêm giá trị trên đầu mỗi cột
        for bar, val in zip(bars, y_data):
            height = bar.get_height()
            ax.annotate(f'{val:,.0f}',
                       xy=(bar.get_x() + bar.get_width() / 2, height),
                       xytext=(0, 5),
                       textcoords="offset points",
                       ha='center', va='bottom', fontsize=9, fontweight='bold')
        
    elif chart_type == "horizontal_bar" or chart_type == "barh":
        bars = ax.barh(x_data, y_data, color=colors[:len(x_data)], edgecolor='white', linewidth=1.2)
        # Thêm giá trị bên phải mỗi thanh
        for bar, val in zip(bars, y_data):
            width = bar.get_width()
            ax.annotate(f'{val:,.0f}',
                       xy=(width, bar.get_y() + bar.get_height() / 2),
                       xytext=(5, 0),
                       textcoords="offset points",
                       ha='left', va='center', fontsize=9, fontweight='bold')
                       
    elif chart_type == "pie":
        # Tạo pie chart đẹp hơn
        wedges, texts, autotexts = ax.pie(
            y_data,
            labels=x_data,
            autopct='%1.1f%%',
            colors=colors[:len(x_data)],
            explode=[0.02] * len(x_data),
            shadow=True,
            startangle=90
        )
        for autotext in autotexts:
            autotext.set_fontweight('bold')
            autotext.set_fontsize(10)
        ax.axis('equal')
        
    elif chart_type == "area":
        ax.fill_between(range(len(x_data)), y_data, alpha=0.6, color=colors[0])
        ax.plot(range(len(x_data)), y_data, marker='o', linewidth=2, color=colors[0])
        ax.set_xticks(range(len(x_data)))
        ax.set_xticklabels(x_data, rotation=45, ha='right')
    
    else:
        # Mặc định là bar chart
        bars = ax.bar(x_data, y_data, color=colors[:len(x_data)], edgecolor='white')
    
    # Styling chung
    ax.set_title(title, fontsize=16, fontweight='bold', pad=20, color='#1e293b')
    
    if chart_type != "pie":
        ax.set_xlabel(x, fontsize=12, fontweight='medium', color='#475569')
        ax.set_ylabel(y, fontsize=12, fontweight='medium', color='#475569')
        
        # Grid nhẹ nhàng
        ax.yaxis.grid(True, linestyle='--', alpha=0.3, color='#94a3b8')
        ax.set_axisbelow(True)
        
        # Xoay label trục x nếu dài
        if len(x_data) > 5 or any(len(str(label)) > 10 for label in x_data):
            plt.xticks(rotation=45, ha='right')
        
        # Format số trên trục y
        ax.get_yaxis().set_major_formatter(
            matplotlib.ticker.FuncFormatter(lambda x, p: format(int(x), ','))
        )
        
        # Bỏ viền trên và phải
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color('#cbd5e1')
        ax.spines['bottom'].set_color('#cbd5e1')
    
    plt.tight_layout()
    
    # Chuyển sang numpy array
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close(fig)
    
    buf.seek(0)
    if HAS_CV2:
        return cv2.imdecode(np.frombuffer(buf.getvalue(), np.uint8), cv2.IMREAD_COLOR)
    elif HAS_PIL:
        img = Image.open(buf)
        return np.array(img)
    else:
        return buf.getvalue()


@tool
def plot_chart(payload: dict):
    """
    Vẽ biểu đồ từ dữ liệu SQL.

    payload:
      chart_type: line | bar | pie | horizontal_bar | area
      data: list[dict]
      x: cột trục x
      y: cột trục y
      title: tiêu đề (optional)
    """
    return create_chart(
        chart_type=payload["chart_type"],
        df=pd.DataFrame(payload["data"]),
        x=payload["x"],
        y=payload["y"],
        title=payload.get("title", "Biểu đồ thống kê")
    )

    
def dataframe_to_markdown(df: pd.DataFrame, max_rows: int = 50) -> str:
    """
    Chuyển DataFrame thành markdown table.
    
    Args:
        df: DataFrame cần chuyển
        max_rows: Số dòng tối đa hiển thị
    
    Returns:
        Markdown string
    """
    if df.empty:
        return "Không có dữ liệu phù hợp."

    if len(df) <= max_rows:
        return df.to_markdown(index=False)

    return (
        f"Dữ liệu có {len(df)} dòng.\n\n"
        f"{max_rows} dòng đầu:\n"
        f"{df.head(max_rows).to_markdown(index=False)}"
    )


class StorePipeline:
    """
    Pipeline xử lý các câu hỏi về kho hàng và thống kê.
    Sử dụng GPT để:
    1. Phân tích câu hỏi và tạo SQL query
    2. Quyết định có cần vẽ biểu đồ không
    3. Tạo câu trả lời từ kết quả query
    """
    
    def __init__(self, db_path: str = None):
        """
        Khởi tạo StorePipeline.
        
        Args:
            db_path: Đường dẫn tới SQLite database
        """
        if db_path is None:
            db_path = f"sqlite:///{DB_PATH}"
        
        # Sử dụng GPT thay vì openai-oss
        llm = get_llm("gpt-4o-mini")  # Dùng GPT-4o-mini cho tốc độ và chi phí
        plan_llm = llm.with_structured_output(QueryPlan)
        answer_llm = llm.with_structured_output(AnswerQuery)
        
        # Kiểm tra và tạo database nếu chưa tồn tại
        if not DB_PATH.exists():
            logger.warning(f"Database chưa tồn tại tại: {DB_PATH}")
            logger.warning("Đang tạo database trống. Vui lòng chạy script tạo schema:")
            logger.warning("  cd sqlite-db/src && python main.py")
            # Tạo database trống
            import sqlite3
            conn = sqlite3.connect(str(DB_PATH))
            conn.close()
            logger.info(f"Đã tạo database trống tại: {DB_PATH}")
        
        try:
            self.db = SQLDatabase.from_uri(db_path)
            logger.info(f"Connected to database: {db_path}")
        except Exception as e:
            logger.error(f"Không thể kết nối database: {e}")
            logger.error(f"Đường dẫn database: {db_path}")
            raise
        
        self._get_prompt()
        self.plan_chain = self.plan_prompt | plan_llm 
        self.answer_chain = self.answer_prompt | answer_llm
        
        logger.info("StorePipeline initialized with GPT-4o-mini")
    
    def _get_prompt(self):
        """Khởi tạo các prompt templates."""
        self.plan_prompt = ChatPromptTemplate.from_template(SYSTEM_STORE_PLAN_PROMPT)
        self.answer_prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_STORE_ANSWER_PROMPT),
            ("human", USER_STORE_ANSWER_PROMPT),
        ])

    def query(self, query: str) -> dict:
        """
        Xử lý câu hỏi về kho hàng/thống kê.
        
        Args:
            query: Câu hỏi từ người dùng
        
        Returns:
            dict với keys:
                - text: Câu trả lời text
                - is_image: True nếu có biểu đồ
                - image: numpy array của biểu đồ (nếu có)
                - steps: Danh sách các bước xử lý
        """
        logger.info(f"Processing store query: {query}")
        steps = []
        
        # Bước 1: Tạo query plan (SQL + chart config)
        steps.append("2. Query Plan: Tao SQL query va cau hinh bieu do")
        plan: QueryPlan = self.plan_chain.invoke({
            "question": query,
            "schema": self.db.get_table_info()
        })
        
        logger.info(f"Generated SQL: {plan.sql}")
        logger.info(f"Need chart: {plan.need_chart}, Type: {plan.chart_type}")
        steps.append(f"   - SQL: {plan.sql[:100]}..." if len(plan.sql) > 100 else f"   - SQL: {plan.sql}")
        steps.append(f"   - Can bieu do: {'Co' if plan.need_chart else 'Khong'}")
        if plan.need_chart:
            steps.append(f"   - Loai bieu do: {plan.chart_type}")
        
        # Bước 2: Thực thi SQL
        steps.append("3. Execute SQL: Thuc thi query tren database")
        try:
            with self.db._engine.connect() as conn:
                result = conn.execute(text(plan.sql))
                df = pd.DataFrame(result.fetchall(), columns=result.keys())
            
            logger.info(f"Query returned {len(df)} rows")
            steps.append(f"   - Ket qua: {len(df)} dong du lieu")
        except Exception as e:
            logger.error(f"SQL execution error: {e}")
            steps.append(f"   - Loi: {str(e)}")
            return {
                'text': f"Lỗi khi thực thi truy vấn: {str(e)}",
                'is_image': False,
                'image': None,
                'steps': steps
            }
        
        # Bước 3: Nếu không cần chart, trả về text answer
        if not plan.need_chart:
            steps.append("4. Generate Answer: Tao cau tra loi tu du lieu")
            df_string = dataframe_to_markdown(df)
            res_ans = self.answer_chain.invoke({
                'context': df_string,
                'query': query
            })
            steps.append("   - Hoan thanh: Tra ve cau tra loi text")
            return {
                'text': res_ans.answer,
                'is_image': False,
                'image': None,
                'steps': steps
            }

        # Bước 4: Vẽ biểu đồ
        steps.append("4. Create Chart: Ve bieu do thong ke")
        try:
            # Xác định cột x và y
            x_col = plan.x if plan.x and plan.x in df.columns else df.columns[0]
            y_col = plan.y if plan.y and plan.y in df.columns else df.columns[1] if len(df.columns) > 1 else df.columns[0]
            
            image = create_chart(
                chart_type=plan.chart_type or "bar",
                df=df,
                x=x_col,
                y=y_col,
                title=plan.title or "Biểu đồ thống kê"
            )
            
            # Tạo text mô tả kèm theo
            df_string = dataframe_to_markdown(df, max_rows=10)
            description = f"**{plan.title or 'Biểu đồ thống kê'}**\n\nDữ liệu chi tiết:\n\n{df_string}"
            
            logger.info("Chart generated successfully")
            steps.append(f"   - Hoan thanh: Bieu do {plan.chart_type} da duoc tao")
            
            return {
                'text': description,
                'is_image': True,
                'image': image,
                'steps': steps
            }
            
        except Exception as e:
            logger.error(f"Chart generation error: {e}")
            steps.append(f"   - Loi: {str(e)} -> Fallback ve text")
            # Fallback: trả về text nếu không vẽ được chart
            df_string = dataframe_to_markdown(df)
            res_ans = self.answer_chain.invoke({
                'context': df_string,
                'query': query
            })
            return {
                'text': res_ans.answer + f"\n\n(Không thể vẽ biểu đồ: {str(e)})",
                'is_image': False,
                'image': None,
                'steps': steps
            }


if __name__ == "__main__":
    # Test StorePipeline
    pipeline = StorePipeline()
    
    # Test 1: Query đơn giản
    result = pipeline.query("Có bao nhiêu loại thuốc trong kho?")
    print("Result 1:", result['text'])
    
    # Test 2: Query với biểu đồ
    result = pipeline.query("Vẽ biểu đồ top 5 nhà cung cấp theo giá trị nhập hàng")
    print("Result 2:", result['text'])
    print("Has image:", result['is_image'])
