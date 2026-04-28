import { useEffect, useState } from "react";
import { daysUntil } from "../lib/fiscal";
import { formatNumber } from "../lib/format";

interface Props {
  depletionDateISO: string;
  rainyDayBalanceUSD: number;
}

export default function RainyDayCountdown({
  depletionDateISO,
  rainyDayBalanceUSD,
}: Props) {
  const [days, setDays] = useState(() => daysUntil(depletionDateISO));

  useEffect(() => {
    const id = setInterval(() => {
      setDays(daysUntil(depletionDateISO));
    }, 60_000);
    return () => clearInterval(id);
  }, [depletionDateISO]);

  const balanceB = (rainyDayBalanceUSD / 1e9).toFixed(1);

  return (
    <div className="rounded-lg border border-white/10 bg-surface p-8 text-center">
      <div className="text-xs uppercase tracking-[0.2em] text-wtp-sky">
        Rainy Day Fund
      </div>
      <div className="mt-3 font-mono text-5xl font-bold text-wtp-red tabular-nums">
        {formatNumber(days)}
      </div>
      <div className="mt-2 text-sm text-white/70">
        days until projected depletion
      </div>
      <div className="mt-6 text-xs text-white/40">
        Currently ${balanceB}B · Projected drain by FY 2026-27
      </div>
      <div className="mt-1 text-xs text-white/40">
        Source: PA Treasury / IFO projections
      </div>
    </div>
  );
}
