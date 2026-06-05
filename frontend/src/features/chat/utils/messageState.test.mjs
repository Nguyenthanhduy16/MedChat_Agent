import assert from 'node:assert/strict';
import test from 'node:test';

import { hasActiveAssistantTrace } from './messageState.js';

test('detects when an assistant trace is active', () => {
  assert.equal(
    hasActiveAssistantTrace([
      { role: 'user', content: 'Question' },
      { role: 'assistant', content: '', trace_status: 'Dang ket noi' },
    ]),
    true
  );
});

test('ignores user traces and cleared assistant traces', () => {
  assert.equal(
    hasActiveAssistantTrace([
      { role: 'user', content: 'Question', trace_status: 'Dang ket noi' },
      { role: 'assistant', content: 'Answer', trace_status: null },
    ]),
    false
  );
});
