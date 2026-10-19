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

export interface CorpusSource {
  source_url: string;
  title: string | null;
  channel: string | null;
  playlist: string | null;
  license: string | null;
  drills: number;
  with_video: number;
  with_audio: number;
  verified: number;
  varieties: string[];
  tags: string[];
  from_s: number | null;
  to_s: number | null;
  first_id: number;
}

export interface CorpusSources {
  total_drills: number;
  from_sources: number;
  without_source: number;
  channels: number;
  videos: CorpusSource[];
}

// Speaker verification queue (recorded drills whose text a speaker still has to confirm)
export interface VerifyItem extends Drill {
  reason: 'differs' | 'contested' | 'empty' | 'subtitle' | string;
  heard: string[]; // machine readings offered as one-tap answers (never gold)
}
export interface VerifyQueue {
  total: number;
  counts: Record<string, number>;
  labels: Record<string, string>;
  drills: VerifyItem[];
}

export interface Me {
  email?: string | null;
  is_admin?: boolean;
  has_password?: boolean;
  username: string;
  display_name: string;
  variety?: string | null;
  region?: string | null;
  date_created: string;
  drills_contributed: number;
  cards_learning: number;
}

export interface CaptureStatus {
  id: number;
  status: string;                 // pending | claimed | processing | done | failed
  url: string;
  job_id: number | null;
  job_status: string | null;
  drills_created: number[] | null;
  error: string | null;
}

export interface CaptureQueueItem {
  id: number;
  url: string;
  tag: string | null;
  variety: string | null;
  status: string;                 // pending | claimed | processing | done | failed
  job_status: string | null;
  drills_created: number | null;
  error: string | null;
  created_at: string | null;
  claimed_at: string | null;
}

export interface SpaceState {
  state: 'up' | 'waking' | 'down' | 'private_or_missing' | 'unset';
  id?: string;
  code?: number;
}
export type SpacesHealth = Record<string, SpaceState>;

export interface Recording {
  id: number;
  audio_url: string;
  variety?: string | null;
  region?: string | null;
  speaker?: string | null;
  license?: string | null;
  date_created?: string;
}

