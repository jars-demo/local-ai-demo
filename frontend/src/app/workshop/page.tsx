import type { Metadata } from 'next'

import { CodeBlock } from '@/components/CodeBlock'
import { CHAPTERS, PARTS, TOTAL_MINUTES, type Part } from '@/lib/chapters'
import { REPO_URL } from '@/lib/site'

export const metadata: Metadata = {
  title: 'Workshop',
  description:
    'Eleven hands-on modules: run a full-stack local AI app, understand every connection, then package it and deploy it to an offline Linux server.',
  alternates: { canonical: '/workshop/' },
}

export default function WorkshopIndex() {
  return (
    <div>
      <h1 className="text-3xl font-bold tracking-tight">Workshop</h1>
      <p className="mt-2 text-muted">
        {CHAPTERS.length} modules · about {Math.round(TOTAL_MINUTES / 60)} hours · every command says what it does, why,
        and what you should see.
      </p>

      <h2 className="mt-8 text-sm font-medium text-muted">You need Git and Docker with Compose v2.</h2>
      <div className="mt-2">
        <CodeBlock
          lang="bash"
          code={`git clone ${REPO_URL}.git\ncd local-ai-demo\ncp .env.example .env\n./scripts/pull-model.sh\ndocker compose up -d --build --wait`}
        />
      </div>

      {(Object.keys(PARTS) as Part[]).map((part) => (
        <section key={part} className="mt-10" aria-labelledby={`part-${part}`}>
          <h2 id={`part-${part}`} className="text-lg font-semibold">
            {PARTS[part].title}
          </h2>
          <p className="mt-1 text-sm text-muted">{PARTS[part].description}</p>
          <ol className="mt-4 divide-y divide-line rounded-xl border border-line bg-paper">
            {CHAPTERS.filter((chapter) => chapter.part === part).map((chapter) => (
              <li key={chapter.slug}>
                <a href={`/workshop/${chapter.slug}/`} className="flex items-center gap-4 px-4 py-3 hover:bg-paper-2">
                  <span className="w-6 font-mono text-xs text-faint">{chapter.number}</span>
                  <span className="min-w-0 flex-1">
                    <span className="block font-medium">{chapter.title}</span>
                    <span className="block text-sm text-muted">{chapter.summary}</span>
                  </span>
                  <span className="font-mono text-xs text-faint">{chapter.minutes}m</span>
                </a>
              </li>
            ))}
          </ol>
        </section>
      ))}
    </div>
  )
}
