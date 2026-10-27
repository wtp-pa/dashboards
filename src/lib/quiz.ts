/**
 * Candidate Match — types + scoring. Pure functions, no I/O, so the same
 * logic is easy to audit on /vote2026/about.
 *
 * Fairness rules (mirrored in the about page — keep them in sync):
 *  - Every candidate on the ballot is scored the same way, whatever party.
 *  - A stance only counts if it has a public source. "unknown" is skipped,
 *    never counted against anyone.
 *  - Incumbents' votes are a stance source like any other public statement.
 *    Where words and votes conflict, the stance is "mixed" and both show.
 *  - Each issue offers several distinct positions, not two sides. "None of
 *    these" and "Not sure" are skipped, never scored.
 *  - No percentage until a candidate has enough positions on what you
 *    answered (MIN_SCORED), so one lucky overlap can't top the list.
 */

export type Level = 'state' | 'federal' | 'both';
/** An option id, NONE ("none of these fit me"), or null (not sure). */
export type Answer = string | null;
export const NONE = '_none';

export interface Option {
  id: string;
  text: string;
}

export interface Issue {
  id: string;
  level: Level;
  short: boolean;
  topic: string;
  /** Optional one-line background shown above the choice. */
  context?: string;
  question: string;
  /** In order along the issue's main disagreement; shown as-is or reversed. */
  options: Option[];
  /** Pairs of options that partly overlap (half credit). */
  near: [string, string][];
}

export interface Position {
  /** One option id; two when words and record differ; empty = no public position. */
  options: string[];
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

/** You picked a real option (not "not sure" or "none of these"). */
export function picked(a: Answer | undefined): a is string {
  return typeof a === 'string' && a !== NONE;
}

/** 1 = same option, 0.5 = options that overlap, 0 = otherwise. */
export function credit(issue: Issue, you: string, them: string): number {
  if (you === them) return 1;
  return issue.near.some(([x, y]) => (x === you && y === them) || (x === them && y === you)) ? 0.5 : 0;
}

/** Average credit over a candidate's option(s); null when they have none. */
export function issueCredit(issue: Issue, you: string, pos: Position | undefined): number | null {
  const opts = pos?.options ?? [];
  if (!opts.length) return null;
  return opts.reduce((n, o) => n + credit(issue, you, o), 0) / opts.length;
}

export interface MatchResult {
  candidate: Candidate;
  /** 0–100, or null when there are too few overlapping positions to score. */
  pct: number | null;
  /** Issues that counted toward pct. */
  scored: number;
  /** Issues the user picked an option on that apply to this race. */
  asked: number;
}

/** Positions needed for a % (or every answered issue, if fewer than this). */
export const MIN_SCORED = 3;

/**
 * Per issue: same option = 1, overlapping option = 0.5, else 0; a candidate
 * with two options (words vs. record) gets the average. "Important" issues count double. Ties sort by
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
  const relevant = issues.filter((i) => appliesTo(i, race) && picked(answers[i.id]));
  const need = Math.min(MIN_SCORED, relevant.length);
  return race.candidates
    .map((c) => {
      let num = 0;
      let den = 0;
      let scored = 0;
      for (const issue of relevant) {
        const got = issueCredit(issue, answers[issue.id] as string, c.positions[issue.id]);
        if (got === null) continue;
        const w = important.has(issue.id) ? 2 : 1;
        num += w * got;
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