export interface TransliterationForms {
  input: string;
  clean_latin: string;
  tifinagh: string;
  key: string;
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
  corpusSources: () => request<CorpusSources>('/corpus/sources'),
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
  verifyQueue: (reason?: string, limit = 100, offset = 0) =>
    request<VerifyQueue>(`/corpus/verify-queue?limit=${limit}&offset=${offset}${reason ? `&reason=${encodeURIComponent(reason)}` : ''}`),
  resolveDrill: (drillId: number, text_tachelhit?: string) =>
    request<Drill>(`/drills/${drillId}/resolve`, {
      method: 'POST',
      body: JSON.stringify({ text_tachelhit: text_tachelhit ?? null }),
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
  aiExplainDrill: (drillId: number) =>
    request<{ explanation: string; draft: boolean; related: { id: number; text_catalan?: string; text?: string; words: string[] }[] }>(`/ai/explain/${drillId}`, { method: 'POST' }),
  aiAgent: (message: string, drillIds?: number[], history?: { role: string; text: string }[]) =>
    request<{ answer: string; actions: { name: string; args: any; result: any }[] }>('/ai/agent', {
      method: 'POST',
      body: JSON.stringify({ message, drill_ids: drillIds ?? [], history: history ?? [] }),
    }),
  aiSuggestTranslation: (drillId: number) =>
    request<{ field: string; suggestion: string }>(`/ai/suggest-translation/${drillId}`, { method: 'POST' }),

  // --- autonomous local capture (queue a URL for your local agent) ---
  captureRequest: (url: string, opts?: { tag?: string; language?: string; audio_only?: boolean; apply_correction?: boolean; variety?: string }) =>
    request<{ request_id: number; status: string }>('/capture/request', {
      method: 'POST',
      body: JSON.stringify({ url, ...(opts || {}) }),
    }),
  captureStatus: (id: number) => request<CaptureStatus>(`/capture/${id}`),
  captureAgent: () => request<{ online: boolean; last_seen: string | null; version: string | null }>('/capture/agent'),
  captureQueue: (limit = 20) => request<{ requests: CaptureQueueItem[]; agent: { online: boolean; version: string | null } }>(`/capture/queue?limit=${limit}`),

  // --- AI Space health (reliability) ---
  spacesHealth: () => request<SpacesHealth>('/health/spaces'),
  wakeSpaces: (only?: string[]) =>
    request<{ waking: string[] }>(`/health/spaces/wake${only && only.length ? `?only=${only.join(',')}` : ''}`, { method: 'POST' }),

  // --- multi-speaker recordings (many takes per drill) ---
  drillRecordings: (drillId: number) =>
    request<Recording[]>(`/drills/${drillId}/recordings`),
  deleteRecording: (recordingId: number) =>
    request<{ deleted: number }>(`/recordings/${recordingId}`, { method: 'DELETE' }),

  // --- Berber transliteration (phone-Latin -> Tifinagh / clean Latin / key) ---
  transliterate: (text: string) =>
    request<TransliterationForms>(`/transliterate?text=${encodeURIComponent(text)}`),

  // --- one drill's picture: Gemini draws the sentence in the flashcard style; `hint` says what to draw ---
  illustrateDrill: (drillId: number, hint?: string) =>
    request<{ image_url: string; photographer: string }>(`/generate-image/${drillId}`, {
      method: 'POST', body: JSON.stringify({ use_ai: true, search_query: hint?.trim() || null }),
    }),

  // --- bulk image fill (background job) ---
  imageFillStart: (onlyDepictable = true) =>
    request<{ status: string }>(`/images/fill-missing?only_depictable=${onlyDepictable}`, { method: 'POST' }),
  imageFillStatus: () =>
    request<ImageFillStatus>('/images/fill-missing/status'),
  imageFillStop: () =>
    request<{ status: string }>('/images/fill-missing/stop', { method: 'POST' }),

  // --- identity ---
  register: (username: string, display_name?: string | null, variety?: string | null, region?: string | null) =>
    request<{ username: string; display_name: string; token: string }>('/users/register', {
      method: 'POST',
      body: JSON.stringify({ username, display_name, variety, region }),
    }),
  // Returns null when the stored token is invalid (401) so callers can log out
  me: async (): Promise<Me | null> => {
    const res = await fetch(`${API_BASE}/users/me`);
    if (res.status === 401) return null;
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  },
  updateMe: (patch: { display_name?: string; variety?: string | null; region?: string | null }) =>
    request<{ username: string; display_name: string; variety: string | null; region: string | null }>('/users/me', {
      method: 'PUT',
      body: JSON.stringify(patch),
    }),
  varieties: () => request<{ code: string; label: string }[]>('/varieties'),

  // --- accounts (e-mail + password on top of the token identity) ---
  signup: (body: { email: string; password: string; username: string; display_name?: string | null; variety?: string | null; region?: string | null; device?: string }) =>
    request<AuthUser & { token: string }>('/auth/signup', { method: 'POST', body: JSON.stringify(body) }),
  login: (login: string, password: string, device?: string) =>
    request<AuthUser & { token: string }>('/auth/login', { method: 'POST', body: JSON.stringify({ login, password, device }) }),
  logout: () => request<{ ok: boolean }>('/auth/logout', { method: 'POST', body: '{}' }),
  attachCredentials: (email: string, password: string) =>
    request<AuthUser>('/auth/attach', { method: 'POST', body: JSON.stringify({ email, password }) }),
  changePassword: (old_password: string, new_password: string) =>
    request<{ ok: boolean }>('/auth/password', { method: 'POST', body: JSON.stringify({ old_password, new_password }) }),
  forgotPassword: (email: string) => request<{ ok: boolean }>('/auth/forgot', { method: 'POST', body: JSON.stringify({ email }) }),
  resetPassword: (email: string, code: string, new_password: string, device?: string) =>
    request<AuthUser & { token: string }>('/auth/reset', { method: 'POST', body: JSON.stringify({ email, code, new_password, device }) }),
};

export interface AuthUser {
  username: string;
  display_name: string;
  email: string | null;
  variety: string | null;
  region: string | null;
  is_admin: boolean;
  has_password: boolean;
}
