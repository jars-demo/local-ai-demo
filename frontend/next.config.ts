import type { NextConfig } from 'next'

// A fully static site (out/), served by nginx in Docker or by any static host. No Node.js server
// runs in production: the assistant page calls /api, which nginx proxies to the backend.
//
// Builds on Vercel (VERCEL=1) are always the public static flavour, even if the build command
// is not `npm run build:static`: a static host has no backend, so it must never call one.
const siteMode = process.env.NEXT_PUBLIC_SITE_MODE ?? (process.env.VERCEL ? 'static' : '')

const config: NextConfig = {
  output: 'export',
  trailingSlash: true,
  images: { unoptimized: true },
  poweredByHeader: false,
  env: { NEXT_PUBLIC_SITE_MODE: siteMode },
}

export default config
