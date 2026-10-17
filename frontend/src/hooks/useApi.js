// Generic data-loading hook for the service functions in src/api/.
import { useCallback, useEffect, useState } from 'react';

/**
 * Call `fetcher` on mount (and whenever `deps` change).
 * @param {() => Promise<any>} fetcher  e.g. () => getSites()
 * @param {any[]} deps                  re-fetch when these change
 * @returns {{ data, loading, error, reload }}
 */
export function useApi(fetcher, deps = []) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // eslint-disable-next-line react-hooks/exhaustive-deps
  const load = useCallback(fetcher, deps);

  // `silent` refreshes (polling) skip the loading spinner.
  const reload = useCallback(
    async ({ silent = false } = {}) => {
      if (!silent) setLoading(true);
      try {
        setData(await load());
        setError(null);
      } catch (err) {
        setError(err);
      } finally {
        setLoading(false);
      }
    },
    [load],
  );

  useEffect(() => {
    reload();
  }, [reload]);

  return { data, loading, error, reload };
}
