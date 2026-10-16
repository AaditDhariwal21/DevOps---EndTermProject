import { FRONTEND_SHA } from '../constants.js'
import Icon from './Icon.jsx'

const STAGES = ['Commit', 'Test', 'Build', 'Scan', 'Registry', 'Deploy']

// Shows which commit is actually running. During the demo: push a change,
// wait for the pipeline, refresh, and watch the SHAs change.
export default function PipelinePanel({ system, error }) {
  const live = Boolean(system) && !error
  const backendSha = system?.git_sha ?? '—'

  return (
    <section className="card pipeline" aria-labelledby="pipeline-title">
      <header className="card-header">
        <div>
          <h2 id="pipeline-title">Delivery pipeline</h2>
          <p className="muted">GitHub Actions → GHCR → Helm on EKS</p>
        </div>
        <span className={`pill ${live ? 'pill-ok' : 'pill-bad'}`}>{live ? 'Live' : 'Offline'}</span>
      </header>

      <ol className="stages">
        {STAGES.map((stage) => (
          <li key={stage} className={`stage ${live ? 'is-done' : ''}`}>
            <span className="stage-dot">{live ? <Icon name="check" size={12} strokeWidth={3} /> : null}</span>
            <span className="stage-label">{stage}</span>
          </li>
        ))}
      </ol>

      <dl className="deploy-meta">
        <div>
          <dt>Environment</dt>
          <dd>{system?.environment ?? '—'}</dd>
        </div>
        <div>
          <dt>API version</dt>
          <dd>{system?.version ?? '—'}</dd>
        </div>
        <div>
          <dt>
            <Icon name="git" size={13} /> Backend
          </dt>
          <dd className="mono">{backendSha.slice(0, 7)}</dd>
        </div>
        <div>
          <dt>
            <Icon name="git" size={13} /> Frontend
          </dt>
          <dd className="mono">{FRONTEND_SHA.slice(0, 7)}</dd>
        </div>
        <div>
          <dt>Database</dt>
          <dd className={system?.database === 'ok' ? 'ok' : 'bad'}>{system?.database ?? '—'}</dd>
        </div>
      </dl>
    </section>
  )
}
