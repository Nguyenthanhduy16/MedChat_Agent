export function hasActiveAssistantTrace(messages) {
  return messages.some(
    (message) => message.role === 'assistant' && Boolean(message.trace_status)
  );
}
