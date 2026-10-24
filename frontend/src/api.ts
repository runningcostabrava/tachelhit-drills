// Shared typed API client. The global fetch wrapper in config.ts injects
// X-API-Key and X-User-Token on every call, so consumers get identity for
// free. New code should use this instead of raw fetch/axios; existing call
// sites migrate incrementally.
import { API_BASE } from './config';
import type { Drill } from './types';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    // Mai del cau. Una llista que es torna a demanar just després d'escriure-hi ha d'arribar del
    // servidor: servida del cau, una petició creada correctament es veu com si no existís.
    cache: 'no-store',
    headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) },
    ...init,
  });
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    let code: string | undefined;
    try {
      const body = await res.json();
      detail = body.detail || detail;
      code = body.code;
    } catch { /* non-JSON error body */ }
    // The status travels with the error. Without it a caller has to guess from the server's own
    // words — and guessing wrong turns «your session ended» into «you have no connection».
    throw Object.assign(new Error(detail), { status: res.status, code });
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

/** One step of a practice: the tool, and the sentence it works on (ADR 0002). */
export interface PracticeStep {
  id?: number;
  position?: number;
  kind: 'listen_pick' | 'write_heard' | 'say_it' | 'look_say' | 'fill_gap' | 'word_by_word' | 'script_swap' | 'pick_spelling' | 'note';
  drill_id?: number | null;
  // a «note» is the document part of a practice: a heading, a paragraph, a picture
  payload?: { text?: string; heading?: string; image_url?: string } | null;
}
export interface PracticeList {
  id: number; title: string; description?: string | null; drill_ids: string;
  created_by_user_id?: number | null; visibility?: string | null; date_created: string;
}
export interface AdminUser {
  id: number; username: string; display_name: string | null; email: string | null;
  is_admin: boolean; is_native?: boolean | null; variety?: string | null; region?: string | null;
  drills: number; takes: number; date_created: string;
}
export interface Me {
  id: number;
  email?: string | null;
  is_admin?: boolean;
  /** Speaks Tamazight from home (true), is learning it (false), or has never said (null). */
  is_native?: boolean | null;
  has_password?: boolean;
  username: string;
  display_name: string;
  variety?: string | null;
  region?: string | null;
  date_created: string;
  drills_contributed: number;
  cards_learning: number;
}

/** D'on surt el recorregut del Mètode, i què se'n pren i què no. Viatja amb cada capítol. */
export interface MethodSource {
  author: string; title: string; publisher: string; place: string; year: number;
  italian: string; based_on: string; took: string; did_not_take: string;
}

export interface MethodSentence {
  id: number;
  text_tachelhit: string | null;
  text_tachelhit_latin: string | null;
  text_catalan: string | null;
  audio_url: string | null;
  image_url: string | null;
  speaker: string | null;
  variety: string | null;
  region: string | null;
  grammar: string | null;
  topics: string | null;
  /** Paraula per paraula, com al curs de gramàtica: la frase es pot desmuntar, no només repetir. */
  gloss?: { shi: string; ca?: string | null; tif?: string | null }[] | null;
  /** La frase en tifinagh, del nostre transliterador, per posar-la sota la llatina. */
  tif?: string | null;
  /** D'on surt: una línia del manual que algú ha gravat no és una atestació de l'Atles. */
  tag?: string | null;
  from_book?: boolean;
  /** Per què aquesta frase és en aquesta secció. El tria la secció, no l'atzar. */
  why?: string | null;
  /** Les altres maneres de dir-la: la gravació de qui la diu diferent, amb el seu nom i el seu
   *  poble. No són correccions de la de dalt: són dues maneres, i totes dues són bones. */
  variants?: { id: number; text: string; tif?: string | null; audio_url: string; speaker: string | null; variety: string | null; region: string | null; is_native?: boolean | null }[];
}

