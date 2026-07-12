import { useEffect, useMemo, useState } from 'react'
import { fetchCategories, fetchEvents } from '../api.js'
import EventCard from '../components/EventCard.jsx'
import { CrosshairIcon, ListIcon, MapIcon } from '../components/Icons.jsx'
import MapView from '../components/MapView.jsx'

const DATE_PRESETS = [
  { value: '', label: 'All upcoming' },
  { value: 'today', label: 'Today' },
  { value: 'tomorrow', label: 'Tomorrow' },
  { value: 'weekend', label: 'This weekend' },
  { value: 'week', label: 'This week' },
]

const RADII = [2, 5, 10, 25]
const PAGE_SIZE = 24

function SkeletonGrid() {
  return (
    <div className="grid" aria-hidden="true">
      {Array.from({ length: 8 }, (_, i) => (
        <div className="card skeleton" key={i}>
          <div className="card-media shimmer" />
          <div className="card-body">
            <div className="sk-line shimmer" style={{ width: '85%' }} />
            <div className="sk-line shimmer" style={{ width: '55%' }} />
            <div className="sk-line shimmer" style={{ width: '70%' }} />
          </div>
        </div>
      ))}
    </div>
  )
}

export default function FeedPage() {
  const [categories, setCategories] = useState([])
  const [view, setView] = useState('list')
  const [query, setQuery] = useState('')
  const [search, setSearch] = useState('')
  const [category, setCategory] = useState('')
  const [dateFilter, setDateFilter] = useState('')
  const [freeOnly, setFreeOnly] = useState(false)
  const [position, setPosition] = useState(null) // [lat, lng]
  const [radius, setRadius] = useState(10)
  const [geoStatus, setGeoStatus] = useState('idle') // idle | locating | on | error

  const [events, setEvents] = useState([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [hasMore, setHasMore] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetchCategories().then(setCategories).catch(() => {})
  }, [])

  // Debounce free-text search.
  useEffect(() => {
    const t = setTimeout(() => setSearch(query.trim()), 350)
    return () => clearTimeout(t)
  }, [query])

  const params = useMemo(() => ({
    q: search,
    category,
    date_filter: dateFilter,
    free_only: freeOnly || undefined,
    lat: position?.[0],
    lng: position?.[1],
    radius_km: position ? radius : undefined,
    sort: position ? 'distance' : 'date',
    page_size: PAGE_SIZE,
  }), [search, category, dateFilter, freeOnly, position, radius])

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    fetchEvents({ ...params, page: 1 })
      .then((data) => {
        if (cancelled) return
        setEvents(data.items)
        setTotal(data.total)
        setHasMore(data.has_more)
        setPage(1)
      })
      .catch((err) => !cancelled && setError(err.message))
      .finally(() => !cancelled && setLoading(false))
    return () => { cancelled = true }
  }, [params])

  const loadMore = () => {
    const next = page + 1
    fetchEvents({ ...params, page: next }).then((data) => {
      setEvents((prev) => [...prev, ...data.items])
      setHasMore(data.has_more)
      setPage(next)
    }).catch((err) => setError(err.message))
  }

  const toggleNearMe = () => {
    if (position) {
      setPosition(null)
      setGeoStatus('idle')
      return
    }
    if (!navigator.geolocation) {
      setGeoStatus('error')
      return
    }
    setGeoStatus('locating')
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setPosition([pos.coords.latitude, pos.coords.longitude])
        setGeoStatus('on')
      },
      () => {
        // Permission denied or unavailable — fall back to the city centre so
        // the distance filter still works.
        setPosition([33.6995, 73.0655])
        setGeoStatus('on')
      },
      { timeout: 8000 },
    )
  }

  return (
    <main className="feed">
      <section className="hero">
        <div className="hero-glow" aria-hidden="true" />
        <div className="hero-live"><span className="pulse" aria-hidden="true" />live feed · refreshed every 20 min</div>
        <h1>Islamabad,<br /><span className="hollow">what&rsquo;s on?</span></h1>
        <p>Concerts, treks, movies, festivals, summits — every event in the city, one feed.</p>
        <input
          className="search"
          type="search"
          placeholder="Search events, venues, organizers…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
      </section>

      {categories.length > 0 && (
        <div className="ticker" aria-hidden="true">
          <div className="ticker-track">
            {[...categories, ...categories].map((c, i) => (
              <span className="ticker-item" key={i}>{c.name}<i className="tick-dot" /></span>
            ))}
          </div>
        </div>
      )}

      <section className="filters">
        <div className="chip-row">
          <button className={`chip ${category === '' ? 'active' : ''}`} onClick={() => setCategory('')}>All</button>
          {categories.map((c) => (
            <button
              key={c.slug}
              className={`chip ${category === c.slug ? 'active' : ''}`}
              onClick={() => setCategory(category === c.slug ? '' : c.slug)}
            >
              {c.name}
            </button>
          ))}
        </div>
        <div className="chip-row secondary">
          {DATE_PRESETS.map((d) => (
            <button
              key={d.value}
              className={`chip ${dateFilter === d.value ? 'active' : ''}`}
              onClick={() => setDateFilter(d.value)}
            >
              {d.label}
            </button>
          ))}
          <span className="chip-sep" />
          <button className={`chip ${freeOnly ? 'active' : ''}`} onClick={() => setFreeOnly(!freeOnly)}>
            Free only
          </button>
          <button className={`chip geo ${position ? 'active' : ''}`} onClick={toggleNearMe}>
            <CrosshairIcon size={13} />
            {geoStatus === 'locating' ? 'Locating…' : position ? `Near me · ${radius} km` : 'Near me'}
          </button>
          {position && (
            <select className="radius" value={radius} onChange={(e) => setRadius(Number(e.target.value))}>
              {RADII.map((r) => <option key={r} value={r}>within {r} km</option>)}
            </select>
          )}
          <span className="chip-sep" />
          <div className="view-toggle" role="tablist">
            <button className={view === 'list' ? 'active' : ''} onClick={() => setView('list')}>
              <ListIcon size={13} /> List
            </button>
            <button className={view === 'map' ? 'active' : ''} onClick={() => setView('map')}>
              <MapIcon size={13} /> Map
            </button>
          </div>
        </div>
      </section>

      <section className="results">
        {error && <p className="notice error">Couldn't load events: {error}</p>}
        {!error && !loading && (
          <p className="notice count">
            <strong>{total}</strong> event{total === 1 ? '' : 's'}
            {category ? ` · ${categories.find((c) => c.slug === category)?.name ?? category}` : ''}
            {position ? ` · within ${radius} km` : ''}
          </p>
        )}
        {view === 'map' ? (
          <MapView events={events} userPosition={position} />
        ) : loading && events.length === 0 ? (
          <SkeletonGrid />
        ) : (
          <>
            <div className="grid">
              {events.map((event) => <EventCard key={event.id} event={event} />)}
            </div>
            {!loading && events.length === 0 && !error && (
              <div className="empty">
                <p>No events match those filters.</p>
                <button className="chip" onClick={() => { setCategory(''); setDateFilter(''); setFreeOnly(false); setQuery('') }}>
                  Clear filters
                </button>
              </div>
            )}
            {hasMore && (
              <div className="load-more">
                <button onClick={loadMore}>Load more</button>
              </div>
            )}
          </>
        )}
      </section>
    </main>
  )
}
