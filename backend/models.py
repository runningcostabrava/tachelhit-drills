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
    text_catalan = Column(String, nullable=True)
    text_tachelhit = Column(String, nullable=True)
    text_arabic = Column(String, nullable=True)
    audio_url = Column(String, nullable=True)
    audio_tts_url = Column(String, nullable=True)  # Generated TTS for Catalan text
    video_url = Column(String, nullable=True)
    image_url = Column(String, nullable=True)

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

    # Many-to-one relationship with VideoProcessingJob
    job = relationship("VideoProcessingJob", back_populates="segments")
