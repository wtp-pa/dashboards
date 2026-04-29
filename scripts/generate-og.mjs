#!/usr/bin/env node
/**
 * Generate social-share OG images (1200 × 630) for each dashboard.
 * Each card pulls its own headline number from the relevant data file
 * so the share previews stay in sync with what the dashboard shows.
 *
 * Run: `node scripts/generate-og.mjs`
 *
 * Outputs:
 *   public/og-image.png         — Budget Watch ($X.XB structural deficit)
 *   public/og-legislation.png   — Legislation Watch (N bills monitored)
 */

import satori from "satori";
import { Resvg } from "@resvg/resvg-js";
import { readFile, writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const repoRoot = resolve(__dirname, "..");

const COLORS = {
  page: "#08091F",
  navy: "#15184E",
  sky: "#7EC7DA",
  cream: "#F5F2E8",
  red: "#C8262C",
  white: "#ffffff",
};

function card({ kicker, headlineNumber, headlineNumberColor, headlineLabel, footer }) {
  return {
    type: "div",
    props: {
      style: {
        display: "flex",
        flexDirection: "column",
        width: "100%",
        height: "100%",
        backgroundColor: COLORS.page,
        backgroundImage: `linear-gradient(135deg, ${COLORS.page} 0%, ${COLORS.navy} 100%)`,
        color: "white",
        padding: "70px 80px",
        fontFamily: "Poppins",
        position: "relative",
      },
      children: [
        {
          type: "div",
          props: {
            style: {
              display: "flex",
              fontSize: 26,
              color: COLORS.sky,
              letterSpacing: 4,
              textTransform: "uppercase",
              fontWeight: 700,
            },
            children: kicker,
          },
        },
        {
          type: "div",
          props: { style: { display: "flex", flex: 1 }, children: " " },
        },
        {
          type: "div",
          props: {
            style: {
              display: "flex",
              fontSize: 240,
              fontWeight: 700,
              color: headlineNumberColor,
              letterSpacing: -8,
              lineHeight: 1,
            },
            children: headlineNumber,
          },
        },
        {
          type: "div",
          props: {
            style: {
              display: "flex",
              fontSize: 44,
              fontWeight: 700,
              color: COLORS.white,
              marginTop: 14,
              lineHeight: 1.1,
            },
            children: headlineLabel,
          },
        },
        {
          type: "div",
          props: {
            style: {
              display: "flex",
              fontSize: 22,
              color: COLORS.cream,
              opacity: 0.7,
              marginTop: 16,
              fontWeight: 400,
            },
            children: footer,
          },
        },
      ],
    },
  };
}

async function renderCard(tree, fonts, outRelPath) {
  const svg = await satori(tree, { width: 1200, height: 630, fonts });
  const png = new Resvg(svg).render().asPng();
  const outPath = resolve(repoRoot, outRelPath);
  await writeFile(outPath, png);
  console.log(`✓ ${outRelPath} (${png.length} bytes)`);
}

async function main() {
  const [boldFont, regularFont] = await Promise.all([
    readFile(resolve(__dirname, "fonts/Poppins-Bold.ttf")),
    readFile(resolve(__dirname, "fonts/Poppins-Regular.ttf")),
  ]);
  const fonts = [
    { name: "Poppins", data: boldFont, weight: 700, style: "normal" },
    { name: "Poppins", data: regularFont, weight: 400, style: "normal" },
  ];

  // Budget Watch
  const projections = JSON.parse(
    await readFile(resolve(repoRoot, "data/projections.json"), "utf-8"),
  );
  const currentFY = projections.projections.find((p) => p.fiscalYear === "2025-26");
  const annualB = (currentFY.structuralDeficitUSD / 1e9).toFixed(1);

  await renderCard(
    card({
      kicker: "WTPPPA · Pennsylvania Budget Watch",
      headlineNumber: `$${annualB}B`,
      headlineNumberColor: COLORS.red,
      headlineLabel: "Pennsylvania's structural deficit",
      footer: "FY 2025-26 · Source: PA IFO · dashboards.wtpppa.org",
    }),
    fonts,
    "public/og-image.png",
  );

  // Legislation Watch
  const bills = JSON.parse(
    await readFile(resolve(repoRoot, "data/legislation/bills.json"), "utf-8"),
  );
  const manualReview = JSON.parse(
    await readFile(resolve(repoRoot, "data/legislation/manual_review.json"), "utf-8"),
  );
  const reviewIds = new Set(Object.keys(manualReview.reviews ?? {}));
  const monitoredCount = bills.bills.filter(
    (b) => (b.matches?.length ?? 0) > 0 || reviewIds.has(b.id),
  ).length;

  await renderCard(
    card({
      kicker: "WTPPPA · Pennsylvania Legislation Watch",
      headlineNumber: String(monitoredCount),
      headlineNumberColor: COLORS.sky,
      headlineLabel: "PA bills scored against our platform",
      footer: "Source: OpenStates · dashboards.wtpppa.org/legislation",
    }),
    fonts,
    "public/og-legislation.png",
  );

  // Elected Officials Watch
  const officials = JSON.parse(
    await readFile(resolve(repoRoot, "data/elected-officials/officials.json"), "utf-8"),
  );
  const totalOfficials = officials.officials.length;

  await renderCard(
    card({
      kicker: "WTPPPA · Pennsylvania Elected Officials Watch",
      headlineNumber: String(totalOfficials),
      headlineNumberColor: COLORS.sky,
      headlineLabel: "PA legislators tracked",
      footer: "Find your reps · See what they sponsor · dashboards.wtpppa.org/elected-officials",
    }),
    fonts,
    "public/og-elected-officials.png",
  );

  console.log(`  Deficit: $${annualB}B · Bills monitored: ${monitoredCount} · Officials: ${totalOfficials}`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
