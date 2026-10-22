from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class Drill(Base):
    __tablename__ = "drills"

    id = Column(Integer, primary_key=True, index=True)
    date_created = Column(DateTime, default=datetime.utcnow, nullable=False)
    tag = Column(String, nullable=True)
    author = Column(String, nullable=True)
    text_catalan = Column(String, nullable=True)
    text_tachelhit = Column(String, nullable=True)
    text_arabic = Column(String, nullable=True)
    audio_url = Column(String, nullable=True)
    audio_tts_url = Column(String, nullable=True)  # Generated TTS for Catalan text
    audio_tts_shi_url = Column(String, nullable=True)  # Synthesized Tachelhit voice (fallback when no recording)
    voice_wanted = Column(Boolean, nullable=True, default=False)   # somebody asked a native speaker to say this one
    voice_wanted_by = Column(String, nullable=True)                # who asked, so the speakers know who is waiting
    video_url = Column(String, nullable=True)
    image_url = Column(String, nullable=True)
    image_credit = Column(String, nullable=True)  # «title · author · licence · source» for a free-licensed picture
    is_correction_dataset = Column(Boolean, default=False, nullable=False)
    # Timestamp fields for video segments
    video_start_time = Column(Float, nullable=True)  # Start time in seconds
    video_end_time = Column(Float, nullable=True)    # End time in seconds
    # --- Documentation / variation layer (auditor Phase 2) ---
    text_tachelhit_latin = Column(String, nullable=True)  # Latin romanization
    # Script-independent phonemic key (de-geminated, schwa-stripped) computed
    # from the Latin/Tifinagh form via transliteration.phonemic_key. Lets search
    # and dedup match across spellings/scripts. Populated on create/update.
    text_key = Column(String, nullable=True, index=True)
    # Machine/AI drafts — kept SEPARATE from the human-attested gold fields
    # above so an approximation (often a different variety) never overwrites
    # what a real speaker collected.
    text_tachelhit_suggested = Column(String, nullable=True)
    text_catalan_suggested = Column(String, nullable=True)
    # Meaning check of text_tachelhit_suggested (draft_check.py): JSON with the draft
    # checked, its blind back-translation, verdict yes/roughly/no, confidence, note.
    draft_check = Column(String, nullable=True)
    topics = Column(String, nullable=True)         # subject catalogue, comma-separated slugs (topics.py)
    topics_source = Column(String, nullable=True)  # 'auto' (Gemini) | 'owner' (set by hand)
    grammar = Column(String, nullable=True)         # grammar course units, comma-separated slugs (grammar.py)
    grammar_source = Column(String, nullable=True)  # 'auto' | 'owner'
    # A petition: a learner asked how to say this (Catalan only); a native speaker's recording with
    # their own words fills text_tachelhit (see /petitions and add_recording)
    requested_by = Column(String, nullable=True)
    requested_note = Column(Text, nullable=True)
    # A variant: the same sentence as another speaker says it (their words, their voice, their town),
    # created from a take whose own words differ from the drill's; the original lists its variants
    variant_of = Column(Integer, ForeignKey("drills.id"), nullable=True, index=True)
    # Word by word: JSON list of {"shi": word as written, "tif": its Tifinagh, "ca": the Catalan
    # word(s) it answers to or "—"}; written by the gloss pass, shown under the sentence
    glosses = Column(Text, nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # contributor attribution
    variety = Column(String, nullable=True)   # e.g. "tashelhit", "central-atlas", "tarifit"
    region = Column(String, nullable=True)    # e.g. "Souss", "Tafraout", "diaspora-BCN"
    speaker = Column(String, nullable=True)   # speaker/contributor label (with consent)
    source_url = Column(String, nullable=True)  # provenance: where the content came from
    source_title = Column(String, nullable=True)     # e.g. the YouTube video title
    source_channel = Column(String, nullable=True)   # author/channel to credit
    source_playlist = Column(String, nullable=True)  # course/playlist the video belongs to
    license = Column(String, nullable=True)     # e.g. "CC-BY-SA", "personal", "unknown"
    # --- Contribution review (auditor Phase 3): NULL/False = unreviewed ---
    verified = Column(Boolean, nullable=True)
    verified_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    # Delta sync (P4.3): naive UTC like date_created; NULL on legacy rows that
    # pre-date the column (the startup column-sync adds it without a default).
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=True, index=True)

