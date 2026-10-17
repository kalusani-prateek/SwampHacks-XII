// Pill showing a 0-10 hazard index with its band color and, optionally,
// the go / caution / no-go decision.
import { getHazardLevel } from '../../utils/hazard.js';

export default function HazardBadge({ score, showDecision = false, size = 'md' }) {
  const level = getHazardLevel(score);
  const sizing = size === 'lg' ? 'px-3 py-1.5 text-base' : 'px-2 py-0.5 text-xs';

  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full font-semibold ${level.badge} ${sizing}`}>
      <span className="tabular-nums">{score.toFixed(1)}</span>
      <span className="opacity-80">· {showDecision ? level.decision : level.label}</span>
    </span>
  );
}
