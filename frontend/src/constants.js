export const STATUSES = [
  { value: 'open', label: 'Open' },
  { value: 'in_progress', label: 'In progress' },
  { value: 'resolved', label: 'Resolved' },
  { value: 'closed', label: 'Closed' },
]

export const PRIORITIES = [
  { value: 'urgent', label: 'Urgent' },
  { value: 'high', label: 'High' },
  { value: 'medium', label: 'Medium' },
  { value: 'low', label: 'Low' },
]

export const CATEGORIES = [
  { value: 'bug', label: 'Bug' },
  { value: 'billing', label: 'Billing' },
  { value: 'account', label: 'Account' },
  { value: 'feature', label: 'Feature request' },
  { value: 'other', label: 'Other' },
]

export const AGENTS = ['Aadit', 'Neha', 'Sam', 'Priya']

export const labelOf = (list, value) => list.find((item) => item.value === value)?.label ?? value

// Baked in at build time by the Docker build (--build-arg GIT_SHA=...).
export const FRONTEND_SHA = import.meta.env.VITE_GIT_SHA || 'dev'

export function timeAgo(iso) {
  const seconds = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000)
  if (seconds < 60) return 'just now'
  const units = [
    ['d', 86400],
    ['h', 3600],
    ['m', 60],
  ]
  for (const [unit, size] of units) {
    if (seconds >= size) return `${Math.floor(seconds / size)}${unit} ago`
  }
  return 'just now'
}
