// All calls are relative (/api/...). The browser never needs the backend's
// internal hostname: Vite (dev), Nginx (compose) or the Ingress (k8s) routes them.

async function request(path, options = {}) {
  const response = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!response.ok) {
    let message = `${response.status} ${response.statusText}`
    try {
      const body = await response.json()
      if (typeof body.detail === 'string') message = body.detail
      else if (Array.isArray(body.detail)) {
        message = body.detail.map((e) => `${e.loc.at(-1)}: ${e.msg}`).join(', ')
      }
    } catch {
      /* non-JSON error body */
    }
    throw new Error(message)
  }
  return response.status === 204 ? null : response.json()
}

export const api = {
  listTickets: (filters = {}) => {
    const params = new URLSearchParams(
      Object.entries(filters).filter(([, v]) => v !== '' && v != null),
    )
    const qs = params.toString()
    return request(`/api/tickets${qs ? `?${qs}` : ''}`)
  },
  stats: () => request('/api/tickets/stats'),
  activity: (limit = 12) => request(`/api/activity?limit=${limit}`),
  system: () => request('/api/system'),
  createTicket: (data) => request('/api/tickets', { method: 'POST', body: JSON.stringify(data) }),
  updateTicket: (id, data) =>
    request(`/api/tickets/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteTicket: (id) => request(`/api/tickets/${id}`, { method: 'DELETE' }),
}
