// Floating AI assistant on every signed-in page, for crews and supervisors.
// When the user is on a site page (/sites/:siteId) or reporting for a site
// (/reports/new?site=...), that site is sent as context so answers can use
// its live hazard data. The conversation lives in Layout, so it survives
// page navigation and is cleared on sign-out.
import { useEffect, useRef, useState } from 'react';
import { useMatch, useSearchParams } from 'react-router-dom';
import ChatMessage, { TypingIndicator } from './ChatMessage.jsx';
import { useChat } from '../../hooks/useChat.js';
import { useAuth } from '../../context/AuthContext.jsx';
import { getSite } from '../../api/sites.js';
import { USE_MOCKS } from '../../api/client.js';
import { PATHS } from '../../routes.js';
import { isValidSlug } from '../../utils/url.js';

const MAX_MESSAGE_LENGTH = 2000; // matches the backend's per-message limit

/** Site the user is looking at, read from the URL (null if none). */
function useCurrentSiteId() {
  const siteMatch = useMatch(PATHS.siteDetail);
  const reportMatch = useMatch(PATHS.newReport);
  const [params] = useSearchParams();
  const siteId = siteMatch?.params.siteId ?? (reportMatch ? params.get('site') : null);
  return isValidSlug(siteId) ? siteId : null;
}

export default function ChatWidget() {
  const { user } = useAuth();
  const siteId = useCurrentSiteId();
  const { messages, sending, error, send, retry, clear } = useChat({ siteId });
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState('');
  const [site, setSite] = useState(null); // current site, for the header + suggestions
  const listRef = useRef(null);
  const inputRef = useRef(null);

  // Look up the current site's name when the panel is open.
  useEffect(() => {
    if (!open || !siteId) {
      setSite(null);
      return undefined;
    }
    let cancelled = false;
    getSite(siteId) // REST API PLACEHOLDER: GET /api/sites/:siteId
      .then(({ site: found }) => !cancelled && setSite(found))
      .catch(() => !cancelled && setSite(null));
    return () => {
      cancelled = true;
    };
  }, [open, siteId]);

  // Keep the newest message in view.
  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages, sending, error, open]);

  // Focus the input when opened; Escape closes the panel.
  useEffect(() => {
    if (!open) return undefined;
    inputRef.current?.focus();
    const onKeyDown = (e) => e.key === 'Escape' && setOpen(false);
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [open]);

  function submit(text) {
    if (!text.trim() || sending) return;
    send(text);
    setDraft('');
  }

  // Enter sends; Shift+Enter starts a new line (ignored while an IME is composing).
  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      submit(draft);
    }
  }

  // Starter questions, tailored to the site on screen.
  const suggestions = site
    ? [`Is it safe to work at ${site.name} today?`, `What's tomorrow's briefing for ${site.name}?`, 'What is the lightning rule?', 'How do I report a hazard?']
    : ['Which sites are riskiest today?', 'Are there any lightning stop-work alerts?', 'What should we do about extreme heat?', 'How do I report a hazard?'];

  // Closed: just the launcher button.
  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="fixed right-4 bottom-4 z-50 inline-flex items-center gap-2 rounded-full bg-brand px-5 py-3 text-sm font-semibold text-white shadow-lg transition hover:bg-brand-dark"
        aria-label="Open the PlanIT assistant"
      >
        <span aria-hidden="true">💬</span> Ask PlanIT AI
      </button>
    );
  }

  return (
    <section
      role="dialog"
      aria-label="PlanIT assistant"
      className="fixed inset-0 z-50 flex flex-col bg-white sm:inset-auto sm:right-4 sm:bottom-4 sm:h-[560px] sm:max-h-[calc(100vh-2rem)] sm:w-[380px] sm:rounded-2xl sm:border sm:border-slate-200 sm:shadow-2xl"
    >
      {/* Header */}
      <header className="flex items-center gap-2 bg-navy-800 px-4 py-3 text-white sm:rounded-t-2xl">
        <div className="min-w-0 flex-1">
          <p className="flex items-center gap-2 font-semibold">
            PlanIT Assistant
            {USE_MOCKS && (
              <span className="rounded bg-yellow-400/20 px-1.5 py-0.5 text-[10px] font-bold text-yellow-300" title="Canned answers from mock data">
                DEMO
              </span>
            )}
          </p>
          <p className="truncate text-xs text-slate-300">
            {site ? `Asking about ${site.name}` : 'Site risk, alerts and safety rules'}
          </p>
        </div>
        <button
          onClick={clear}
          disabled={sending || messages.length === 0}
          className="rounded px-2 py-1 text-xs text-slate-300 hover:bg-white/10 disabled:opacity-40"
        >
          Clear
        </button>
        <button onClick={() => setOpen(false)} className="rounded px-2 py-1 text-xl leading-none hover:bg-white/10" aria-label="Close the assistant">
          ×
        </button>
      </header>

      {/* Conversation (announced to screen readers as it updates) */}
      <div ref={listRef} className="flex-1 space-y-3 overflow-y-auto bg-slate-50 p-4" aria-live="polite">
        {/* Greeting is UI-only: it is never sent to the API */}
        <ChatMessage
          role="assistant"
          content={`Hi ${user.username}! Ask me about site risk, active alerts, lightning, heat and flood rules, tomorrow's briefing, or how to report a hazard.`}
        />
        {messages.map((m) => (
          <ChatMessage key={m.id} role={m.role} content={m.content} />
        ))}
        {sending && <TypingIndicator />}
        {error && (
          <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-xs text-red-800" role="alert">
            Couldn't reach the assistant: {error.message}{' '}
            <button className="font-semibold underline" onClick={retry}>
              Try again
            </button>
          </div>
        )}
      </div>

      {/* Starter questions, shown until the first message */}
      {messages.length === 0 && (
        <div className="flex flex-wrap gap-2 border-t border-slate-100 px-4 py-2">
          {suggestions.map((q) => (
            <button
              key={q}
              onClick={() => submit(q)}
              className="rounded-full border border-slate-200 px-3 py-1 text-left text-xs text-slate-600 hover:border-brand hover:text-brand"
            >
              {q}
            </button>
          ))}
        </div>
      )}

      {/* Input */}
      <form
        className="border-t border-slate-200 p-3"
        onSubmit={(e) => {
          e.preventDefault();
          submit(draft);
        }}
      >
        <div className="flex items-end gap-2">
          <textarea
            ref={inputRef}
            rows={1}
            value={draft}
            maxLength={MAX_MESSAGE_LENGTH}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about a site, alert or safety rule…"
            aria-label="Message the assistant"
            className="input max-h-32 min-h-10 resize-none field-sizing-content"
          />
          <button type="submit" className="btn-primary px-3" disabled={sending || !draft.trim()}>
            Send
          </button>
        </div>
        <p className="mt-2 text-[11px] leading-snug text-slate-400">
          AI answers can be wrong. Stop-work alerts and your supervisor always come first. Emergency? Call 911.
        </p>
      </form>
    </section>
  );
}
