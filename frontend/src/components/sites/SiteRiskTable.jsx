// Sites ranked by hazard index, used by the supervisor dashboard and the Manage
// overview. Clicking a row selects the site (e.g. to highlight it on the map).
import { Link } from 'react-router-dom';
import { urls } from '../../routes.js';
import HazardBadge from '../common/HazardBadge.jsx';
import { HAZARD_TYPES, rankByRisk } from '../../utils/hazard.js';

export default function SiteRiskTable({ sites, limit, selectedId, onSelect }) {
  const ranked = rankByRisk(sites).slice(0, limit ?? sites.length);

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead className="text-xs text-slate-500 uppercase">
          <tr>
            <th className="px-2 py-2">#</th>
            <th className="px-2 py-2">Site</th>
            <th className="px-2 py-2">Hazard index</th>
            <th className="hidden px-2 py-2 lg:table-cell">Top hazard</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {ranked.map((site, i) => {
            const [topKey] = Object.entries(site.hazards).sort((a, b) => b[1] - a[1])[0];
            return (
              <tr
                key={site.id}
                onClick={() => onSelect?.(site)}
                className={`cursor-pointer hover:bg-slate-50 ${site.id === selectedId ? 'bg-orange-50' : ''}`}
              >
                <td className="px-2 py-2 text-slate-400 tabular-nums">{i + 1}</td>
                <td className="px-2 py-2">
                  <Link to={urls.site(site.id)} className="font-medium text-navy-800 hover:text-brand">
                    {site.name}
                  </Link>
                  <span className="ml-1 text-xs text-slate-400">{site.state}</span>
                </td>
                <td className="px-2 py-2">
                  <HazardBadge score={site.hazardIndex} showDecision />
                </td>
                <td className="hidden px-2 py-2 text-slate-600 lg:table-cell">
                  {HAZARD_TYPES[topKey].icon} {HAZARD_TYPES[topKey].label}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
