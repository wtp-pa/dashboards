// @ts-check
import { defineConfig } from 'astro/config';

import tailwindcss from '@tailwindcss/vite';

import react from '@astrojs/react';

// https://astro.build/config
export default defineConfig({
  // Production URL for absolute links (OG/Twitter images, sitemaps, RSS).
  // Set to the Vercel demo URL for now; change when migrating to a custom domain.
  site: 'https://wtp-budget-watch.vercel.app',

  vite: {
    plugins: [tailwindcss()]
  },

  integrations: [react()]
});