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
    # Parse the URL to extract video ID and preserve other parameters
    from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
    
    parsed_url = urlparse(video_url)
    query_params = parse_qs(parsed_url.query)
    
    # Remove any existing timestamp parameters
    if 't' in query_params:
        del query_params['t']
    if 'start' in query_params:
        del query_params['start']
    if 'end' in query_params:
        del query_params['end']
    
    # Add the new start time parameter
    query_params['t'] = [str(int(start_time))]
    
    # Add end time if provided (YouTube doesn't officially support end time in URL,
    # but we can add it as a custom parameter for our app to use)
    if end_time is not None:
        query_params['end'] = [str(int(end_time))]
    
    # Reconstruct the URL with updated query parameters
    new_query = urlencode(query_params, doseq=True)
    new_parsed_url = parsed_url._replace(query=new_query)
    url_with_time = urlunparse(new_parsed_url)
    
    return url_with_time

def is_corrupted_text(text: str) -> bool:
    """
    Detect if text appears to be corrupted OCR/encoding garbage.
    
    Args:
        text: Text to check
        
    Returns:
        True if text appears corrupted, False if valid
    """
    if not text or len(text.strip()) == 0:
        return True
    
    # Check for common OCR corruption patterns
    text_lower = text.lower()
    
    # 1. Too many special characters or digits mixed with letters
    # Count special characters (excluding common punctuation and spaces)
    special_char_count = sum(1 for c in text if not c.isalnum() and not c.isspace() and c not in ',.!?¿¡\'"-')
    if special_char_count > len(text) * 0.25:  # More than 25% special chars
        return True
    
    # 2. Contains common OCR garbage patterns
    garbage_patterns = [
        r'[0-9]+[a-z]',  # Numbers followed by letters (e.g., "7a", "a2")
        r'[a-z][0-9]+',  # Letters followed by numbers
        r'[^a-zA-Z0-9\s]{2,}',  # 2+ consecutive non-alphanumeric chars
        r'[<>+*^|\\/]{2,}',  # Multiple special characters together
        r'\b[a-z0-9]{1,3}\b',  # Very short alphanumeric words (1-3 chars) that aren't common words
    ]
    
    # Common short valid words to exclude from the short word check
    common_short_words = {'a', 'i', 'o', 'u', 'el', 'la', 'en', 'de', 'que', 'y', 'es', 'no', 'si'}
    
    for pattern in garbage_patterns:
        if re.search(pattern, text_lower):
            # For the short word pattern, check if it's a common word
            if pattern == r'\b[a-z0-9]{1,3}\b':
                matches = re.findall(pattern, text_lower)
                # If all short words are uncommon, it's likely garbage
                if matches and all(word not in common_short_words for word in matches):
                    return True
            else:
                return True
    
    # 3. Check ratio of letters to total characters
    letter_count = sum(1 for c in text if c.isalpha())
    if letter_count < len(text) * 0.4:  # Less than 40% letters
        return True
    
    # 4. Check for excessive digit-to-letter transitions
    digit_letter_transitions = 0
    for i in range(len(text) - 1):
        if text[i].isdigit() and text[i+1].isalpha():
            digit_letter_transitions += 1
        elif text[i].isalpha() and text[i+1].isdigit():
            digit_letter_transitions += 1
    
    if digit_letter_transitions > len(text) * 0.2:  # More than 20% transitions
        return True
    
    return False

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
            
            # Skip corrupted text segments
            if is_corrupted_text(text):
                print(f"[SRT PARSER] Skipping corrupted segment {index}: '{text[:50]}...'")
                continue
            
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
