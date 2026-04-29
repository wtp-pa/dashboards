/**
 * Shared bill domain logic — used by both the Legislation Watch page and
 * the Elected Officials Watch pages so both surfaces describe the same
 * bill the same way.
 *
 * If you find yourself wanting to change "topic-only" → "unscored", or
 * the auto-alignment threshold, or what counts as "passed legislature":
 * change it here, not inline in a page.
 */

export type Alignment = 'aligned' | 'mixed' | 'opposed' | 'topic-only' | 'under-review';
export type AlignmentSource = 'manual' | 'auto' | 'none';
export type Stage = 'introduced' | 'committee' | 'on-floor' | 'passed' | 'signed';

export interface BillMatch {
  positionId: string;
  score: number;
  evidence: string;
  mechanism: 'keyword' | 'tfidf';
  autoAlignment?: 'likely-aligned' | 'likely-opposed' | 'topic-only';
  autoConfidence?: number;
  alignedVerbs?: string[];
  opposedVerbs?: string[];
}

export interface BillRecord {
  id: string;
  chamber: string;
  title: string;
  sponsor: string;
  status: string;
  lastAction: string;
  url: string;
  summary: string;
  matches: BillMatch[];
  autoAlignment?: 'likely-aligned' | 'likely-opposed' | 'topic-only';
  autoConfidence?: number;
}

export interface ManualReview {
  alignment: 'aligned' | 'mixed' | 'opposed';
  note: string;
  reviewedBy?: string;
  reviewedAt?: string;
}

export interface ResolvedAlignment {
  alignment: Alignment;
  source: AlignmentSource;
  confidence?: number;
}

// Confidence threshold above which an auto-alignment is presented as the
// bill's alignment. Below this, the bill renders as "Touches our platform".
export const AUTO_ALIGNMENT_THRESHOLD = 0.65;

export const STAGE_LABELS: Record<Stage, string> = {
  introduced: 'Introduced',
  committee: 'In committee',
  'on-floor': 'On floor',
  passed: 'Passed legislature',
  signed: 'Signed into law',
};

// Lower number = more advanced. Used for sorting bills "most-progressed first".
export const STAGE_ORDER: Record<Stage, number> = {
  signed: 0,
  passed: 1,
  'on-floor': 2,
  committee: 3,
  introduced: 4,
};

// Display priority within a stage bucket.
export const ALIGNMENT_ORDER: Record<Alignment, number> = {
  aligned: 0, opposed: 1, mixed: 2, 'topic-only': 3, 'under-review': 4,
};

// Map an OpenStates status string to a stage in the PA legislative process.
// PA-specific phrases — extend as new ones show up.
export function stageOf(status: string): Stage {
  const s = status.toLowerCase();
  if (s.includes('signed') || s.includes('act of') || s.includes('became law')) return 'signed';
  if (s.includes('passed both') || s.includes('to governor') || s.includes('enacted')) return 'passed';
  if (s.includes('third consideration') || s.includes('passed house') || s.includes('passed senate') || s.includes('on floor') || s.includes('adopted')) return 'on-floor';
  if (s.includes('appropriations')) return 'committee'; // Re-referred to Appropriations = past initial committee
  return 'introduced';
}

// Strip the boilerplate "An Act amending the act of ... known as the X, in Y,
// providing for Z" preamble down to the bill's actual subject. Falls back to
// the raw title if no clean extraction is possible.
export function cleanTitle(title: string): string {
  let t = title.trim().replace(/\s+/g, ' ');
  const provMatch = t.match(/(?:further\s+)?providing for (.+?)\.?$/i);
  if (provMatch && provMatch[1].length >= 8) {
    return provMatch[1].trim().replace(/^the\s+/i, '').replace(/^["']|["']$/g, '').replace(/\.$/, '');
  }
  const knownMatch = t.match(/known as the (.+?)(?:,|\.|$)/i);
  if (knownMatch && knownMatch[1].length >= 8) {
    return knownMatch[1].trim();
  }
  t = t.replace(/^an act\s+/i, '');
  if (t.length > 120) return t.slice(0, 117).trim() + '…';
  return t;
}

// Resolve a bill's display alignment from (in priority order):
//   1. an editor's manual review (highest authority)
//   2. an auto-detected alignment with confidence above threshold
//   3. "topic-only" if any platform plank matched
//   4. "under-review" if nothing matched (rare given matches.length filter)
export function resolveAlignment(
  bill: BillRecord,
  review?: ManualReview,
  threshold: number = AUTO_ALIGNMENT_THRESHOLD,
): ResolvedAlignment {
  if (review) {
    return { alignment: review.alignment, source: 'manual' };
  }
  if (
    (bill.autoAlignment === 'likely-aligned' || bill.autoAlignment === 'likely-opposed') &&
    typeof bill.autoConfidence === 'number' &&
    bill.autoConfidence >= threshold
  ) {
    return {
      alignment: bill.autoAlignment === 'likely-aligned' ? 'aligned' : 'opposed',
      source: 'auto',
      confidence: bill.autoConfidence,
    };
  }
  if (bill.matches.length > 0) {
    return { alignment: 'topic-only', source: 'none' };
  }
  return { alignment: 'under-review', source: 'none' };
}

// Sort bills "most-relevant first" — most-advanced stage, then strongest
// alignment signal, then most-recent action.
export function compareByRelevance<T extends { stage: Stage; alignment: Alignment; lastAction: string }>(
  a: T,
  b: T,
): number {
  const stageDiff = STAGE_ORDER[a.stage] - STAGE_ORDER[b.stage];
  if (stageDiff !== 0) return stageDiff;
  const alignDiff = ALIGNMENT_ORDER[a.alignment] - ALIGNMENT_ORDER[b.alignment];
  if (alignDiff !== 0) return alignDiff;
  return b.lastAction.localeCompare(a.lastAction);
}
