import { useMemo, useState } from "react";
import { formatCurrencyShort, formatNumber } from "../lib/format";

interface County {
  fips: string;
  name: string;
  totalObligationsUSD: number;
  population: number;
  perCapitaUSD: number;
}

interface Props {
  fiscalYear: string;
  totalObligationsUSD: number;
  counties: County[];
  defaultCounty?: string;
}

export default function CountyFederalImpact({
  fiscalYear,
  totalObligationsUSD,
  counties,
  defaultCounty = "Allegheny County",
}: Props) {
  const [selectedName, setSelectedName] = useState(defaultCounty);

  const selected = useMemo(
    () => counties.find((c) => c.name === selectedName) ?? counties[0],
    [selectedName, counties],
  );

  const totalPopulation = useMemo(
    () => counties.reduce((sum, c) => sum + c.population, 0),
    [counties],
  );
  const statewidePerCapita = totalObligationsUSD / totalPopulation;
  const vsStateAvg = selected.perCapitaUSD / statewidePerCapita;
  const vsStateLabel =
    vsStateAvg >= 1
      ? `${vsStateAvg.toFixed(2)}× the state average`
      : `${(1 / vsStateAvg).toFixed(2)}× below the state average`;

  return (
    <div className="rounded-lg border border-white/10 bg-surface p-6 md:p-8">
      <div className="text-xs uppercase tracking-[0.2em] text-wtp-sky">
        Federal money flowing to your county
      </div>
      <h3 className="mt-2 text-2xl font-bold md:text-3xl">
        How exposed is your county?
      </h3>
      <p className="mt-3 max-w-2xl text-sm leading-relaxed text-wtp-cream/70">
        Federal dollars obligated to recipients located in each PA county for{" "}
        {fiscalYear}. This is the money at risk if federal cuts hit — and PA's
        General Fund deficit limits how much the state can backfill.
      </p>

      <div className="mt-6">
        <label
          htmlFor="county-select"
          className="block text-sm text-wtp-cream/70"
        >
          Pick your county
        </label>
        <select
          id="county-select"
          value={selectedName}
          onChange={(e) => setSelectedName(e.target.value)}
          className="mt-2 w-full rounded-md border border-white/10 bg-page px-4 py-3 text-base font-semibold text-white focus:border-wtp-sky focus:outline-none md:max-w-sm"
        >
          {counties.map((c) => (
            <option key={c.fips} value={c.name}>
              {c.name}
            </option>
          ))}
        </select>
      </div>

      <div className="mt-8 grid gap-4 sm:grid-cols-2">
        <div className="rounded-md border border-white/10 bg-page p-5">
          <div className="text-xs uppercase tracking-[0.18em] text-wtp-cream/60">
            Total federal obligations
          </div>
          <div className="mt-2 font-mono text-3xl font-bold text-white md:text-4xl">
            {formatCurrencyShort(selected.totalObligationsUSD)}
          </div>
          <div className="mt-2 text-xs text-wtp-cream/50">
            in {selected.name}, {fiscalYear}
          </div>
        </div>
        <div className="rounded-md border border-white/10 bg-page p-5">
          <div className="text-xs uppercase tracking-[0.18em] text-wtp-cream/60">
            Per resident
          </div>
          <div className="mt-2 font-mono text-3xl font-bold text-wtp-sky md:text-4xl">
            ${formatNumber(selected.perCapitaUSD)}
          </div>
          <div className="mt-2 text-xs text-wtp-cream/50">{vsStateLabel}</div>
        </div>
      </div>

      <p className="mt-6 text-xs leading-relaxed text-wtp-cream/50">
        Includes federal contracts, grants, direct payments, loans, and
        insurance — not just "aid." Large research grants and federal
        contractors inflate metro-county totals.{" "}
        <a
          href="/budget/about#federal-by-county"
          className="text-wtp-sky no-underline hover:underline"
        >
          See methodology →
        </a>
      </p>
      <p className="mt-2 text-xs text-wtp-cream/40">Source: USAspending.gov</p>
    </div>
  );
}
