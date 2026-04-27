export function formatCurrencyFull(usd: number): string {
  return "$" + Math.floor(usd).toLocaleString("en-US");
}

export function formatCurrencyShort(usd: number, decimals = 1): string {
  if (usd >= 1e9) return `$${(usd / 1e9).toFixed(decimals)}B`;
  if (usd >= 1e6) return `$${(usd / 1e6).toFixed(decimals)}M`;
  if (usd >= 1e3) return `$${(usd / 1e3).toFixed(decimals)}K`;
  return `$${usd.toFixed(0)}`;
}

export function formatNumber(n: number): string {
  return Math.floor(n).toLocaleString("en-US");
}
