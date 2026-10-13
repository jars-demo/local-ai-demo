// The stack as a diagram built from HTML boxes, so it reflows on a phone and stays readable for
// screen readers (it is a list of hops). Names and ports match compose.yaml exactly.

function Box({
  name,
  role,
  detail,
  tone = 'default',
}: {
  name: string
  role: string
  detail: string
  tone?: 'default' | 'model' | 'data'
}) {
  const ring = tone === 'model' ? 'border-accent' : tone === 'data' ? 'border-ok-mark' : 'border-line'
  return (
    <div className={`rounded-lg border-2 ${ring} bg-paper px-3 py-2.5`}>
      <p className="font-mono text-sm font-semibold">{name}</p>
      <p className="text-xs text-muted">{role}</p>
      <p className="mt-1 font-mono text-[11px] text-faint">{detail}</p>
    </div>
  )
}

function Arrow({ label }: { label: string }) {
  return (
    <div
      className="flex items-center justify-center gap-1 py-1 text-faint lg:flex-col lg:px-1 lg:py-0"
      aria-hidden="true"
    >
      <span className="text-lg leading-none lg:rotate-0">
        <span className="lg:hidden">↓</span>
        <span className="hidden lg:inline">→</span>
      </span>
      <span className="font-mono text-[10px] whitespace-nowrap">{label}</span>
    </div>
  )
}

export function ArchitectureDiagram() {
  return (
    <figure className="card overflow-hidden">
      <div className="grid items-center gap-1 p-4 lg:grid-cols-[auto_auto_1fr_auto_2.4fr] lg:gap-2 lg:p-6">
        <Box name="Browser" role="You" detail="any device on your network" />
        <Arrow label="HTTP :3000" />

        <div className="rounded-xl border border-dashed border-line p-2">
          <p className="px-1 pb-1.5 font-mono text-[11px] font-semibold text-muted">edge network</p>
          <Box name="web" role="nginx: static site + /api proxy" detail="local-ai-demo-web · :8080" />
        </div>
        <Arrow label="/api → backend:8000" />

        <div className="rounded-xl border border-dashed border-accent/60 bg-accent-soft/40 p-2">
          <p className="px-1 pb-1.5 font-mono text-[11px] font-semibold text-accent">
            private network · internal: true · no route to the internet
          </p>
          <div className="grid gap-2 sm:grid-cols-[1fr_auto_1fr] sm:items-center">
            <Box name="backend" role="FastAPI: notes, retrieval, prompts" detail="local-ai-demo-backend · :8000" />
            <div className="grid gap-2 text-center font-mono text-[10px] text-faint" aria-hidden="true">
              <span>SQL →</span>
              <span>HTTP →</span>
            </div>
            <div className="grid gap-2">
              <Box name="postgres" role="notes + full-text index" detail="volume: postgres-data" tone="data" />
              <Box name="ollama" role="qwen3:0.6b on the CPU" detail="volume: ollama-models (read-only)" tone="model" />
            </div>
          </div>
        </div>
      </div>
      <figcaption className="border-t border-line bg-paper-2 px-4 py-3 text-xs text-muted">
        One published port. Containers find each other by service name through Docker&apos;s DNS, never through{' '}
        <code>localhost</code>. The browser only ever talks to <code>web</code>.
      </figcaption>
    </figure>
  )
}
