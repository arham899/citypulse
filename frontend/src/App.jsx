import { Link, NavLink, Route, Routes } from 'react-router-dom'
import AdminPage from './pages/AdminPage.jsx'
import EventDetailPage from './pages/EventDetailPage.jsx'
import FeedPage from './pages/FeedPage.jsx'
import SubmitPage from './pages/SubmitPage.jsx'

export default function App() {
  return (
    <div className="app">
      <header className="topbar">
        <Link to="/" className="brand">
          <span className="brand-dot" aria-hidden="true" />
          CityPulse
          <span className="brand-city">Islamabad</span>
        </Link>
        <nav className="topnav">
          <NavLink to="/" end>Explore</NavLink>
          <NavLink to="/submit">Submit event</NavLink>
        </nav>
      </header>
      <Routes>
        <Route path="/" element={<FeedPage />} />
        <Route path="/event/:id" element={<EventDetailPage />} />
        <Route path="/submit" element={<SubmitPage />} />
        <Route path="/admin" element={<AdminPage />} />
      </Routes>
      <footer className="footer">
        CityPulse · live event data from AllEvents, Eventbrite &amp; organizers · <Link to="/admin">admin</Link>
      </footer>
    </div>
  )
}
