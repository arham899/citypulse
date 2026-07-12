import { useNavigate } from 'react-router-dom'
import { formatDistance, formatPrice, formatWhen } from '../format.js'
import { ArrowIcon, PinIcon } from './Icons.jsx'

const MONTH_FMT = new Intl.DateTimeFormat('en-PK', { month: 'short' })

export default function EventCard({ event }) {
  const navigate = useNavigate()
  const start = new Date(event.start_time)
  const distance = formatDistance(event.distance_km)
  const slug = event.category?.slug || 'other'

  return (
    <article
      className="card"
      onClick={() => navigate(`/event/${event.id}`)}
      onKeyDown={(e) => e.key === 'Enter' && navigate(`/event/${event.id}`)}
      tabIndex={0}
      role="link"
      aria-label={event.title}
    >
      <div className="card-media">
        <div className={`card-fallback fb-${slug}`} aria-hidden="true">
          <span>{(event.category?.name || 'Event').split(' ')[0]}</span>
        </div>
        {event.image_url && (
          <img src={event.image_url} alt="" loading="lazy" onError={(e) => { e.currentTarget.style.display = 'none' }} />
        )}
        <div className="card-date" aria-hidden="true">
          <span className="card-date-day">{start.getDate()}</span>
          <span className="card-date-month">{MONTH_FMT.format(start)}</span>
        </div>
        <span className={`card-cat cat-${slug}`}>{event.category?.name || 'Other'}</span>
      </div>
      <div className="card-body">
        <h3 className="card-title">{event.title}</h3>
        <p className="card-when">{formatWhen(event.start_time, event.end_time)}</p>
        <p className="card-venue">
          <PinIcon size={13} />
          <span>{event.venue_name || event.address}{event.city ? ` · ${event.city}` : ''}</span>
        </p>
        <div className="card-foot">
          <span className={`card-price ${event.is_free ? 'free' : ''}`}>
            {formatPrice(event)}{distance ? <em className="card-distance"> · {distance}</em> : null}
          </span>
          {event.source_url && (
            <a
              className="card-book"
              href={event.source_url}
              target="_blank"
              rel="noreferrer"
              onClick={(e) => e.stopPropagation()}
            >
              Book <ArrowIcon size={12} />
            </a>
          )}
        </div>
      </div>
    </article>
  )
}
