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
    video_url = Column(String, nullable=True)
    image_url = Column(String, nullable=True)
    is_correction_dataset = Column(Boolean, default=False, nullable=False)
    # Timestamp fields for video segments
    video_start_time = Column(Float, nullable=True)  # Start time in seconds
    video_end_time = Column(Float, nullable=True)    # End time in seconds

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

    # Relationships
    attempts = relationship("TestAttempt", back_populates="test")

class TestAttempt(Base):
    __tablename__ = "test_attempts"

    id = Column(Integer, primary_key=True, index=True)
    test_id = Column(Integer, ForeignKey("tests.id"), nullable=False)
    date_taken = Column(DateTime, default=datetime.utcnow, nullable=False)

    # User info (optional, can add authentication later)
    user_name = Column(String, nullable=True)

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
    drill_id = Column(Integer, ForeignKey("drills.id"), unique=True, nullable=False, index=True)
    ease = Column(Float, default=2.5, nullable=False)
    interval_days = Column(Float, default=0.0, nullable=False)
    repetitions = Column(Integer, default=0, nullable=False)
    due_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_grade = Column(Integer, nullable=True)     # 0=again 1=hard 2=good 3=easy
    last_reviewed = Column(DateTime, nullable=True)
    total_reviews = Column(Integer, default=0, nullable=False)
    lapses = Column(Integer, default=0, nullable=False)
