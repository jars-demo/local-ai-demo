// Build flavours. `npm run build` (and Docker) makes the full app: the assistant page calls /api on
// the same origin, which nginx proxies to the backend. `npm run build:static` makes the public site:
// the same pages, but the assistant explains how to run the stack, because a static host has no
// backend and this site never shows invented answers.
export const IS_STATIC_SITE = process.env.NEXT_PUBLIC_SITE_MODE === 'static'

// Empty in Docker (same origin). For `npm run dev`, point it at a running stack:
// NEXT_PUBLIC_API_URL=http://localhost:3000
export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? ''

export const SITE_URL = 'https://local-ai.jishanahmed.in'
export const REPO_URL = 'https://github.com/jars-demo/local-ai-demo'

export const SITE_NAME = 'Local AI Demo'
export const TAGLINE = 'Local AI. Zero External APIs. Fully Offline Deployment.'

// Pinned versions, kept in step with compose.yaml, the Dockerfiles and the README.
export const VERSIONS = {
  app: '1.0.0',
  model: 'qwen3:0.6b',
  ollama: '0.40.3',
  postgres: '18.6',
  python: '3.13',
  fastapi: '0.143.0',
  next: '16.4.0',
  node: '22',
} as const

export type NavItem = { href: string; label: string }

export const NAV: NavItem[] = [
  { href: '/', label: 'Overview' },
  { href: '/app/', label: 'Assistant' },
  { href: '/workshop/', label: 'Workshop' },
  { href: '/deploy/', label: 'Offline deployment' },
]

export const JARS_LINKS = [
  { href: 'https://github.com/jars-demo', label: 'JARS Demo on GitHub' },
  { href: 'https://github.com/jars-demo/jars-skills', label: 'JARS Skills' },
  { href: 'https://skills.jishanahmed.in', label: 'skills.jishanahmed.in' },
  { href: 'https://jishanahmed.in', label: 'Jishanahmed' },
] as const
