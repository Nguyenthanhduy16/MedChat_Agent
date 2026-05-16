import { useState, useCallback, useEffect } from 'react';
import { chatApi } from '../services/chatApi';
import { useToast } from '../../../context/ToastContext';

const USE_MOCK = false;

const mockSessions = [
  { id: '1', title: 'Triệu chứng đau đầu', preview: 'Bot: Đây là thông tin về thuốc...', date: 'Hôm nay, 10:45' },
  { id: '2', title: 'Tư vấn Paracetamol', preview: 'Bot: Liều lượng khuyên dùng...', date: 'Hôm qua, 14:30' },
];

export function useConversations() {
  const { addToast } = useToast();
  const [sessions, setSessions] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchSessions = useCallback(async () => {
    setIsLoading(true);
    try {
      if (USE_MOCK) {
        await new Promise(resolve => setTimeout(resolve, 500));
        setSessions(mockSessions);
      } else {
        const data = await chatApi.getChatSessions();
        setSessions(data);
      }
    } catch (err) {
      const msg = 'Không thể tải danh sách cuộc trò chuyện.';
      setError(msg);
      addToast(msg, 'error');
    } finally {
      setIsLoading(false);
    }
  }, [addToast]);

  const deleteSession = useCallback(async (sessionId) => {
    try {
      if (!USE_MOCK) {
        await chatApi.deleteSession(sessionId);
      }
      setSessions(prev => prev.filter(s => s.id !== sessionId));
      addToast('Đã xóa cuộc trò chuyện', 'success');
    } catch (err) {
      addToast('Lỗi khi xóa cuộc trò chuyện.', 'error');
    }
  }, [addToast]);

  useEffect(() => {
    fetchSessions();
  }, [fetchSessions]);

  return {
    sessions,
    isLoading,
    error,
    fetchSessions,
    deleteSession,
  };
}
