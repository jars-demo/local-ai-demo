import type { Metadata } from 'next'

import { Markdown } from '@/components/Markdown'
import { PageHeader } from '@/components/ui'
import { loadDoc } from '@/lib/markdown'
import { REPO_URL } from '@/lib/site'

export const metadata: Metadata = {
  title: 'Offline deployment',
  description:
    'Build a portable bundle on a connected machine, carry it to an air-gapped Linux server, and deploy the stack with no internet access.',
  alternates: { canonical: '/deploy/' },
}

// The guide is docs/offline-deployment.md, the same file that ships inside every offline bundle.
export default async function DeployPage() {
  const body = await loadDoc('offline-deployment')
  return (
    <div className="mx-auto max-w-4xl px-4 py-10 sm:px-6 lg:py-14">
      <PageHeader eyebrow="Advanced · operators" title="Offline deployment guide">
        Connected build machine → portable bundle → air-gapped Linux server. This page is{' '}
        <a
          className="text-accent underline underline-offset-2"
          href={`${REPO_URL}/blob/main/docs/offline-deployment.md`}
          target="_blank"
          rel="noreferrer"
        >
          docs/offline-deployment.md
        </a>
        , the same guide that ships inside every bundle.
      </PageHeader>
      <div className="mt-10">
        <Markdown source={body} />
      </div>
    </div>
  )
}
