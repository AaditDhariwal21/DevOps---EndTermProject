import { PRIORITIES, STATUSES, timeAgo } from '../constants.js'
import { Avatar, CategoryTag, PriorityBadge } from './Badge.jsx'
import Icon from './Icon.jsx'

function FilterChips({ value, onChange, counts }) {
  const total = Object.values(counts ?? {}).reduce((a, b) => a + b, 0)
  const chips = [{ value: '', label: 'All', count: total }].concat(
    STATUSES.map((s) => ({ ...s, count: counts?.[s.value] ?? 0 })),
  )
  return (
    <div className="chips" role="tablist" aria-label="Filter by status">
      {chips.map((chip) => (
        <button
          key={chip.value || 'all'}
          role="tab"
          aria-selected={value === chip.value}
          className={`chip ${value === chip.value ? 'is-active' : ''}`}
          onClick={() => onChange(chip.value)}
        >
          {chip.label}
          <span className="chip-count">{chip.count}</span>
        </button>
      ))}
    </div>
  )
}

function SkeletonRows() {
  return Array.from({ length: 5 }, (_, i) => (
    <tr key={i} className="skeleton-row">
      <td colSpan={6}>
        <span className="skeleton" />
      </td>
    </tr>
  ))
}

export default function TicketTable({
  title,
  tickets,
  total,
  loading,
  error,
  onRetry,
  statusFilter,
  onStatusFilter,
  priorityFilter,
  priorityLocked,
  onPriorityFilter,
  statusCounts,
  onEdit,
  onDelete,
  onStatusChange,
  onCreate,
}) {
  return (
    <section className="card table-card" aria-labelledby="tickets-title">
      <header className="card-header">
        <div>
          <h2 id="tickets-title">{title}</h2>
          <p className="muted">{loading ? 'Loading…' : `${total} ticket${total === 1 ? '' : 's'}`}</p>
        </div>
        <select
          className="select"
          value={priorityFilter}
          disabled={priorityLocked}
          onChange={(e) => onPriorityFilter(e.target.value)}
          aria-label="Filter by priority"
        >
          <option value="">All priorities</option>
          {PRIORITIES.map((p) => (
            <option key={p.value} value={p.value}>
              {p.label}
            </option>
          ))}
        </select>
      </header>

      <FilterChips value={statusFilter} onChange={onStatusFilter} counts={statusCounts} />

      {error ? (
        <div className="state state-error" role="alert">
          <Icon name="alert" size={28} />
          <h3>Can’t reach the DeskFlow API</h3>
          <p>{error}</p>
          <button className="btn btn-secondary" onClick={onRetry}>
            <Icon name="refresh" size={16} /> Retry
          </button>
        </div>
      ) : !loading && tickets.length === 0 ? (
        <div className="state">
          <Icon name="inbox" size={28} />
          <h3>No tickets here</h3>
          <p>Nothing matches these filters. Inbox zero — or create a new ticket.</p>
          <button className="btn btn-primary" onClick={onCreate}>
            <Icon name="plus" size={16} /> New ticket
          </button>
        </div>
      ) : (
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>Ticket</th>
                <th>Category</th>
                <th>Priority</th>
                <th>Status</th>
                <th>Assignee</th>
                <th>
                  <span className="sr-only">Actions</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {loading && tickets.length === 0 ? (
                <SkeletonRows />
              ) : (
                tickets.map((t) => (
                  <tr key={t.id}>
                    <td data-label="Ticket" className="cell-title">
                      <button className="link" onClick={() => onEdit(t)}>
                        <span className="ticket-id">#{t.id}</span> {t.title}
                      </button>
                      <small>
                        {t.requester_email} · updated {timeAgo(t.updated_at)}
                      </small>
                    </td>
                    <td data-label="Category">
                      <CategoryTag value={t.category} />
                    </td>
                    <td data-label="Priority">
                      <PriorityBadge value={t.priority} />
                    </td>
                    <td data-label="Status">
                      <select
                        className={`status-select status-${t.status}`}
                        value={t.status}
                        onChange={(e) => onStatusChange(t, e.target.value)}
                        aria-label={`Status of ticket ${t.id}`}
                      >
                        {STATUSES.map((s) => (
                          <option key={s.value} value={s.value}>
                            {s.label}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td data-label="Assignee">
                      <span className="assignee">
                        <Avatar name={t.assignee} />
                        {t.assignee ?? <em className="muted">Unassigned</em>}
                      </span>
                    </td>
                    <td className="cell-actions">
                      <button className="icon-btn" onClick={() => onEdit(t)} aria-label={`Edit ticket ${t.id}`}>
                        <Icon name="edit" size={16} />
                      </button>
                      <button
                        className="icon-btn danger"
                        onClick={() => onDelete(t)}
                        aria-label={`Delete ticket ${t.id}`}
                      >
                        <Icon name="trash" size={16} />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
