// Single KPI tile (e.g. "No-go sites: 4") used on the dashboard and Manage overview.

export default function StatCard({ label, value, tone = 'default', hint }) {
  const tones = {
    default: 'text-navy-800',
    danger: 'text-red-600',
    warning: 'text-orange-600',
    good: 'text-emerald-600',
  };
  return (
    <div className="card">
      <p className="label">{label}</p>
      <p className={`text-3xl font-bold tabular-nums ${tones[tone]}`}>{value}</p>
      {hint && <p className="mt-1 text-xs text-slate-500">{hint}</p>}
    </div>
  );
}
