// Numbers measured on a real run of this stack. Nothing here is estimated. When you change an
// image, the model or a version, re-measure (commands in docs/measurements.md) and update this file,
// the README and docs/measurements.md together.
//
// Machine: Windows 11 laptop, Docker Desktop 28.2.2 (WSL 2, linux/amd64, overlay2), 4 CPUs and 7.8 GiB
// given to Docker. Measured 2026-10-13. A dedicated Linux server will differ, mostly in model load time.

export const MEASURED = {
  modelSize: '523 MB',
  images: [
    {
      service: 'web',
      image: 'local-ai-demo-web',
      size: '62.7 MB',
      role: 'nginx (unprivileged): the static site, /api reverse proxy',
      reach: 'your browser, port 3000',
    },
    {
      service: 'backend',
      image: 'local-ai-demo-backend',
      size: '158 MB',
      role: 'FastAPI: notes, retrieval, prompts, readiness',
      reach: 'web only (private network)',
    },
    {
      service: 'ollama',
      image: 'local-ai-demo-ollama',
      size: '142 MB',
      role: 'Ollama 0.40.3, CPU-only build of the official image (5.57 GB)',
      reach: 'backend only (private network)',
    },
    {
      service: 'postgres',
      image: 'postgres:18.6-alpine3.24',
      size: '304 MB',
      role: 'PostgreSQL: notes and the full-text index',
      reach: 'backend only (private network)',
    },
  ],
  imagesNote:
    'Sizes as reported by `docker images` (unpacked). The model (qwen3:0.6b, 523 MB) is not in any image: it lives in the ollama-models volume.',
  requirements: [
    [
      'Operating system',
      'Linux x86_64. Tested in Docker Desktop (WSL 2) and an offline Docker-in-Docker simulation; not yet on bare metal. Docker Desktop on Windows or macOS works for the core workshop.',
    ],
    ['Docker', 'Engine 24+ with the Compose v2 plugin 2.24+ (tested: 28.2.2 and 28.5.2)'],
    ['CPU', '2 cores minimum, 4+ recommended. AVX2 helps; no GPU needed.'],
    [
      'Memory',
      '4 GB minimum, 8 GB recommended. Measured: about 1.2 GB for the whole stack with the model loaded (Ollama 1.11 GiB).',
    ],
    [
      'Disk',
      'About 1.2 GB for loaded images and the model, plus the 774 MB bundle while installing. 4 GB free recommended.',
    ],
    ['Network', 'Only on the build machine. The server needs none.'],
  ] as [string, string][],
} as const

// A real /api/ask response from this stack, recorded through the web container. Kept static so the
// public site never shows a live answer it did not produce.
export const RECORDED_ANSWER = {
  where: 'a laptop CPU (Docker Desktop)',
  question: 'Where is the backup NAS?',
  sources: '#1 Server rack layout (rank 0.8)',
  model: 'qwen3:0.6b',
  answer: 'The backup NAS is in rack 4, slot 12. [#1]',
  timing: 'retrieval 2 ms · inference 488 ms (model already loaded) · 122 tokens in · 18 tokens out',
}
