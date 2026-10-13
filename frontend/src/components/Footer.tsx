import { REPO_URL, VERSIONS } from '@/lib/site'

export function Footer() {
  return (
    <footer className="mt-24 border-t border-line bg-paper-2">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-x-6 gap-y-2 px-4 py-6 text-sm text-muted sm:px-6">
        <p>
          Local AI Demo, an open-source workshop (MIT). Model: Qwen3 0.6B by the Qwen team (Apache 2.0), served by
          Ollama (MIT).
        </p>
        <p className="flex items-center gap-4">
          <span className="font-mono text-xs text-faint">
            {VERSIONS.model} · Ollama {VERSIONS.ollama}
          </span>
          <a className="hover:text-text" href={REPO_URL} target="_blank" rel="noreferrer">
            Source on GitHub
          </a>
        </p>
      </div>
    </footer>
  )
}
