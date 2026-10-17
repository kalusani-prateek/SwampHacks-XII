// Server feature flags for components (null until loaded).
import { useEffect, useState } from 'react';
import { getMeta } from '../api/meta.js';

export function useMeta() {
  const [meta, setMeta] = useState(null);
  useEffect(() => {
    let active = true;
    getMeta().then((value) => active && setMeta(value));
    return () => {
      active = false;
    };
  }, []);
  return meta;
}
