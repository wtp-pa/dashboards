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

  integrations: [react()]
});