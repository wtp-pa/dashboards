// @ts-check
import { defineConfig } from 'astro/config';

import tailwindcss from '@tailwindcss/vite';

import react from '@astrojs/react';

// https://astro.build/config
export default defineConfig({
  // Production URL for absolute links (OG/Twitter images, sitemaps, RSS).
  // Hosted on GitHub Pages with custom domain.
  site: 'https://dashboards.wtpppa.org',

  vite: {
    plugins: [tailwindcss()]
  },

  integrations: [react()],

  // Quiz moved from /quiz to /vote2026 before launch; keep stray links working.
  redirects: {
    '/quiz': '/vote2026',
    '/quiz/widget': '/vote2026/widget',
    '/quiz/about': '/vote2026/about',
  }
});