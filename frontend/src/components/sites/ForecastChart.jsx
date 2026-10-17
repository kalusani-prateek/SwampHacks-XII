// 7-day ML hazard-index forecast as a simple bar chart (pure Tailwind, no
// chart library). Bars are colored by hazard band.
import { getHazardLevel } from '../../utils/hazard.js';
import { weekdayLabel } from '../../utils/time.js';

export default function ForecastChart({ forecast }) {
  return (
    <div className="flex h-44 items-end gap-2" role="img" aria-label="7-day hazard forecast">
      {forecast.map((day) => {
        const level = getHazardLevel(day.hazardIndex);
        return (
          <div key={day.date} className="flex flex-1 flex-col items-center gap-1">
            <span className="text-xs font-semibold tabular-nums text-slate-600">{day.hazardIndex.toFixed(1)}</span>
            <div
              className="w-full rounded-t-md"
              style={{ height: `${Math.max(day.hazardIndex, 0.3) * 12}px`, backgroundColor: level.hex }}
              title={`${day.date}: ${level.label}`}
            />
            {/* Parse as local noon so the weekday doesn't shift across time zones */}
            <span className="text-xs text-slate-500">{weekdayLabel(`${day.date}T12:00:00`)}</span>
          </div>
        );
      })}
    </div>
  );
}
