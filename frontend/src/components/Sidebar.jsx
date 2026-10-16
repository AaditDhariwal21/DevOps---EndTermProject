import Icon from './Icon.jsx'

const NAV = [
  { id: 'dashboard', label: 'Dashboard', icon: 'dashboard' },
  { id: 'tickets', label: 'All tickets', icon: 'tickets' },
  { id: 'unassigned', label: 'Unassigned', icon: 'inbox' },
  { id: 'urgent', label: 'Urgent queue', icon: 'flame' },
]

const SECONDARY = [
  { label: 'Customers', icon: 'users' },
  { label: 'Reports', icon: 'chart' },
  { label: 'Settings', icon: 'settings' },
]

export default function Sidebar({ view, onNavigate, counts, open, onClose, system }) {
  const healthy = system?.database === 'ok'
  return (
    <>
      <div className={`sidebar-scrim ${open ? 'is-open' : ''}`} onClick={onClose} />
      <aside className={`sidebar ${open ? 'is-open' : ''}`} aria-label="Primary">
        <div className="brand">
          <span className="brand-mark">
            <Icon name="logo" size={20} strokeWidth={2.4} />
          </span>
          <span className="brand-name">DeskFlow</span>
          <button className="icon-btn sidebar-close" onClick={onClose} aria-label="Close menu">
            <Icon name="close" />
          </button>
        </div>

        <button className="workspace" type="button">
          <span className="workspace-avatar">AS</span>
          <span className="workspace-text">
            <strong>Acme Support</strong>
            <small>Pro workspace</small>
          </span>
        </button>

        <nav className="nav">
          <p className="nav-label">Workspace</p>
          {NAV.map((item) => (
            <button
              key={item.id}
              className={`nav-item ${view === item.id ? 'is-active' : ''}`}
              onClick={() => onNavigate(item.id)}
            >
              <Icon name={item.icon} />
              <span>{item.label}</span>
              {counts[item.id] != null && <span className="nav-count">{counts[item.id]}</span>}
            </button>
          ))}

          <p className="nav-label">Manage</p>
          {SECONDARY.map((item) => (
            <button key={item.label} className="nav-item is-muted" disabled title="Coming soon">
              <Icon name={item.icon} />
              <span>{item.label}</span>
            </button>
          ))}
        </nav>

        <div className="sidebar-footer">
          <span className={`status-dot ${healthy ? 'is-ok' : system ? 'is-bad' : ''}`} />
          <div>
            <strong>{healthy ? 'All systems normal' : system ? 'Database issue' : 'Connecting…'}</strong>
            <small>{system ? `${system.environment} · ${system.git_sha.slice(0, 7)}` : 'API'}</small>
          </div>
        </div>
      </aside>
    </>
  )
}
