import assert from 'node:assert/strict';
import test from 'node:test';

import { getApiErrorMessage } from './apiErrors.js';

test('reports axios timeout as a slow backend response instead of a connection failure', () => {
  const message = getApiErrorMessage({
    code: 'ECONNABORTED',
    message: 'timeout of 60000ms exceeded',
  });

  assert.equal(
    message,
    'May chu dang xu ly lau hon du kien. Vui long doi them hoac thu lai sau.'
  );
});

test('uses backend detail when the server returns an error response', () => {
  const message = getApiErrorMessage({
    response: {
      data: {
        detail: 'OPENAI_API_KEY is missing',
      },
    },
  });

  assert.equal(message, 'OPENAI_API_KEY is missing');
});
