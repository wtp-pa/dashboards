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
  revenueProposals: Proposal[];
  cutProposals: Proposal[];
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

function ProposalRow({
  proposal,
  on,
  onToggle,
}: {
  proposal: Proposal;
  on: boolean;
  onToggle: () => void;
}) {
  return (
    <li>
      <label
        className={`flex cursor-pointer flex-col gap-3 rounded-lg border p-4 transition md:flex-row md:items-start md:gap-4 ${
          on
            ? 'border-wtp-sky/40 bg-wtp-sky/5'
            : 'border-white/10 bg-surface/50 hover:border-white/20'
        }`}
      >
        <input
          type="checkbox"
          checked={on}
          onChange={onToggle}
          className="mt-1 h-5 w-5 flex-shrink-0 cursor-pointer accent-wtp-sky"
        />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
            <h4 className="text-base font-bold text-white">{proposal.name}</h4>
            <span
              className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider ${STATUS_CLASS[proposal.status]}`}
            >
              {STATUS_LABEL[proposal.status]}
            </span>
            <span className="ml-auto font-mono text-base font-bold text-wtp-sky">
              {formatUSD(proposal.revenueMidUSD)}
              <span className="text-xs font-normal text-wtp-cream/60">/yr</span>
            </span>
          </div>
          <p className="mt-2 text-sm leading-relaxed text-wtp-cream/80">{proposal.description}</p>
          <p className="mt-2 text-xs text-wtp-cream/60">
            Range: {formatUSD(proposal.revenueLowUSD)} – {formatUSD(proposal.revenueHighUSD)} ·{' '}
            {proposal.statusDetail}
          </p>
          <p className="mt-1 text-xs text-wtp-cream/50">Source: {proposal.sourceDetail}</p>
        </div>
      </label>
    </li>
  );
}

function LeverSection({
  label,
  proposals,
  enabled,
  setEnabled,
  defaultOpen = false,
}: {
  label: string;
  proposals: Proposal[];
  enabled: Record<string, boolean>;
  setEnabled: (next: Record<string, boolean>) => void;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  const onCount = proposals.filter((p) => enabled[p.id]).length;
  const onSum = proposals.reduce(
    (s, p) => (enabled[p.id] ? s + p.revenueMidUSD : s),
    0,
  );
  const maxSum = proposals.reduce((s, p) => s + p.revenueMidUSD, 0);

  const toggle = (id: string) => setEnabled({ ...enabled, [id]: !enabled[id] });

  return (
    <div className="rounded-lg border border-white/10 bg-surface/30">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full cursor-pointer items-center justify-between gap-3 px-5 py-4 text-left transition hover:bg-white/[0.03]"
        aria-expanded={open}
      >
        <div className="min-w-0">
          <div className="font-semibold text-white">{label}</div>
          <div className="mt-0.5 text-xs text-wtp-cream/60">
            {onCount === 0
              ? `${proposals.length} options · up to ${formatUSD(maxSum)}/yr`
              : `${onCount} of ${proposals.length} enabled · ${formatUSD(onSum)}/yr`}
          </div>
        </div>
        <span
          className="grid h-8 w-8 flex-shrink-0 place-items-center rounded-full border border-white/15 bg-white/5 text-sm font-bold text-wtp-cream/70 transition"
          style={{ transform: open ? 'rotate(180deg)' : undefined }}
          aria-hidden="true"
        >
          ▾
        </span>
      </button>
      {open && (
        <ul className="space-y-3 border-t border-white/10 px-5 pb-5 pt-4">
          {proposals.map((p) => (
            <ProposalRow
              key={p.id}
              proposal={p}
              on={!!enabled[p.id]}
              onToggle={() => toggle(p.id)}
            />
          ))}
        </ul>
      )}
    </div>
  );
}

export default function BudgetPlan({
  revenueProposals,
  cutProposals,
  annualDeficitUSD,
}: Props) {
  const [enabledRevenue, setEnabledRevenue] = useState<Record<string, boolean>>({});
  const [enabledCuts, setEnabledCuts] = useState<Record<string, boolean>>({});

  const totalRevenue = useMemo(
    () =>
      revenueProposals.reduce(
        (s, p) => (enabledRevenue[p.id] ? s + p.revenueMidUSD : s),
        0,
      ),
    [revenueProposals, enabledRevenue],
  );
  const totalCuts = useMemo(
    () =>
      cutProposals.reduce((s, p) => (enabledCuts[p.id] ? s + p.revenueMidUSD : s), 0),
    [cutProposals, enabledCuts],
  );
  const totalImpact = totalRevenue + totalCuts;

  const pctClosed = Math.min(100, (totalImpact / annualDeficitUSD) * 100);
  const remaining = Math.max(0, annualDeficitUSD - totalImpact);
  const enabledCount =
    Object.values(enabledRevenue).filter(Boolean).length +
    Object.values(enabledCuts).filter(Boolean).length;

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

  const reset = () => {
    setEnabledRevenue({});
    setEnabledCuts({});
  };

  return (
    <div>
      {/* Running total panel */}
      <div className="rounded-lg border border-wtp-sky/20 bg-gradient-to-br from-wtp-navy/60 to-wtp-indigo/40 p-6 md:p-8">
        <div className="flex flex-wrap items-baseline justify-between gap-3">
          <p className="text-xs uppercase tracking-[0.2em] text-wtp-sky">Your plan closes</p>
          <p className="text-xs text-wtp-cream/60">
            {enabledCount === 0
              ? 'Toggle options below to build a plan'
              : `${enabledCount} option${enabledCount === 1 ? '' : 's'} enabled`}
          </p>
        </div>
        <p className={`mt-2 font-mono text-4xl font-bold leading-tight md:text-5xl ${headlineColor}`}>
          {formatUSD(totalImpact)}
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
          <div className="mt-4 flex flex-wrap items-center gap-x-5 gap-y-1 text-xs text-wtp-cream/70">
            <span>
              From new revenue: <span className="font-mono text-wtp-cream">{formatUSD(totalRevenue)}</span>
            </span>
            <span>
              From spending cuts: <span className="font-mono text-wtp-cream">{formatUSD(totalCuts)}</span>
            </span>
            <button
              type="button"
              onClick={reset}
              className="ml-auto cursor-pointer text-wtp-sky/70 uppercase tracking-wider hover:text-wtp-sky"
            >
              Reset
            </button>
          </div>
        )}
      </div>

      {/* Lever sections */}
      <div className="mt-6 space-y-4">
        <LeverSection
          label="Find new revenue"
          proposals={revenueProposals}
          enabled={enabledRevenue}
          setEnabled={setEnabledRevenue}
          defaultOpen={false}
        />
        <LeverSection
          label="Cut spending"
          proposals={cutProposals}
          enabled={enabledCuts}
          setEnabled={setEnabledCuts}
          defaultOpen={false}
        />
      </div>

      <p className="mt-6 text-xs leading-relaxed text-wtp-cream/50">
        All figures are mid-range estimates from cited PA sources (governor's budget proposals, IFO
        analyses, Department of Revenue fiscal notes, Auditor General reports). Real impact
        depends on tax rate, implementation, ramp-up, and economic conditions. Treat these as
        informative, not precise. Estimates refresh annually.
      </p>
    </div>
  );
}
