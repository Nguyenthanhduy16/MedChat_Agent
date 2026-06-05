import assert from 'node:assert/strict';
import test from 'node:test';

import { createSseParser } from './streamParser.js';

test('parses SSE events split across network chunks', () => {
  const received = [];
  const parser = createSseParser((event) => received.push(event));

  parser.push('data: {"type":"trace","step":"safety","message":"Dang kiem');
  parser.push(' tra"}\n\n');
  parser.push('data: {"type":"token","text":"Hello"}\n\n');
  parser.flush();

  assert.deepEqual(received, [
    { type: 'trace', step: 'safety', message: 'Dang kiem tra' },
    { type: 'token', text: 'Hello' },
  ]);
});
