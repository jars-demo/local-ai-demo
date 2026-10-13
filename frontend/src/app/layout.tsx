import type { Metadata, Viewport } from 'next'
import type { ReactNode } from 'react'

import { BackToTop } from '@/components/BackToTop'
import { Footer } from '@/components/Footer'
import { Header } from '@/components/Header'
import { SITE_URL, TAGLINE } from '@/lib/site'

import './globals.css'

// No web fonts are downloaded: the site must render identically on an offline server, so it uses
// the system font stack (globals.css) instead of fetching fonts at build or run time.

const TITLE = `Local AI Demo · ${TAGLINE}`
const DESCRIPTION =
  'A hands-on workshop: build a full-stack AI notes assistant with Next.js, FastAPI, PostgreSQL and a small local model on Ollama, then ship it to an air-gapped Linux server. No external AI APIs, no API keys.'

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: { default: TITLE, template: '%s · Local AI Demo' },
  description: DESCRIPTION,
  applicationName: 'Local AI Demo',
  keywords: [
    'local AI',
    'self-hosted LLM',
    'Ollama',
    'air-gapped deployment',
    'offline',
    'Docker Compose',
    'FastAPI',
    'PostgreSQL',
    'Next.js',
    'workshop',
  ],
  alternates: { canonical: '/' },
  openGraph: { type: 'website', url: SITE_URL, siteName: 'Local AI Demo', title: TITLE, description: DESCRIPTION },
  twitter: { card: 'summary', title: TITLE, description: DESCRIPTION },
  robots: { index: true, follow: true },
}

export const viewport: Viewport = {
  themeColor: [{ color: '#ffffff' }],
}

// White-first: light unless the visitor picked dark with the toggle. Runs before first paint.
const THEME_SCRIPT = `try{document.documentElement.dataset.theme=localStorage.getItem('theme')==='dark'?'dark':'light'}catch(e){document.documentElement.dataset.theme='light'}`

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_SCRIPT }} />
      </head>
      <body className="min-h-screen antialiased">
        <Header />
        <main id="main">{children}</main>
        <Footer />
        <BackToTop />
      </body>
    </html>
  )
}
