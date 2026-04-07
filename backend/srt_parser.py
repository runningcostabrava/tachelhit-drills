"""
SRT Parser for YouTube subtitle files.
Parses SRT files and extracts segments with timestamps and text.
"""
import re
from typing import List, Dict, Any
from datetime import datetime

def parse_srt_file(file_path: str) -> List[Dict[str, Any]]:
    """
    Parse an SRT file and return a list of segments.
    
    Args:
        file_path: Path to the SRT file
        
    Returns:
        List of dictionaries with keys:
        - index: Segment number
        - start_time: Start time in seconds (float)
        - end_time: End time in seconds (float)
        - start_timestamp: Original timestamp string (HH:MM:SS,mmm)
        - end_timestamp: Original timestamp string (HH:MM:SS,mmm)
        - text: Subtitle text
    """
    segments = []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Split by double newlines (standard SRT format)
    blocks = content.strip().split('\n\n')
    
    for block in blocks:
        if not block.strip():
            continue
            
        lines = block.strip().split('\n')
        if len(lines) < 3:
            continue
            
        try:
            # First line: index
            index = int(lines[0].strip())
            
            # Second line: timestamp
            timestamp_match = re.match(r'(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})', lines[1].strip())
            if not timestamp_match:
                continue
                
            start_timestamp = timestamp_match.group(1)
            end_timestamp = timestamp_match.group(2)
            
            # Convert timestamp to seconds
            start_seconds = timestamp_to_seconds(start_timestamp)
            end_seconds = timestamp_to_seconds(end_timestamp)
            
            # Remaining lines: text
            text_lines = lines[2:]
            text = ' '.join(line.strip() for line in text_lines)
            
            segments.append({
                'index': index,
                'start_time': start_seconds,
                'end_time': end_seconds,
                'start_timestamp': start_timestamp,
                'end_timestamp': end_timestamp,
                'text': text
            })
            
        except (ValueError, IndexError) as e:
            print(f"Error parsing block: {e}")
            continue
    
    return segments

def timestamp_to_seconds(timestamp: str) -> float:
    """
    Convert SRT timestamp (HH:MM:SS,mmm) to seconds.
    
    Args:
        timestamp: Timestamp string in format HH:MM:SS,mmm
        
    Returns:
        Time in seconds as float
    """
    # Replace comma with dot for milliseconds
    timestamp = timestamp.replace(',', '.')
    
    # Parse hours, minutes, seconds
    parts = timestamp.split(':')
    if len(parts) != 3:
        raise ValueError(f"Invalid timestamp format: {timestamp}")
    
    hours = int(parts[0])
    minutes = int(parts[1])
    seconds = float(parts[2])
    
    return hours * 3600 + minutes * 60 + seconds

def seconds_to_timestamp(seconds: float) -> str:
    """
    Convert seconds to SRT timestamp format (HH:MM:SS,mmm).
    
    Args:
        seconds: Time in seconds
        
    Returns:
        Timestamp string in format HH:MM:SS,mmm
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    
    # Format with 3 decimal places (milliseconds)
    return f"{hours:02d}:{minutes:02d}:{secs:06.3f}".replace('.', ',')

def create_youtube_url_with_timestamp(video_url: str, start_time: float, end_time: float = None) -> str:
    """
    Create a YouTube URL with timestamp for a specific segment.
    
    Args:
        video_url: Base YouTube URL
        start_time: Start time in seconds
        end_time: End time in seconds (optional)
        
    Returns:
        YouTube URL with timestamp parameters
    """
    # Clean URL - remove existing timestamp parameters
    base_url = video_url.split('?')[0] if '?' in video_url else video_url
    
    # Add start time parameter
    if '?' in base_url:
        url_with_time = f"{base_url}&t={int(start_time)}"
    else:
        url_with_time = f"{base_url}?t={int(start_time)}"
    
    # Add end time if provided (YouTube doesn't officially support end time in URL,
    # but we can add it as a custom parameter for our app to use)
    if end_time is not None:
        url_with_time = f"{url_with_time}&end={int(end_time)}"
    
    return url_with_time

def parse_srt_content(content: str) -> List[Dict[str, Any]]:
    """
    Parse SRT content from a string (not file).
    
    Args:
        content: SRT content as string
        
    Returns:
        List of segments (same format as parse_srt_file)
    """
    segments = []
    
    # Split by double newlines (standard SRT format)
    blocks = content.strip().split('\n\n')
    
    for block in blocks:
        if not block.strip():
            continue
            
        lines = block.strip().split('\n')
        if len(lines) < 3:
            continue
            
        try:
            # First line: index
            index = int(lines[0].strip())
            
            # Second line: timestamp
            timestamp_match = re.match(r'(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})', lines[1].strip())
            if not timestamp_match:
                continue
                
            start_timestamp = timestamp_match.group(1)
            end_timestamp = timestamp_match.group(2)
            
            # Convert timestamp to seconds
            start_seconds = timestamp_to_seconds(start_timestamp)
            end_seconds = timestamp_to_seconds(end_timestamp)
            
            # Remaining lines: text
            text_lines = lines[2:]
            text = ' '.join(line.strip() for line in text_lines)
            
            segments.append({
                'index': index,
                'start_time': start_seconds,
                'end_time': end_seconds,
                'start_timestamp': start_timestamp,
                'end_timestamp': end_timestamp,
                'text': text
            })
            
        except (ValueError, IndexError) as e:
            print(f"Error parsing block: {e}")
            continue
    
    return segments