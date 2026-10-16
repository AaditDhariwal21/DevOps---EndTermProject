import { CATEGORIES, PRIORITIES, STATUSES, labelOf } from '../constants.js'

export function PriorityBadge({ value }) {
  return (
    <span className={`badge priority-${value}`}>
      <span className="badge-dot" />
      {labelOf(PRIORITIES, value)}
    </span>
  )
}

export function StatusBadge({ value }) {
  return <span className={`badge status-${value}`}>{labelOf(STATUSES, value)}</span>
}

export function CategoryTag({ value }) {
  return <span className="tag">{labelOf(CATEGORIES, value)}</span>
}

export function Avatar({ name }) {
  if (!name) return <span className="avatar is-empty">?</span>
  const hue = [...name].reduce((h, c) => h + c.charCodeAt(0), 0) % 360
  return (
    <span className="avatar" style={{ '--hue': hue }} title={name}>
      {name.slice(0, 2).toUpperCase()}
    </span>
  )
}
