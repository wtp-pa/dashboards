import { useMemo, useState } from 'react';

type Status = 'blocked' | 'active-bill' | 'proposed' | 'concept';

interface Proposal {
  id: string;
  name: string;
  description: string;
  revenueLowUSD: number;
  revenueMidUSD: number;
  revenueHighUSD: number;
  status: Status;
  statusDetail: string;
  sourceDetail: string;
}

interface Props {
  proposals: Proposal[];
  annualDeficitUSD: number;
}

function formatUSD(usd: number): string {
  if (usd >= 1e9) return `$${(usd / 1e9).toFixed(2)}B`;
  if (usd >= 1e6) return `$${Math.round(usd / 1e6)}M`;
  return `$${Math.round(usd).toLocaleString()}`;
}

const STATUS_LABEL: Record<Status, string> = {
  blocked: 'Blocked',
  'active-bill': 'Active bill',
  proposed: 'Proposed',
  concept: 'Concept',
};

const STATUS_CLASS: Record<Status, string> = {
  blocked: 'border-wtp-red/40 bg-wtp-red/10 text-wtp-red',
  'active-bill': 'border-wtp-sky/40 bg-wtp-sky/10 text-wtp-sky',
  proposed: 'border-wtp-gold/40 bg-wtp-gold/10 text-wtp-gold',
  concept: 'border-white/20 bg-white/5 text-wtp-cream/70',
};

export default function RescuePlan({ proposals, annualDeficitUSD }: Props) {
  const [enabled, setEnabled] = useState<Record<string, boolean>>({});

  const totalRevenue = useMemo(
    () => proposals.reduce((sum, p) => (enabled[p.id] ? sum + p.revenueMidUSD : sum), 0),
    [proposals, enabled],
  );

  const pctClosed = Math.min(100, (totalRevenue / annualDeficitUSD) * 100);
  const remaining = Math.max(0, annualDeficitUSD - totalRevenue);
  const enabledCount = Object.values(enabled).filter(Boolean).length;

  const barColor =
    pctClosed >= 100
      ? 'bg-wtp-sky'
      : pctClosed >= 50
        ? 'bg-wtp-gold'
        : pctClosed > 0
          ? 'bg-wtp-cream/50'
          : 'bg-white/10';

  const headlineColor =
    pctClosed >= 100 ? 'text-wtp-sky' : pctClosed >= 50 ? 'text-wtp-gold' : 'text-wtp-cream';

  const toggle = (id: string) =>
    setEnabled((prev) => ({ ...prev, [id]: !prev[id] }));

  const reset = () => setEnabled({});

  return (
    <div>
      {/* Running total panel */}
      <div className="rounded-lg border border-wtp-sky/20 bg-gradient-to-br from-wtp-navy/60 to-wtp-indigo/40 p-6 md:p-8">
        <div className="flex flex-wrap items-baseline justify-between gap-3">
          <p className="text-xs uppercase tracking-[0.2em] text-wtp-sky">Your plan closes</p>
          <p className="text-xs text-wtp-cream/60">
            {enabledCount === 0
              ? 'Toggle proposals below'
              : `${enabledCount} of ${proposals.length} enabled`}
          </p>
        </div>
        <p className={`mt-2 font-mono text-4xl font-bold leading-tight md:text-5xl ${headlineColor}`}>
          {formatUSD(totalRevenue)}
          <span className="text-wtp-cream/40"> / {formatUSD(annualDeficitUSD)}</span>
        </p>

        {/* Progress bar */}
        <div className="mt-5 h-3 w-full overflow-hidden rounded-full bg-white/5">
          <div
            className={`h-full rounded-full transition-all duration-300 ${barColor}`}
            style={{ width: `${pctClosed}%` }}
          />
        </div>
        <div className="mt-2 flex flex-wrap justify-between gap-2 text-sm">
          <span className="text-wtp-cream/70">{pctClosed.toFixed(0)}% of the gap closed</span>
          <span className="text-wtp-cream/70">
            Remaining: <span className="font-mono text-wtp-cream">{formatUSD(remaining)}</span>
          </span>
        </div>

        {enabledCount > 0 && (
          <button
            type="button"
            onClick={reset}
            className="mt-4 text-xs uppercase tracking-wider text-wtp-sky/70 hover:text-wtp-sky"
          >
            Reset
          </button>
        )}
      </div>

      {/* Proposal list */}
      <ul className="mt-8 space-y-3">
        {proposals.map((p) => {
          const isOn = !!enabled[p.id];
          return (
            <li key={p.id}>
              <label
                className={`flex cursor-pointer flex-col gap-3 rounded-lg border p-5 transition md:flex-row md:items-start md:gap-4 ${
                  isOn
                    ? 'border-wtp-sky/40 bg-wtp-sky/5'
                    : 'border-white/10 bg-surface/50 hover:border-white/20'
                }`}
              >
                <input
                  type="checkbox"
                  checked={isOn}
                  onChange={() => toggle(p.id)}
                  className="mt-1 h-5 w-5 flex-shrink-0 cursor-pointer accent-wtp-sky"
                />
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
                    <h3 className="text-base font-bold text-white md:text-lg">{p.name}</h3>
                    <span
                      className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider ${STATUS_CLASS[p.status]}`}
                    >
                      {STATUS_LABEL[p.status]}
                    </span>
                    <span className="ml-auto font-mono text-base font-bold text-wtp-sky md:text-lg">
                      {formatUSD(p.revenueMidUSD)}
                      <span className="text-xs font-normal text-wtp-cream/60">/yr</span>
                    </span>
                  </div>
                  <p className="mt-2 text-sm leading-relaxed text-wtp-cream/80">{p.description}</p>
                  <p className="mt-2 text-xs text-wtp-cream/60">
                    Range: {formatUSD(p.revenueLowUSD)} – {formatUSD(p.revenueHighUSD)} ·{' '}
                    {p.statusDetail}
                  </p>
                  <p className="mt-1 text-xs text-wtp-cream/50">Source: {p.sourceDetail}</p>
                </div>
              </label>
            </li>
          );
        })}
      </ul>

      <p className="mt-6 text-xs leading-relaxed text-wtp-cream/50">
        All revenue figures are mid-range estimates from cited PA sources (governor's budget
        proposals, IFO analyses, Department of Revenue fiscal notes). Real revenue depends on tax
        rate, implementation, ramp-up, and economic conditions. Treat these as informative, not
        precise. Estimates refresh annually.
      </p>
    </div>
  );
}
