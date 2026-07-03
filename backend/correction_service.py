import os
import json
import difflib
from openai import OpenAI
from typing import List, Dict, Optional, Tuple

class CorrectionService:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        if not self.api_key:
            print("[CORRECTION] Warning: DEEPSEEK_API_KEY not set. Falling back to local fuzzy matching.")
            self.client = None
        else:
            self.client = OpenAI(
                api_key=self.api_key,
                base_url="https://api.deepseek.com/v1"
            )

    def correct_transcription(self, transcription: str, phrases: List[str]) -> Tuple[str, float]:
        """
        Calls DeepSeek to find the most likely matching phrase from the selection.
        Returns (corrected_phrase, similarity_score).
        """
        if not transcription:
            return "", 0.0
        
        if not phrases:
            print("[CORRECTION] No phrase dataset provided for correction. Returning original.")
            return transcription, 1.0

        # First try DeepSeek if client available
        if self.client:
            prompt = f"""
You are a Tamazight language expert. Given the rough ASR transcription:
"{transcription}"

Select the most likely matching phrase from the following controlled dataset of known Tamazight phrases:
{json.dumps(phrases, ensure_ascii=False, indent=2)}

Always return a phrase from the dataset, even if the match is not perfect. Choose the most likely one.
Return the exact phrase and a confidence score between 0 and 1.
FORMAT:
PHRASE: <exact phrase from dataset>
SCORE: <0.0 to 1.0>
"""

            try:
                print(f"[CORRECTION] Calling DeepSeek for '{transcription}'...")
                response = self.client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[
                        {"role": "system", "content": "You are a Tamazight language expert. You help correct rough ASR transcriptions using a set of known phrases."},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.0
                )
                
                content = response.choices[0].message.content
                print(f"[CORRECTION] DeepSeek response: {content}")
                
                # Extract phrase and score from response
                corrected_phrase = transcription
                score = 0.5
                
                lines = content.splitlines()
                for line in lines:
                    if line.startswith("PHRASE:"):
                        corrected_phrase = line.replace("PHRASE:", "").strip().strip('"')
                    elif line.startswith("SCORE:"):
                        try:
                            score = float(line.replace("SCORE:", "").strip())
                        except:
                            pass
                
                # If the extracted phrase is not in dataset, fall back to local matching
                if corrected_phrase in phrases:
                    return corrected_phrase, score
                # else continue to local matching
            except Exception as e:
                print(f"[CORRECTION] Error in DeepSeek correction: {e}")
                # Fallback to local matching
        
        # Local matching fallback: choose phrase with highest text similarity
        best_phrase = transcription
        best_score = 0.0
        for phrase in phrases:
            similarity = difflib.SequenceMatcher(None, transcription.lower(), phrase.lower()).ratio()
            if similarity > best_score:
                best_score = similarity
                best_phrase = phrase
        # Return best match even if score low
        return best_phrase, best_score

# Singleton instance
_correction_service = None

def get_correction_service():
    global _correction_service
    if _correction_service is None:
        _correction_service = CorrectionService()
    return _correction_service
