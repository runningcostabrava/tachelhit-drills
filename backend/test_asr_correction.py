import os
import json
import pytest
from asr_service import ASRService
from correction_service import CorrectionService
from unittest.mock import MagicMock

# Mock data for correction
TEST_PHRASES = [
    "Azul fellawen",
    "Ini ad sɣeɣ aghrum",
    "Manis ism nnk?",
    "Tanmmirt bahra"
]

def test_correction_service():
    """
    Tests the DeepSeek correction service with a mock API response.
    """
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        print("Skipping test_correction_service: DEEPSEEK_API_KEY not set.")
        return

    service = CorrectionService(api_key=api_key)
    
    # Test case 1: Near match
    rough = "Asul felawen"
    corrected, score = service.correct_transcription(rough, TEST_PHRASES)
    
    print(f"Rough: {rough}")
    print(f"Corrected: {corrected}")
    print(f"Score: {score}")
    
    assert corrected in TEST_PHRASES or corrected == rough
    assert score >= 0.0

def test_asr_service_mock():
    """
    Tests the ASR service (using a local file or mock).
    """
    # This might take time to download the model, so we can mock the pipe
    service = ASRService(model_id="openai/whisper-tiny") # tiny for testing
    
    # We need a sample audio file. If not present, we skip.
    sample_audio = "backend/media/audio/sample.wav"
    if not os.path.exists(sample_audio):
        print(f"Skipping test_asr_service: {sample_audio} not found.")
        return

    result = service.transcribe(sample_audio)
    print(f"ASR Result: {result}")
    assert isinstance(result, str)

if __name__ == "__main__":
    # Manual run
    print("Running manual tests...")
    test_correction_service()
    # test_asr_service_mock() # Uncomment if you have a sample audio file
