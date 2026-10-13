import type { Metadata } from 'next'

import { CodeBlock } from '@/components/CodeBlock'
import { NotesApp } from '@/components/NotesApp'
import { PageHeader } from '@/components/ui'
import { IS_STATIC_SITE, REPO_URL } from '@/lib/site'

export const metadata: Metadata = {
  title: 'AI Notes Assistant',
  description: 'Write notes, ask questions about them and summarise them with a small model running on your machine.',
  alternates: { canonical: '/app/' },
}

export default function AssistantPage() {
  return (
    <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6 lg:py-14">
      <PageHeader eyebrow="The application" title="AI Notes Assistant">
        Notes in PostgreSQL, answers from <code className="font-mono text-base">qwen3:0.6b</code> on Ollama. Every
        request on this page goes to <code className="font-mono text-base">/api</code> on this server and nowhere else.
      </PageHeader>
      <div className="mt-8">
        {IS_STATIC_SITE ? (
          <div className="card max-w-3xl space-y-4 p-6">
            <p className="font-semibold">This public site has no backend, so the assistant runs on your machine.</p>
            <p className="text-sm text-muted">
              The live assistant needs the full stack: nginx, FastAPI, PostgreSQL and Ollama with the model installed.
              Start it, then open <code>http://localhost:3000/app/</code>. It never calls an external AI service.
            </p>
            <CodeBlock
              lang="bash"
              code={`git clone ${REPO_URL}.git && cd local-ai-demo\ncp .env.example .env\n./scripts/pull-model.sh\ndocker compose up -d --build --wait`}
            />
          </div>
        ) : (
          <NotesApp />
        )}
      </div>
    </div>
  )
}
