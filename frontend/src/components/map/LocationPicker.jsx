// Map used in the hazard report form: tap anywhere to drop the hazard pin.
import { CircleMarker, MapContainer, TileLayer, Tooltip, useMapEvents } from 'react-leaflet';

/** Listens for map clicks and reports the clicked coordinates. */
function ClickHandler({ onPick }) {
  useMapEvents({
    click: (e) => onPick({ lat: e.latlng.lat, lng: e.latlng.lng }),
  });
  return null;
}

export default function LocationPicker({ site, value, onChange }) {
  return (
    // `key` re-creates the map so it re-centres when a different site is chosen.
    <MapContainer key={site.id} center={[site.lat, site.lng]} zoom={15} className="rounded-xl">
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <ClickHandler onPick={onChange} />

      {/* Site reference point */}
      <CircleMarker center={[site.lat, site.lng]} radius={8} pathOptions={{ color: '#1b2440', fillOpacity: 0.3 }}>
        <Tooltip>{site.name}</Tooltip>
      </CircleMarker>

      {/* The hazard pin being reported */}
      {value && (
        <CircleMarker
          center={[value.lat, value.lng]}
          radius={10}
          pathOptions={{ color: '#ffffff', weight: 2, fillColor: '#e8590c', fillOpacity: 1 }}
        >
          <Tooltip permanent direction="top">
            Hazard here
          </Tooltip>
        </CircleMarker>
      )}
    </MapContainer>
  );
}
