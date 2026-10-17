// Loading / error / empty placeholders shown while API data is in flight.

export function LoadingState({ label = 'Loading…' }) {
  return (
    <div className="flex items-center justify-center gap-3 p-10 text-sm text-slate-500">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-slate-300 border-t-brand" />
      {label}
    </div>
  );
}

export function ErrorState({ error, onRetry }) {
  return (
    <div className="card border-red-200 bg-red-50 text-sm text-red-800">
      <p className="font-semibold">Couldn't load data</p>
      <p className="mt-1">{error?.message ?? 'Unknown error'}</p>
      {onRetry && (
        <button className="btn-secondary mt-3" onClick={() => onRetry()}>
          Try again
        </button>
      )}
    </div>
  );
}

export function EmptyState({ children }) {
  return <p className="p-6 text-center text-sm text-slate-500">{children}</p>;
}
