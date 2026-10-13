import { ArchitectureDiagram } from '@/components/ArchitectureDiagram'
import { CodeBlock } from '@/components/CodeBlock'
import { StackStatus } from '@/components/StackStatus'
import { Badge, Section } from '@/components/ui'
import { CHAPTERS, PARTS, TOTAL_MINUTES, type Part } from '@/lib/chapters'
import { MEASURED, RECORDED_ANSWER } from '@/lib/measurements'
import { IS_STATIC_SITE, REPO_URL, VERSIONS } from '@/lib/site'

const TECH = ['Next.js', 'FastAPI', 'PostgreSQL', 'Ollama', VERSIONS.model, 'Docker Compose']

const PROMISES = [
  {
    title: 'No external AI APIs',
    claim: 'Every answer comes from a model running in your own container. No API keys, no cloud inference.',
    how: 'The backend has exactly one model client, for Ollama at http://ollama:11434. It has no pull method and no fallback provider. Ollama runs with OLLAMA_NO_CLOUD=1.',
    proof: 'tests/test_llm.py, grep the backend for any other host',
  },
  {
    title: 'No internet at runtime',
    claim: 'Once the bundle is on the server, nothing is downloaded: not images, not models, not fonts.',
    how: 'The installer loads images with docker load, restores the model from the bundle and starts Compose with --pull never. The site uses system fonts.',
    proof: './scripts/airgap-test.sh --require-offline-host on a disconnected server',
  },
  {
    title: 'Strict network isolation',
    claim: 'Even on a connected host, the backend, database and model cannot reach the internet.',
    how: 'They sit on a Docker network with internal: true. Only nginx has a published port. The model volume is mounted read-only.',
    proof: './scripts/airgap-test.sh checks egress from inside each container',
  },
]

const CONNECTED = [
  ['Test', 'Unit and integration tests, lint, Compose validation', './scripts/build-bundle.sh runs them first'],
  ['Build', 'Multi-stage images: web, backend, slim Ollama', 'docker compose build'],
  ['Pull', 'Third-party image: postgres', 'docker pull postgres:18.6-alpine3.24'],
  ['Download', 'The model, with Ollama verifying every blob', './scripts/pull-model.sh'],
  ['Export', 'docker save | gzip per image; the model blobs as a tar', 'images/*.tar.gz, models/*.tar'],
  ['Describe', 'manifest.json (versions, architectures, sizes) + SHA256SUMS', 'every file is checksummed'],
  ['Package', 'One archive with a stable file order and timestamps', 'dist/local-ai-demo-bundle-*.tar'],
]

const OFFLINE = [
  ['Verify', 'Archive checksum, then every file inside it', 'sha256sum -c *.tar.sha256'],
  ['Check', 'Linux, architecture, Docker, Compose, CPU, RAM, disk', './scripts/check-prereqs.sh'],
  ['Load', 'docker load each image, compare image IDs to the manifest', 'no registry is contacted'],
  ['Restore', 'Model blobs into the model volume, re-hashed on disk', 'sha256 of each blob'],
  ['Start', 'docker compose up --pull never --no-build --wait', './scripts/offline-install.sh'],
  ['Prove', 'Health, a note in PostgreSQL, a real answer, a restart', './scripts/smoke-test.sh'],
  ['Diagnose', 'Every failure prints the command that fixes it', './scripts/diagnose.sh'],
]

const OUTCOMES = [
  'Explain every hop: browser → nginx → FastAPI → PostgreSQL and Ollama',
  'Use Docker DNS and an internal network instead of localhost and open ports',
  'Run retrieval before inference with nothing but SQL full-text search',
  'Read Ollama timings, manifests and blobs, and verify a model by checksum',
  'Shrink an image from 5.6 GB to 142 MB with a multi-stage build',
  'Package, move, verify and deploy a stack on a server with no internet',
]

function StepList({ title, steps, tone }: { title: string; steps: string[][]; tone: 'accent' | 'ok' }) {
  return (
    <div className="card p-5">
      <p className="flex items-center gap-2 font-semibold">
        <Badge tone={tone}>{tone === 'accent' ? 'online' : 'offline'}</Badge> {title}
      </p>
      <ol className="mt-4 space-y-3">
        {steps.map(([name, text, command], i) => (
          <li key={name} className="grid grid-cols-[1.75rem_1fr] gap-x-2">
            <span className="font-mono text-xs leading-6 text-faint">{String(i + 1).padStart(2, '0')}</span>
            <span>
              <span className="font-semibold">{name}.</span> <span className="text-sm text-muted">{text}</span>
              <code className="mt-0.5 block font-mono text-xs break-all text-accent">{command}</code>
            </span>
          </li>
        ))}
      </ol>
    </div>
  )
}