class Test(Base):
    __tablename__ = "tests"

    id = Column(Integer, primary_key=True, index=True)
    date_created = Column(DateTime, default=datetime.utcnow, nullable=False)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)

    # Configuration
    question_type = Column(String, nullable=False)  # "text_input", "audio", "video"
    hint_level = Column(String, nullable=False)  # "none", "partial", "full_after_tries"
    hint_percentage = Column(Integer, nullable=True)  # % of letters to reveal if partial
    hint_tries_before_reveal = Column(Integer, nullable=True)  # tries before full reveal
    time_limit_seconds = Column(Integer, nullable=True)  # time limit per question (optional)
    passing_score = Column(Float, nullable=False, default=70.0)  # % needed to pass

    # Selected drills (stored as comma-separated IDs)
    drill_ids = Column(Text, nullable=False)
    video_url = Column(String, nullable=True) # New field for demo video URL
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=True, index=True)

    # Relationships
    attempts = relationship("TestAttempt", back_populates="test")

class TestAttempt(Base):
    __tablename__ = "test_attempts"

    id = Column(Integer, primary_key=True, index=True)
    test_id = Column(Integer, ForeignKey("tests.id"), nullable=False)
    date_taken = Column(DateTime, default=datetime.utcnow, nullable=False)

    # User info: user_name is the free-text display label (kept); user_id is
    # the real identity when the attempt was taken with an X-User-Token (P4.8).
    user_name = Column(String, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    # Results
    score = Column(Float, nullable=False)  # percentage score
    time_taken_seconds = Column(Integer, nullable=False)
    total_questions = Column(Integer, nullable=False)
    correct_answers = Column(Integer, nullable=False)

    # Detailed results (JSON stored as text)
    question_results = Column(Text, nullable=True)  # JSON: [{drill_id, correct, attempts, time}]

    # Relationship
    test = relationship("Test", back_populates="attempts")

class YouTubeShort(Base):
    __tablename__ = "youtube_shorts"

    id = Column(Integer, primary_key=True, index=True)
    date_created = Column(DateTime, default=datetime.utcnow, nullable=False)
    drill_id = Column(Integer, nullable=False)
    video_path = Column(String, nullable=False)  # Path to generated short

    # Drill info (denormalized for display)
    text_catalan = Column(String, nullable=True)
    text_tachelhit = Column(String, nullable=True)
    text_arabic = Column(String, nullable=True)

class VideoProcessingJob(Base):
    __tablename__ = "video_processing_jobs"

    id = Column(Integer, primary_key=True, index=True)
    date_submitted = Column(DateTime, default=datetime.utcnow, nullable=False)
    source_url = Column(String, nullable=True)  # Original YouTube URL or similar
    source_filepath = Column(String, nullable=True) # Path to uploaded file if applicable
    status = Column(String, default="PENDING", nullable=False) # PENDING, IN_PROGRESS, COMPLETED, FAILED
    error_message = Column(Text, nullable=True)
    processing_log = Column(Text, nullable=True) # Store detailed log if needed
    # P4.6: what the job renders ("asr" = transcription, "auto" = full capture
    # pipeline, "short" = vertical reel, "demo" = test demo video); NULL = legacy.
    kind = Column(String, nullable=True)
    # bumped on every status change so the startup reaper can tell a job that
    # died with the process from one that is still legitimately running
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=True)

    # One-to-many relationship with VideoSegment
    segments = relationship("VideoSegment", back_populates="job")

class VideoSegment(Base):
    __tablename__ = "video_segments"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("video_processing_jobs.id"), nullable=False)
    segment_start_time = Column(Float, nullable=False) # in seconds
    segment_end_time = Column(Float, nullable=False)   # in seconds
    video_url = Column(String, nullable=True) # URL to the clipped video segment
    audio_url = Column(String, nullable=True) # URL to the extracted audio segment
    text_original = Column(Text, nullable=True) # Transcription or lyrics
    text_catalan = Column(Text, nullable=True)  # Translation

    # Many-to-one relationship with VideoProcessingJob
    job = relationship("VideoProcessingJob", back_populates="segments")

