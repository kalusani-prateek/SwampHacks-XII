// Consistent page title row with an optional subtitle and right-side actions.
// Also sets the browser tab title (override with `documentTitle`).
import { usePageTitle } from '../../hooks/usePageTitle.js';

export default function PageHeader({ title, subtitle, actions, documentTitle }) {
  usePageTitle(documentTitle ?? title);

  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 className="text-2xl font-bold text-navy-800">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-slate-500">{subtitle}</p>}
      </div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </div>
  );
}
