import Icon from './Icon.jsx'

export default function KpiCards({ stats, loading }) {
  const s = stats ?? { total: 0, by_status: {}, open_urgent: 0, unassigned: 0, resolution_rate: 0 }
  const active = (s.by_status.open ?? 0) + (s.by_status.in_progress ?? 0)

  const cards = [
    {
      label: 'Active tickets',
      value: active,
      hint: `${s.by_status.in_progress ?? 0} in progress`,
      icon: 'tickets',
      tone: 'indigo',
    },
    {
      label: 'Urgent & open',
      value: s.open_urgent,
      hint: s.open_urgent ? 'Needs attention now' : 'Nothing on fire',
      icon: 'flame',
      tone: s.open_urgent ? 'red' : 'green',
    },
    {
      label: 'Unassigned',
      value: s.unassigned,
      hint: 'Waiting for an owner',
      icon: 'userx',
      tone: 'amber',
    },
    {
      label: 'Resolution rate',
      value: `${s.resolution_rate}%`,
      hint: `${s.total} tickets total`,
      icon: 'check',
      tone: 'green',
      progress: s.resolution_rate,
    },
  ]

  return (
    <section className="kpis" aria-label="Key metrics">
      {cards.map((card) => (
        <article key={card.label} className={`kpi tone-${card.tone} ${loading ? 'is-loading' : ''}`}>
          <div className="kpi-top">
            <span className="kpi-label">{card.label}</span>
            <span className="kpi-icon">
              <Icon name={card.icon} size={16} />
            </span>
          </div>
          <strong className="kpi-value">{loading ? '—' : card.value}</strong>
          {card.progress != null ? (
            <div className="kpi-progress" aria-hidden="true">
              <span style={{ width: `${card.progress}%` }} />
            </div>
          ) : null}
          <span className="kpi-hint">{card.hint}</span>
        </article>
      ))}
    </section>
  )
}
