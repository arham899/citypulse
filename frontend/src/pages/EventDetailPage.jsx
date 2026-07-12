import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { fetchEvent } from '../api.js'
import { ArrowIcon, CalendarIcon, PinIcon, ShareIcon, TicketIcon, UserIcon } from '../components/Icons.jsx'
import MapView from '../components/MapView.jsx'
import { formatPrice, formatWhen } from '../format.js'

export default function EventDetailPage() {
  const { id } = useParams()
  const [event, setEvent] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    setEvent(null)
    fetchEvent(id).then(setEvent).catch((err) => setError(err.message))
  }, [id])

  if (error) {
    return (
      <main className="detail">
        <p className="notice error">Event not found.</p>
        <Link to="/" className="back">← Back to events</Link>
      </main>
    )
  }
  if (!event) return <main className="detail"><p className="notice">Loading…</p></main>

  const slug = event.category?.slug || 'other'
  const mapsUrl = event.latitude != null
    ? `https://www.google.com/maps/dir/?api=1&destination=${event.latitude},${event.longitude}`
    : `https://www.google.com/maps/search/${encodeURIComponent(`${event.venue_name} ${event.city}`)}`

  return (
    <main className="detail">
      <Link to="/" className="back">← Back to events</Link>
      <div className="detail-hero">
        <div className={`card-fallback fb-${slug}`} aria-hidden="true">
          <span>{event.category?.name || 'Event'}</span>
        </div>
        {event.image_url && <img src={event.image_url} alt="" onError={(e) => { e.currentTarget.style.display = 'none' }} />}
      </div>
      <div className="detail-head">
        <span className="badge">{event.category?.name || 'Other'}</span>
        <h1>{event.title}</h1>
        <p className="detail-meta"><CalendarIcon size={15} /> <span className="detail-when">{formatWhen(event.start_time, event.end_time)}</span></p>
        <p className="detail-meta">
          <PinIcon size={15} />
          <span>{event.venue_name}{event.address && event.address !== event.venue_name ? ` — ${event.address}` : ''}, {event.city}</span>
        </p>
        <p className="detail-meta"><TicketIcon size={15} /> <span>{formatPrice(event)}</span></p>
        {event.organizer_name && (
          <p className="detail-meta"><UserIcon size={15} /> <span>Organized by <strong>{event.organizer_name}</strong></span></p>
        )}
        <div className="detail-actions">
          {event.source_url && (
            <a className="btn primary" href={event.source_url} target="_blank" rel="noreferrer">
              Book / RSVP <ArrowIcon size={13} />
            </a>
          )}
          <a className="btn" href={mapsUrl} target="_blank" rel="noreferrer">Directions</a>
          <button
            className="btn"
            onClick={() => {
              const share = { title: event.title, url: window.location.href }
              if (navigator.share) navigator.share(share).catch(() => {})
              else navigator.clipboard?.writeText(window.location.href)
            }}
          >
            <ShareIcon size={13} /> Share
          </button>
        </div>
      </div>
      {event.description && (
        <section className="detail-section">
          <h2>About this event</h2>
          <p className="detail-desc">{event.description}</p>
        </section>
      )}
      {event.latitude != null && (
        <section className="detail-section">
          <h2>Location</h2>
          <MapView events={[event]} />
        </section>
      )}
      <p className="detail-source">Source: {event.source.replaceAll('_', ' ')}</p>
    </main>
  )
}
