import { useEffect, useRef, useState } from 'react'
import { AGENTS, CATEGORIES, PRIORITIES, STATUSES } from '../constants.js'
import Icon from './Icon.jsx'

const EMPTY = {
  title: '',
  requester_email: '',
  description: '',
  category: 'bug',
  priority: 'medium',
  status: 'open',
  assignee: '',
}

export default function TicketModal({ ticket, onClose, onSave }) {
  const editing = Boolean(ticket)
  const [form, setForm] = useState(() =>
    editing ? { ...EMPTY, ...ticket, assignee: ticket.assignee ?? '' } : EMPTY,
  )
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const firstField = useRef(null)

  useEffect(() => {
    firstField.current?.focus()
    const onKey = (e) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  const set = (field) => (e) => setForm((f) => ({ ...f, [field]: e.target.value }))

  async function submit(e) {
    e.preventDefault()
    setSaving(true)
    setError('')
    const payload = {
      title: form.title.trim(),
      requester_email: form.requester_email.trim(),
      description: form.description.trim(),
      category: form.category,
      priority: form.priority,
      status: form.status,
      assignee: form.assignee || null,
    }
    try {
      await onSave(payload)
    } catch (err) {
      setError(err.message)
      setSaving(false)
    }
  }

  return (
    <div className="modal-backdrop" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal" role="dialog" aria-modal="true" aria-labelledby="modal-title">
        <header className="modal-header">
          <div>
            <h2 id="modal-title">{editing ? `Edit ticket #${ticket.id}` : 'New ticket'}</h2>
            <p className="muted">
              {editing ? 'Changes are logged to the activity feed.' : 'Log a customer request for the support team.'}
            </p>
          </div>
          <button className="icon-btn" onClick={onClose} aria-label="Close">
            <Icon name="close" />
          </button>
        </header>

        <form className="form" onSubmit={submit}>
          <label className="field span-2">
            <span>Subject</span>
            <input
              ref={firstField}
              value={form.title}
              onChange={set('title')}
              placeholder="e.g. Unable to download invoice"
              minLength={3}
              maxLength={200}
              required
            />
          </label>

          <label className="field span-2">
            <span>Requester email</span>
            <input
              type="email"
              value={form.requester_email}
              onChange={set('requester_email')}
              placeholder="customer@company.com"
              required
            />
          </label>

          <label className="field">
            <span>Category</span>
            <select value={form.category} onChange={set('category')}>
              {CATEGORIES.map((c) => (
                <option key={c.value} value={c.value}>
                  {c.label}
                </option>
              ))}
            </select>
          </label>

          <label className="field">
            <span>Priority</span>
            <select value={form.priority} onChange={set('priority')}>
              {PRIORITIES.map((p) => (
                <option key={p.value} value={p.value}>
                  {p.label}
                </option>
              ))}
            </select>
          </label>

          <label className="field">
            <span>Status</span>
            <select value={form.status} onChange={set('status')}>
              {STATUSES.map((s) => (
                <option key={s.value} value={s.value}>
                  {s.label}
                </option>
              ))}
            </select>
          </label>

          <label className="field">
            <span>Assignee</span>
            <select value={form.assignee} onChange={set('assignee')}>
              <option value="">Unassigned</option>
              {AGENTS.concat(
                form.assignee && !AGENTS.includes(form.assignee) ? [form.assignee] : [],
              ).map((a) => (
                <option key={a} value={a}>
                  {a}
                </option>
              ))}
            </select>
          </label>

          <label className="field span-2">
            <span>Description</span>
            <textarea
              rows={4}
              value={form.description}
              onChange={set('description')}
              placeholder="What happened? Steps to reproduce, order IDs, screenshots…"
              maxLength={5000}
            />
          </label>

          {error && (
            <p className="form-error span-2" role="alert">
              <Icon name="alert" size={16} /> {error}
            </p>
          )}

          <footer className="modal-footer span-2">
            <button type="button" className="btn btn-secondary" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={saving}>
              {saving ? 'Saving…' : editing ? 'Save changes' : 'Create ticket'}
            </button>
          </footer>
        </form>
      </div>
    </div>
  )
}
