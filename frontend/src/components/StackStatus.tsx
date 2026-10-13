'use client'

import { useEffect, useState } from 'react'

import { ApiError, api, formatBytes, type ModelInfo, type Ready } from '@/lib/api'

import { NoBackend } from './NoBackend'
import { ErrorNote, Spinner, Status } from './ui'

type State =
  | { kind: 'loading' }
  | { kind: 'error'; message: string; hint?: string; code?: string }
  | { kind: 'ok'; ready: Ready; model: ModelInfo | null }

const LABELS: Record<string, string> = {
  database: 'PostgreSQL answers and the notes table exists',
  ollama: 'Ollama answers on the private network',
  model: 'The model is installed in the model volume',
}

// Live readiness of the stack serving this page: real calls to /api/ready and /api/model.
export function StackStatus() {
  const [state, setState] = useState<State>({ kind: 'loading' })

  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        const ready = await api.ready()
        const model = ready.checks.ollama === 'ok' ? await api.model() : null
        if (!cancelled) setState({ kind: 'ok', ready, model })
      } catch (e) {
        if (cancelled) return
        const error = e instanceof ApiError ? e : null
        setState({ kind: 'error', message: error?.message ?? 'Unexpected error', hint: error?.hint, code: error?.code })
      }
    }
    load()
    return () => {
      cancelled = true
    }
  }, [])

  if (state.kind === 'loading') {
    return (
      <p className="card flex items-center gap-2 p-5 text-sm text-muted" role="status">
        <Spinner /> Asking this server&apos;s backend for its readiness…
      </p>
    )
  }
  if (state.kind === 'error' && state.code === 'NO_BACKEND') return <NoBackend />
  if (state.kind === 'error') {
    return <ErrorNote title="Could not reach the backend" message={state.message} hint={state.hint} />
  }
  const { ready, model } = state
  return (
    <div className="card p-5">
      <p className="text-sm font-semibold">
        {ready.status === 'ready' ? 'This server is ready for local inference.' : 'This server is not ready yet.'}
      </p>
      <ul className="mt-3 space-y-2">
        {Object.entries(ready.checks).map(([name, value]) => (
          <li key={name} className="flex flex-wrap items-center gap-x-3 text-sm">
            <Status state={value === 'ok' ? 'ok' : 'danger'}>{value === 'ok' ? 'OK' : 'Problem'}</Status>
            <span>{LABELS[name] ?? name}</span>
            {value !== 'ok' && <span className="font-mono text-xs text-danger">{value}</span>}
          </li>
        ))}
      </ul>
      {model?.installed && (
        <p className="mt-3 font-mono text-xs text-muted">
          {model.name} · {model.family} · {model.parameter_size} parameters · {model.quantization} ·{' '}
          {model.size_bytes ? formatBytes(model.size_bytes) : ''} · Ollama {model.ollama_version}
        </p>
      )}
      <a href="/app/" className="mt-4 inline-block text-sm font-semibold text-accent hover:underline">
        Open the assistant →
      </a>
    </div>
  )
}
