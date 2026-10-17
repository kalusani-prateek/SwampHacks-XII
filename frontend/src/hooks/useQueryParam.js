// Keep a filter/search value in the URL query string (e.g. /alerts?type=lightning)
// so filtered views are readable, shareable and survive a reload.
import { useCallback, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';

/**
 * @param {string} key                      query parameter name
 * @param {object} [options]
 * @param {string} [options.defaultValue]   value used when the param is missing (kept out of the URL)
 * @param {string[]} [options.allowed]      whitelist; invalid values fall back to the default and are removed from the URL
 * @returns {[string, (next: string) => void]}
 */
export function useQueryParam(key, { defaultValue = '', allowed } = {}) {
  const [params, setParams] = useSearchParams();
  const raw = params.get(key);
  const isValid = raw !== null && (!allowed || allowed.includes(raw));
  const value = isValid ? raw : defaultValue;

  const setValue = useCallback(
    (next) => {
      setParams(
        (prev) => {
          const updated = new URLSearchParams(prev);
          // Defaults and empty values are dropped to keep the URL clean.
          if (next == null || next === '' || next === defaultValue) updated.delete(key);
          else updated.set(key, next);
          return updated;
        },
        { replace: true }, // filter changes shouldn't flood the back button
      );
    },
    [key, defaultValue, setParams],
  );

  // Strip invalid values (e.g. /alerts?type=banana) from the address bar.
  useEffect(() => {
    if (raw !== null && !isValid) setValue(null);
  }, [raw, isValid, setValue]);

  return [value, setValue];
}
