// Conversation state for the AI assistant: messages, sending flag, errors.
import { useCallback, useRef, useState } from 'react';
import { sendChatMessage } from '../api/chat.js';

/**
 * @param {object} [options]
 * @param {string|null} [options.siteId]  site the user is viewing; sent as context with each message
 * @returns {{ messages, sending, error, send, retry, clear }}
 */
export function useChat({ siteId = null } = {}) {
  const [messages, setMessages] = useState([]); // [{ id, role: 'user' | 'assistant', content }]
  const [sending, setSending] = useState(false);
  const [error, setError] = useState(null);
  // Plain counter for React keys (crypto.randomUUID() only works over HTTPS,
  // which a phone testing against the dev server's LAN address won't have).
  const nextId = useRef(1);

  /** Ask the assistant to reply to `history` (which ends with the user's message). */
  const request = useCallback(
    async (history) => {
      setSending(true);
      setError(null);
      try {
        // REST API PLACEHOLDER: POST /api/chat
        const { reply } = await sendChatMessage({ messages: history, siteId });
        setMessages((prev) => [...prev, { id: nextId.current++, role: 'assistant', content: reply.content }]);
      } catch (err) {
        setError(err);
      } finally {
        setSending(false);
      }
    },
    [siteId],
  );

  /** Add the user's message and fetch a reply. Ignored while a reply is pending. */
  const send = useCallback(
    (text) => {
      const content = text.trim();
      if (!content || sending) return;
      const history = [...messages, { id: nextId.current++, role: 'user', content }];
      setMessages(history);
      request(history);
    },
    [messages, sending, request],
  );

  /** Re-send after a failed request (the user's last message is still in the list). */
  const retry = useCallback(() => request(messages), [messages, request]);

  /** Start a new conversation. */
  const clear = useCallback(() => {
    setMessages([]);
    setError(null);
  }, []);

  return { messages, sending, error, send, retry, clear };
}
