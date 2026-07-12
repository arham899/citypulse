import { useState } from 'react'
import { fetchPending, moderateEvent } from '../api.js'
import { formatWhen } from '../format.js'

export default function AdminPage() {
  const [key, setKey] = useState('')
  const [pending, setPending] = useState(null)
  const [error, setError] = useState('')

  const load = async (adminKey) => {
    setError('')
    try {
      setPending(await fetchPending(adminKey))
    } catch (err) {
      setPending(null)
      setError(err.message)
    }
  }

  const act = async (id, action) => {
    try {
      await moderateEvent(id, action, key)
      setPending((prev) => prev.filter((e) => e.id !== id))
    } catch (err) {
      setError(err.message)
    }
  }

  if (pending === null) {
    return (
      <main className="admin">
        <h1>Moderation queue</h1>
        <form className="form admin-login" onSubmit={(e) => { e.preventDefault(); load(key) }}>
          <label>Admin key
            <input type="password" value={key} onChange={(e) => setKey(e.target.value)} placeholder="X-Admin-Key" />
          </label>
          {error && <p className="notice error">{error}</p>}
          <button className="btn primary" type="submit">Open queue</button>
        </form>
      </main>
    )
  }

  return (
    <main className="admin">
      <h1>Moderation queue</h1>
      {error && <p className="notice error">{error}</p>}
      {pending.length === 0 && <p className="notice">Queue is empty — nothing awaiting review.</p>}
      <div className="admin-list">
        {pending.map((event) => (
          <div key={event.id} className="admin-item">
            <div>
              <strong>{event.title}</strong>
              <p>{formatWhen(event.start_time, event.end_time)} · {event.venue_name}, {event.city}</p>
              <p className="admin-org">by {event.organizer_name}</p>
              {event.description && <p className="admin-desc">{event.description}</p>}
            </div>
            <div className="admin-actions">
              <button className="btn primary" onClick={() => act(event.id, 'approve')}>Approve</button>
              <button className="btn danger" onClick={() => act(event.id, 'reject')}>Reject</button>
            </div>
          </div>
        ))}
      </div>
    </main>
  )
}
