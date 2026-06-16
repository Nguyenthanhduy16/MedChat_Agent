import axios from 'axios';

/**
 * Axios Instance Configuration
 * Base URL trỏ tới FastAPI Backend (mặc định localhost:8000)
 */
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  timeout: 60000, // 60s vì RAG và SQL processing có thể mất thời gian
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request Interceptor: Có thể thêm Token hoặc Session ID vào Header nếu cần
api.interceptors.request.use(
  (config) => {
    // Ví dụ: config.headers['X-Session-ID'] = localStorage.getItem('sessionId');
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response Interceptor: Xử lý lỗi tập trung
api.interceptors.response.use(
  (response) => {
    return response.data;
  },
  (error) => {
    // Format lại message lỗi để UI hiển thị đẹp hơn
    const message = error.response?.data?.detail || 
                    error.response?.data?.message || 
                    'Không thể kết nối tới máy chủ y tế. Vui lòng kiểm tra lại kết nối.';
    
    console.error('API Error:', {
      message,
      status: error.response?.status,
      data: error.response?.data
    });

    return Promise.reject(new Error(message));
  }
);

export default api;
