import api from '../../../services/api';

/**
 * Chat API Services
 * Định nghĩa các endpoints liên quan đến hội thoại
 */
export const chatApi = {
  /**
   * Gửi tin nhắn tới MedAgent AI
   * @param {string} sessionId - ID của phiên chat
   * @param {string} message - Nội dung tin nhắn của user
   * @returns {Promise} - Kết quả từ Backend (answer, sources, image, v.v.)
   */
  sendMessage: (sessionId, message) => {
    return api.post('/api/chat', {
      session_id: sessionId,
      message: message
    });
  },

  /**
   * Lấy lịch sử của một phiên chat cụ thể
   */
  getChatHistory: (sessionId) => {
    return api.get(`/api/chat/history/${sessionId}`);
  },

  /**
   * Lấy danh sách tất cả các phiên chat (Chat History Sidebar)
   */
  getChatSessions: () => {
    return api.get('/api/chat/sessions');
  },

  /**
   * Xóa một phiên chat
   */
  deleteSession: (sessionId) => {
    return api.delete(`/api/chat/sessions/${sessionId}`);
  }
};
