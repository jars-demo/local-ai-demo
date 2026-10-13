import type { MetadataRoute } from 'next'

import { CHAPTERS } from '@/lib/chapters'
import { NAV, SITE_URL } from '@/lib/site'

export const dynamic = 'force-static'

export default function sitemap(): MetadataRoute.Sitemap {
  const pages = NAV.map((item) => item.href)
  const chapters = CHAPTERS.map((chapter) => `/workshop/${chapter.slug}/`)
  return [...pages, ...chapters].map((path) => ({ url: `${SITE_URL}${path}` }))
}
