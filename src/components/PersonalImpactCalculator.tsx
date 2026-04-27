import { useState } from "react";
import { formatNumber } from "../lib/format";

interface Props {
  baseFamilyShareUSD: number;
  totalDeficitUSD: number;
  totalHouseholds: number;
}

const HOUSEHOLD_OPTIONS = [1, 2, 3, 4, 5, 6] as const;

export default function PersonalImpactCalculator({
  baseFamilyShareUSD,
  totalDeficitUSD,
  totalHouseholds,
}: Props) {
  const [householdSize, setHouseholdSize] = useState(4);

  const perPerson = baseFamilyShareUSD / 4;
  const yourShare = perPerson * householdSize;
  const avgPerHousehold = totalDeficitUSD / totalHouseholds;

  return (
    <div className="rounded-lg border border-white/10 bg-surface p-8">
      <div className="text-xs uppercase tracking-[0.2em] text-wtp-gold">
        Personal Impact
      </div>
      <h3 className="mt-2 text-2xl font-bold">Your share of PA's deficit</h3>

      <div className="mt-6">
        <div className="text-sm text-white/70">How many people in your household?</div>
        <div className="mt-3 flex flex-wrap gap-2">
          {HOUSEHOLD_OPTIONS.map((n) => (
            <button
              key={n}
              type="button"
              onClick={() => setHouseholdSize(n)}
              className={`min-w-[3.5rem] flex-1 rounded-md border px-4 py-3 text-lg font-semibold transition ${
                householdSize === n
                  ? "border-wtp-gold bg-wtp-gold/10 text-wtp-gold"
                  : "border-white/10 text-white/70 hover:border-white/30 hover:text-white"
              }`}
            >
              {n === 6 ? "6+" : n}
            </button>
          ))}
        </div>
      </div>

      <div className="mt-8 rounded-md bg-page/60 p-6 text-center">
        <div className="text-xs uppercase tracking-[0.2em] text-white/50">
          Your household's share
        </div>
        <div className="mt-3 font-mono text-4xl font-bold text-wtp-red md:text-5xl">
          ${formatNumber(yourShare)}
        </div>
        <div className="mt-3 text-xs text-white/50">
          Based on IFO's $1,500-per-family-of-4 figure, scaled by household size
        </div>
      </div>

      <div className="mt-4 text-center text-xs text-white/40">
        Average across all PA households: ${formatNumber(avgPerHousehold)}
      </div>
    </div>
  );
}
