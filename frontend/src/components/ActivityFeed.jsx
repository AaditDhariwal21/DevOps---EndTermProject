import { timeAgo } from '../constants.js'
import Icon from './Icon.jsx'

const ICONS = { created: 'plus', updated: 'edit', deleted: 'trash' }

export default function ActivityFeed({ items, loading }) {
  return (
    <section className="card" aria-labelledby="activity-title">
      <header className="card-header">
        <div>
          <h2 id="activity-title">Recent activity</h2>
          <p className="muted">Live audit log from the API</p>
        </div>
      </header>
      {loading && items.length === 0 ? (
        <p className="muted pad">Loading activity…</p>
      ) : items.length === 0 ? (
        <p className="muted pad">No activity yet.</p>
      ) : (
        <ol className="feed">
          {items.map((item) => (
            <li key={item.id} className={`feed-item action-${item.action}`}>
              <span className="feed-icon">
                <Icon name={ICONS[item.action] ?? 'activity'} size={14} />
              </span>
              <div className="feed-body">
                <p>
                  <strong>{item.ticket_title}</strong>{' '}
                  <span className="muted">{item.action}</span>
                </p>
                <small className="muted">
                  {item.detail ? `${item.detail} · ` : ''}
                  {timeAgo(item.created_at)}
                </small>
              </div>
            </li>
          ))}
        </ol>
      )}
    </section>
  )
}