export interface MethodChapterSummary {
  n: number; slug: string; name: string | null; title: string; about: string;
  /** El dibuix del capítol: diu de què va abans de llegir-ne una paraula. Viu a `/artwork`. */
  cover?: string | null;
  functions: string[]; roles: string[];
  grammar: { slug: string; title: string }[];
  topics: string[];
  sentences: number; with_voice: number; varieties: string[];
  /** Seccions amb prou frases que es puguin escoltar, de les que té. No és el teu progrés. */
  sections_ready: number; sections_total: number;
}

export interface MethodIndex { chapters: MethodChapterSummary[]; source: MethodSource }

/** La portada. Tot són comptes: la graella de drills pesa sis megues i no pot obrir l'app. */
export interface HomeData {
  library: { sentences: number; with_voice: number; speakers: number; varieties: number; videos: number; wanted: number };
  /** Una imatge per porta, de les nostres il·lustracions. Mai una imatge trobada per la xarxa. */
  covers: { method: string | null; grammar: string | null; practice: string | null; library: string | null; stories: string | null; capture: string | null };
  method: { chapters: number; written: number };
  grammar: { units: number; with_lesson: number };
  practice: { all: number; mine: number };
  you: { signed_in: boolean; name: string | null; is_admin: boolean; recordings: number };
}

/** El text d'un capítol: l'explicació, el diàleg i el vocabulari. Viu a la base de dades, no al
 *  repositori, i per això qui administra el pot corregir sense desplegar res. */
/** `drill_id` apareix quan algú ha volgut dir aquesta línia: llavors és una frase de la nostra
 *  biblioteca, amb la seva veu i el seu poble. */
export interface MethodGloss { shi: string; ca?: string | null; tif?: string | null }
export interface MethodExample {
  shi: string; ca: string; note?: string; drill_id?: number;
  /** La mateixa línia en tifinagh. La posa el servidor en servir-la; no s'escriu a mà. */
  tif?: string | null;
  /** Paraula per paraula, escrita amb el capítol: és el que converteix una frase en una lliçó. */
  gloss?: MethodGloss[];
  /** El que la biblioteca ja en té, enganxat en servir el capítol: la veu, qui la diu, la imatge. */
  audio_url?: string | null;
  image_url?: string | null;
  speaker?: string | null;
  /** D'on és qui la diu: el crèdit és d'una persona i d'un poble, i la varietat no s'amaga. */
  region?: string | null;
}
export interface MethodContent {
  intro?: string;
  sections?: {
    id: string; title: string; text?: string;
    examples?: MethodExample[];
    table?: { title: string; rows: { p: string; v: string; v_tif?: string | null }[] };
    columns?: { title: string; rows: { shi: string; ca: string; tif?: string | null }[] }[];
    /** `note`: per què aquesta fila no és com les altres — «ens falta sentir-ho» quan el buit hi
     *  és a posta, «forma derivada» quan la forma l'hem construïda nosaltres i no l'ha dita ningú. */
    numbers?: { n: number; m: string; f?: string; note?: string; m_tif?: string | null; f_tif?: string | null }[];
    /** Més a fons: el que el manual dóna per sabut i aquí s'explica. S'obre qui vol. */
    deep?: string;
    /** De quina zona del capítol és: el que cal per fer la compra, o el que l'escena deixa veure. */
    zone?: 'shop' | 'aside';
    /** Una línia que es llegeix amb la secció plegada: què hi trobaràs. */
    summary?: string;
    /** El que la NOSTRA varietat fa d'una altra manera. Això no ve del llibre. */
    ours?: string;
    /** La unitat de gramàtica de què va aquesta secció: d'aquí surten les nostres frases. */
    unit?: string;
    /** Les nostres, amb veu i imatge, dins de la secció que expliquen. */
    ours_drills?: MethodSentence[];
    ours_total?: number;
  }[];
  dialogue?: { title: string; scene?: string; turns: { who: string; shi: string; ca: string; drill_id?: number; tif?: string | null; gloss?: MethodGloss[]; audio_url?: string | null; image_url?: string | null; speaker?: string | null; region?: string | null }[] };
  practice?: {
    title: string; scene?: string;
    pattern: { who: string; shi: string; ca: string; tif?: string | null }[];
    fills: { shi: string; ca: string; qty_shi: string; qty_ca: string; tif?: string | null; qty_tif?: string | null }[];
  };
  vocabulary?: { shi: string; ca: string; audio_url?: string | null; drill_id?: number; tif?: string | null; image_url?: string | null; speaker?: string | null; region?: string | null; from_drill_id?: number }[];
  source_note?: string;
  source_pages?: string;
  updated_at?: string | null;
  updated_by?: string | null;
}

