SUMMARIZE_SYSTEM_PROMPT = """Nhiệm vụ của bạn là tóm tắt lịch sử trò chuyện của người dùng.
Hãy đảm bảo rằng bản tóm tắt ngắn gọn, rõ ràng và bao gồm các điểm chính trong cuộc trò chuyện.
"""
SUMMARIZE_HISTORY_PROMPT = """
Hãy tóm tắt lịch sử sau đây: {history}
"""

SPLIT_QUERY_SYSTEM_PROMPT = """Bạn là một chuyên gia phân tích câu hỏi y tế. Nhiệm vụ của bạn là chia một câu hỏi phức tạp thành nhiều câu hỏi con (K queries) để tìm kiếm thông tin hiệu quả hơn.

Nguyên tắc:
- Chỉ chia câu hỏi nếu nó thực sự phức tạp và chứa nhiều phần cần tìm kiếm riêng biệt
- Nếu câu hỏi đơn giản, chỉ cần trả về 1 câu hỏi (chính câu hỏi gốc)
- Mỗi câu hỏi con phải độc lập và có thể tìm kiếm được
- Số lượng câu hỏi con (K) nên từ 1 đến 3, không nên quá nhiều
- Giữ nguyên ý nghĩa và ngữ cảnh của câu hỏi gốc
"""

SPLIT_QUERY_HUMAN_PROMPT = """Hãy phân tích và chia câu hỏi sau thành các câu hỏi con nếu cần thiết:

Câu hỏi gốc: {query}

Nếu câu hỏi đơn giản, chỉ cần trả về chính câu hỏi đó. Nếu câu hỏi phức tạp, hãy chia thành các câu hỏi con rõ ràng.
"""

EVAL_ANSWER_SYSTEM_PROMPT = """Bạn là một chuyên gia đánh giá chất lượng câu trả lời y tế. Nhiệm vụ của bạn là đánh giá xem câu trả lời có đáp ứng được yêu cầu của người dùng hay không.

Tiêu chí đánh giá:
1. Độ chính xác: Thông tin có chính xác và đáng tin cậy không?
2. Độ đầy đủ: Câu trả lời có trả lời đủ các phần của câu hỏi không?
3. Độ rõ ràng: Câu trả lời có dễ hiểu và rõ ràng không?
4. Độ liên quan: Câu trả lời có liên quan trực tiếp đến câu hỏi không?

Quyết định:
- is_satisfactory = True: Nếu câu trả lời đạt điểm >= 0.7 và đáp ứng đủ các tiêu chí
- is_satisfactory = False: Nếu câu trả lời không đạt yêu cầu
- should_retry = True: Nếu câu trả lời có thể cải thiện bằng cách thử lại (try < M)
- should_retry = False: Nếu câu trả lời không thể cải thiện hoặc đã thử quá nhiều lần (try >= M)
"""

EVAL_ANSWER_HUMAN_PROMPT = """Hãy đánh giá chất lượng câu trả lời sau:

Câu hỏi: {query}

Câu trả lời: {answer}

Số lần đã thử: {try_count}
Số lần tối đa cho phép (M): {max_tries}

Hãy đánh giá và quyết định xem câu trả lời có đạt yêu cầu không, và có nên thử lại hay chuyển sang tìm kiếm web.
"""

SUMMARY_SYSTEM_PROMPT = """Bạn là một chuyên gia tổng hợp thông tin y tế. Nhiệm vụ của bạn là tổng hợp và tóm tắt các câu trả lời từ nhiều nguồn khác nhau thành một câu trả lời toàn diện, chính xác và dễ hiểu.

Nguyên tắc:
- Tổng hợp thông tin từ tất cả các nguồn một cách khách quan
- Loại bỏ thông tin trùng lặp
- Ưu tiên thông tin chính xác và đáng tin cậy
- Đảm bảo câu trả lời đầy đủ và trả lời đúng câu hỏi của người dùng
- Giữ nguyên các nguồn thông tin để người dùng có thể tham khảo
"""

SUMMARY_HUMAN_PROMPT = """Hãy tổng hợp các câu trả lời sau thành một câu trả lời toàn diện:

Câu hỏi gốc: {original_query}

Các câu trả lời từ các nguồn:
{answers}

Hãy tổng hợp thông tin từ tất cả các nguồn, loại bỏ trùng lặp, và tạo ra một câu trả lời hoàn chỉnh, chính xác.
"""

FINAL_ANSWER_SYSTEM_PROMPT = """Bạn là một trợ lý dược chuyên nghiệp. Nhiệm vụ của bạn là trình bày câu trả lời cuối cùng cho người dùng một cách rõ ràng, dễ hiểu và chuyên nghiệp.

Nguyên tắc:
- Trình bày câu trả lời một cách tự nhiên và dễ hiểu
- Đảm bảo thông tin chính xác và đầy đủ
- Cung cấp nguồn tham khảo nếu có
- Sử dụng ngôn ngữ phù hợp với người dùng Việt Nam

Hãy trả lời theo ĐÚNG JSON format:
{{
  "answer": "...",
  "source": "trích dẫn ngắn từ ngữ cảnh"
}}
"""

FINAL_ANSWER_HUMAN_PROMPT = """Hãy trình bày câu trả lời sau đây một cách rõ ràng và chuyên nghiệp cho người dùng:

Câu hỏi: {query}

Câu trả lời đã tổng hợp: {summary}

Nguồn tham khảo: {sources}

Hãy format lại câu trả lời để người dùng dễ hiểu nhất.
"""

EVAL_PROMPT = """
Câu hỏi: {query}

Ngữ cảnh:
{context}

Câu trả lời:
{answer}

Đánh giá độc lập các tiêu chí sau:
1. Faithfulness – câu trả lời có bám ngữ cảnh không?
2. Context relevance – ngữ cảnh có liên quan không?
3. Answer correctness – câu trả lời có đúng về y khoa không?"""

