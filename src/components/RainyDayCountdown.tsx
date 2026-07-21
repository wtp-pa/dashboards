interface Props {
  rainyDayBalanceUSD: number;
}

export default function RainyDayCountdown({ rainyDayBalanceUSD }: Props) {
  const balanceB = (rainyDayBalanceUSD / 1e9).toFixed(1);

  return (
    <div className="rounded-lg border border-white/10 bg-surface p-8 text-center">
      <div className="text-xs uppercase tracking-[0.2em] text-wtp-sky">
        Rainy Day Fund
      </div>
      <div className="mt-3 font-mono text-4xl font-bold text-wtp-gold tabular-nums">
        ${balanceB}B
      </div>
      <div className="mt-2 text-sm text-wtp-cream/70">
        left untouched in the FY 2026-27 budget
      </div>
      <div className="mt-6 text-xs text-wtp-cream/40">
        Gov. Shapiro proposed drawing it down by $4.6B; the enacted budget didn't.
      </div>
      <div className="mt-1 text-xs text-wtp-cream/40">
        Source: PA Treasury / IFO projections
      </div>
    </div>
  );
}
