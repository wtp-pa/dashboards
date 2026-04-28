#!/usr/bin/env node
/**
 * Generate the social-share OG image for the budget dashboard.
 * Pulls the current deficit from data/projections.json so the
 * image stays in sync with what the dashboard shows.
 *
 * Run: `node scripts/generate-og.mjs`
 *
 * Output: public/og-image.png  (1200 × 630)
 */

import satori from "satori";
import { Resvg } from "@resvg/resvg-js";
import { readFile, writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const repoRoot = resolve(__dirname, "..");

async function main() {
  const projections = JSON.parse(
    await readFile(resolve(repoRoot, "data/projections.json"), "utf-8"),
  );
  const currentFY = projections.projections.find((p) => p.fiscalYear === "2025-26");
  const annualB = (currentFY.structuralDeficitUSD / 1e9).toFixed(1);

  // Fonts committed in scripts/fonts/ to keep the script offline-friendly.
  const [boldFont, regularFont] = await Promise.all([
    readFile(resolve(__dirname, "fonts/Poppins-Bold.ttf")),
    readFile(resolve(__dirname, "fonts/Poppins-Regular.ttf")),
  ]);

  const tree = {
    type: "div",
    props: {
      style: {
        display: "flex",
        flexDirection: "column",
        width: "100%",
        height: "100%",
        backgroundColor: "#08091F",
        backgroundImage: "linear-gradient(135deg, #08091F 0%, #15184E 100%)",
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
              color: "#7EC7DA",
              letterSpacing: 4,
              textTransform: "uppercase",
              fontWeight: 700,
            },
            children: "WTP-PA · Pennsylvania Budget Watch",
          },
        },
        {
          type: "div",
          props: {
            style: { display: "flex", flex: 1 },
            children: " ",
          },
        },
        {
          type: "div",
          props: {
            style: {
              display: "flex",
              fontSize: 240,
              fontWeight: 700,
              color: "#C8262C",
              letterSpacing: -8,
              lineHeight: 1,
            },
            children: `$${annualB}B`,
          },
        },
        {
          type: "div",
          props: {
            style: {
              display: "flex",
              fontSize: 44,
              fontWeight: 700,
              color: "white",
              marginTop: 14,
              lineHeight: 1.1,
            },
            children: "Pennsylvania's structural deficit",
          },
        },
        {
          type: "div",
          props: {
            style: {
              display: "flex",
              fontSize: 22,
              color: "#F5F2E8",
              opacity: 0.7,
              marginTop: 16,
              fontWeight: 400,
            },
            children: "FY 2025-26 · Source: PA IFO · dashboards.wtpppa.org",
          },
        },
      ],
    },
  };

  const svg = await satori(tree, {
    width: 1200,
    height: 630,
    fonts: [
      { name: "Poppins", data: boldFont, weight: 700, style: "normal" },
      { name: "Poppins", data: regularFont, weight: 400, style: "normal" },
    ],
  });

  const png = new Resvg(svg).render().asPng();
  const outPath = resolve(repoRoot, "public/og-image.png");
  await writeFile(outPath, png);
  console.log(`✓ OG image generated (${png.length} bytes) → public/og-image.png`);
  console.log(`  Deficit: $${annualB}B (FY 2025-26)`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
