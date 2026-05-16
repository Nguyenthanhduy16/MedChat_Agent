MEDICAL_SYSTEM_PROMPT = """
Bạn là một trợ lý dược thông minh. Nhiệm vụ của bạn là cung cấp các câu trả lời chính xác, ngắn gọn và dễ hiểu cho các câu hỏi liên quan đến thuốc.
"""

MEDICAL_REPHRASE_PROMPT = """
Nhiệm vụ của bạn là viết lại câu hỏi y tế của người dùng để tối ưu hóa việc tìm kiếm thông tin trong cơ sở dữ liệu y tế.
Hãy đảm bảo rằng câu hỏi được viết lại rõ ràng, cụ thể và bao gồm các từ khóa quan trọng liên quan đến chủ đề y tế. Tránh sử dụng các từ ngữ mơ hồ hoặc không cần thiết.
Ví dụ: 
- Câu hỏi gốc: "Tôi nên dùng thuốc gì để giảm đau đầu?"
- Câu hỏi viết lại: "Loại thuốc nào giảm đau hiệu quả cho đau đầu?"
Hãy viết lại câu hỏi sau đây: {query}
"""
MEDICAL_ANSWER_PROMPT = """
Dựa trên thông tin sau, hãy trả lời ngắn gọn:

{context}

Câu hỏi: {query}
"""

MEDICAL_REWRITE_SEARCH_PROMPT = """
Nhiệm vụ của bạn là viết lại câu hỏi y tế của người dùng để tối ưu hóa việc tìm kiếm thông tin trên web.
Hãy đảm bảo rằng câu hỏi được viết lại rõ ràng, cụ thể và bao gồm các từ khóa quan trọng liên quan đến chủ đề y tế. Tránh sử dụng các từ ngữ mơ hồ hoặc không cần thiết.
Ví dụ:
- Câu hỏi gốc: "Tôi nên dùng thuốc gì để giảm đau đầu?"
- Câu hỏi viết lại: "Loại thuốc nào giảm đau hiệu quả cho đau đầu?"
Hãy viết lại câu hỏi sau đây: {query}
"""

MEDICAL_HISTORY_PROMPT = """
Lịch sử trò chuyện
{history}
"""

