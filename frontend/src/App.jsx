import { useCallback, useEffect, useMemo, useState } from 'react'
import { api } from './api.js'
import ActivityFeed from './components/ActivityFeed.jsx'
import Breakdown from './components/Breakdown.jsx'
import Icon from './components/Icon.jsx'
import KpiCards from './components/KpiCards.jsx'
import PipelinePanel from './components/PipelinePanel.jsx'
import Sidebar from './components/Sidebar.jsx'
import TicketModal from './components/TicketModal.jsx'
import TicketTable from './components/TicketTable.jsx'

const VIEWS = {
  dashboard: { title: 'Support overview', table: 'Latest tickets', filters: {} },
  tickets: { title: 'All tickets', table: 'Ticket queue', filters: {} },
  unassigned: { title: 'Unassigned', table: 'Needs an owner', filters: { unassigned: true } },
  urgent: { title: 'Urgent queue', table: 'Urgent tickets', filters: { priority: 'urgent' } },
}

const REFRESH_MS = 15000

function useDebounced(value, delay = 300) {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const id = setTimeout(() => setDebounced(value), delay)
    return () => clearTimeout(id)
  }, [value, delay])
  return debounced
}

export default function App() {
  const [view, setView] = useState('dashboard')
  const [sidebarOpen, setSidebarOpen] = useState(false)

  const [statusFilter, setStatusFilter] = useState('')
  const [priorityFilter, setPriorityFilter] = useState('')
  const [search, setSearch] = useState('')
  const debouncedSearch = useDebounced(search)

  const [tickets, setTickets] = useState({ total: 0, items: [] })
  const [stats, setStats] = useState(null)
  const [activity, setActivity] = useState([])
  const [system, setSystem] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const [modal, setModal] = useState(null) // null | { ticket?: Ticket }
  const [toast, setToast] = useState(null)

  const filters = useMemo(
    () => ({
      ...(priorityFilter && { priority: priorityFilter }),
      ...VIEWS[view].filters, // a view's own filters (e.g. urgent queue) always win
      status: statusFilter,
      q: debouncedSearch.trim(),
    }),
    [view, statusFilter, priorityFilter, debouncedSearch],
  )

  const load = useCallback(async () => {
    const [t, s, a, sys] = await Promise.allSettled([
      api.listTickets(filters),
      api.stats(),
      api.activity(),
      api.system(),
    ])
    if (t.status === 'fulfilled') {
      setTickets(t.value)
      setError('')
    } else {
      setError(t.reason.message)
    }
    if (s.status === 'fulfilled') setStats(s.value)
    if (a.status === 'fulfilled') setActivity(a.value)
    setSystem(sys.status === 'fulfilled' ? sys.value : null)
    setLoading(false)
  }, [filters])

  useEffect(() => {
    load()
    const id = setInterval(load, REFRESH_MS)
    return () => clearInterval(id)
  }, [load])

  useEffect(() => {
    if (!toast) return
    const id = setTimeout(() => setToast(null), 3500)
    return () => clearTimeout(id)
  }, [toast])

  const notify = (message, tone = 'ok') => setToast({ message, tone })

  function navigate(next) {
    setView(next)
    setStatusFilter('')
    setPriorityFilter('')
    setSidebarOpen(false)
  }

  async function saveTicket(payload) {
    if (modal?.ticket) {
      await api.updateTicket(modal.ticket.id, payload)
      notify(`Ticket #${modal.ticket.id} updated`)
    } else {
      const created = await api.createTicket(payload)
      notify(`Ticket #${created.id} created`)
    }
    setModal(null)
    load()
  }

  async function changeStatus(ticket, status) {
    try {
      await api.updateTicket(ticket.id, { status })
      notify(`#${ticket.id} moved to ${status.replace('_', ' ')}`)
      load()
    } catch (err) {
      notify(err.message, 'bad')
    }
  }

  async function deleteTicket(ticket) {
    if (!window.confirm(`Delete ticket #${ticket.id} “${ticket.title}”?`)) return
    try {
      await api.deleteTicket(ticket.id)
      notify(`Ticket #${ticket.id} deleted`)
      load()
    } catch (err) {
      notify(err.message, 'bad')
    }
  }

  const navCounts = {
    tickets: stats?.total,
    unassigned: stats?.unassigned,
    urgent: stats ? stats.by_priority.urgent : undefined,
  }
  const isDashboard = view === 'dashboard'

  return (
    <div className="app">
      <Sidebar
        view={view}
        onNavigate={navigate}
        counts={navCounts}
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        system={system}
      />

      <div className="main">
        <header className="topbar">
          <button className="icon-btn menu-btn" onClick={() => setSidebarOpen(true)} aria-label="Open menu">
            <Icon name="menu" />
          </button>
          <label className="search">
            <Icon name="search" size={16} />
            <input
              type="search"
              placeholder="Search tickets or requesters…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              aria-label="Search tickets"
            />
          </label>
          <div className="topbar-actions">
            <button className="icon-btn" onClick={load} aria-label="Refresh" title="Refresh">
              <Icon name="refresh" size={17} />
            </button>
            <span className="avatar me" title="Signed in as Aadit">
              AD
            </span>
          </div>
        </header>

        <main className="content">
          <div className="page-head">
            <div>
              <p className="eyebrow">Acme Support · Helpdesk</p>
              <h1>{VIEWS[view].title}</h1>
            </div>
            <button className="btn btn-primary" onClick={() => setModal({})}>
              <Icon name="plus" size={16} /> New ticket
            </button>
          </div>

          {isDashboard && <KpiCards stats={stats} loading={loading} />}

          <div className={`grid ${isDashboard ? '' : 'grid-single'}`}>
            <TicketTable
              title={VIEWS[view].table}
              tickets={tickets.items}
              total={tickets.total}
              loading={loading}
              error={error}
              onRetry={load}
              statusFilter={statusFilter}
              onStatusFilter={setStatusFilter}
              priorityFilter={filters.priority ?? ''}
              priorityLocked={Boolean(VIEWS[view].filters.priority)}
              onPriorityFilter={setPriorityFilter}
              statusCounts={stats?.by_status}
              onEdit={(ticket) => setModal({ ticket })}
              onDelete={deleteTicket}
              onStatusChange={changeStatus}
              onCreate={() => setModal({})}
            />

            {isDashboard && (
              <aside className="side">
                <PipelinePanel system={system} error={error} />
                <ActivityFeed items={activity} loading={loading} />
                <Breakdown stats={stats} />
              </aside>
            )}
          </div>
        </main>
      </div>

      {modal && <TicketModal ticket={modal.ticket} onClose={() => setModal(null)} onSave={saveTicket} />}

      {toast && (
        <div className={`toast toast-${toast.tone}`} role="status">
          <Icon name={toast.tone === 'ok' ? 'check' : 'alert'} size={16} />
          {toast.message}
        </div>
      )}
    </div>
  )
}
