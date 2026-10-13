'use client'

import { type FormEvent, useCallback, useEffect, useState } from 'react'

import {
  type AskResponse,
  ApiError,
  api,
  formatBytes,
  formatMs,
  type Inference,
  type ModelInfo,
  type Note,
  type Ready,
} from '@/lib/api'

import { Badge, Button, Empty, ErrorNote, Spinner, Status } from './ui'

type Failure = { message: string; hint?: string; code?: string }

function toFailure(error: unknown): Failure {
  if (error instanceof ApiError) return { message: error.message, hint: error.hint, code: error.code }
  return { message: 'Something went wrong. Check the browser console and `docker compose logs backend`.' }
}

function InferenceLine({ inference }: { inference: Inference }) {
  const loaded = inference.load_ms > 500 ? ` (model load ${formatMs(inference.load_ms)})` : ''
  return (
    <p className="font-mono text-xs text-muted">
      {inference.model} · {formatMs(inference.total_ms)}
      {loaded} · {inference.prompt_tokens} tokens in · {inference.output_tokens} tokens out · ran on your machine
    </p>
  )
}

// --- Stack status -------------------------------------------------------------------------------

function StackBar({ ready, model, error }: { ready: Ready | null; model: ModelInfo | null; error: Failure | null }) {
  if (error) return <ErrorNote title="The backend is not reachable" message={error.message} hint={error.hint} />
  if (!ready) {
    return (
      <p className="flex items-center gap-2 text-sm text-muted" role="status">
        <Spinner /> Checking the stack…
      </p>
    )
  }
  const labels: Record<string, string> = { database: 'PostgreSQL', ollama: 'Ollama', model: 'Model' }
  return (
    <div className="card flex flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3">
      {Object.entries(ready.checks).map(([name, value]) => (
        <Status key={name} state={value === 'ok' ? 'ok' : 'danger'}>
          {labels[name] ?? name}
          <span className="sr-only">: {value}</span>
          {value !== 'ok' && <span className="font-normal">({value})</span>}
        </Status>
      ))}
      {model?.installed && (
        <span className="font-mono text-xs text-muted sm:ml-auto">
          {model.name} · {model.parameter_size} · {model.quantization} ·{' '}
          {model.size_bytes ? formatBytes(model.size_bytes) : '?'} · Ollama {model.ollama_version}
        </span>
      )}
      {ready.checks.model && ready.checks.model !== 'ok' && (
        <p className="w-full text-sm text-danger">
          The model is not installed. On a connected machine run <code>./scripts/pull-model.sh</code>; on an offline
          server run <code>./scripts/offline-install.sh</code> from the bundle. Notes still work meanwhile.
        </p>
      )}
    </div>
  )
}

// --- Ask ------------------------------------------------------------------------------------------

