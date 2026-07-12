import L from 'leaflet'
import { MapContainer, Marker, Popup, TileLayer } from 'react-leaflet'
import { Link } from 'react-router-dom'
import { formatWhen } from '../format.js'

// Vite doesn't resolve Leaflet's default marker asset paths; point them at CDN copies.
delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
})

const ISLAMABAD = [33.6995, 73.0655]

export default function MapView({ events, userPosition }) {
  const pinned = events.filter((e) => e.latitude != null && e.longitude != null)
  const center = userPosition || (pinned.length ? [pinned[0].latitude, pinned[0].longitude] : ISLAMABAD)
  return (
    <div className="map-wrap">
      <MapContainer center={center} zoom={12} className="map" scrollWheelZoom>
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>'
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
        />
        {userPosition && (
          <Marker position={userPosition} opacity={0.85}>
            <Popup>You are here</Popup>
          </Marker>
        )}
        {pinned.map((event) => (
          <Marker key={event.id} position={[event.latitude, event.longitude]}>
            <Popup>
              <strong>{event.title}</strong>
              <br />
              {formatWhen(event.start_time, event.end_time)}
              <br />
              {event.venue_name}
              <br />
              <Link to={`/event/${event.id}`}>View details →</Link>
            </Popup>
          </Marker>
        ))}
      </MapContainer>
    </div>
  )
}
