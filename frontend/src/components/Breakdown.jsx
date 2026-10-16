import { CATEGORIES, PRIORITIES } from '../constants.js'

function Bars({ items, counts, kind }) {
  const max = Math.max(1, ...items.map((i) => counts?.[i.value] ?? 0))
  return (
    <ul className="bars">
      {items.map((item) => {
        const n = counts?.[item.value] ?? 0
        return (
          <li key={item.value}>
            <span className="bar-label">{item.label}</span>
            <span className="bar-track">
              <span className={`bar-fill ${kind}-${item.value}`} style={{ width: `${(n / max) * 100}%` }} />
            </span>
            <span className="bar-value">{n}</span>
          </li>
        )
      })}
    </ul>
  )
}

export default function Breakdown({ stats }) {
  return (
    <section className="card" aria-labelledby="breakdown-title">
      <header className="card-header">
        <div>
          <h2 id="breakdown-title">Workload breakdown</h2>
          <p className="muted">All tickets, by priority and category</p>
        </div>
      </header>
      <div className="breakdown">
        <div>
          <h3 className="mini-title">Priority</h3>
          <Bars items={PRIORITIES} counts={stats?.by_priority} kind="priority" />
        </div>
        <div>
          <h3 className="mini-title">Category</h3>
          <Bars items={CATEGORIES} counts={stats?.by_category} kind="category" />
        </div>
      </div>
    </section>
  )
}
