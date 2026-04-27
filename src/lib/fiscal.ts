// PA fiscal year runs July 1 → June 30.
// Label format: "2025-26" means July 1 2025 through June 30 2026.

export function fiscalYearBounds(label: string): { start: Date; end: Date } {
  const [startYearStr] = label.split("-");
  const startYear = parseInt(startYearStr, 10);
  return {
    start: new Date(startYear, 6, 1, 0, 0, 0),
    end: new Date(startYear + 1, 5, 30, 23, 59, 59),
  };
}

export function accruedDeficit(
  annualDeficitUSD: number,
  fyStart: Date,
  fyEnd: Date,
  now: Date = new Date(),
): number {
  const totalMs = fyEnd.getTime() - fyStart.getTime();
  const elapsedMs = now.getTime() - fyStart.getTime();
  const fraction = Math.min(Math.max(elapsedMs / totalMs, 0), 1);
  return annualDeficitUSD * fraction;
}

export function daysUntil(targetISO: string, now: Date = new Date()): number {
  const target = new Date(targetISO);
  const ms = target.getTime() - now.getTime();
  return Math.max(0, Math.floor(ms / (1000 * 60 * 60 * 24)));
}
