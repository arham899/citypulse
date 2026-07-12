const BASE = '/api'

async function request(path, options) {
  const res = await fetch(`${BASE}${path}`, options)
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail ? JSON.stringify(body.detail) : `Request failed (${res.status})`)
  }
  return res.json()
}

export function fetchEvents(params = {}) {
  const qs = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== '') qs.set(key, value)
  }
  return request(`/events?${qs.toString()}`)
}

export const fetchEvent = (id) => request(`/events/${id}`)
export const fetchCategories = () => request('/categories')
export const fetchCities = () => request('/cities')
export const fetchStats = () => request('/stats')

export function submitEvent(payload) {
  return request('/submissions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export const fetchPending = (key) =>
  request('/admin/pending', { headers: { 'X-Admin-Key': key } })

export const moderateEvent = (id, action, key) =>
  request(`/admin/events/${id}/${action}`, { method: 'POST', headers: { 'X-Admin-Key': key } })
