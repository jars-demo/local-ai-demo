import type { NextConfig } from 'next'

// A fully static site (out/), served by nginx in Docker or by any static host. No Node.js server
// runs in production: the assistant page calls /api, which nginx proxies to the backend.
const config: NextConfig = {
  output: 'export',
  trailingSlash: true,
  images: { unoptimized: true },
  poweredByHeader: false,
}

export default config