class GlossaryItem(Base):
    __tablename__ = "glossary"

    id = Column(Integer, primary_key=True, index=True)
    word_sound = Column(String, nullable=False) # e.g., "anayr"
    correct_spelling = Column(String, nullable=False) # e.g., "anaygh"
    notes = Column(String, nullable=True)
    date_created = Column(DateTime, default=datetime.utcnow, nullable=False)

class DrillReview(Base):
    """Spaced-repetition state for a drill (SM-2 style scheduling)."""
    __tablename__ = "drill_reviews"

    id = Column(Integer, primary_key=True, index=True)
    drill_id = Column(Integer, ForeignKey("drills.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)  # NULL = anonymous/legacy
    ease = Column(Float, default=2.5, nullable=False)
    interval_days = Column(Float, default=0.0, nullable=False)
    repetitions = Column(Integer, default=0, nullable=False)
    due_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_grade = Column(Integer, nullable=True)     # 0=again 1=hard 2=good 3=easy
    last_reviewed = Column(DateTime, nullable=True)
    total_reviews = Column(Integer, default=0, nullable=False)
    lapses = Column(Integer, default=0, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=True)

class GrammarLesson(Base):
    """A grammar unit's lesson (JSON steps, see grammar.py), written once by Gemini and kept here so
    a deploy doesn't lose it; `version` lets a format change rewrite it on next open."""
    __tablename__ = "grammar_lessons"

    id = Column(String, primary_key=True)          # the unit slug
    body = Column(Text, nullable=False)            # JSON: {"intro": str, "steps": [...]}
    version = Column(Integer, nullable=True, default=1)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=True)


class GrammarNote(Base):
    """Why ONE sentence sits in ONE grammar unit: what that sentence shows of that unit's point.
    A sentence belongs to up to three units and shows something different in each, so the note is
    kept per pair. Written once by the notes pass (grammar.py), shown under the sentence."""
    __tablename__ = "grammar_notes"

    id = Column(String, primary_key=True)             # f"{slug}:{drill_id}"
    slug = Column(String, nullable=False, index=True)
    drill_id = Column(Integer, nullable=False, index=True)
    body = Column(Text, nullable=False)               # 25-45 words of plain Catalan
    version = Column(Integer, nullable=True, default=1)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=True)


class AppSetting(Base):
    """A server setting an admin can change from the app itself (the mail sender, today), so a
    deploy or a dashboard visit is not needed. Secrets live here instead of the environment and are
    never returned to the client."""
    __tablename__ = "app_settings"

    key = Column(String, primary_key=True)
    value = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=True)


