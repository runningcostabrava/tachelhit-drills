// Canonical Drill shape shared across the app; mirrors backend/schemas.py.
// All content/media fields are nullable server-side, so they are optional here.
export interface Drill {
  id: number;
  text_catalan?: string;
  text_tachelhit?: string;
  text_arabic?: string;
  audio_url?: string;
  audio_tts_url?: string;
  video_url?: string;
  image_url?: string;
  tag?: string;
  author?: string;
  date_created: string;
  video_start_time?: number;
  video_end_time?: number;
  is_correction_dataset?: boolean;
  is_local?: boolean; // client-side marker for drills created offline
  // Documentation / variation layer
  text_tachelhit_latin?: string;
  variety?: string;
  region?: string;
  speaker?: string;
  source_url?: string;
  license?: string;
  verified?: boolean;
}
