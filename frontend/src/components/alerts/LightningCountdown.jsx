// Lightning stop-work panel. Any strike within 10 miles starts a 30-minute
// all-clear countdown, and every newer strike restarts it.
import { useEffect, useState } from 'react';
import { getLightningStatus, simulateLightningStrike } from '../../api/sites.js';
import { USE_MOCKS } from '../../api/client.js';
import { usePolling } from '../../hooks/usePolling.js';
import { formatCountdown } from '../../utils/time.js';

const STATUS_POLL_MS = 15_000;

export default function LightningCountdown({ siteId, allClearMinutes = 30 }) {
  const [status, setStatus] = useState({ lastStrikeAt: null, distanceMiles: null });
  const [now, setNow] = useState(Date.now());

  // REST API PLACEHOLDER: GET /api/sites/:id/lightning (polled every 15 s)
  const refresh = () => getLightningStatus(siteId).then(setStatus).catch(() => {});
  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [siteId]);
  usePolling(refresh, STATUS_POLL_MS);

  // Tick once a second for the countdown display.
  usePolling(() => setNow(Date.now()), 1000);

  const allClearAt = status.lastStrikeAt ? new Date(status.lastStrikeAt).getTime() + allClearMinutes * 60000 : 0;
  const remaining = allClearAt - now;
  const stopWork = remaining > 0;

  return (
    <div className={`card ${stopWork ? 'border-red-300 bg-red-50' : 'border-emerald-200 bg-emerald-50'}`}>
      <p className="label">Lightning ({allClearMinutes}-min rule)</p>
      {stopWork ? (
        <>
          <p className="text-xl font-extrabold text-red-700">⚡ STOP WORK</p>
          <p className="mt-1 text-sm text-red-800">
            Strike {status.distanceMiles} mi away. All-clear in
          </p>
          <p className="text-4xl font-bold tabular-nums text-red-700">{formatCountdown(remaining)}</p>
          <p className="mt-1 text-xs text-red-700/80">The timer restarts if another strike lands within 10 mi.</p>
        </>
      ) : (
        <>
          <p className="text-xl font-extrabold text-emerald-700">✓ ALL CLEAR</p>
          <p className="mt-1 text-sm text-emerald-800">No strikes within 10 mi in the last {allClearMinutes} min.</p>
        </>
      )}

      {/* Demo only: lets you watch the countdown restart without a live feed */}
      {USE_MOCKS && (
        <button
          className="btn-secondary mt-3 text-xs"
          onClick={() => {
            simulateLightningStrike(siteId);
            refresh();
          }}
        >
          Simulate strike (mock)
        </button>
      )}
    </div>
  );
}
