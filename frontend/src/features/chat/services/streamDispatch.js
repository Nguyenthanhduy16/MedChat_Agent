const DEFAULT_TOKEN_CHUNK_SIZE = 12;
const DEFAULT_TOKEN_DELAY_MS = 18;

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export function splitTokenText(text, chunkSize = DEFAULT_TOKEN_CHUNK_SIZE) {
  if (!text) {
    return [];
  }

  const safeChunkSize = Math.max(1, chunkSize);
  const chunks = [];
  for (let index = 0; index < text.length; index += safeChunkSize) {
    chunks.push(text.slice(index, index + safeChunkSize));
  }
  return chunks;
}

export async function dispatchStreamEvent(
  event,
  onEvent,
  {
    tokenChunkSize = DEFAULT_TOKEN_CHUNK_SIZE,
    tokenDelayMs = DEFAULT_TOKEN_DELAY_MS,
    wait = delay,
  } = {}
) {
  if (event.type !== 'token') {
    onEvent(event);
    return;
  }

  const chunks = splitTokenText(event.text || '', tokenChunkSize);
  for (const text of chunks) {
    onEvent({ ...event, text });
    if (tokenDelayMs > 0) {
      await wait(tokenDelayMs);
    }
  }
}