class LessonProposal(Base):
    """A learner's or speaker's proposed change to a lesson card (the text of one step, or the
    intro when step = -1), reviewed by an admin: accepted = written into the stored lesson."""
    __tablename__ = "lesson_proposals"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String, nullable=False, index=True)
    step = Column(Integer, nullable=False)            # index in lesson["steps"]; -1 = the intro
    kind = Column(String, nullable=False, default="text")  # 'text' (replace the card's text) | 'note' (free comment)
    text = Column(Text, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    display_name = Column(String, nullable=True)
    region = Column(String, nullable=True)
    status = Column(String, nullable=False, default="pending", index=True)  # pending | accepted | rejected
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class User(Base):
    """Contributor/learner identity (auditor Phase 1: multi-tenancy)."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False, index=True)
    display_name = Column(String, nullable=True)
    token = Column(String, unique=True, nullable=False, index=True)
    # The contributor's own variety/region, declared once and used to prefill
    # (and label) the drills they collect — so their variety stays sovereign
    # instead of being defaulted to a standard. e.g. "rif" / "diaspora-BCN".
    variety = Column(String, nullable=True)
    region = Column(String, nullable=True)
    # IANA zone used to compute "today" for streaks (P4.10). NULL = Europe/Madrid.
    tz = Column(String, nullable=True, default="Europe/Madrid")
    # Accounts (2026-10-19): e-mail + password sign-in on top of the token identity.
    email = Column(String, nullable=True, unique=True, index=True)
    password_hash = Column(String, nullable=True)        # pbkdf2_sha256$iters$salt$hash
    is_admin = Column(Boolean, nullable=True, default=False)
    is_native = Column(Boolean, nullable=True)           # speaks Tamazight from home, or is learning it
    reset_code_hash = Column(String, nullable=True)      # password reset code (hashed), 30 min
    reset_expires = Column(DateTime, nullable=True)
    date_created = Column(DateTime, default=datetime.utcnow, nullable=False)

class CaptureRequest(Base):
    """A queued 'download this URL' request. Because YouTube blocks yt-dlp from
    Render's IP, the download is done by a local agent on the user's machine
    (residential IP): the web app queues a request here, the agent polls, grabs
    it, downloads locally and uploads the file back for processing. Fully
    autonomous once the agent is running."""
    __tablename__ = "capture_requests"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String, nullable=False)
    tag = Column(String, nullable=True)
    language = Column(String, nullable=True)
    audio_only = Column(Boolean, default=True, nullable=False)
    apply_correction = Column(Boolean, default=True, nullable=False)
    variety = Column(String, nullable=True)  # which variety the source teaches (shi/tzm/rif/zgh/kab/other)
    drills_created = Column(Integer, nullable=True)  # set when the agent processed it on another backend
    # pending -> claimed -> processing -> done | failed
    status = Column(String, default="pending", nullable=False, index=True)
    job_id = Column(Integer, nullable=True)      # the resulting VideoProcessingJob
    error = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    claimed_at = Column(DateTime, nullable=True)


class Recording(Base):
    """One audio take of a drill by one speaker. Lets the SAME drill carry
    recordings from different people/varieties (multi-attestation) — each take
    keeps its speaker's variety/region so we know how it's being said and by
    whom. The drill's own audio_url stays as the primary/first take."""
    __tablename__ = "recordings"

    id = Column(Integer, primary_key=True, index=True)
    drill_id = Column(Integer, ForeignKey("drills.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    audio_url = Column(String, nullable=False)
    variety = Column(String, nullable=True)
    region = Column(String, nullable=True)
    speaker = Column(String, nullable=True)                 # display label
    is_native = Column(Boolean, nullable=True)              # a native speaker's take, or a learner's
    license = Column(String, nullable=True, default="CC-BY-SA")
    text = Column(Text, nullable=True)       # the sentence as THIS speaker says it, when their dialect's words differ
    date_created = Column(DateTime, default=datetime.utcnow, nullable=False)

class ReviewLog(Base):
    """One row per review grade — powers streaks and progress stats."""
    __tablename__ = "review_logs"

    id = Column(Integer, primary_key=True, index=True)
    drill_id = Column(Integer, ForeignKey("drills.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    grade = Column(Integer, nullable=False)
    reviewed_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class DrillTombstone(Base):
    """A deleted drill's id + when it went, so an offline client syncing with
    ?since= learns about deletions as well as changes (P4.3)."""
    __tablename__ = "drill_tombstones"

    id = Column(Integer, primary_key=True, index=True)
    drill_id = Column(Integer, nullable=False, index=True)
    deleted_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class GeminiUsage(Base):
    """One row per Gemini call: who/what asked, tokens, and the priced cost (micro-euros).
    The monthly budget and the per-person daily cap are computed from this table."""
    __tablename__ = "gemini_usage"

    id = Column(Integer, primary_key=True, index=True)
    at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    model = Column(String, nullable=True)
    feature = Column(String, nullable=True, index=True)   # ask | agent | explain | ... | pipeline
    actor = Column(String, nullable=True, index=True)     # "user:<id>" | "ip:<hash>" | NULL (pipeline)
    prompt_tokens = Column(Integer, default=0, nullable=False)
    output_tokens = Column(Integer, default=0, nullable=False)
    images = Column(Integer, default=0, nullable=False)
    cost_micro_eur = Column(Integer, default=0, nullable=False)
    ok = Column(Boolean, default=True, nullable=False)


class UserSession(Base):
    """A signed-in device: the X-User-Token presented by a browser or phone after sign-in.
    The legacy users.token (shown once at registration) still works as a session too."""
    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    token_hash = Column(String, unique=True, nullable=False, index=True)
    device = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_used = Column(DateTime, default=datetime.utcnow, nullable=True)
