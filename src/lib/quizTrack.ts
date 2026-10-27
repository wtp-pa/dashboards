/**
 * Anonymous usage counts for /vote2026 via GoatCounter events (no cookies,
 * no answers, no IPs stored). No-op when the GoatCounter script isn't on the
 * page, i.e. PUBLIC_GOATCOUNTER_CODE unset at build or blocked by the browser.
 */

export interface QuizEvent {
  event: 'start' | 'complete' | 'reveal' | 'share';
  mode?: 'short' | 'long';
  race_id?: string | null;
  source?: string | null;
}

declare global {
  interface Window {
    goatcounter?: { count: (o: { path: string; title?: string; event?: boolean }) => void };
  }
}

export function track(e: QuizEvent): void {
  // Each part becomes its own event so the GoatCounter dashboard shows plain
  // totals per step, per source, per length, and per district.
  const parts = [
    `vote2026-${e.event}`,
    e.source && `vote2026-${e.event}-src-${e.source}`,
    e.mode && `vote2026-${e.event}-${e.mode}`,
    e.event === 'complete' && `vote2026-complete-${e.race_id || 'statewide'}`,
  ].filter(Boolean) as string[];
  try {
    for (const path of parts) window.goatcounter?.count({ path, event: true });
  } catch {
    // Never break the quiz on analytics.
  }
}
