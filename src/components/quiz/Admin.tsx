import { useEffect, useState } from 'react';
import type { Session } from '@supabase/supabase-js';
import { supabase } from '../../lib/quizBackend';

interface RaceSummary {
  id: string;
  office: string;
  candidateCount: number;
}

interface Stats {
  totals: Record<string, number>;
  byMode: Record<string, number>;
  byRace: Record<string, number>;
  bySource: Record<string, number>;
  byDay: { day: string; starts: number; completes: number }[];
}

const RANGES = [
  { label: 'Last 24h', days: 1 },
  { label: 'Last 7 days', days: 7 },
  { label: 'Last 30 days', days: 30 },
];

export default function Admin({ races }: { races: RaceSummary[] }) {
  const sb = supabase();
  const [session, setSession] = useState<Session | null>(null);
  const [email, setEmail] = useState('');
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [days, setDays] = useState(7);
  const [stats, setStats] = useState<Stats | null>(null);
  const [visible, setVisible] = useState<Record<string, boolean>>({});
  const [saving, setSaving] = useState<string | null>(null);

  useEffect(() => {
    if (!sb) return;
    sb.auth.getSession().then(({ data }) => setSession(data.session));
    const { data } = sb.auth.onAuthStateChange((_e, s) => setSession(s));
    return () => data.subscription.unsubscribe();
  }, []);

  useEffect(() => {
    if (!sb || !session) return;
    setError(null);
    sb.rpc('quiz_stats', { since: new Date(Date.now() - days * 86_400_000).toISOString() }).then(({ data, error }) => {
      if (error) setError(error.message.includes('not authorized') ? 'This email is not on the officer list.' : error.message);
      else setStats(data as Stats);
    });
    sb.from('quiz_race_settings')
      .select('race_id, visible')
      .then(({ data }) => setVisible(Object.fromEntries((data ?? []).map((r) => [r.race_id, r.visible]))));
  }, [session, days]);

  if (!sb) {
    return <p className="text-sm text-wtp-red">Supabase isn't configured for this build (PUBLIC_SUPABASE_* env vars).</p>;
  }

  if (!session) {
    return (
      <form
        className="max-w-sm space-y-3"
        onSubmit={async (e) => {
          e.preventDefault();
          const { error } = await sb.auth.signInWithOtp({
            email,
            options: { emailRedirectTo: window.location.href, shouldCreateUser: true },
          });
          if (error) setError(error.message);
          else setSent(true);
        }}
      >
        <p className="text-sm text-wtp-cream/70">Officers: enter your email and we'll send a sign-in link.</p>
        <input
          type="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="w-full rounded-lg border border-white/15 bg-page px-3 py-2.5 text-sm"
          placeholder="you@example.org"
        />
        <button className="w-full rounded-lg bg-wtp-sky px-4 py-2.5 text-sm font-semibold text-wtp-navy">Send link</button>
        {sent && <p className="text-sm text-wtp-sky">Check your inbox.</p>}
        {error && <p className="text-sm text-wtp-red">{error}</p>}
      </form>
    );
  }

  async function toggle(raceId: string, next: boolean) {
    setSaving(raceId);
    const { error } = await sb!.from('quiz_race_settings').upsert({ race_id: raceId, visible: next });
    setSaving(null);
    if (error) setError(error.message);
    else setVisible((v) => ({ ...v, [raceId]: next }));
  }

  const starts = stats?.totals.start ?? 0;
  const completes = stats?.totals.complete ?? 0;
  const reveals = stats?.totals.reveal ?? 0;

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-center justify-between gap-3 text-sm">
        <span className="text-wtp-cream/60">Signed in as {session.user.email}</span>
        <button type="button" onClick={() => sb.auth.signOut()} className="text-wtp-sky">
          Sign out
        </button>
      </div>
      {error && <p className="text-sm text-wtp-red">{error}</p>}

      <section>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-lg font-semibold">Usage</h2>
          <div className="flex gap-1">
            {RANGES.map((r) => (
              <button
                key={r.days}
                type="button"
                onClick={() => setDays(r.days)}
                className={`rounded px-2.5 py-1 text-xs ${days === r.days ? 'bg-wtp-sky text-wtp-navy' : 'text-wtp-cream/60'}`}
              >
                {r.label}
              </button>
            ))}
          </div>
        </div>
        <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Tile label="Started" value={starts} />
          <Tile label="Finished" value={completes} />
          <Tile label="Finish rate" value={starts ? `${Math.round((completes / starts) * 100)}%` : '—'} />
          <Tile label="Revealed names" value={reveals} />
        </div>
        {stats && (
          <div className="mt-4 grid gap-4 sm:grid-cols-3">
            <Breakdown title="Where people came from" rows={stats.bySource} />
            <Breakdown title="Quiz length (finished)" rows={stats.byMode} />
            <Breakdown title="District picked (finished)" rows={stats.byRace} />
          </div>
        )}
        {stats && stats.byDay.length > 0 && (
          <table className="mt-4 w-full text-sm">
            <thead className="text-left text-xs text-wtp-cream/50">
              <tr>
                <th className="py-1 font-normal">Day</th>
                <th className="py-1 text-right font-normal">Started</th>
                <th className="py-1 text-right font-normal">Finished</th>
              </tr>
            </thead>
            <tbody className="tabular-nums">
              {stats.byDay.map((d) => (
                <tr key={d.day} className="border-t border-white/10">
                  <td className="py-1">{d.day}</td>
                  <td className="py-1 text-right">{d.starts}</td>
                  <td className="py-1 text-right">{d.completes}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <section>
        <h2 className="text-lg font-semibold">Races shown in the quiz</h2>
        <p className="text-sm text-wtp-cream/60">Turning a race off hides it for everyone within a few seconds. Every change is logged.</p>
        <ul className="mt-3 divide-y divide-white/10 rounded-lg border border-white/10">
          {races.map((r) => {
            const on = visible[r.id] !== false;
            return (
              <li key={r.id} className="flex items-center justify-between gap-3 px-3 py-2 text-sm">
                <span>
                  {r.office} <span className="text-wtp-cream/40">· {r.candidateCount} candidates</span>
                </span>
                <button
                  type="button"
                  disabled={saving === r.id}
                  onClick={() => toggle(r.id, !on)}
                  className={`w-20 rounded px-2 py-1 text-xs font-semibold ${on ? 'bg-wtp-sky/20 text-wtp-sky' : 'bg-white/5 text-wtp-cream/50'}`}
                >
                  {saving === r.id ? '…' : on ? 'Shown' : 'Hidden'}
                </button>
              </li>
            );
          })}
        </ul>
      </section>
    </div>
  );
}

function Tile({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="rounded-lg border border-white/10 bg-surface p-3">
      <div className="text-xs text-wtp-cream/50">{label}</div>
      <div className="mt-1 text-2xl font-semibold tabular-nums">{value}</div>
    </div>
  );
}

function Breakdown({ title, rows }: { title: string; rows: Record<string, number> }) {
  const entries = Object.entries(rows).sort((a, b) => b[1] - a[1]);
  return (
    <div>
      <div className="text-xs text-wtp-cream/50">{title}</div>
      <ul className="mt-1 text-sm tabular-nums">
        {entries.length === 0 && <li className="text-wtp-cream/40">No data yet</li>}
        {entries.map(([k, v]) => (
          <li key={k} className="flex justify-between border-t border-white/10 py-1">
            <span>{k}</span>
            <span>{v}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
