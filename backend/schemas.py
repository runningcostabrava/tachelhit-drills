from pydantic import BaseModel, field_validator
from datetime import datetime
from typing import Optional, List

def normalize_media_url(url: str) -> str:
    """
    Ensure URL has correct protocol (https:// or http://).
    If it starts with https// or http//, replace with proper colon.
    Also remove any accidental API_BASE prefix before https//.
    """
    # Función corregida para evitar corrupción de URLs Cloudinary - commit actual
    if not url:
        return url

    # 1. Fix malformed protocol (global replace) - do this first
    url = url.replace("https//", "https://").replace("http//", "http://")

    # 2. Remove API_BASE prefix if present (with or without protocol)
    prefixes_to_remove =  [
        "https://tachelhit-drills-api.onrender.com",
        "http://tachelhit-drills-api.onrender.com",
        "tachelhit-drills-api.onrender.com",
    ]
    for prefix in prefixes_to_remove:
        if url.startswith(prefix):
            url = url[len(prefix):]
            break

    # 3. Si después de quitar prefijos es una URL de Cloudinary correctamente formada, NO LA TOQUIS
    if "res.cloudinary.com" in url and url.startswith("http"):
        # Ya es válida, retornar sin más cambios
        return url

    # 4. Ensure protocol for double slash
    if url.startswith("//"):
        url = "https:" + url

    # Return as is (could be relative path, absolute URL, etc.)
    return url

class DrillBase(BaseModel):
    tag: Optional[str] = None
    author: Optional[str] = None
    
    @field_validator('author')
    @classmethod
    def validate_author(cls, v: str | None) -> str | None:
        if v is not None:
            v = v.strip()
            if v == '':
                return None
        return v
    text_catalan: Optional[str] = None
    text_tachelhit: Optional[str] = None
    text_arabic: Optional[str] = None
    audio_url: Optional[str] = None
    audio_tts_url: Optional[str] = None  # Generated TTS for Catalan text
    video_url: Optional[str] = None
    image_url: Optional[str] = None
    is_correction_dataset: Optional[bool] = None
    video_start_time: Optional[float] = None  # Start time in seconds
    video_end_time: Optional[float] = None    # End time in seconds

    # Validators for URL fields
    @field_validator('audio_url', 'audio_tts_url', 'video_url', 'image_url')
    @classmethod
    def normalize_urls(cls, v: str | None) -> str | None:
        if not v:
            return v
        return normalize_media_url(v)

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
    video_url: Optional[str] = None # New field for demo video URL

    @field_validator('video_url')
    @classmethod
    def normalize_video_url(cls, v: str | None) -> str | None:
        if not v:
            return v
        return normalize_media_url(v)

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

    @field_validator('video_path')
    @classmethod
    def normalize_video_path(cls, v: str | None) -> str | None:
        if not v:
            return v
        return normalize_media_url(v)

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
    video_url: Optional[str] = None
    audio_url: Optional[str] = None
    text_original: Optional[str] = None
    text_catalan: Optional[str] = None

class VideoSegmentCreate(VideoSegmentBase):
    pass

class VideoSegment(VideoSegmentBase):
    id: int

    class Config:
        from_attributes = True

# ASR and Correction Schemas
class TranscribeRequest(BaseModel):
    cloudinary_path: Optional[str] = None
    audio_url: Optional[str] = None
    selected_pair_ids: List[int] = []
    model_id: Optional[str] = None # New: to select ASR model

class TranscribeResponse(BaseModel):
    rough_transcription: str
    corrected_transcription: str
    similarity_score: float

class DrillPairInfo(BaseModel):
    id: int
    text_tachelhit: str
    text_catalan: Optional[str] = None

# Translation Schemas
class TranslateRequest(BaseModel):
    text: str
    source_lang: str = "ca"
    target_lang: str = "shi"

class TranslateResponse(BaseModel):
    translated_text: str

# Glossary Schemas
class GlossaryItemBase(BaseModel):
    word_sound: str
    correct_spelling: str
    notes: Optional[str] = None

class GlossaryItemCreate(GlossaryItemBase):
    pass

class GlossaryItem(GlossaryItemBase):
    id: int
    date_created: datetime

    class Config:
        from_attributes = True

# SRT Import Schemas
class SrtSegment(BaseModel):
    index: int
    start_time: float
    end_time: float
    start_timestamp: str
    end_timestamp: str
    text: str

class SrtImportRequest(BaseModel):
    video_url: str
    srt_content: str
    tag: Optional[str] = None
    author: Optional[str] = None
    create_test: bool = False
    test_title: Optional[str] = None
    test_description: Optional[str] = None

class SrtImportResponse(BaseModel):
    success: bool
    message: str
    drill_count: int
    drill_ids: List[int]
    test_id: Optional[int] = None
    segments: List[SrtSegment]

# Bulk Video URL Update Schemas
class BulkVideoUrlUpdateRequest(BaseModel):
    drill_ids: List[int]
    base_video_url: str
    update_timestamps: bool = True  # Whether to update timestamps based on video_start_time

class BulkVideoUrlUpdateResponse(BaseModel):
    success: bool
    message: str
    updated_count: int
    failed_ids: List[int] = []
