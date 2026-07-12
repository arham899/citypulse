const DATE_FMT = new Intl.DateTimeFormat('en-PK', {
  weekday: 'short', day: 'numeric', month: 'short',
})
const TIME_FMT = new Intl.DateTimeFormat('en-PK', {
  hour: 'numeric', minute: '2-digit', hour12: true,
})

export function formatWhen(startIso, endIso) {
  const start = new Date(startIso)
  let text = `${DATE_FMT.format(start)} · ${TIME_FMT.format(start)}`
  if (endIso) {
    const end = new Date(endIso)
    text += end.toDateString() === start.toDateString()
      ? ` – ${TIME_FMT.format(end)}`
      : ` → ${DATE_FMT.format(end)}`
  }
  return text
}

export function formatPrice(event) {
  if (event.is_free) return 'Free'
  if (event.price_min == null) return 'See listing'
  const fmt = (n) => Number(n).toLocaleString('en-PK', { maximumFractionDigits: 0 })
  if (event.price_max != null && event.price_max !== event.price_min) {
    return `${event.currency} ${fmt(event.price_min)} – ${fmt(event.price_max)}`
  }
  return `${event.currency} ${fmt(event.price_min)}`
}

export function formatDistance(km) {
  if (km == null) return null
  return km < 1 ? `${Math.round(km * 1000)} m away` : `${km.toFixed(1)} km away`
}