export interface MethodChapterData {
  n: number; slug: string; name: string | null; title: string; about: string;
  functions: string[]; roles: string[];
  cover?: string | null;
  topics: { slug: string; label: string }[];
  /** El text del capítol. Nul mentre no s'hagi escrit: llavors el capítol són les frases soles. */
  content: MethodContent | null;
  sections: { slug: string; title: string; sentences: MethodSentence[]; total: number; with_voice: number }[];
  also: MethodSentence[];
  sentences: number; with_voice: number;
  sections_ready: number; sections_total: number;
  /** La pràctica que comprova les funcions del capítol, si se n'ha fet cap. */
  practice_test?: { id: number; title: string; steps: number } | null;
  missing: {
    thin: { slug: string; title: string; sentences: number; with_voice: number; nowhere: boolean }[];
    voiceless: { id: number; text_tachelhit: string | null; text_catalan: string | null }[];
    voiceless_total: number;
  };
  source: MethodSource;
}

export interface CaptureCut {
  id: number;
  start: number | null;
  end: number | null;
  text_tachelhit: string | null;
  text_catalan: string | null;
  text_tachelhit_suggested: string | null;
  audio_url: string | null;
  video_url: string | null;
  image_url: string | null;
  verified: boolean;
  variety: string | null;
  author: string | null;
  tag: string | null;
  topics: string | null;
}

