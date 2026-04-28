import { useState } from "react";
import { formatNumber } from "../lib/format";

interface Props {
  baseFamilyShareUSD: number;
  totalDeficitUSD: number;
  totalHouseholds: number;
}

const HOUSEHOLD_OPTIONS = [1, 2, 3, 4, 5, 6] as const;
const YEAR_OPTIONS = [1, 5, 10, 20] as const;

// IFO projections anchor the deficit growth curve.
// Beyond FY 2029-30 we extrapolate at the FY 26-27 → 29-30 slope (~$0.5B/year).
function projectedAnnualDeficitUSD(year: number): number {
  const Y1 = 3.9e9;   // FY 2025-26
  const Y2 = 6.7e9;   // FY 2026-27
  const Y5 = 8.4e9;   // FY 2029-30
  if (year <= 1) return Y1;
  if (year <= 2) return Y2;
  if (year <= 5) {
    const t = (year - 2) / 3;
    return Y2 + t * (Y5 - Y2);
  }
  return Y5 + (year - 5) * 0.5e9;
}

function cumulativeFamilyShare(years: number, baseShareYear1: number): number {
  let total = 0;
  const baseDeficit = 3.9e9;
  for (let y = 1; y <= years; y++) {
    total += baseShareYear1 * (projectedAnnualDeficitUSD(y) / baseDeficit);
  }
  return total;
}

export default function PersonalImpactCalculator({
  baseFamilyShareUSD,
  totalDeficitUSD,
  totalHouseholds,
}: Props) {
  const [householdSize, setHouseholdSize] = useState(4);
  const [years, setYears] = useState(1);

  const perPerson = baseFamilyShareUSD / 4;
  const baseShareForHousehold = perPerson * householdSize;
  const yourShare = cumulativeFamilyShare(years, baseShareForHousehold);
  const avgPerHousehold = totalDeficitUSD / totalHouseholds;

  return (
    <div className="rounded-lg border border-white/10 bg-surface p-8">
      <div className="text-xs uppercase tracking-[0.2em] text-wtp-sky">
        Personal Impact
      </div>
      <h3 className="mt-2 text-2xl font-bold">Your share of PA's deficit</h3>

      <div className="mt-6">
        <div className="text-sm text-wtp-cream/70">How many people in your household?</div>
        <div className="mt-3 flex flex-wrap gap-2">
          {HOUSEHOLD_OPTIONS.map((n) => (
            <button
              key={n}
              type="button"
              onClick={() => setHouseholdSize(n)}
              className={`min-w-[3.5rem] flex-1 rounded-md border px-4 py-3 text-lg font-semibold transition ${
                householdSize === n
                  ? "border-wtp-sky bg-wtp-sky/10 text-wtp-sky"
                  : "border-white/10 text-wtp-cream/70 hover:border-white/30 hover:text-white"
              }`}
            >
              {n === 6 ? "6+" : n}
            </button>
          ))}
        </div>
      </div>

      <div className="mt-6">
        <div className="text-sm text-wtp-cream/70">Time horizon</div>
        <div className="mt-3 flex flex-wrap gap-2">
          {YEAR_OPTIONS.map((y) => (
            <button
              key={y}
              type="button"
              onClick={() => setYears(y)}
              className={`flex-1 rounded-md border px-4 py-3 text-base font-semibold transition ${
                years === y
                  ? "border-wtp-sky bg-wtp-sky/10 text-wtp-sky"
                  : "border-white/10 text-wtp-cream/70 hover:border-white/30 hover:text-white"
              }`}
            >
              {y === 1 ? "1 yr" : `${y} yrs`}
            </button>
          ))}
        </div>
      </div>

      <div className="mt-8 rounded-md bg-page/60 p-6 text-center">
        <div className="text-xs uppercase tracking-[0.2em] text-wtp-cream/50">
          Your household's cumulative share
        </div>
        <div className="mt-3 font-mono text-4xl font-bold text-wtp-red md:text-5xl">
          ${formatNumber(yourShare)}
        </div>
        <div className="mt-3 text-xs text-wtp-cream/50">
          {years === 1
            ? "This year, based on IFO's $1,500-per-family-of-4 figure scaled by household size."
            : `Cumulative over ${years} years using IFO projections ($3.9B today → $6.7B FY 26-27 → $8.4B FY 29-30, then extrapolated).`}
        </div>
      </div>

      <div className="mt-4 text-center text-xs text-wtp-cream/40">
        Average across all PA households (this year): ${formatNumber(avgPerHousehold)}
      </div>
    </div>
  );
}
