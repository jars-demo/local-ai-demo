// A typed client for the backend. Every call goes to /api on the same origin; nginx proxies it to
// the backend container by its Docker DNS name (http://backend:8000). The browser never talks to
// PostgreSQL or Ollama, and nothing here calls any service outside your machine.
import { API_URL } from './site'

export type Note = {
  id: number
  title: string
  body: string
  created_at: string
  updated_at: string
}

export type NoteList = { data: Note[]; meta: { total: number; limit: number; offset: number } }

export type Inference = {
  model: string
  total_ms: number
  load_ms: number
  prompt_tokens: number
  output_tokens: number
}

export type AskResponse = {
  answer: string
  retrieval: 'search' | 'recent' | 'none'
  sources: { id: number; title: string; score: number | null }[]
  retrieval_ms: number
  inference: Inference | null
}

export type SummaryResponse = { note_id: number; summary: string; inference: Inference }

export type Ready = { status: 'ready' | 'not_ready'; checks: Record<string, string> }

export type ModelInfo = {
  name: string
  installed: boolean
  ollama_version: string | null
  size_bytes: number | null
  digest: string | null
  family: string | null
  parameter_size: string | null
  quantization: string | null
  context_length: number | null
}

/** The backend's error shape, or a network failure described the same way. */
export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly code: string,
    readonly hint?: string,
  ) {
    super(message)
  }
}

export const NO_BACKEND_MESSAGE =
  'This website is the static workshop site: it has no backend, database or model behind it.'
export const NO_BACKEND_HINT =
  'Run the stack on your machine (docker compose up -d --build --wait) and open http://localhost:3000.'

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${API_URL}/api${path}`, {
      method,
      headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
      body: body === undefined ? undefined : JSON.stringify(body),
    })
  } catch {
    throw new ApiError('The backend is not reachable.', 0, 'NETWORK', 'Is the stack running? docker compose ps')
  }
  if (response.status === 204) return undefined as T
  // No backend behind this site (a static host such as Vercel): /api is a 404 page or a redirect,
  // not this API's JSON. Say so plainly instead of reporting an HTTP error.
  const isJson = response.headers.get('content-type')?.includes('application/json') ?? false
  if (!isJson && (response.status === 404 || response.redirected || response.status < 400)) {
    throw new ApiError(NO_BACKEND_MESSAGE, response.status, 'NO_BACKEND', NO_BACKEND_HINT)
  }
  const data = await response.json().catch(() => null)
  if (!response.ok) {
    const error = data?.error
    if (error) throw new ApiError(error.message, response.status, error.code, error.hint)
    // /api/ready answers 503 with its own shape: pass it through to the caller.
    if (response.status === 503 && data?.checks) return data as T
    throw new ApiError(`HTTP ${response.status}`, response.status, 'HTTP_ERROR')
  }
  return data as T
}

export const api = {
  ready: () => request<Ready>('GET', '/ready'),
  model: () => request<ModelInfo>('GET', '/model'),
  listNotes: (limit = 100) => request<NoteList>('GET', `/notes?limit=${limit}`),
  createNote: (title: string, body: string) => request<Note>('POST', '/notes', { title, body }),
  updateNote: (id: number, changes: { title?: string; body?: string }) =>
    request<Note>('PATCH', `/notes/${id}`, changes),
  deleteNote: (id: number) => request<void>('DELETE', `/notes/${id}`),
  summarise: (id: number) => request<SummaryResponse>('POST', `/notes/${id}/summary`),
  ask: (question: string) => request<AskResponse>('POST', '/ask', { question }),
}

export function formatMs(ms: number): string {
  return ms < 1000 ? `${ms} ms` : `${(ms / 1000).toFixed(1)} s`
}

export function formatBytes(bytes: number): string {
  return bytes >= 1e9 ? `${(bytes / 1e9).toFixed(2)} GB` : `${Math.round(bytes / 1e6)} MB`
}
