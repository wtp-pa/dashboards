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
    shortName: "WTPPPA",
    // Per officer guidance (Nathan, 2026-04-29): the abbreviation is WTPPPA
    // — three p's, no dash, no space. When rendered in 2 colors, "WTPP" goes
    // in one color and "PA" in the contrast color.
    shortNameSplit: { primary: "WTPP", accent: "PA" },
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
    // Matches WTPPPA Squarespace site palette + Poppins font.
    // Source: Site Styles → Colors / Fonts on wtpppa.org
    colors: {
      navy: "#15184E",
      sky: "#7EC7DA",
      indigo: "#2E3279",
      cream: "#F5F2E8",
      gold: "#D4B962",
      red: "#C8262C",
      white: "#FFFFFF",
      page: "#08091F",
      surface: "#1B1F5E",
    },
    fontFamily: '"Poppins", ui-sans-serif, system-ui, -apple-system, sans-serif',
    logoPath: "/wtp-logo.png",
    ogImagePath: "/og-image.png",
  },
  project: {
    // The currently-built project. Used by /budget pages and the embed widget.
    name: "PA Budget Watch",
    repoUrl: "https://github.com/wtp-pa/dashboards",
    license: "MIT",
    dashboardUrl: "https://dashboards.wtpppa.org/budget",
  },
  portfolio: {
    // The umbrella that holds all WTPPPA dashboards. Used by the / landing page.
    name: "WTPPPA Dashboards",
    tagline: "Tools for Pennsylvania accountability",
    baseUrl: "https://dashboards.wtpppa.org",
    projects: [
      {
        name: "PA Budget Watch",
        slug: "budget",
        tagline: "Tracking Pennsylvania's $3.9B structural deficit in real time",
        status: "live" as const,
      },
      {
        name: "PA Legislation Watch",
        slug: "legislation",
        tagline: "Scoring PA bills against the WTPPPA platform",
        status: "live" as const,
      },
      {
        name: "Elected Officials Watch",
        slug: "elected-officials",
        tagline: "How your representatives vote and how they align with the WTPPPA platform",
        status: "coming-soon" as const,
      },
      {
        name: "Local Impact",
        slug: "local",
        tagline: "How state policy affects your county and community",
        status: "coming-soon" as const,
      },
    ],
  },
} as const;

export type Config = typeof config;
export type Project = (typeof config.portfolio.projects)[number];
