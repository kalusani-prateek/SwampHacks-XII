// The "combined risk picture": one bar per hazard category for a site.
import { getHazardLevel, HAZARD_TYPES } from '../../utils/hazard.js';

export default function HazardBreakdown({ hazards }) {
  // Show the worst hazards first.
  const rows = Object.entries(hazards).sort((a, b) => b[1] - a[1]);

  return (
    <ul className="space-y-3">
      {rows.map(([key, score]) => {
        const level = getHazardLevel(score);
        return (
          <li key={key}>
            <div className="mb-1 flex justify-between text-sm">
              <span className="font-medium text-slate-700">
                {HAZARD_TYPES[key].icon} {HAZARD_TYPES[key].label}
              </span>
              <span className="font-semibold tabular-nums text-slate-600">{score.toFixed(1)}</span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-slate-100">
              <div className="h-full rounded-full" style={{ width: `${score * 10}%`, backgroundColor: level.hex }} />
            </div>
          </li>
        );
      })}
    </ul>
  );
}
