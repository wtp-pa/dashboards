/**
 * Thin Supabase layer for /quiz. Everything degrades to a no-op when the
 * PUBLIC_SUPABASE_* env vars aren't set, so the quiz still works (all races
 * visible, no tracking) on local builds or if Supabase is down.
 */
import { createClient, type SupabaseClient } from '@supabase/supabase-js';

const URL = import.meta.env.PUBLIC_SUPABASE_URL as string | undefined;
const KEY = import.meta.env.PUBLIC_SUPABASE_PUBLISHABLE_KEY as string | undefined;

let client: SupabaseClient | null = null;
export function supabase(): SupabaseClient | null {
  if (!URL || !KEY) return null;
  client ??= createClient(URL, KEY);
  return client;
}

export interface QuizEvent {
  event: 'start' | 'complete' | 'reveal';
  mode?: 'short' | 'long';
  race_id?: string | null;
  answered?: number;
  source?: string | null;
}

export function track(e: QuizEvent): void {
  const sb = supabase();
  if (!sb) return;
  // Fire and forget — never block or break the quiz on analytics.
  sb.from('quiz_events').insert(e).then(() => {}, () => {});
}

/** race_id → visible. Races with no row are visible. */
export async function loadVisibility(): Promise<Record<string, boolean>> {
  const sb = supabase();
  if (!sb) return {};
  const { data, error } = await sb.from('quiz_race_settings').select('race_id, visible');
  if (error || !data) return {};
  return Object.fromEntries(data.map((r) => [r.race_id, r.visible]));
}