export default function HomePage() {
  return (
    <>
      <section className="border-b border-line bg-gradient-to-b from-accent-soft to-bg">
        <div className="mx-auto grid max-w-7xl gap-12 px-4 py-14 sm:px-6 lg:grid-cols-[1fr_1fr] lg:py-20">
          <div>
            <p className="font-mono text-sm font-semibold text-accent">local-ai-demo · JARS workshop</p>
            <h1 className="mt-3 text-4xl font-bold leading-[1.08] tracking-tight sm:text-5xl">
              Local AI.
              <br />
              Zero External APIs.
              <br />
              <span className="text-accent">Fully Offline Deployment.</span>
            </h1>
            <p className="mt-6 max-w-xl text-lg leading-relaxed text-muted">
              Build a full-stack AI notes assistant with Next.js, FastAPI, PostgreSQL and a {MEASURED.modelSize} model
              on Ollama. Then package every image and the model weights into one verified bundle and deploy it to a
              Linux server with no internet connection.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <a
                href="/workshop/"
                className="inline-flex h-11 items-center gap-2 rounded-lg bg-brand px-5 font-semibold text-white hover:bg-brand-hover"
              >
                Start the workshop <span aria-hidden="true">→</span>
              </a>
              <a
                href={IS_STATIC_SITE ? REPO_URL : '/app/'}
                target={IS_STATIC_SITE ? '_blank' : undefined}
                rel={IS_STATIC_SITE ? 'noreferrer' : undefined}
                className="inline-flex h-11 items-center gap-2 rounded-lg border border-line bg-paper px-5 font-semibold hover:border-accent hover:text-accent"
              >
                {IS_STATIC_SITE ? 'View on GitHub' : 'Open the assistant'} <span aria-hidden="true">→</span>
              </a>
            </div>
            <ul className="mt-8 flex flex-wrap gap-2" aria-label="Technologies">
              {TECH.map((tech) => (
                <li
                  key={tech}
                  className="rounded-md border border-line bg-paper px-2.5 py-1 font-mono text-xs text-muted"
                >
                  {tech}
                </li>
              ))}
            </ul>
          </div>

          <figure className="card self-center overflow-hidden">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-line bg-paper-2 px-4 py-2.5">
              <span className="font-mono text-xs text-muted">POST /api/ask · recorded on {RECORDED_ANSWER.where}</span>
              <Badge tone="ok">no network</Badge>
            </div>
            <div className="space-y-4 p-4 text-sm">
              <p>
                <span className="block text-xs font-semibold uppercase tracking-wide text-muted">Question</span>
                {RECORDED_ANSWER.question}
              </p>
              <p>
                <span className="block text-xs font-semibold uppercase tracking-wide text-muted">
                  Retrieved by PostgreSQL full-text search
                </span>
                <span className="font-mono text-xs">{RECORDED_ANSWER.sources}</span>
              </p>
              <p>
                <span className="block text-xs font-semibold uppercase tracking-wide text-muted">
                  Answer from {RECORDED_ANSWER.model}
                </span>
                {RECORDED_ANSWER.answer}
              </p>
            </div>
            <figcaption className="border-t border-line px-4 py-3 font-mono text-xs text-muted">
              {RECORDED_ANSWER.timing}
              <span className="mt-1 block font-sans text-faint">
                A real response from this stack, kept as a static example.
              </span>
            </figcaption>
          </figure>
        </div>
      </section>

      <div className="mx-auto max-w-7xl px-4 sm:px-6">
        <Section
          id="promises"
          title="Three promises, kept apart"
          intro="They are often blurred together. They are different claims, enforced in different places, and each one is tested separately."
        >
          <div className="grid gap-4 md:grid-cols-3">
            {PROMISES.map((promise) => (
              <div key={promise.title} className="card flex flex-col p-5">
                <p className="text-lg font-semibold">{promise.title}</p>
                <p className="mt-2 text-sm">{promise.claim}</p>
                <p className="mt-3 text-sm text-muted">
                  <span className="font-semibold text-text">How: </span>
                  {promise.how}
                </p>
                <p className="mt-auto pt-3 font-mono text-xs text-accent">{promise.proof}</p>
              </div>
            ))}
          </div>
        </Section>

        <Section id="architecture" title="Architecture" intro="Four containers, two networks, two volumes, one port.">
          <ArchitectureDiagram />
          <div className="table-wrap mt-6">
            <table>
              <thead>
                <tr>
                  <th scope="col">Service</th>
                  <th scope="col">Image</th>
                  <th scope="col">Size</th>
                  <th scope="col">Role</th>
                  <th scope="col">Reachable from</th>
                </tr>
              </thead>
              <tbody>
                {MEASURED.images.map((image) => (
                  <tr key={image.service}>
                    <td className="font-mono">{image.service}</td>
                    <td className="font-mono text-xs">{image.image}</td>
                    <td className="font-mono text-xs whitespace-nowrap">{image.size}</td>
                    <td>{image.role}</td>
                    <td className="text-muted">{image.reach}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="mt-2 text-xs text-faint">{MEASURED.imagesNote}</p>
        </Section>

        {!IS_STATIC_SITE && (
          <Section
            id="status"
            title="This server, right now"
            intro="Live: these checks call the backend that serves this page."
          >
            <div className="max-w-2xl">
              <StackStatus />
            </div>
          </Section>
        )}

        <Section
          id="workflow"
          title="Connected build → air-gapped deployment"
          intro="Everything that needs the internet happens on the build machine. The server only ever receives one archive."
        >
          <div className="grid gap-4 lg:grid-cols-2">
            <StepList title="On the connected build machine" steps={CONNECTED} tone="accent" />
            <StepList title="On the offline Linux server" steps={OFFLINE} tone="ok" />
          </div>
          <p className="mt-4 text-sm">
            <a href="/deploy/" className="font-semibold text-accent hover:underline">
              Read the full offline deployment guide →
            </a>
          </p>
        </Section>

        <Section
          id="workshop"
          title="The workshop"
          intro={`${CHAPTERS.length} modules, about ${Math.round(TOTAL_MINUTES / 60)} hours. Every command says what it does, why, and what you should see. Every module ends with exercises and troubleshooting.`}
        >
          <div className="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
            <div className="space-y-6">
              {(Object.keys(PARTS) as Part[]).map((part) => (
                <div key={part}>
                  <p className="font-semibold">{PARTS[part].title}</p>
                  <ol className="mt-2 divide-y divide-line rounded-xl border border-line bg-paper">
                    {CHAPTERS.filter((c) => c.part === part).map((chapter) => (
                      <li key={chapter.slug}>
                        <a
                          href={`/workshop/${chapter.slug}/`}
                          className="flex items-center gap-3 px-4 py-2.5 hover:bg-paper-2"
                        >
                          <span className="font-mono text-xs text-faint">{chapter.number}</span>
                          <span className="min-w-0 flex-1 text-sm font-medium">{chapter.title}</span>
                          <span className="font-mono text-xs text-faint">{chapter.minutes}m</span>
                        </a>
                      </li>
                    ))}
                  </ol>
                </div>
              ))}
            </div>
            <div className="card h-fit p-5">
              <p className="font-semibold">You will be able to</p>
              <ul className="mt-3 space-y-2 text-sm">
                {OUTCOMES.map((outcome) => (
                  <li key={outcome} className="flex gap-2">
                    <span aria-hidden="true" className="text-ok">
                      ✓
                    </span>
                    {outcome}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </Section>

        <Section id="quick-start" title="Quick start" intro="Prerequisites, measured on a real run of this stack.">
          <div className="grid gap-6 lg:grid-cols-[1fr_1.2fr]">
            <div className="table-wrap h-fit">
              <table>
                <tbody>
                  {MEASURED.requirements.map(([what, value]) => (
                    <tr key={what}>
                      <th scope="row" className="w-36">
                        {what}
                      </th>
                      <td>{value}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="space-y-3">
              <CodeBlock
                lang="bash"
                title="Run it locally (connected machine)"
                code={`git clone ${REPO_URL}.git\ncd local-ai-demo\ncp .env.example .env            # then set POSTGRES_PASSWORD\n./scripts/pull-model.sh         # downloads ${VERSIONS.model} (${MEASURED.modelSize})\ndocker compose up -d --build --wait\n./scripts/smoke-test.sh         # health, a note, a real answer`}
              />
              <CodeBlock
                lang="bash"
                title="Ship it to an offline server"
                code={`./scripts/build-bundle.sh                        # on the connected machine\n# carry dist/local-ai-demo-bundle-*.tar and its .sha256 to the server, then:\nsha256sum -c local-ai-demo-bundle-*.tar.sha256\ntar -xf local-ai-demo-bundle-*.tar && cd local-ai-demo-bundle-*/\n./scripts/offline-install.sh`}
              />
              <p className="text-sm text-muted">
                Then open <code className="font-mono">http://localhost:3000</code>. Windows and macOS work for the core
                workshop through Docker Desktop; the offline deployment targets Linux.
              </p>
            </div>
          </div>
        </Section>

        <Section id="links" title="Where to go next">
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <a href={REPO_URL} target="_blank" rel="noreferrer" className="card p-4 hover:border-accent">
              <p className="font-semibold">Source code</p>
              <p className="text-sm text-muted">github.com/jars-demo/local-ai-demo</p>
            </a>
            <a href="/workshop/01-architecture/" className="card p-4 hover:border-accent">
              <p className="font-semibold">Module 01</p>
              <p className="text-sm text-muted">Architecture and prerequisites</p>
            </a>
            <a href="/deploy/" className="card p-4 hover:border-accent">
              <p className="font-semibold">Offline deployment</p>
              <p className="text-sm text-muted">The operator guide that ships in the bundle</p>
            </a>
            <a
              href="https://ollama.com/library/qwen3"
              target="_blank"
              rel="noreferrer"
              className="card p-4 hover:border-accent"
            >
              <p className="font-semibold">The model</p>
              <p className="text-sm text-muted">Qwen3 0.6B by the Qwen team, Apache 2.0</p>
            </a>
          </div>
          <p className="mt-6 text-xs text-faint">
            An educational project. A 0.6B model is small: it answers simple questions about short notes well and can be
            wrong. It is not a production platform and makes no availability or accuracy guarantees.
          </p>
        </Section>
      </div>
    </>
  )
}
