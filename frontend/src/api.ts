// Shared typed API client. The global fetch wrapper in config.ts injects
// X-API-Key and X-User-Token on every call, so consumers get identity for
// free. New code should use this instead of raw fetch/axios; existing call
// sites migrate incrementally.
import { API_BASE } from './config';
import type { Drill } from './types';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) },
    ...init,
  });
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      detail = (await res.json()).detail || detail;
    } catch { /* non-JSON error body */ }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

export interface ReviewStats {
  total_drills: number;
  new: number;
  due: number;
  learning: number;
}

export interface ReviewStreak {
  streak_days: number;
  reviews_today: number;
  reviews_week: number;
  active_days: number;
}

export interface CorpusStats {
  total_drills: number;
  with_audio: number;
  with_video: number;
  with_latin_script: number;
  verified: number;
  by_variety: Record<string, number>;
  by_region: Record<string, number>;
}

export interface Me {
  username: string;
  display_name: string;
  date_created: string;
  drills_contributed: number;
  cards_learning: number;
}

export interface ImageFillStatus {
  running: boolean;
  total: number;
  done: number;
  failed: number;
  skipped: number;
  current: string;
}

export const api = {
  // --- spaced repetition ---
  dueReviews: (limit = 30) => request<Drill[]>(`/reviews/due?limit=${limit}`),
  gradeReview: (drillId: number, grade: number) =>
    request<{ next_due: string; interval_days: number }>(`/reviews/${drillId}/grade`, {
      method: 'POST',
      body: JSON.stringify({ grade }),
    }),
  reviewStats: () => request<ReviewStats>('/reviews/stats'),
  reviewStreak: () => request<ReviewStreak>('/reviews/streak'),

  // --- corpus ---
  corpusStats: () => request<CorpusStats>('/corpus/stats'),
  corpusSearch: (params: { q?: string; variety?: string; region?: string; limit?: number; offset?: number }) => {
    const sp = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== '') sp.set(k, String(v));
    });
    return request<Drill[]>(`/corpus/search?${sp.toString()}`);
  },
  verifyDrill: (drillId: number, verified: boolean) =>
    request<{ verified: boolean }>(`/drills/${drillId}/verify`, {
      method: 'POST',
      body: JSON.stringify({ verified }),
    }),
  corpusGapsSummary: () =>
    request<{ total: number; gaps: { kind: string; label: string; count: number }[] }>('/corpus/gaps'),
  corpusGapDrills: (kind: string, limit = 100) =>
    request<{ kind: string; drills: Drill[] }>(`/corpus/gaps?kind=${encodeURIComponent(kind)}&limit=${limit}`),

  // --- AI grammar tutor ---
  aiStatus: () => request<{ available: boolean; grammar_chars: number }>('/ai/status'),
  aiAsk: (question: string, drillId?: number, history?: { role: string; text: string }[]) =>
    request<{ answer: string; used_drill: boolean }>('/ai/ask', {
      method: 'POST',
      body: JSON.stringify({ question, drill_id: drillId ?? null, history: history ?? [] }),
    }),
  aiAnalyzeDrill: (drillId: number) =>
    request<{ analysis: string }>(`/ai/analyze-drill/${drillId}`, { method: 'POST' }),
  aiReviewDrill: (drillId: number) =>
    request<{ review: string }>(`/ai/review-drill/${drillId}`, { method: 'POST' }),
  aiAgent: (message: string, drillIds?: number[], history?: { role: string; text: string }[]) =>
    request<{ answer: string; actions: { name: string; args: any; result: any }[] }>('/ai/agent', {
      method: 'POST',
      body: JSON.stringify({ message, drill_ids: drillIds ?? [], history: history ?? [] }),
    }),
  aiSuggestTranslation: (drillId: number) =>
    request<{ field: string; suggestion: string }>(`/ai/suggest-translation/${drillId}`, { method: 'POST' }),

  // --- bulk image fill (background job) ---
  imageFillStart: (onlyDepictable = true) =>
    request<{ status: string }>(`/images/fill-missing?only_depictable=${onlyDepictable}`, { method: 'POST' }),
  imageFillStatus: () =>
    request<ImageFillStatus>('/images/fill-missing/status'),
  imageFillStop: () =>
    request<{ status: string }>('/images/fill-missing/stop', { method: 'POST' }),

  // --- identity ---
  register: (username: string, display_name?: string | null) =>
    request<{ username: string; display_name: string; token: string }>('/users/register', {
      method: 'POST',
      body: JSON.stringify({ username, display_name }),
    }),
  // Returns null when the stored token is invalid (401) so callers can log out
  me: async (): Promise<Me | null> => {
    const res = await fetch(`${API_BASE}/users/me`);
    if (res.status === 401) return null;
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  },
};
