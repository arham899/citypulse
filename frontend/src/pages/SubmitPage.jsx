import { useEffect, useState } from 'react'
import { fetchCategories, submitEvent } from '../api.js'

const INITIAL = {
  title: '', description: '', category_slug: '', start_time: '', end_time: '',
  venue_name: '', address: '', city: 'Islamabad', price_min: '', price_max: '',
  is_free: false, image_url: '', ticket_url: '', organizer_name: '', organizer_email: '',
}

export default function SubmitPage() {
  const [categories, setCategories] = useState([])
  const [form, setForm] = useState(INITIAL)
  const [status, setStatus] = useState('idle') // idle | sending | done | error
  const [error, setError] = useState('')

  useEffect(() => {
    fetchCategories().then(setCategories).catch(() => {})
  }, [])

  const set = (key) => (e) =>
    setForm({ ...form, [key]: e.target.type === 'checkbox' ? e.target.checked : e.target.value })

  const onSubmit = async (e) => {
    e.preventDefault()
    setStatus('sending')
    setError('')
    try {
      await submitEvent({
        ...form,
        category_slug: form.category_slug || null,
        end_time: form.end_time || null,
        price_min: form.is_free || form.price_min === '' ? null : Number(form.price_min),
        price_max: form.is_free || form.price_max === '' ? null : Number(form.price_max),
      })
      setStatus('done')
      setForm(INITIAL)
    } catch (err) {
      setStatus('error')
      setError(err.message)
    }
  }

  if (status === 'done') {
    return (
      <main className="submit">
        <div className="submit-done">
          <h1>Thanks — you're in the queue</h1>
          <p>Your event is in the moderation queue. It will appear in the feed once our team approves it.</p>
          <button className="btn primary" onClick={() => setStatus('idle')}>Submit another</button>
        </div>
      </main>
    )
  }

  return (
    <main className="submit">
      <h1>Submit an event</h1>
      <p className="submit-sub">Reach thousands of residents. Submissions are reviewed before going live.</p>
      <form onSubmit={onSubmit} className="form">
        <label>Event title *
          <input required minLength={3} value={form.title} onChange={set('title')} placeholder="e.g. Open Mic Night at Kuch Khaas" />
        </label>
        <label>Description
          <textarea rows={4} value={form.description} onChange={set('description')} placeholder="What should attendees know?" />
        </label>
        <div className="form-row">
          <label>Category
            <select value={form.category_slug} onChange={set('category_slug')}>
              <option value="">Auto-detect</option>
              {categories.map((c) => <option key={c.slug} value={c.slug}>{c.name}</option>)}
            </select>
          </label>
          <label>City *
            <input required value={form.city} onChange={set('city')} />
          </label>
        </div>
        <div className="form-row">
          <label>Starts *
            <input required type="datetime-local" value={form.start_time} onChange={set('start_time')} />
          </label>
          <label>Ends
            <input type="datetime-local" value={form.end_time} onChange={set('end_time')} />
          </label>
        </div>
        <label>Venue name *
          <input required minLength={2} value={form.venue_name} onChange={set('venue_name')} placeholder="e.g. Jinnah Convention Centre" />
        </label>
        <label>Full address
          <input value={form.address} onChange={set('address')} placeholder="Street, sector, city" />
        </label>
        <label className="check">
          <input type="checkbox" checked={form.is_free} onChange={set('is_free')} /> This event is free
        </label>
        {!form.is_free && (
          <div className="form-row">
            <label>Price from (PKR)
              <input type="number" min="0" value={form.price_min} onChange={set('price_min')} />
            </label>
            <label>Price to (PKR)
              <input type="number" min="0" value={form.price_max} onChange={set('price_max')} />
            </label>
          </div>
        )}
        <div className="form-row">
          <label>Ticket / RSVP link
            <input type="url" value={form.ticket_url} onChange={set('ticket_url')} placeholder="https://…" />
          </label>
          <label>Image URL
            <input type="url" value={form.image_url} onChange={set('image_url')} placeholder="https://…" />
          </label>
        </div>
        <div className="form-row">
          <label>Organizer name *
            <input required minLength={2} value={form.organizer_name} onChange={set('organizer_name')} />
          </label>
          <label>Organizer email
            <input type="email" value={form.organizer_email} onChange={set('organizer_email')} />
          </label>
        </div>
        {status === 'error' && <p className="notice error">Submission failed: {error}</p>}
        <button className="btn primary" type="submit" disabled={status === 'sending'}>
          {status === 'sending' ? 'Submitting…' : 'Submit for review'}
        </button>
      </form>
    </main>
  )
}
