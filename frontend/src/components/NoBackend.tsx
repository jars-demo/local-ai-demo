import { REPO_URL } from '@/lib/site'

// Shown when a page that needs the API finds no backend: the static workshop site (Vercel), or a
// page opened without the stack behind it. An explanation, not an error.
export function NoBackend() {
  return (
    <div role="status" className="card space-y-2 border-accent/40 bg-accent-soft p-5 text-sm">
      <p className="font-semibold text-text">No backend on this website, by design.</p>
      <p className="text-muted">
        This is the static workshop site. The assistant, PostgreSQL and the local model run on your own machine, never
        on a hosted server. Start the stack, then open <code className="font-mono">http://localhost:3000</code>:
      </p>
      <pre className="overflow-x-auto rounded-lg border border-line bg-paper px-3 py-2 font-mono text-xs">
        {`git clone ${REPO_URL}.git && cd local-ai-demo\ncp .env.example .env\n./scripts/pull-model.sh\ndocker compose up -d --build --wait`}
      </pre>
    </div>
  )
}
