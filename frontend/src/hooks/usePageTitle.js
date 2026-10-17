// Set the browser tab title, e.g. "Turkey Point · PlanIT Control".
import { useEffect } from 'react';

const APP_NAME = 'PlanIT Control';

export function usePageTitle(title) {
  useEffect(() => {
    document.title = title ? `${title} · ${APP_NAME}` : APP_NAME;
  }, [title]);
}