function AskPanel({ onOpenNote }: { onOpenNote: (id: number) => void }) {
  const [question, setQuestion] = useState('')
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState<AskResponse | null>(null)
  const [error, setError] = useState<Failure | null>(null)

  async function ask(event: FormEvent) {
    event.preventDefault()
    if (question.trim().length < 3) return
    setBusy(true)
    setError(null)
    try {
      setResult(await api.ask(question.trim()))
    } catch (e) {
      setResult(null)
      setError(toFailure(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <section aria-labelledby="ask-title" className="card p-5">
      <h2 id="ask-title" className="text-lg font-semibold">
        Ask your notes
      </h2>
      <p className="mt-1 text-sm text-muted">
        The backend finds matching notes with PostgreSQL full-text search, then the local model answers from them.
      </p>
      <form onSubmit={ask} className="mt-4 flex flex-col gap-2 sm:flex-row">
        <label htmlFor="question" className="sr-only">
          Question
        </label>
        <input
          id="question"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Where is the backup NAS?"
          maxLength={500}
          className="h-10 min-w-0 flex-1 rounded-lg border border-line bg-paper px-3 text-sm"
        />
        <Button type="submit" busy={busy} disabled={question.trim().length < 3}>
          {busy ? 'Thinking on your CPU…' : 'Ask'}
        </Button>
      </form>

      <div aria-live="polite" className="mt-4 space-y-3">
        {busy && (
          <p className="text-sm text-muted">
            Running on the local model. The first answer after a start also loads the model into memory.
          </p>
        )}
        {error && <ErrorNote title={error.code} message={error.message} hint={error.hint} />}
        {result && !busy && (
          <div className="space-y-3 rounded-lg border border-line bg-paper-2 p-4">
            <p className="whitespace-pre-wrap leading-relaxed">{result.answer}</p>
            {result.sources.length > 0 && (
              <div className="flex flex-wrap items-center gap-2 text-sm">
                <span className="text-muted">
                  {result.retrieval === 'search' ? 'Matched notes:' : 'No note matched; used the most recent:'}
                </span>
                {result.sources.map((source) => (
                  <button
                    key={source.id}
                    type="button"
                    onClick={() => onOpenNote(source.id)}
                    className="rounded-md border border-line bg-paper px-2 py-0.5 font-mono text-xs hover:border-accent hover:text-accent"
                  >
                    #{source.id} {source.title}
                  </button>
                ))}
              </div>
            )}
            {result.inference ? (
              <InferenceLine inference={result.inference} />
            ) : (
              <p className="font-mono text-xs text-muted">No model call: there are no notes to answer from.</p>
            )}
          </div>
        )}
      </div>
    </section>
  )
}

// --- Editor -----------------------------------------------------------------------------------

function Editor({
  note,
  onSaved,
  onDeleted,
}: {
  note: Note | null
  onSaved: (note: Note) => void
  onDeleted: (id: number) => void
}) {
  const [title, setTitle] = useState(note?.title ?? '')
  const [body, setBody] = useState(note?.body ?? '')
  const [saving, setSaving] = useState(false)
  const [confirming, setConfirming] = useState(false)
  const [summary, setSummary] = useState<{ text: string; inference: Inference } | null>(null)
  const [summarising, setSummarising] = useState(false)
  const [error, setError] = useState<Failure | null>(null)

  const dirty = note ? title !== note.title || body !== note.body : title.trim() !== '' || body !== ''

  async function save(event: FormEvent) {
    event.preventDefault()
    setSaving(true)
    setError(null)
    try {
      onSaved(note ? await api.updateNote(note.id, { title, body }) : await api.createNote(title, body))
    } catch (e) {
      setError(toFailure(e))
    } finally {
      setSaving(false)
    }
  }

  async function remove() {
    if (!note) return
    setError(null)
    try {
      await api.deleteNote(note.id)
      onDeleted(note.id)
    } catch (e) {
      setError(toFailure(e))
      setConfirming(false)
    }
  }

  async function summarise() {
    if (!note) return
    setSummarising(true)
    setError(null)
    try {
      const response = await api.summarise(note.id)
      setSummary({ text: response.summary, inference: response.inference })
    } catch (e) {
      setError(toFailure(e))
    } finally {
      setSummarising(false)
    }
  }

  return (
    <form onSubmit={save} className="card space-y-4 p-5" aria-label={note ? `Edit note ${note.id}` : 'New note'}>
      <div className="flex items-center justify-between gap-2">
        <h2 className="text-lg font-semibold">{note ? `Note #${note.id}` : 'New note'}</h2>
        {note && <span className="text-xs text-faint">Updated {new Date(note.updated_at).toLocaleString()}</span>}
      </div>
      <div>
        <label htmlFor="note-title" className="text-sm font-medium">
          Title
        </label>
        <input
          id="note-title"
          required
          maxLength={200}
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          className="mt-1 h-10 w-full rounded-lg border border-line bg-paper px-3 text-sm"
        />
      </div>
      <div>
        <label htmlFor="note-body" className="text-sm font-medium">
          Body
        </label>
        <textarea
          id="note-body"
          rows={9}
          maxLength={20000}
          value={body}
          onChange={(e) => setBody(e.target.value)}
          className="mt-1 w-full rounded-lg border border-line bg-paper px-3 py-2 text-sm leading-relaxed"
        />
      </div>
      {error && <ErrorNote title={error.code} message={error.message} hint={error.hint} />}
      <div className="flex flex-wrap items-center gap-2">
        <Button type="submit" busy={saving} disabled={!dirty || !title.trim()}>
          {note ? 'Save changes' : 'Create note'}
        </Button>
        {note && (
          <Button variant="secondary" onClick={summarise} busy={summarising} disabled={dirty}>
            {summarising ? 'Summarising…' : 'Summarise with the local model'}
          </Button>
        )}
        {note &&
          (confirming ? (
            <span className="flex items-center gap-2 text-sm sm:ml-auto">
              Delete for good?
              <Button variant="danger" onClick={remove}>
                Yes, delete
              </Button>
              <Button variant="secondary" onClick={() => setConfirming(false)}>
                Cancel
              </Button>
            </span>
          ) : (
            <span className="sm:ml-auto">
              <Button variant="danger" onClick={() => setConfirming(true)}>
                Delete
              </Button>
            </span>
          ))}
      </div>
      {note && dirty && <p className="text-xs text-muted">Save your changes before summarising.</p>}
      <div aria-live="polite">
        {summary && (
          <div className="space-y-2 rounded-lg border border-line bg-paper-2 p-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-accent">Summary</p>
            <p className="whitespace-pre-wrap text-sm leading-relaxed">{summary.text}</p>
            <InferenceLine inference={summary.inference} />
          </div>
        )}
      </div>
    </form>
  )
}

// --- The page ---------------------------------------------------------------------------------

export function NotesApp() {
  const [notes, setNotes] = useState<Note[] | null>(null)
  const [total, setTotal] = useState(0)
  const [selected, setSelected] = useState<number | 'new'>('new')
  const [loadError, setLoadError] = useState<Failure | null>(null)
  const [ready, setReady] = useState<Ready | null>(null)
  const [model, setModel] = useState<ModelInfo | null>(null)
  const [stackError, setStackError] = useState<Failure | null>(null)

  // Fetches the list; `isCurrent` lets the first load ignore a response that arrives after unmount.
  const loadNotes = useCallback(async (isCurrent: () => boolean = () => true) => {
    try {
      const page = await api.listNotes()
      if (!isCurrent()) return
      setNotes(page.data)
      setTotal(page.meta.total)
      setLoadError(null)
    } catch (e) {
      if (isCurrent()) setLoadError(toFailure(e))
    }
  }, [])

  useEffect(() => {
    let cancelled = false
    const isCurrent = () => !cancelled
    async function load() {
      const notesLoaded = loadNotes(isCurrent)
      try {
        const status = await api.ready()
        if (cancelled) return
        setReady(status)
        setStackError(null)
        if (status.checks.ollama === 'ok') setModel(await api.model())
      } catch (e) {
        if (!cancelled) setStackError(toFailure(e))
      }
      await notesLoaded
    }
    load()
    return () => {
      cancelled = true
    }
  }, [loadNotes])

  const current = selected === 'new' ? null : (notes?.find((n) => n.id === selected) ?? null)

  return (
    <div className="space-y-6">
      <StackBar ready={ready} model={model} error={stackError} />
      <AskPanel onOpenNote={(id) => setSelected(id)} />

      <div className="grid gap-6 lg:grid-cols-[320px_minmax(0,1fr)]">
        <section aria-labelledby="notes-title" className="card p-4">
          <div className="flex items-center justify-between gap-2">
            <h2 id="notes-title" className="text-lg font-semibold">
              Notes <span className="font-mono text-sm font-normal text-muted">{notes ? total : ''}</span>
            </h2>
            <Button variant="secondary" onClick={() => setSelected('new')}>
              + New
            </Button>
          </div>
          <div className="mt-3">
            {loadError && <ErrorNote message={loadError.message} hint={loadError.hint} />}
            {!notes && !loadError && (
              <ul className="space-y-2" aria-label="Loading notes">
                {[0, 1, 2].map((i) => (
                  <li key={i} className="h-12 animate-pulse rounded-lg bg-paper-2 motion-reduce:animate-none" />
                ))}
              </ul>
            )}
            {notes && notes.length === 0 && (
              <Empty>
                No notes yet. Write one, then ask a question about it. Notes are stored in PostgreSQL on this machine.
              </Empty>
            )}
            {notes && notes.length > 0 && (
              <ul className="max-h-[28rem] space-y-1 overflow-y-auto">
                {notes.map((note) => (
                  <li key={note.id}>
                    <button
                      type="button"
                      onClick={() => setSelected(note.id)}
                      aria-current={selected === note.id ? 'true' : undefined}
                      className="w-full rounded-lg px-3 py-2 text-left hover:bg-paper-2 aria-[current=true]:bg-accent-soft"
                    >
                      <span className="flex items-center gap-2">
                        <span className="font-mono text-xs text-faint">#{note.id}</span>
                        <span className="truncate font-medium">{note.title}</span>
                      </span>
                      <span className="block truncate text-xs text-muted">{note.body || 'Empty note'}</span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </section>

        <Editor
          key={current ? `${current.id}-${current.updated_at}` : 'new'}
          note={current}
          onSaved={(note) => {
            setSelected(note.id)
            loadNotes()
          }}
          onDeleted={() => {
            setSelected('new')
            loadNotes()
          }}
        />
      </div>
      <p className="text-xs text-faint">
        <Badge>Private</Badge> Notes, questions and answers stay on this server: the browser talks only to this origin,
        and the model runs in a container with no internet route.
      </p>
    </div>
  )
}
