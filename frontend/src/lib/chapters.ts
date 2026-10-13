// The workshop modules, in order. The content lives in /workshop/*.md at the repository root (the
// single source of truth, also readable on GitHub); this list adds the titles, timings and parts
// the site needs for navigation. Keep it in step with the files.
export type Part = 'core' | 'advanced'

export type Chapter = {
  slug: string
  number: string
  title: string
  minutes: number
  summary: string
  part: Part
}

export const PARTS: Record<Part, { title: string; description: string }> = {
  core: {
    title: 'Part 1 · Core: run and understand the stack',
    description: 'For everyone. Containers, ports, volumes, HTTP, SQL, Docker DNS and a local model.',
  },
  advanced: {
    title: 'Part 2 · Advanced: ship it to an offline server',
    description: 'For operators. Bundle every artifact, deploy without internet, prove it, update it.',
  },
}

export const CHAPTERS: Chapter[] = [
  {
    slug: '01-architecture',
    number: '01',
    title: 'Architecture and Prerequisites',
    minutes: 20,
    summary: 'The four services, what "offline" really means, and getting your machine ready',
    part: 'core',
  },
  {
    slug: '02-containers',
    number: '02',
    title: 'Images, Containers, Ports and Volumes',
    minutes: 25,
    summary: 'Start the stack and see what each Docker building block does',
    part: 'core',
  },
  {
    slug: '03-frontend-to-backend',
    number: '03',
    title: 'Frontend to Backend over HTTP',
    minutes: 20,
    summary: 'Follow one click from the browser through nginx to FastAPI and back',
    part: 'core',
  },
  {
    slug: '04-backend-to-postgres',
    number: '04',
    title: 'Backend to PostgreSQL',
    minutes: 25,
    summary: 'Connection pools, migrations, parameterised SQL and full-text retrieval',
    part: 'core',
  },
  {
    slug: '05-docker-networking',
    number: '05',
    title: 'Docker DNS and Service Networking',
    minutes: 20,
    summary: 'Why service names work, why localhost does not, and the internal network',
    part: 'core',
  },
  {
    slug: '06-local-llm',
    number: '06',
    title: 'Running and Querying the Local LLM',
    minutes: 25,
    summary: 'Talk to the model directly, then through the app; retrieval before inference',
    part: 'core',
  },
  {
    slug: '07-inference-api',
    number: '07',
    title: 'The Inference API and Model Storage',
    minutes: 20,
    summary: 'Ollama endpoints, timings, manifests, blobs and checksums on disk',
    part: 'core',
  },
  {
    slug: '08-image-optimization',
    number: '08',
    title: 'Multi-stage Builds and Image Optimization',
    minutes: 25,
    summary: 'From a 5.6 GB Ollama image to 142 MB, and why each stage exists',
    part: 'core',
  },
  {
    slug: '09-offline-bundle',
    number: '09',
    title: 'Packaging a Portable Offline Bundle',
    minutes: 25,
    summary: 'Images, model, manifest and SHA-256 checksums in one reproducible archive',
    part: 'advanced',
  },
  {
    slug: '10-airgapped-deployment',
    number: '10',
    title: 'Deploying on Bare-metal Linux without Internet',
    minutes: 30,
    summary: 'Verify, load, restore, start and smoke test on a disconnected server',
    part: 'advanced',
  },
  {
    slug: '11-operations',
    number: '11',
    title: 'Acceptance Testing, Troubleshooting and Offline Updates',
    minutes: 25,
    summary: 'Prove the offline claim, diagnose failures, update and roll back without internet',
    part: 'advanced',
  },
]

export const TOTAL_MINUTES = CHAPTERS.reduce((sum, c) => sum + c.minutes, 0)

export function chapterIndex(slug: string): number {
  return CHAPTERS.findIndex((c) => c.slug === slug)
}
