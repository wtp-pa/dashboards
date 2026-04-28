import { useEffect, useState } from "react";
import { formatCurrencyFull } from "../lib/format";
import { accruedDeficit, fiscalYearBounds } from "../lib/fiscal";

interface Props {
  fiscalYear: string;
  annualDeficitUSD: number;
  compact?: boolean;
}

export default function DeficitClock({
  fiscalYear,
  annualDeficitUSD,
  compact = false,
}: Props) {
  const { start, end } = fiscalYearBounds(fiscalYear);
  const [accrued, setAccrued] = useState(() =>
    accruedDeficit(annualDeficitUSD, start, end),
  );

  useEffect(() => {
    const reducedMotion =
      typeof window !== "undefined" &&
      window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

    if (reducedMotion) return;

    const id = setInterval(() => {
      setAccrued(accruedDeficit(annualDeficitUSD, start, end));
    }, 100);
    return () => clearInterval(id);
  }, [annualDeficitUSD, start.getTime(), end.getTime()]);

  const annualB = (annualDeficitUSD / 1e9).toFixed(1);

  const numberClasses = compact
    ? "font-mono text-3xl font-bold text-wtp-red tabular-nums tracking-tight md:text-4xl"
    : "font-mono text-4xl font-bold text-wtp-red tabular-nums tracking-tight md:text-7xl";

  return (
    <div className="text-center">
      <div className={numberClasses}>{formatCurrencyFull(accrued)}</div>
      {!compact && (
        <>
          <div className="mt-4 text-xs uppercase tracking-[0.2em] text-wtp-cream/60">
            FY {fiscalYear} structural deficit accrued so far
          </div>
          <div className="mt-1 text-xs text-wtp-cream/40">
            of ${annualB}B projected annual total · Source: PA Independent Fiscal Office
          </div>
        </>
      )}
    </div>
  );
}
