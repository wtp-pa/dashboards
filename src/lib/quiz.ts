/**
 * Candidate Match — types + scoring. Pure functions, no I/O, so the same
 * logic is easy to audit on /quiz/about.
 *
 * Fairness rules (mirrored in the about page — keep them in sync):
 *  - Every candidate on the ballot is scored the same way, whatever party.
 *  - A stance only counts if it has a public source. "unknown" is skipped,
 *    never counted against anyone.
 *  - Incumbents' votes are a stance source like any other public statement.
 *    Where words and votes conflict, the stance is "mixed" and both show.
 *  - Answers are a 5-step scale between the two sides. "In between" is a
 *    real answer (0); "Not sure" is skipped, never scored as a midpoint.
 *  - No percentage until a candidate has enough positions on what you
 *    answered (MIN_SCORED), so one lucky overlap can't top the list.
 */

export type Level = 'state' | 'federal' | 'both';
export type Stance = 'agree' | 'disagree' | 'mixed' | 'unknown';
/**
 * Where you sit between the two sides: 1 = side a, 0.5 = lean a,
 * 0 = in between, -0.5 = lean b, -1 = side b. null = not sure (skipped).
 */
export type Answer = number | null;

export interface Issue {
  id: string;
  level: Level;
  short: boolean;
  topic: string;
  /** Optional one-line background shown above the choice. */
  context?: string;
  /** The side a candidate stance of "agree" means. */
  a: string;
  /** The side a candidate stance of "disagree" means. */
  b: string;
}

export interface Position {
  stance: Stance;
  summary?: string;
  source?: string;
  sourceDate?: string;
  record?: { summary: string; source: string };
}

export interface Candidate {
  id: string;
  name: string;
  party: string;
  incumbent: boolean;
  positions: Record<string, Position>;
}

export interface Race {
  id: string; // "gov", "pa-01" … "pa-17"
  office: string;
  level: 'state' | 'federal';
  counties?: string[];
  candidates: Candidate[];
}

export type Mode = 'short' | 'long';

export function issuesFor(issues: Issue[], mode: Mode): Issue[] {
  return mode === 'short' ? issues.filter((i) => i.short) : issues;
}

export function appliesTo(issue: Issue, race: Race): boolean {
  return issue.level === 'both' || issue.level === race.level;
}

const STANCE_VAL: Partial<Record<Stance, number>> = { agree: 1, mixed: 0, disagree: -1 };

export interface MatchResult {
  candidate: Candidate;
  /** 0–100, or null when there are too few overlapping positions to score. */
  pct: number | null;
  /** Issues that counted toward pct. */
  scored: number;
  /** Issues the user took a side on (not "not sure") that apply to this race. */
  asked: number;
}

/** Positions needed for a % (or every answered issue, if fewer than this). */
export const MIN_SCORED = 3;

/**
 * Per issue: 1 − |you − them| / 2, so same side = 1, lean vs. same side =
 * 0.75, side vs. mixed = 0.5, opposite sides = 0. "Important" issues count double. Ties sort by
 * tieOrder (candidate id → number); the quiz passes a per-visit random
 * order so list position never hints at incumbency or party.
 */
export function scoreRace(
  race: Race,
  issues: Issue[],
  answers: Record<string, Answer | undefined>,
  important: Set<string>,
  tieOrder: Record<string, number> = {},
): MatchResult[] {
  const relevant = issues.filter((i) => appliesTo(i, race) && typeof answers[i.id] === 'number');
  const need = Math.min(MIN_SCORED, relevant.length);
  return race.candidates
    .map((c) => {
      let num = 0;
      let den = 0;
      let scored = 0;
      for (const issue of relevant) {
        const theirs = STANCE_VAL[c.positions[issue.id]?.stance ?? 'unknown'];
        if (theirs === undefined) continue;
        const w = important.has(issue.id) ? 2 : 1;
        num += w * (1 - Math.abs((answers[issue.id] as number) - theirs) / 2);
        den += w;
        scored++;
      }
      return {
        candidate: c,
        pct: den > 0 && scored >= need ? Math.round((num / den) * 100) : null,
        scored,
        asked: relevant.length,
      };
    })
    .sort(
      (a, b) =>
        (b.pct ?? -1) - (a.pct ?? -1) ||
        (tieOrder[a.candidate.id] ?? 0) - (tieOrder[b.candidate.id] ?? 0),
    );
}
