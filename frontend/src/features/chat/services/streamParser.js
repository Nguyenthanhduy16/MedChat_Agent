function parseBlock(block) {
  const dataLines = block
    .split('\n')
    .filter((line) => line.startsWith('data: '))
    .map((line) => line.slice(6));

  if (dataLines.length === 0) {
    return null;
  }

  const payload = dataLines.join('\n').trim();
  if (!payload || payload === '[DONE]') {
    return null;
  }

  return JSON.parse(payload);
}

export function createSseEventBuffer() {
  let buffer = '';

  return {
    push(chunk) {
      buffer += chunk;
      const blocks = buffer.split('\n\n');
      buffer = blocks.pop() || '';
      return blocks.map(parseBlock).filter(Boolean);
    },
    flush() {
      const events = [];
      if (buffer.trim()) {
        const event = parseBlock(buffer);
        if (event) {
          events.push(event);
        }
      }
      buffer = '';
      return events;
    },
  };
}

export function createSseParser(onEvent) {
  const eventBuffer = createSseEventBuffer();

  return {
    push(chunk) {
      eventBuffer.push(chunk).forEach(onEvent);
    },
    flush() {
      eventBuffer.flush().forEach(onEvent);
    },
  };
}
