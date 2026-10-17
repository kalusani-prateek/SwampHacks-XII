// AI assistant service. The browser never talks to the language model
// directly: the Flask backend keeps the API key, adds live site data as
// context, calls Gemini or Claude and returns the reply (docs/API.md § AI assistant).
import { apiRequest, mockResponse, USE_MOCKS } from './client.js';
import { ENDPOINTS } from './endpoints.js';
import { mockChatReply } from '../mocks/chatbot.js';

/** Only the most recent turns are sent; the server enforces its own limit too. */
export const MAX_HISTORY = 20;

/**
 * Send the conversation and get the assistant's reply.
 * REST API PLACEHOLDER: POST /api/chat
 *   { messages: [{ role: 'user' | 'assistant', content }], siteId? }
 *   -> { reply: { role: 'assistant', content } }
 * `siteId` is the site the user is looking at, so answers can use its live hazard data.
 */
export async function sendChatMessage({ messages, siteId }) {
  // Strip UI-only fields and keep the latest turns. The model API requires the
  // conversation to start with a user message, so drop a leading assistant turn.
  const recent = messages.slice(-MAX_HISTORY).map(({ role, content }) => ({ role, content }));
  while (recent.length && recent[0].role !== 'user') recent.shift();

  if (USE_MOCKS) {
    return mockResponse({ reply: { role: 'assistant', content: mockChatReply(recent, siteId) } }, 700);
  }
  return apiRequest(ENDPOINTS.chat, { method: 'POST', body: { messages: recent, siteId: siteId || undefined } });
}
