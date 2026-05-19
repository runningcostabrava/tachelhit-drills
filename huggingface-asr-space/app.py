import os
import torch
import gradio as gr
from transformers import pipeline
import librosa
from fastapi import FastAPI, UploadFile, File, HTTPException

# 1. Initialize Whisper Model on CPU
print("[ASR] Loading Whisper model on CPU...")
device = "cpu"
pipe = pipeline(
    "automatic-speech-recognition",
    model="SoufianeDahimi/whisper-small-tamazight",
    device=device
)
print("[ASR] Whisper Model loaded successfully.")

# Core transcription utility engine
def transcribe_audio_logic(audio_path):
    if not audio_path:
        return "Error: No audio file received."
    try:
        audio_data, sr = librosa.load(audio_path, sr=16000)
        asr_result = pipe(audio_data)
        return asr_result.get("text", "").strip()
    except Exception as e:
        return f"Error during processing: {str(e)}"

# 2. Define standard Gradio Interface (Used by Mobile Microphone)
demo = gr.Interface(
    fn=transcribe_audio_logic,
    inputs=gr.Audio(type="filepath", label="Input Audio"),
    outputs=gr.Textbox(label="Tachelhit Transcription"),
    title="Tachelhit ASR Service"
)

# 3. Mount custom FastAPI route onto Gradio (Used by Video Upload Parser)
app = demo.app 

@app.post("/transcribe")
async def transcribe_uploaded_file(audio_file: UploadFile = File(...)):
    try:
        import tempfile
        suffix = os.path.splitext(audio_file.filename)[1] or ".mp4"
        
        # Save incoming video binary data to temporary disk memory
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await audio_file.read()
            tmp.write(content)
            tmp_path = tmp.name

        # Run inference computation
        text = transcribe_audio_logic(tmp_path)

        # Securely remove temporary file pointer cache
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

        # Return structural layout payload exactly how main.py task loops expect it
        return {
            "rough_transcription": text,
            "corrected_transcription": text,
            "similarity_score": 1.0,
            "segments": [{"start": 0.0, "end": 5.0, "text": text}]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
