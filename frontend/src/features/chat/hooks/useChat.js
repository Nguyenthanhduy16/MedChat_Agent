import { useState, useCallback } from 'react';
import { v4 as uuidv4 } from 'uuid';
import { chatApi } from '../services/chatApi';
import { useToast } from '../../../context/ToastContext';

// Toggles between mock data and real API calls
const USE_MOCK = false;

/**
 * useChat Hook
 * Quản lý trạng thái cuộc trò chuyện, tin nhắn, loading và lỗi.
 */
export function useChat() {
  const { addToast } = useToast();
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [currentSessionId, setCurrentSessionId] = useState(() => uuidv4());

  // Lấy thời gian hiện tại định dạng HH:MM AM/PM
  const getCurrentTime = () => {
    return new Date().toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,
    });
  };

  const sendMessage = useCallback(async (content) => {
    if (!content.trim()) return;
    console.log('useChat: sendMessage called with:', content);

    // 1. Thêm tin nhắn của User
    const userMessage = {
      id: uuidv4(),
      role: 'user',
      content: content.trim(),
      timestamp: getCurrentTime(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);
    setError(null);

    try {
      let botResponse;

      if (USE_MOCK) {
        // GIẢ LẬP GỌI API
        await new Promise((resolve) => setTimeout(resolve, 1500));
        
        botResponse = {
          answer: "Đây là câu trả lời mẫu từ MedAgent Mock API.",
          sources: [
            { id: 1, title: 'MedAgent Knowledge Base', url: 'https://medagent.vn/kb' }
          ],
          is_image: false,
          image: null
        };

        const lowerContent = content.toLowerCase();
        if (lowerContent.includes('thuốc') || lowerContent.includes('paracetamol')) {
          botResponse.answer = "Dưới đây là thông tin về thuốc bạn quan tâm:\n\n| Thuốc | Liều lượng | Chỉ định |\n|---|---|---|\n| Paracetamol | 500mg | Hạ sốt, giảm đau |\n| Ibuprofen | 200mg | Kháng viêm, giảm đau |\n\nBạn nên tham khảo ý kiến bác sĩ trước khi sử dụng.";
        } else if (lowerContent.includes('biểu đồ') || lowerContent.includes('thống kê')) {
          botResponse.answer = "Dưới đây là thống kê tình hình sức khỏe khu vực của bạn trong tuần qua:";
          botResponse.image = "https://images.unsplash.com/photo-1551288049-bebda4e38f71?q=80&w=2070&auto=format&fit=crop";
          botResponse.is_image = true;
        }

        const responseData = {
          id: uuidv4(),
          role: 'assistant',
          timestamp: getCurrentTime(),
          content: botResponse.answer,
          sources: botResponse.sources,
          image: botResponse.image,
        };
        setMessages((prev) => [...prev, responseData]);

      } else {
        // GỌI API THẬT
        const botResponseId = uuidv4();
        const initialResponseData = {
          id: botResponseId,
          role: 'assistant',
          timestamp: getCurrentTime(),
          content: '',
          sources: [],
          trace_status: 'Đang kết nối tới máy chủ...',
        };
        
        setMessages((prev) => [...prev, initialResponseData]);

        await chatApi.streamChat(currentSessionId, content, (data) => {
          setIsLoading(false);
          setMessages((prev) => {
            return prev.map(msg => {
              if (msg.id === botResponseId) {
                if (data.type === 'trace') {
                  return { ...msg, trace_status: data.message };
                } else if (data.type === 'token') {
                  return { ...msg, content: msg.content + data.text };
                } else if (data.type === 'citations') {
                  return { ...msg, sources: data.data || [] };
                } else if (data.type === 'done') {
                  const noticeText = [data.response.safety_notice, ...(data.response.warnings || [])]
                    .filter(Boolean)
                    .join('\n');
                  const finalAnswer = data.response.answer || msg.content;
                  const finalContent = noticeText ? `${finalAnswer}\n\n${noticeText}` : finalAnswer;
                  return { ...msg, content: finalContent, trace_status: null };
                } else if (data.type === 'error') {
                  return { ...msg, content: `Lỗi kết nối: ${data.message}`, isError: true, trace_status: null };
                }
              }
              return msg;
            });
          });
        });
      }
    } catch (err) {
      console.error('SendMessage Error:', err);
      setError(err.message || 'Có lỗi xảy ra khi gửi tin nhắn.');
      addToast(err.message || 'Lỗi gửi tin nhắn', 'error');
      
      setMessages((prev) => [...prev, {
        id: uuidv4(),
        role: 'assistant',
        content: `⚠️ Lỗi kết nối: ${err.message || 'Vui lòng kiểm tra lại Backend.'}`,
        isError: true,
        timestamp: getCurrentTime(),
      }]);
    } finally {
      setIsLoading(false);
    }
  }, [currentSessionId]);

  const loadHistory = useCallback(async (sessionId) => {
    setIsLoading(true);
    setError(null);
    setCurrentSessionId(sessionId);

    try {
      if (USE_MOCK) {
        // Mock loading history
        await new Promise(resolve => setTimeout(resolve, 800));
        setMessages([
          { id: '1', role: 'user', content: 'Lịch sử chat cũ...', timestamp: '10:00 AM' },
          { id: '2', role: 'assistant', content: 'Đây là nội dung được tải lại từ session ' + sessionId, timestamp: '10:01 AM' }
        ]);
      } else {
        const history = await chatApi.getChatHistory(sessionId);
        setMessages(history.map(item => ({
          id: uuidv4(),
          role: item.role,
          content: item.content,
          timestamp: item.timestamp || '00:00 AM',
          sources: item.sources,
          image: item.image
        })));
      }
    } catch (err) {
      setError('Không thể tải lịch sử cuộc trò chuyện.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  const newConversation = useCallback(() => {
    setMessages([]);
    setError(null);
    setCurrentSessionId(uuidv4());
  }, []);

  const retry = useCallback(async () => {
    const lastUserMessage = [...messages].reverse().find(m => m.role === 'user');
    if (lastUserMessage) {
      sendMessage(lastUserMessage.content);
    }
  }, [messages, sendMessage]);

  return {
    messages,
    isLoading,
    error,
    currentSessionId,
    sendMessage,
    newConversation,
    loadHistory,
    retry,
  };
}
