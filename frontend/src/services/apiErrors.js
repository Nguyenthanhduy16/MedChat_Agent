export const DEFAULT_API_ERROR_MESSAGE =
  'Khong the ket noi toi may chu y te. Vui long kiem tra lai ket noi.';

export const API_TIMEOUT_ERROR_MESSAGE =
  'May chu dang xu ly lau hon du kien. Vui long doi them hoac thu lai sau.';

export function isTimeoutError(error) {
  return (
    error?.code === 'ECONNABORTED' ||
    error?.code === 'ETIMEDOUT' ||
    String(error?.message || '').toLowerCase().includes('timeout')
  );
}

export function getApiErrorMessage(error) {
  if (error?.response?.data?.detail) {
    return error.response.data.detail;
  }

  if (error?.response?.data?.message) {
    return error.response.data.message;
  }

  if (isTimeoutError(error)) {
    return API_TIMEOUT_ERROR_MESSAGE;
  }

  return DEFAULT_API_ERROR_MESSAGE;
}
