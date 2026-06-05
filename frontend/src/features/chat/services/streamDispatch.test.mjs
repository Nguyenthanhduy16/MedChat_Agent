import assert from 'node:assert/strict';
import test from 'node:test';

import { splitTokenText } from './streamDispatch.js';

test('splits long token text into smaller display chunks', () => {
  assert.deepEqual(splitTokenText('abcdefghij', 4), ['abcd', 'efgh', 'ij']);
});

test('keeps short token text as a single display chunk', () => {
  assert.deepEqual(splitTokenText('abc', 4), ['abc']);
});
