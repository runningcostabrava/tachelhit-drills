// Canonical Drill shape shared across the app; mirrors backend/schemas.py.
// All content/media fields are nullable server-side, so they are optional here.
export interface Drill {
  id: number;
  text_catalan?: string;
  text_tachelhit?: string;
  text_arabic?: string;
  audio_url?: string;
  audio_tts_url?: string;
  audio_tts_shi_url?: string; // synthesized Tachelhit voice (fallback when no recording)
  video_url?: string;
  image_url?: string;
  /** attribution of a free-licensed picture: «title · author · licence · source» */
  image_credit?: string | null;
  tag?: string;
  author?: string;
  date_created: string;
  updated_at?: string | null;
  /** Whose sentence it is. Empty means the library's, which is the administrators'. */
  created_by_user_id?: number | null;
  video_start_time?: number;
  video_end_time?: number;
  is_correction_dataset?: boolean;
  is_local?: boolean; // client-side marker for drills created offline
  // Documentation / variation layer
  text_tachelhit_latin?: string;
  glosses?: string;               // word by word (JSON: [{shi, tif, ca}]), see components/WordGloss.tsx
  text_tachelhit_suggested?: string; // machine/AI draft (not gold)
  draft_check?: string; // JSON verdict of the draft's meaning check (yes/roughly/no)
  topics?: string;        // subject catalogue: comma-separated slugs (see utils/topics.ts)
  topics_source?: string; // 'auto' | 'owner'
  grammar?: string;        // grammar course units: comma-separated slugs (see GrammarPage)
  grammar_source?: string; // 'auto' | 'owner'
  text_catalan_suggested?: string;
  /** Les propostes de màquina amb la seva procedència, en JSON: [{text, model, llengua, de}]. */
  esborranys?: string | null;
  variety?: string;
  region?: string;
  speaker?: string;
  source_url?: string;
  source_title?: string;
  source_channel?: string;
  source_playlist?: string;
  license?: string;
  verified?: boolean;
}