export interface CaptureVideo {
  source_url: string;
  title: string | null;
  channel: string | null;
  playlist: string | null;
  license: string | null;
  cuts: CaptureCut[];
  covered_from: number | null;
  covered_to: number | null;
  /** Stretches of the video nothing was taken from: the machine may have skipped something. */
  holes: { from: number; to: number; after: number; before: number }[];
  /** Cuts that step on each other: one of them may be carrying the other's words. */
  overlaps: { by: number; a: number; b: number }[];
  with_voice: number;
  verified: number;
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
  /** the sentence as this speaker says it, when their dialect's words differ from the drill's */
  text?: string | null;
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
  aiStatus: () => request<{ available: boolean; configured?: boolean; budget_ok?: boolean; budget_eur?: number; grammar_chars: number }>('/ai/status'),
  aiUsage: () => request<AiUsage>('/ai/usage'),
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
    request<{ explanation: string; draft: boolean; related: RelatedDrill[] }>(`/ai/explain/${drillId}`, { method: 'POST' }),
  drill: (id: number) => request<Drill>(`/drills/${id}`),
  /** Una frase nova. Amb el text amazic buit, neix esperant que algú la digui. */
  createDrill: (d: { text_catalan: string; text_tachelhit?: string; note?: string | null }) =>
    request<Drill>('/drills/', { method: 'POST', body: JSON.stringify(d) }),
  // --- Pràctiques: una seqüència de passos, no una llista de números (ADR 0002) ---
  /** The steps of a practice, in the order a learner meets them, plus the tools that exist. */
  practiceSteps: (testId: number) => request<{ test_id: number; steps: PracticeStep[]; kinds: Record<string, { needs_drill: boolean; asks: string }> }>(`/tests/${testId}/steps`),
  /** Rewrite them in this order. Whoever made the practice, or an admin. */
  savePracticeSteps: (testId: number, steps: PracticeStep[]) =>
    request<{ test_id: number; steps: PracticeStep[] }>(`/tests/${testId}/steps`, { method: 'PUT', body: JSON.stringify({ steps }) }),
  /** Find sentences for a practice without downloading the library. */
  searchDrills: (q: string, limit = 40) => request<Drill[]>(`/drills/?search=${encodeURIComponent(q)}&limit=${limit}`),
  /** Every practice. `mine` keeps only the ones the person may call theirs — what «les meves
   *  llistes» means, and what that screen was not doing: it listed everybody's. */
  practices: (mine = false) => request<PracticeList[]>(`/tests/${mine ? '?mine=1' : ''}`),
  /** One practice, without downloading the whole list to find it. */
  practice: (id: number) => request<PracticeList>(`/tests/${id}`),
  /** The sentences a practice's steps point at, in one request. */
  drillsByIds: (ids: number[]) => request<Drill[]>(`/drills/?ids=${ids.join(',')}`),
  updatePractice: (id: number, patch: { title?: string; description?: string }) =>
    request<PracticeList>(`/tests/${id}`, { method: 'PUT', body: JSON.stringify(patch) }),
  createPractice: (title: string) => request<PracticeList>('/tests/', { method: 'POST', body: JSON.stringify({ title, description: '', question_type: 'audio', hint_level: 'none', hint_percentage: 30, hint_tries_before_reveal: 3, passing_score: 70, drill_ids: '' }) }),
  renamePractice: (id: number, title: string) => request<PracticeList>(`/tests/${id}`, { method: 'PUT', body: JSON.stringify({ title }) }),
  deletePractice: (id: number) => request<{ detail: string }>(`/tests/${id}`, { method: 'DELETE' }),
  /** Anyone signed in: say it your way. A second version linked to the first, same Catalan. */
  addVariant: (id: number, text_tachelhit: string, note?: string) =>
    request<Drill>(`/drills/${id}/variant`, { method: 'POST', body: JSON.stringify({ text_tachelhit, note }) }),
  /** Admin: correct a sentence by hand. The speakers' own words are only ever changed here, on
   *  purpose, by a person — never by a machine pass. */
  editDrillText: (id: number, patch: { text_tachelhit?: string; text_catalan?: string }) =>
    request<Drill>(`/drills/${id}`, { method: 'PUT', body: JSON.stringify(patch) }),
  // `testId` tells the copilot which practice is open, which is what lets it read and rewrite
  // the sequence instead of only talking about it.
  aiAgent: (message: string, drillIds?: number[], history?: { role: string; text: string }[], testId?: number) =>
    request<{ answer: string; actions: { name: string; args: any; result: any }[] }>('/ai/agent', {
      method: 'POST',
      body: JSON.stringify({ message, drill_ids: drillIds ?? [], history: history ?? [], test_id: testId ?? null }),
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
  // `latest`: the version the release is built from, so an old agent can be named as old (#197)
  captureQueue: (limit = 20) => request<{ requests: CaptureQueueItem[]; agent: { online: boolean; version: string | null; latest?: string | null } }>(`/capture/queue?limit=${limit}`),
  retryCapture: (id: number) => request<{ id: number; status: string }>(`/capture/${id}/retry`, { method: 'POST' }),
  forgetCapture: (id: number) => request<{ id: number; forgotten: boolean }>(`/capture/${id}`, { method: 'DELETE' }),

  // --- AI Space health (reliability) ---
  spacesHealth: () => request<SpacesHealth>('/health/spaces'),
  wakeSpaces: (only?: string[]) =>
    request<{ waking: string[] }>(`/health/spaces/wake${only && only.length ? `?only=${only.join(',')}` : ''}`, { method: 'POST' }),

  // --- grammar course ---
  grammarUnits: () => request<{ units: GrammarUnit[]; counts: Record<string, number>; status: { running: boolean; done: number; pending: number } }>('/grammar'),
  grammarUnit: (slug: string, limit = 60) => request<GrammarUnitPage>(`/grammar/${slug}?limit=${limit}`),
  grammarRewrite: (slug: string) => request<GrammarUnitPage>(`/grammar/${slug}/rewrite`, { method: 'POST' }),
  // `hand_written`: somebody edited this lesson, so the writer leaves it alone (#187)
  grammarLesson: (slug: string) => request<{ slug: string; lesson: GrammarLesson; writing: boolean; hand_written?: boolean }>(`/grammar/${slug}/lesson`),
  putGrammarLesson: (slug: string, lesson: { intro: string; steps: LessonStep[] }) =>
    request<{ slug: string; hand_written: boolean; steps: number }>(`/grammar/${slug}/lesson`, {
      method: 'PUT', body: JSON.stringify({ lesson }),
    }),
  releaseGrammarLesson: (slug: string) =>
    request<{ slug: string; hand_written: boolean }>(`/grammar/${slug}/lesson/release`, { method: 'POST' }),
  /** The unit's «a fons» level: same shape as the unit page, written on first open. */
  grammarDeep: (slug: string, limit = 60) => request<GrammarUnitPage>(`/grammar/${slug}/deep?limit=${limit}`),
  grammarDeepRewrite: (slug: string) => request<GrammarUnitPage>(`/grammar/${slug}/deep/rewrite`, { method: 'POST' }),
  grammarWishlist: () => request<{ units: GrammarWishUnit[] }>('/grammar/wishlist'),
  /** Admin: who is in this library, and who administers it. */
  adminUsers: (q?: string) => request<{ users: AdminUser[] }>(`/admin/users${q ? `?q=${encodeURIComponent(q)}` : ''}`),
  setAdmin: (userId: number, is_admin: boolean) =>
    request<{ id: number; username: string; is_admin: boolean }>(`/admin/users/${userId}/admin`, { method: 'POST', body: JSON.stringify({ is_admin }) }),
  /** Admin: ask for every sentence the library cannot say out loud, in one pass. */
  askForEveryMissingVoice: () => request<{ asked: number; already_asked: number; with_a_take: number }>('/drills/voice-wanted/missing', { method: 'POST', body: JSON.stringify({ include_synthetic: true }) }),
  /** Ask our speakers to say this sentence out loud; it goes to the top of «Veus». */
  // --- El Mètode: deu capítols fets amb la nostra biblioteca (ADR 0003) ---
  methodIndex: () => request<MethodIndex>('/method/'),
  /** El que hi ha a casa: les portes i quant hi ha darrere de cadascuna. Només comptes. */
  home: () => request<HomeData>('/home'),
  methodChapter: (slug: string) => request<MethodChapterData>(`/method/${encodeURIComponent(slug)}`),
  /** La frase nostra darrere una línia del capítol, creant-la el primer cop que algú la vol dir. */
  methodLineDrill: (slug: string, kind: 'example' | 'turn' | 'vocabulary', index: number, section?: string) =>
    request<{ drill_id: number; created: boolean; drill: Drill }>(
      `/method/${encodeURIComponent(slug)}/line`,
      { method: 'POST', body: JSON.stringify({ kind, index, section: section ?? null }) }),
  /** Desa el text d'un capítol. Només qui administra. */
  saveMethodContent: (slug: string, body: MethodContent) =>
    request<{ slug: string; ok: boolean; sections: number }>(
      `/method/${encodeURIComponent(slug)}/content`,
      { method: 'PUT', body: JSON.stringify(body) }),
  /** La frase darrere una fila d'una taula de formes: la crea el primer cop i obre la gravadora. */
  grammarRowDrill: (slug: string, step: number, row: number, deep = false) =>
    request<{ drill_id: number; created: boolean; drill: Drill }>(`/grammar/${slug}/row`, {
      method: 'POST', body: JSON.stringify({ step, row, deep }),
    }),
  askForVoice: (drillId: number, wanted = true) => request<{ id: number; voice_wanted: boolean; voice_wanted_by: string | null }>(`/drills/${drillId}/voice-wanted`, { method: 'POST', body: JSON.stringify({ wanted }) }),
  petitions: (kind: 'open' | 'synthetic' | 'voiceless' | 'untranscribed' | 'aitmraw', limit = 40) => request<{ items: PetitionItem[]; total: number }>(`/petitions?kind=${kind}&limit=${limit}`),
  addPetition: (text_catalan: string, note: string | null) => request<Drill>('/petitions', { method: 'POST', body: JSON.stringify({ text_catalan, note }) }),
  lessonProposals: (slug: string) => request<LessonProposal[]>(`/grammar/${slug}/proposals`),
  proposeLessonChange: (slug: string, step: number, text: string, kind: 'text' | 'note' = 'text') => request<{ id: number; status: string }>(`/grammar/${slug}/proposals`, { method: 'POST', body: JSON.stringify({ step, text, kind }) }),
  decideProposal: (id: number, accept: boolean) => request<{ id: number; status: string }>(`/grammar/proposals/${id}/decide`, { method: 'POST', body: JSON.stringify({ accept }) }),
  userPage: (username: string) => request<UserPublicPage>(`/users/by-name/${encodeURIComponent(username)}`),
  drillVariants: (id: number) => request<{ original: Drill; variants: Drill[] }>(`/drills/${id}/variants`),
  // One word, said by a person: a recording we already have and the span the word sits in. No new
  // sound files -- the player seeks there and stops at the end of the word.
  wordAudio: (word: string, limit = 6) =>
    request<{ word: string; count: number; clips: WordClip[] }>(`/words/audio?word=${encodeURIComponent(word)}&limit=${limit}`),
  wordAlignStatus: () => request<{ running: boolean; done: number; words: number; failed: number; stored: number; recordings: number }>('/words/align/status'),
  runWordAlign: (limit = 200, redo = false) =>
    request<{ started: boolean }>(`/words/align/run?limit=${limit}&redo=${redo}`, { method: 'POST' }),
  stories: () => request<{ stories: Story[] }>('/stories'),
  story: (slug: string) => request<StoryPage>(`/stories/${encodeURIComponent(slug)}`),
  // What the project owes to other people, read from the repository's own docs/CREDITS.md
  credits: () => request<{ markdown: string; source: string }>('/credits'),
  practiceCollections: () => request<PracticeCollections>('/practice/collections'),
  practiceSession: (query: string) => request<{ drills: Drill[]; cards: PracticeCard[] }>(`/practice/session?${query}`),
  reviewsDue: (limit = 10) => request<Drill[]>(`/reviews/due?limit=${limit}`),
  reviewGrade: (drillId: number, grade: number) => request<unknown>(`/reviews/${drillId}/grade`, { method: 'POST', body: JSON.stringify({ grade }) }),

  // --- multi-speaker recordings (many takes per drill) ---
  drillRecordings: (drillId: number) =>
    request<Recording[]>(`/drills/${drillId}/recordings`),
  deleteRecording: (recordingId: number) =>
    request<{ deleted: number }>(`/recordings/${recordingId}`, { method: 'DELETE' }),
  updateRecording: (recordingId: number, body: { text?: string; variety?: string; region?: string }) =>
    request<{ id: number; text: string | null; variety: string | null; region: string | null }>(`/recordings/${recordingId}`, { method: 'PATCH', body: JSON.stringify(body) }),

  // --- Berber transliteration (phone-Latin -> Tifinagh / clean Latin / key) ---
  transliterate: (text: string) =>
    request<TransliterationForms>(`/transliterate?text=${encodeURIComponent(text)}`),

  // --- one drill's picture: Gemini draws the sentence in the flashcard style; `hint` says what to draw ---
  /** What a video gave us: its cuts in time order, plus the holes and the overlaps between them. */
  captureVideo: (url: string) => request<CaptureVideo>(`/capture/video?url=${encodeURIComponent(url)}`),
  /** Cut this sentence's clip again from the ORIGINAL video — the only way to make a cut longer. */
  recutDrill: (drillId: number, start_time: number, end_time: number) =>
    request<{ id: number; video_url: string; image_url: string | null; video_start_time: number; video_end_time: number; kept_drawing: boolean }>(
      `/drills/${drillId}/recut`, { method: 'POST', body: JSON.stringify({ start_time, end_time }) }),
  /** Change only the fields you pass. The server leaves everything else exactly as it was. */
  updateDrill: (drillId: number, patch: Record<string, unknown>) =>
    request<Drill>(`/drills/${drillId}`, { method: 'PUT', body: JSON.stringify(patch) }),
  deleteDrill: (drillId: number) =>
    request<{ detail?: string }>(`/drills/${drillId}`, { method: 'DELETE' }),
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
  updateMe: (patch: { display_name?: string; variety?: string | null; region?: string | null; is_native?: boolean }) =>
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
  /** Change the handle people see («@pablo»). Nothing you contributed is tied to the name. */
  changeUsername: (username: string) => request<AuthUser>('/auth/username', { method: 'POST', body: JSON.stringify({ username }) }),
  changePassword: (old_password: string, new_password: string) =>
    request<{ ok: boolean }>('/auth/password', { method: 'POST', body: JSON.stringify({ old_password, new_password }) }),
  /** `mail: false` means this server sends no e-mail: ask an admin for a code instead. */
  forgotPassword: (login: string) => request<{ ok: boolean; mail?: boolean }>('/auth/forgot', { method: 'POST', body: JSON.stringify({ login }) }),
  adminMailGet: () => request<MailSettings>('/admin/mail'),
  adminMailSet: (settings: Record<string, string>) => request<MailSettings>('/admin/mail', { method: 'POST', body: JSON.stringify({ settings }) }),
  adminMailTest: (to?: string) => request<{ sent_to: string }>('/admin/mail/test', { method: 'POST', body: JSON.stringify({ to: to || null }) }),
  adminResetCode: (login: string) => request<{ username: string; email: string; code: string; expires_in_hours: number; mailed: boolean }>('/auth/admin-reset-code', { method: 'POST', body: JSON.stringify({ login }) }),
  /** `login` is the e-mail OR the user name: an account with no address is recovered by code. */
  resetPassword: (login: string, code: string, new_password: string, device?: string) =>
    request<AuthUser & { token: string }>('/auth/reset', { method: 'POST', body: JSON.stringify({ login, code, new_password, device }) }),
};

/** A drill that shares words with the one being explained: playable in place, with its picture for the card. */
export interface RelatedDrill { id: number; text_catalan?: string; text?: string; words: string[]; audio_url?: string | null; audio_tts_shi_url?: string | null; image_url?: string | null; region?: string | null }
export interface GrammarUnit { slug: string; title: string; level: number }
/** A drill as a lesson quotes it: both texts plus its picture and a voice (the speaker's when recorded). */
/** `gloss`: the library's word-by-word reading of the sentence, refreshed on every serve.
 *  `why`: what this sentence shows of THIS unit's point (stored per sentence and unit). */
export interface LessonExample { id: number; shi: string; ca: string; image_url?: string | null; audio_url?: string | null; recorded: boolean; author?: string | null; region?: string | null; origin?: string | null; focus?: string | null; gloss?: { shi: string; ca: string; tif?: string | null }[] | null; why?: string | null; tif?: string | null; source_url?: string | null; source_channel?: string | null;
  /** Les altres maneres de dir-la: la gravació de qui la diu diferent, amb el seu nom i el seu poble. */
  variants?: { id: number; text: string; tif?: string | null; audio_url: string; speaker: string | null; variety: string | null; region: string | null; is_native?: boolean | null }[] }
export type LessonStep =
  | { type: 'explain'; title: string; text: string; examples: LessonExample[] }
  /** `drill_ids`: la frase de la biblioteca darrere cada fila, quan algú ja l'ha volguda dir. */
  | { type: 'pattern'; title: string; rows: string[][]; drill_ids?: Record<string, number> }
  | { type: 'quiz'; kind: 'meaning' | 'listen' | 'picture'; question: string; options: string[]; answer: number; example: LessonExample }
  | { type: 'tip'; text: string }
  | { type: 'dialect'; text: string }
  | { type: 'end' };
/** `writing`: a new lesson is being written right now; ask again in a few seconds. `stale`: what you have is the
 *  previous one meanwhile. */
export interface GrammarLesson { intro: string; steps: LessonStep[]; study?: string; error?: string; writing?: boolean; stale?: boolean }
/** `practice`: the ids the unit's test is made of (real sentences only: no single words, no conjugation lists). */
export interface GrammarUnitPage extends GrammarUnit { lesson: GrammarLesson; total: number; practice: number[]; drills: Drill[] }
/** Pràctica: how the library is offered for practice, and what a session card needs beyond the drill. */
export interface PracticeCollections {
  days: { day: string; speaker: string; count: number }[];
  topics: { slug: string; label: string; count: number }[];
  units: { slug: string; title: string; level: number; count: number }[];
  /** `count` is the steps it holds; `cover` is its first illustrated sentence, if any. */
  lists: { id: number; title: string; count: number; cover?: string | null }[];
  videos: { title: string; url: string | null; count: number }[];
  people: { name: string; count: number }[];
  tags: { tag: string; count: number }[];
}
/** Where one word is spoken: the recording, and the seconds it sits between. `source`:
 *  'library' = one of our speakers, with a name; 'tosd' = the open corpus, anonymous. */
export interface WordClip {
  word: string; drill_id: number; audio_url: string; start: number; end: number;
  speaker: string | null; source: string; sentence: string | null; meaning: string | null;
}
/** A whole story or song: a group of drills from one source, put back in the order they are
 *  spoken. `missing_words` = lines that can be heard but not read yet (#189). */
export interface Story {
  slug: string; title: string; lines: number; written: number; missing_words: number; voiced: number;
  cover: string | null; video_url: string | null; source_url: string | null;
  channel: string | null; speaker: string | null;
}
export interface StoryPage extends Story { drills: Drill[] }
export interface PracticeTip { sound: string; label: string; found: string; tip: string }
export interface PracticeCard { speaker: string; origin: string; day: string | null; tips: PracticeTip[]; highlights: string[] }
export interface PronunciationWord { word: string; ok: boolean; heard: string | null }
// «parla» (record and be scored) was dropped on 2026-10-22: see PracticeSession.tsx.
export type PracticeMode = 'escolta' | 'auto';
/** The mail sender as the app has it; the password itself is never sent back. */
export interface MailSettings { SMTP_HOST: string; SMTP_PORT: string; SMTP_USER: string; SMTP_FROM: string; has_password: boolean; ready: boolean; from_app: Record<string, boolean>; MAIL_API_PROVIDER?: string; has_api_key?: boolean }
/** A person's public page: who they are and what they gave the library. */
export interface ContributionDrill { id: number; text_tachelhit?: string | null; text_catalan?: string | null; audio_url?: string | null; image_url?: string | null; region?: string | null; variety?: string | null; tag?: string | null; variant_of?: number | null; verified?: boolean | null; date_created?: string | null }
export interface Contributions { counts: { drills: number; petitions: number; variants: number; takes: number; proposals_accepted: number; proposals_pending: number }; drills: ContributionDrill[]; takes: { id: number; audio_url: string; text: string | null; variety: string | null; region: string | null; date_created: string; drill: ContributionDrill }[] }
export interface UserPublicPage extends Contributions { username: string; display_name: string; variety: string | null; region: string | null; since: string | null }
/** Veus: a drill the community can record (a petition, a synthetic-only drill, or a wishlist sentence). */
export interface PetitionItem { drill: Drill; units: string[]; level: number; requested_by: string | null; note: string | null }
export interface LessonProposal { id: number; slug: string; step: number; kind: 'text' | 'note'; text: string; display_name: string | null; region: string | null; status: string; created_at: string }
/** A unit in the recording wishlist: how many of its sentences carry an Aït Mraw voice, and the ones worth recording. */
export interface GrammarWishUnit extends GrammarUnit { total: number; aitmraw_voiced: number; wanted: Drill[] }

export interface AiUsage {
  today: { used: number; limit: number | null; remaining: number | null };
  month: { spent_eur: number; budget_eur: number; remaining_eur: number; resets_at: string; by_feature?: Record<string, { calls: number; eur: number }> };
  available: boolean;
}

export interface AuthUser {
  username: string;
  display_name: string;
  email: string | null;
  variety: string | null;
  region: string | null;
  is_admin: boolean;
  has_password: boolean;
}
