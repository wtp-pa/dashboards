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
} from '../../lib/quiz';
import { loadVisibility, track } from '../../lib/quizBackend';

interface Props {
  issues: Issue[];
  races: Race[];
  defaultMode?: Mode;
  /** Widget embeds: tighter padding, links open in the parent page. */
  compact?: boolean;
}

type Step = 'intro' | 'quiz' | 'results';

const ANSWER_LABEL: Record<Answer, string> = { agree: 'Agree', neutral: 'Not sure', disagree: 'Disagree' };
const STANCE_LABEL = { agree: 'Agrees', disagree: 'Disagrees', mixed: 'Mixed', unknown: 'No public position' } as const;

function readParams() {
  const p = new URLSearchParams(window.location.search);
  const mode = p.get('mode');
  return {
    mode: mode === 'short' || mode === 'long' ? (mode as Mode) : null,
    district: p.get('district'),
    source: (p.get('src') ?? p.get('utm_source'))?.slice(0, 40) ?? null,
  };
}

export default function Quiz({ issues, races, defaultMode = 'short', compact = false }: Props) {
  const [mode, setMode] = useState<Mode>(defaultMode);
  const [district, setDistrict] = useState<string>('');
  const [source, setSource] = useState<string | null>(null);
  const [visible, setVisible] = useState<Record<string, boolean>>({});
  const [step, setStep] = useState<Step>('intro');
  const [idx, setIdx] = useState(0);
  const [answers, setAnswers] = useState<Record<string, Answer>>({});
  const [important, setImportant] = useState<Set<string>>(new Set());
  const [revealed, setRevealed] = useState(false);

  useEffect(() => {
    const p = readParams();
    if (p.mode) setMode(p.mode);
    if (p.district) setDistrict(p.district);
    setSource(p.source);
    loadVisibility().then(setVisible);
  }, []);

  const shownRaces = races.filter((r) => visible[r.id] !== false);
  const statewide = shownRaces.filter((r) => r.level === 'state');
  const houseRaces = shownRaces.filter((r) => r.level === 'federal');
  const myRaces = [...statewide, ...houseRaces.filter((r) => r.id === district)];

  // Only ask questions that apply to a race the user will see results for.
  const questions = useMemo(
    () => issuesFor(issues, mode).filter((i) => myRaces.some((r) => appliesTo(i, r))),
    [issues, mode, myRaces.map((r) => r.id).join()],
  );
  const q = questions[idx];

  function start() {
    setStep('quiz');
    setIdx(0);
    setAnswers({});
    setImportant(new Set());
    setRevealed(false);
    track({ event: 'start', mode, race_id: district || null, source });
  }

  function answer(a: Answer | null) {
    if (a) setAnswers((prev) => ({ ...prev, [q.id]: a }));
    else
      setAnswers((prev) => {
        const { [q.id]: _, ...rest } = prev;
        return rest;
      });
    if (idx + 1 < questions.length) setIdx(idx + 1);
    else finish(a ? { ...answers, [q.id]: a } : answers);
  }

  function finish(final: Record<string, Answer>) {
    setStep('results');
    track({ event: 'complete', mode, race_id: district || null, answered: Object.keys(final).length, source });
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

  if (step === 'intro') {
    return (
      <div className={card}>
        <h2 className="text-xl font-semibold sm:text-2xl">Who do you line up with on Nov 3?</h2>
        <p className="mt-2 text-sm text-wtp-cream/70">
          Answer a few questions on the issues. Candidate names stay hidden until the end, so you judge positions, not
          parties. Every candidate on the ballot is scored the same way, from their own public record.
        </p>

        <label className="mt-6 block text-sm font-medium" htmlFor="quiz-district">
          Your U.S. House district <span className="text-wtp-cream/50">(optional)</span>
        </label>
        <select
          id="quiz-district"
          value={district}
          onChange={(e) => setDistrict(e.target.value)}
          className="mt-1 w-full rounded-lg border border-white/15 bg-page px-3 py-2.5 text-sm"
        >
          <option value="">Statewide races only</option>
          {houseRaces.map((r) => (
            <option key={r.id} value={r.id}>
              {r.office}
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
          Not sure? Look up your district by ZIP →
        </a>

        <fieldset className="mt-6">
          <legend className="text-sm font-medium">Length</legend>
          <div className="mt-2 flex gap-2">
            {(['short', 'long'] as const).map((m) => (
              <button
                key={m}
                type="button"
                onClick={() => setMode(m)}
                aria-pressed={mode === m}
                className={`${btn} border ${mode === m ? 'border-wtp-sky bg-wtp-sky/15 text-white' : 'border-white/15 text-wtp-cream/70 hover:border-white/30'}`}
              >
                {m === 'short' ? 'Quick' : 'Full'} · {issuesFor(issues, m).length} issues
              </button>
            ))}
          </div>
        </fieldset>

        <button type="button" onClick={start} className={`${btn} mt-6 w-full bg-wtp-sky text-wtp-navy hover:bg-white`}>
          Start →
        </button>
      </div>
    );
  }

  if (step === 'quiz' && q) {
    return (
      <div className={card}>
        <div className="flex items-center justify-between text-xs text-wtp-cream/50">
          <span>
            {idx + 1} of {questions.length} · {q.topic}
          </span>
          {idx > 0 && (
            <button type="button" onClick={() => setIdx(idx - 1)} className="text-wtp-sky">
              ← Back
            </button>
          )}
        </div>
        <div className="mt-2 h-1 rounded bg-white/10">
          <div className="h-1 rounded bg-wtp-sky transition-all" style={{ width: `${(idx / questions.length) * 100}%` }} />
        </div>

        <p className="mt-6 min-h-[4.5rem] text-lg font-medium sm:text-xl">{q.statement}</p>

        <div className="mt-6 grid grid-cols-3 gap-2">
          {(['agree', 'neutral', 'disagree'] as const).map((a) => (
            <button
              key={a}
              type="button"
              onClick={() => answer(a)}
              className={`${btn} border ${answers[q.id] === a ? 'border-wtp-sky bg-wtp-sky/15' : 'border-white/15 hover:border-wtp-sky/60'}`}
            >
              {ANSWER_LABEL[a]}
            </button>
          ))}
        </div>

        <div className="mt-4 flex items-center justify-between text-sm">
          <label className="flex cursor-pointer items-center gap-2 text-wtp-cream/70">
            <input type="checkbox" checked={important.has(q.id)} onChange={() => toggleImportant(q.id)} />
            This one matters a lot to me
          </label>
          <button type="button" onClick={() => answer(null)} className="text-wtp-cream/50 hover:text-wtp-cream">
            Skip
          </button>
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
            {revealed ? 'Names revealed.' : 'Names hidden — compare positions first.'} Based on{' '}
            {Object.keys(answers).length} answers.
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
          results={scoreRace(race, questions, answers, important)}
          answers={answers}
          revealed={revealed}
          card={card}
        />
      ))}

      <div className="flex flex-wrap gap-2">
        <button type="button" onClick={() => setStep('intro')} className={`${btn} border border-white/15 hover:border-white/30`}>
          Retake
        </button>
        {mode === 'short' && (
          <button
            type="button"
            onClick={() => {
              setMode('long');
              setStep('intro');
            }}
            className={`${btn} border border-wtp-sky/50 text-wtp-sky hover:border-wtp-sky`}
          >
            Try the full version ({issuesFor(issues, 'long').length} issues)
          </button>
        )}
        <a
          href="/quiz/about"
          target={compact ? '_top' : undefined}
          className={`${btn} text-wtp-cream/60 no-underline hover:text-wtp-sky`}
        >
          How we score →
        </a>
      </div>

      <p className="text-xs text-wtp-cream/40">
        A match score is a starting point, not an endorsement. Check the sources, then find your polling place at{' '}
        <a href="https://www.pa.gov/en/agencies/vote" target="_blank" rel="noopener" className="text-wtp-sky">
          vote.pa.gov
        </a>
        .
      </p>
    </div>
  );
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
  const relevant = issues.filter((i) => appliesTo(i, race) && answers[i.id]);

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
                    {r.pct === null ? 'Not enough public positions to score' : `Scored on ${r.scored} of ${r.asked} issues`}
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
                            You: {ANSWER_LABEL[answers[issue.id]]} · Them: {STANCE_LABEL[pos.stance]}
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
                  {!revealed && <li className="text-xs text-wtp-cream/40">Reveal names to see sources.</li>}
                </ul>
              )}
            </li>
          );
        })}
      </ul>
    </section>
  );
}
