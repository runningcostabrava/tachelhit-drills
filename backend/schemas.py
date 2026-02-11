from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

class DrillBase(BaseModel):
    tag: Optional[str] = None
    text_catalan: Optional[str] = None
    text_tachelhit: Optional[str] = None
    text_arabic: Optional[str] = None
    audio_url: Optional[str] = None
    audio_tts_url: Optional[str] = None  # Generated TTS for Catalan text
    video_url: Optional[str] = None
    image_url: Optional[str] = None

class DrillCreate(DrillBase):
    pass

class DrillUpdate(DrillBase):
    pass

class Drill(DrillBase):
    id: int
    date_created: datetime

    class Config:
        from_attributes = True

# Test Schemas
class TestBase(BaseModel):
    title: str
    description: Optional[str] = None
    question_type: str  # "text_input", "audio", "video"
    hint_level: str  # "none", "partial", "full_after_tries"
    hint_percentage: Optional[int] = None
    hint_tries_before_reveal: Optional[int] = None
    time_limit_seconds: Optional[int] = None
    passing_score: float = 70.0
    drill_ids: str  # comma-separated IDs

class TestCreate(TestBase):
    pass

class TestUpdate(TestBase):
    pass

class Test(TestBase):
    id: int
    date_created: datetime

    class Config:
        from_attributes = True

# Test Attempt Schemas
class TestAttemptBase(BaseModel):
    test_id: int
    user_name: Optional[str] = None
    score: float
    time_taken_seconds: int
    total_questions: int
    correct_answers: int
    question_results: Optional[str] = None

class TestAttemptCreate(TestAttemptBase):
    pass

class TestAttempt(TestAttemptBase):
    id: int
    date_taken: datetime

    class Config:
        from_attributes = True

# YouTube Short Schemas
class YouTubeShortBase(BaseModel):
    drill_id: int
    video_path: str
    text_catalan: Optional[str] = None
    text_tachelhit: Optional[str] = None
    text_arabic: Optional[str] = None

class YouTubeShortCreate(YouTubeShortBase):
    pass

class YouTubeShort(YouTubeShortBase):
    id: int
    date_created: datetime

    class Config:
        from_attributes = True

# Video Processing Schemas
class VideoProcessingJobBase(BaseModel):
    source_url: Optional[str] = None
    source_filepath: Optional[str] = None
    status: str = "PENDING"
    error_message: Optional[str] = None
    processing_log: Optional[str] = None

class VideoProcessingJobCreate(VideoProcessingJobBase):
    pass

class VideoProcessingJob(VideoProcessingJobBase):
    id: int
    date_submitted: datetime
    
    class Config:
        from_attributes = True

class VideoSegmentBase(BaseModel):
    job_id: int
    segment_start_time: float
    segment_end_time: float
    original_transcription: Optional[str] = None
    original_language: Optional[str] = None
    translated_arabic: Optional[str] = None
    translated_catalan: Optional[str] = None
    translated_tachelhit: Optional[str] = None
    video_url: Optional[str] = None
    audio_url: Optional[str] = None

class VideoSegmentCreate(VideoSegmentBase):
    pass

class VideoSegment(VideoSegmentBase):
    id: int
    
    class Config:
        from_attributes = True
