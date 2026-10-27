import { useEffect, useMemo, useState } from 'react';
import {
  appliesTo,
  issuesFor,
  scoreRace,
  type Answer,
  type Issue,
  type MatchResult,
  type Mode,
  type Race,
  type Stance,
} from '../../lib/quiz';
import { track } from '../../lib/quizTrack';

interface Props {
  issues: Issue[];
  races: Race[];
  defaultMode?: Mode;
  /** Race ids officers pulled (config.quiz.hiddenRaces). */
  hidden?: string[];
  /** YYYY-MM-DD, for the countdown. */
  electionDate: string;
  /** Widget embeds: tighter padding, links open in the parent page. */
  compact?: boolean;
}

type Step = 'intro' | 'quiz' | 'results';

function readParams() {
  const p = new URLSearchParams(window.location.search);
  const mode = p.get('mode');
  return {
    mode: mode === 'short' || mode === 'long' ? (mode as Mode) : null,
    district: p.get('district'),
    source: (p.get('src') ?? p.get('utm_source'))?.slice(0, 40) ?? null,
  };
}

export default function Quiz({ issues, races, defaultMode = 'short', hidden = [], electionDate, compact = false }: Props) {
  const [mode, setMode] = useState<Mode>(defaultMode);
  const [district, setDistrict] = useState<string>('');
  const [showDistrict, setShowDistrict] = useState(false);
  const [source, setSource] = useState<string | null>(null);
  const [step, setStep] = useState<Step>('intro');
  const [copied, setCopied] = useState(false);
  const [idx, setIdx] = useState(0);
  const [answers, setAnswers] = useState<Record<string, Answer>>({});
  const [important, setImportant] = useState<Set<string>>(new Set());
  const [revealed, setRevealed] = useState(false);
  // Per visit: random tie-break order (see scoreRace) and which side of each
  // question shows first, so neither side always gets the top spot.
  const [tieOrder] = useState(() =>
    Object.fromEntries(races.flatMap((r) => r.candidates).map((c) => [c.id, Math.random()])),
  );
  const [bFirst] = useState(() => Object.fromEntries(issues.map((i) => [i.id, Math.random() < 0.5])));
  const [daysLeft, setDaysLeft] = useState<number | null>(null);

  useEffect(() => {
    const p = readParams();
    if (p.mode) setMode(p.mode);
    if (p.district) {
      setDistrict(p.district);
      setShowDistrict(true);
    }
    setSource(p.source);
    // Days until polls open, in Pennsylvania time.
    const today = new Date().toLocaleDateString('en-CA', { timeZone: 'America/New_York' });
    setDaysLeft(Math.round((Date.parse(electionDate) - Date.parse(today)) / 86_400_000));
  }, []);

  const shownRaces = races.filter((r) => !hidden.includes(r.id));
  const statewide = shownRaces.filter((r) => r.level === 'state');
  const houseRaces = shownRaces.filter((r) => r.level === 'federal');

  // Only ask questions that apply to a race the user will see results for.
  function questionsFor(m: Mode, d: string) {
    const mine = [...statewide, ...houseRaces.filter((r) => r.id === d)];
    return issuesFor(issues, m).filter((i) => mine.some((r) => appliesTo(i, r)));
  }
  const myRaces = [...statewide, ...houseRaces.filter((r) => r.id === district)];
  const questions = useMemo(() => questionsFor(mode, district), [issues, mode, district, hidden.join()]);
  const q = questions[idx];

  function start() {
    setStep('quiz');
    setIdx(0);
    setAnswers({});
    setImportant(new Set());
    setRevealed(false);
    track({ event: 'start', mode, race_id: district || null, source });
  }

  /** From results: add a House race or more issues, asking only what's new. */
  function extend(m: Mode, d: string) {
    setMode(m);
    setDistrict(d);
    const first = questionsFor(m, d).findIndex((i) => !(i.id in answers));
    if (first >= 0) {
      setIdx(first);
      setStep('quiz');
    }
  }

  function answer(a: Answer) {
    const next = { ...answers, [q.id]: a };
    setAnswers(next);
    // Go to the next unanswered question (after Back, this returns you to where you were).
    const after = questions.findIndex((i, n) => n > idx && !(i.id in next));
    if (after >= 0) setIdx(after);
    else {
      setStep('results');
      track({ event: 'complete', mode, race_id: district || null, source });
    }
  }

  async function share() {
    const url = `${window.location.origin}/vote2026/?src=share`;
    const text = "See which PA candidates for Governor line up with you on the issues. Names hidden until the end.";
    track({ event: 'share', source });
    try {
      if (navigator.share) await navigator.share({ title: 'Vote 2026: Candidate Match', text, url });
      else {
        await navigator.clipboard.writeText(url);
        setCopied(true);
      }
    } catch {
      // Share sheet dismissed.
    }
  }

  function toggleImportant(id: string) {
    setImportant((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  }

  const pad = compact ? 'p-4' : 'p-6 sm:p-8';
  const card = `rounded-xl border border-white/10 bg-surface ${pad}`;
  const btn = 'rounded-lg px-4 py-2.5 text-sm font-semibold transition';
  const other: Mode = mode === 'short' ? 'long' : 'short';

  const districtSelect = (value: string, onChange: (d: string) => void, emptyLabel: string) => (
    <>
      <select
        aria-label="Your U.S. House district"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="mt-2 w-full rounded-lg border border-white/15 bg-page px-3 py-2.5 text-sm"
      >
        <option value="">{emptyLabel}</option>
        {houseRaces.map((r) => (
          <option key={r.id} value={r.id}>
            {r.office.replace('U.S. House — ', '')}
            {r.counties?.length ? ` — ${r.counties.slice(0, 3).join(', ')}${r.counties.length > 3 ? '…' : ''}` : ''}
          </option>
        ))}
      </select>
      <a
        href="https://www.house.gov/representatives/find-your-representative"
        target="_blank"
        rel="noopener"
        className="mt-1 inline-block text-xs text-wtp-sky"
      >
        Don't know your district? Look it up by ZIP code →
      </a>
    </>
  );

  if (step === 'intro') {
    return (
      <div className={card}>
        {daysLeft !== null && daysLeft >= 0 && (
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-wtp-gold">
            {daysLeft === 0
              ? 'Election Day is today. Polls are open 7 a.m. to 8 p.m.'
              : `Election Day is in ${daysLeft} day${daysLeft === 1 ? '' : 's'}`}
          </p>
        )}
        <p className="mt-3 text-base text-wtp-cream/80">
          Every Pennsylvania voter picks a <strong className="text-white">Governor</strong> on Nov 3. Answer a few
          questions, then see which candidates are closest to you. Names stay hidden until the end.
        </p>

        <button type="button" onClick={start} className={`${btn} mt-6 w-full bg-wtp-sky py-3 text-base text-wtp-navy hover:bg-white`}>
          Start · {questions.length} questions →
        </button>
        <p className="mt-2 text-center text-xs text-wtp-cream/50">
          {district ? `Governor + ${myRaces[myRaces.length - 1]?.office.replace('U.S. House — ', 'U.S. House ')}` : 'Governor race'}
          {' · '}
          <button type="button" onClick={() => setMode(other)} className="text-wtp-sky">
            {mode === 'short' ? `Want more issues? Use the full version (${questionsFor('long', district).length})` : `Shorter version (${questionsFor('short', district).length})`}
          </button>
        </p>

        <div className="mt-6 border-t border-white/10 pt-4">
          {!showDistrict ? (
            <button type="button" onClick={() => setShowDistrict(true)} className="text-sm font-medium text-wtp-sky">
              + Also compare your U.S. House race (optional)
            </button>
          ) : (
            <div>
              <p className="text-sm font-medium">Your U.S. House race (optional)</p>
              <p className="mt-1 text-xs text-wtp-cream/60">
                Your ballot also has a race for U.S. House. Which district depends on where you live.
              </p>
              {districtSelect(district, setDistrict, 'Skip, just the Governor')}
            </div>
          )}
          <p className="mt-4 text-xs text-wtp-cream/40">
            Your ballot also has state legislature races, which aren't in this quiz. Your county election office posts a
            sample ballot.
          </p>
        </div>
      </div>
    );
  }

  if (step === 'quiz' && q) {
    const sides: Answer[] = bFirst[q.id] ? ['disagree', 'agree'] : ['agree', 'disagree'];
    return (
      <div className={card}>
        <div className="text-xs text-wtp-cream/50">
          {idx + 1} of {questions.length} · {q.topic}
        </div>
        <div className="mt-2 h-1 rounded bg-white/10">
          <div className="h-1 rounded bg-wtp-sky transition-all" style={{ width: `${(idx / questions.length) * 100}%` }} />
        </div>

        {q.context && <p className="mt-5 text-sm text-wtp-cream/60">{q.context}</p>}
        <p className="mt-4 text-lg font-semibold">Which comes closer to your view?</p>

        <div className="mt-3 space-y-2">
          {sides.map((side) => (
            <button
              key={side}
              type="button"
              onClick={() => answer(side)}
              className={`${btn} block w-full border text-left text-base font-medium ${answers[q.id] === side ? 'border-wtp-sky bg-wtp-sky/15' : 'border-white/15 hover:border-wtp-sky/60'}`}
            >
              {side === 'agree' ? q.a : q.b}
            </button>
          ))}
          <button
            type="button"
            onClick={() => answer('neutral')}
            className={`${btn} block w-full border font-normal text-wtp-cream/70 ${answers[q.id] === 'neutral' ? 'border-wtp-sky bg-wtp-sky/15' : 'border-white/10 hover:border-white/30'}`}
          >
            Not sure / neither
          </button>
        </div>

        <label className="mt-4 flex cursor-pointer items-center gap-2 text-sm text-wtp-cream/70">
          <input type="checkbox" checked={important.has(q.id)} onChange={() => toggleImportant(q.id)} />
          This issue matters a lot to me
        </label>

        <div className="mt-5 flex items-center justify-between gap-3 border-t border-white/10 pt-4">
          <button
            type="button"
            onClick={() => (idx > 0 ? setIdx(idx - 1) : setStep('intro'))}
            className={`${btn} border border-white/20 hover:border-white/40`}
          >
            ← Back
          </button>
          <span className="text-right text-xs text-wtp-cream/40">"Not sure" doesn't count for or against anyone.</span>
        </div>
      </div>
    );
  }

  // Results
  return (
    <div className="space-y-4">
      <div className={`${card} flex flex-wrap items-center justify-between gap-3`}>
        <div>
          <h2 className="text-xl font-semibold">Your matches</h2>
          <p className="text-sm text-wtp-cream/60">
            {revealed ? 'Names revealed.' : 'Names hidden. Compare positions first.'} Based on{' '}
            {Object.values(answers).filter((a) => a !== 'neutral').length} answers.
          </p>
        </div>
        {!revealed && (
          <button
            type="button"
            onClick={() => {
              setRevealed(true);
              track({ event: 'reveal', mode, race_id: district || null, source });
            }}
            className={`${btn} bg-wtp-gold text-wtp-navy hover:bg-white`}
          >
            Reveal names
          </button>
        )}
      </div>

      {myRaces.map((race) => (
        <RaceResults
          key={race.id}
          race={race}
          issues={questions}
          results={scoreRace(race, questions, answers, important, tieOrder)}
          answers={answers}
          revealed={revealed}
          card={card}
        />
      ))}

      {!district && (
        <div className={card}>
          <p className="text-sm font-medium">Add your U.S. House race</p>
          <p className="mt-1 text-xs text-wtp-cream/60">
            Your ballot also has a race for U.S. House. Pick your district to compare those candidates too. We'll ask only the 2–3 extra questions.
          </p>
          {districtSelect('', (d) => d && extend(mode, d), 'Choose your district')}
        </div>
      )}

      <div className="flex flex-wrap gap-2">
        {mode === 'short' && (
          <button
            type="button"
            onClick={() => extend('long', district)}
            className={`${btn} border border-wtp-sky/50 text-wtp-sky hover:border-wtp-sky`}
          >
            Answer more issues ({questionsFor('long', district).length - questions.length} more)
          </button>
        )}
        <button type="button" onClick={share} className={`${btn} border border-white/15 hover:border-white/30`}>
          {copied ? 'Link copied' : 'Share with a friend'}
        </button>
        <button type="button" onClick={() => setStep('intro')} className={`${btn} text-wtp-cream/60 hover:text-wtp-cream`}>
          Start over
        </button>
      </div>
      <p className="text-sm">
        <a href="/vote2026/sources" target={compact ? '_top' : undefined} className="text-wtp-sky">
          Every candidate's positions + sources →
        </a>
        <span className="mx-2 text-wtp-cream/30">·</span>
        <a href="/vote2026/about" target={compact ? '_top' : undefined} className="text-wtp-sky">
          How we score →
        </a>
      </p>

      <VotePlan card={card} />

      <p className="text-xs text-wtp-cream/40">
        A match score is a starting point, not an endorsement. Read the sources, then go vote.
      </p>
    </div>
  );
}

/** How a candidate's stance compares with your answer, in plain words. */
function compare(you: Answer, them: Stance): string {
  if (them === 'unknown') return 'No public position';
  if (them === 'mixed') return 'Mixed record';
  return you === them ? 'Same side as you' : 'Opposite side';
}

function RaceResults({
  race,
  issues,
  results,
  answers,
  revealed,
  card,
}: {
  race: Race;
  issues: Issue[];
  results: MatchResult[];
  answers: Record<string, Answer>;
  revealed: boolean;
  card: string;
}) {
  const [open, setOpen] = useState<string | null>(null);
  const relevant = issues.filter((i) => appliesTo(i, race) && answers[i.id] && answers[i.id] !== 'neutral');

  return (
    <section className={card}>
      <h3 className="text-xs uppercase tracking-[0.18em] text-wtp-sky">{race.office}</h3>
      {race.candidates.length < 2 && (
        <p className="mt-2 text-xs text-wtp-cream/50">Only one candidate is on the ballot in this race.</p>
      )}
      <ul className="mt-3 space-y-3">
        {results.map((r, i) => {
          const c = r.candidate;
          const label = revealed ? c.name : `Candidate ${String.fromCharCode(65 + i)}`;
          const isOpen = open === c.id;
          return (
            <li key={c.id} className="rounded-lg border border-white/10 bg-page/40 p-3">
              <button
                type="button"
                onClick={() => setOpen(isOpen ? null : c.id)}
                aria-expanded={isOpen}
                className="flex w-full items-center gap-3 text-left"
              >
                <span className="w-14 flex-shrink-0 text-2xl font-semibold tabular-nums">
                  {r.pct === null ? '—' : `${r.pct}%`}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate font-medium">{label}</span>
                  <span className="block text-xs text-wtp-cream/50">
                    {revealed && `${c.party}${c.incumbent ? ' · incumbent' : ''} · `}
                    {r.pct === null
                      ? `Not enough public positions to score (${r.scored} of ${r.asked})`
                      : `Scored on ${r.scored} of ${r.asked} issues`}
                  </span>
                </span>
                <span className="text-xs text-wtp-sky">{isOpen ? 'Hide' : 'Details'}</span>
              </button>
              {r.pct !== null && (
                <div className="mt-2 h-1.5 rounded bg-white/10">
                  <div className="h-1.5 rounded bg-wtp-sky" style={{ width: `${r.pct}%` }} />
                </div>
              )}
              {isOpen && (
                <ul className="mt-3 space-y-2 border-t border-white/10 pt-3 text-sm">
                  {relevant.map((issue) => {
                    const pos = c.positions[issue.id] ?? { stance: 'unknown' as const };
                    return (
                      <li key={issue.id}>
                        <div className="flex justify-between gap-2">
                          <span className="font-medium">{issue.topic}</span>
                          <span className="text-xs text-wtp-cream/60">
                            {compare(answers[issue.id], pos.stance)}
                          </span>
                        </div>
                        {/* Summaries often name the candidate, so they wait for the reveal. */}
                        {revealed && pos.summary && (
                          <p className="mt-0.5 text-xs text-wtp-cream/60">
                            {pos.summary}{' '}
                            {pos.source && (
                              <a href={pos.source} target="_blank" rel="noopener" className="text-wtp-sky">
                                source
                              </a>
                            )}
                          </p>
                        )}
                        {revealed && pos.record && (
                          <p className="mt-0.5 text-xs text-wtp-cream/50">
                            Record: {pos.record.summary}{' '}
                            <a href={pos.record.source} target="_blank" rel="noopener" className="text-wtp-sky">
                              source
                            </a>
                          </p>
                        )}
                      </li>
                    );
                  })}
                  {!revealed && <li className="text-xs text-wtp-cream/40">Reveal names to see what they said and the sources.</li>}
                </ul>
              )}
            </li>
          );
        })}
      </ul>
    </section>
  );
}

const EXT = { target: '_blank', rel: 'noopener', className: 'text-wtp-sky' } as const;

/** Election Day checklist. Rules from vote.pa.gov — re-check before each election. */
function VotePlan({ card }: { card: string }) {
  return (
    <section className={`${card} border-wtp-gold/40`}>
      <h3 className="text-lg font-semibold">Now make your plan to vote</h3>
      <p className="mt-1 text-sm text-wtp-cream/70">
        Tuesday, Nov 3. Polls are open 7 a.m. to 8 p.m. If you're in line by 8, you can vote.
      </p>
      <ul className="mt-3 space-y-2 text-sm text-wtp-cream/80">
        <li>
          — <a href="https://www.pa.gov/services/vote/find-your-local-polling-place" {...EXT}>Find your polling place</a>
        </li>
        <li>
          — Voting by mail? Your county has to <strong className="text-white">receive</strong> it by 8 p.m. Nov 3. A
          postmark isn't enough, and you can't drop it at your polling place.{' '}
          <a href="https://www.pavoterservices.pa.gov/pages/ballottracking.aspx" {...EXT}>Track your ballot</a>
        </li>
        <li>— Voting at your polling place for the first time? Bring ID.</li>
        <li>
          — Questions? <a href="https://www.pa.gov/agencies/vote" {...EXT}>vote.pa.gov</a> or your county election office.
        </li>
      </ul>
      <p className="mt-3 text-sm text-wtp-cream/70">Then bring someone with you. Three PA House races in 2024 were decided by fewer than 10,000 votes.</p>
    </section>
  );
}
