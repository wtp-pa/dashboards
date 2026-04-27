/**
 * Central party + brand + project config.
 * Forking for another state party? Edit this file and the JSON files in data/.
 *
 * Color values are also defined in src/styles/global.css (Tailwind theme).
 * Keep them in sync until we generate one from the other.
 */

export const config = {
  party: {
    name: "We The People Party of Pennsylvania",
    shortName: "WTP-PA",
    state: "Pennsylvania",
    stateAbbr: "PA",
    tagline: "Empowering People. Restoring Trust.",
    website: "https://www.wtpppa.org",
    socials: {
      twitter: "https://twitter.com/wethepeoplepa_",
      facebook: "https://www.facebook.com/profile.php?id=61566478845878",
    },
  },
  brand: {
    // APPROXIMATE — sampled from logo. Replace with official brand kit hex codes when available.
    colors: {
      navy: "#1B2A5E",
      gold: "#D4B962",
      red: "#C8262C",
      lightBlue: "#7FB6C0",
      white: "#FFFFFF",
      page: "#0A0E1A",
      surface: "#13182B",
    },
    logoPath: "/wtp-logo.png",
  },
  project: {
    name: "PA Budget Watch",
    repoUrl: "https://github.com/wtp-pa/wtp-budget-watch",
    license: "MIT",
  },
} as const;

export type Config = typeof config;
