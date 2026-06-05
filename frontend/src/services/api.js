import axios from 'axios';
import { getApiErrorMessage } from './apiErrors';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000',
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use(
  (config) => {
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

api.interceptors.response.use(
  (response) => {
    return response.data;
  },
  (error) => {
    const message = getApiErrorMessage(error);

    console.error('API Error:', {
      message,
      status: error.response?.status,
      code: error.code,
      data: error.response?.data,
    });

    return Promise.reject(new Error(message));
  }
);

export default api;
