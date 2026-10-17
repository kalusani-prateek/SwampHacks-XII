// One chat bubble. Replies are plain text (the backend asks the model for plain
// text), so newlines are kept and nothing is ever rendered as HTML.

export default function ChatMessage({ role, content }) {
  const isUser = role === 'user';
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-[85%] rounded-2xl px-3 py-2 text-sm whitespace-pre-wrap wrap-break-word shadow-sm ${
          isUser ? 'rounded-br-sm bg-brand text-white' : 'rounded-bl-sm bg-white text-slate-800'
        }`}
      >
        {content}
      </div>
    </div>
  );
}

/** Animated "assistant is typing" dots shown while a reply is pending. */
export function TypingIndicator() {
  return (
    <div className="flex w-fit gap-1 rounded-2xl rounded-bl-sm bg-white px-3 py-3 shadow-sm" role="status" aria-label="Assistant is typing">
      {[0, 150, 300].map((delay) => (
        <span key={delay} className="h-2 w-2 animate-bounce rounded-full bg-slate-400" style={{ animationDelay: `${delay}ms` }} />
      ))}
    </div>
  );
}
