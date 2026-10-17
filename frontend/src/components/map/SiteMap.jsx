// Leaflet map of job sites. Each site is a circle colored by its hazard band
// and sized by score, so the riskiest sites stand out at a glance.
// Optional `reports` are drawn as small dark dots (crew hazard pins).
import { CircleMarker, MapContainer, Popup, TileLayer, Tooltip } from 'react-leaflet';
import { Link } from 'react-router-dom';
import { urls } from '../../routes.js';
import HazardBadge from '../common/HazardBadge.jsx';
import { getHazardLevel, REPORT_TYPES } from '../../utils/hazard.js';

const US_CENTER = [38.5, -96];

export default function SiteMap({ sites = [], reports = [], center = US_CENTER, zoom = 4, selectedId, onSelect }) {
  return (
    <MapContainer center={center} zoom={zoom} scrollWheelZoom className="rounded-xl">
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />

      {sites.map((site) => {
        const level = getHazardLevel(site.hazardIndex);
        const selected = site.id === selectedId;
        return (
          <CircleMarker
            key={site.id}
            center={[site.lat, site.lng]}
            radius={6 + site.hazardIndex * 1.2}
            pathOptions={{
              color: selected ? '#111827' : '#ffffff',
              weight: selected ? 3 : 1.5,
              fillColor: level.hex,
              fillOpacity: 0.85,
            }}
            eventHandlers={{ click: () => onSelect?.(site) }}
          >
            <Popup>
              <div className="space-y-1">
                <p className="font-semibold">{site.name}</p>
                <p className="text-xs text-slate-500">
                  {site.state} · {site.plantType}
                </p>
                <HazardBadge score={site.hazardIndex} showDecision />
                <Link to={urls.site(site.id)} className="block pt-1 text-xs font-semibold text-brand">
                  Open site →
                </Link>
              </div>
            </Popup>
          </CircleMarker>
        );
      })}

      {reports.map((report) => (
        <CircleMarker
          key={report.id}
          center={[report.lat, report.lng]}
          radius={5}
          pathOptions={{ color: '#ffffff', weight: 1.5, fillColor: '#1b2440', fillOpacity: 1 }}
        >
          <Tooltip>
            {REPORT_TYPES[report.type]?.icon} {report.description}
          </Tooltip>
        </CircleMarker>
      ))}
    </MapContainer>
  );
}
