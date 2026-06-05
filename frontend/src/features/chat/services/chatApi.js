import api from '../../../services/api';
import { createSseEventBuffer } from './streamParser';
import { dispatchStreamEvent } from './streamDispatch';

const CHAT_REQUEST_TIMEOUT_MS = Number.parseInt(
  import.meta.env.VITE_CHAT_TIMEOUT_MS || '300000',
  10
);

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
    return api.post('/chat', {
      conversation_id: sessionId,
      message: message
    }, {
      timeout: CHAT_REQUEST_TIMEOUT_MS
    });
  },

  /**
   * Streaming chat endpoint
   */
  streamChat: async (sessionId, message, onChunk) => {
    const baseUrl = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
    const response = await fetch(`${baseUrl}/chat/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        conversation_id: sessionId,
        message: message
      }),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder('utf-8');
    const parser = createSseEventBuffer();

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      
      const events = parser.push(decoder.decode(value, { stream: true }));
      for (const event of events) {
        await dispatchStreamEvent(event, onChunk);
      }
    }

    const events = [
      ...parser.push(decoder.decode()),
      ...parser.flush(),
    ];
    for (const event of events) {
      await dispatchStreamEvent(event, onChunk);
    }
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
