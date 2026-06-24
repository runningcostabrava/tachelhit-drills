import os
import tempfile

import torch
import gradio as gr
from transformers import pipeline
import librosa
from fastapi import FastAPI, UploadFile, File, HTTPException

# 1. Initialize Whisper Model on CPU
print("[ASR] Loading Whisper model on CPU...")
device = "cpu"
MODEL_ID = os.getenv("ASR_MODEL_ID", "SoufianeDahimi/whisper-small-tamazight")
# chunk_length_s lets the pipeline transcribe audio longer than the model's
# 30s receptive field; stride keeps context across chunk boundaries.
CHUNK_LENGTH_S = int(os.getenv("ASR_CHUNK_LENGTH_S", "30"))
STRIDE_LENGTH_S = int(os.getenv("ASR_STRIDE_LENGTH_S", "5"))
pipe = pipeline(
    "automatic-speech-recognition",
    model=MODEL_ID,
    device=device,
    chunk_length_s=CHUNK_LENGTH_S,
    stride_length_s=STRIDE_LENGTH_S,
)
print("[ASR] Whisper Model loaded successfully.")


def transcribe_with_segments(audio_path):
    """
    Transcribe an audio/video file into timestamped segments.

    Returns a tuple (full_text, segments) where segments is a list of
    {"start": float, "end": float, "text": str}. Handles long-form audio via
    the pipeline's chunking and falls back gracefully if the model does not
    emit usable timestamps.
    """
    audio_data, sr = librosa.load(audio_path, sr=16000)
    duration = float(len(audio_data) / sr) if sr else 0.0

    # return_timestamps=True yields chunk-level (start, end) spans.
    result = pipe(audio_data, return_timestamps=True)

    full_text = (result.get("text") or "").strip()
    raw_chunks = result.get("chunks") or []

    segments = []
    last_end = 0.0
    for chunk in raw_chunks:
        text = (chunk.get("text") or "").strip()
        if not text:
            continue
        ts = chunk.get("timestamp") or (None, None)
        start, end = ts[0], ts[1]
        # Whisper can return None for an open-ended final chunk, or missing
        # starts; coerce these into a monotonic, non-negative timeline.
        start = float(start) if start is not None else last_end
        end = float(end) if end is not None else max(start, duration)
        if end < start:
            end = start
        segments.append({"start": start, "end": end, "text": text})
        last_end = end

    # Fallback: no usable chunks but we did get text -> one segment spanning
    # the whole clip (still far better than a hardcoded 0-5s window).
    if not segments and full_text:
        segments = [{"start": 0.0, "end": duration or 0.0, "text": full_text}]

    return full_text, segments


# Core transcription utility engine (text-only, used by the Gradio UI)
def transcribe_audio_logic(audio_path):
    if not audio_path:
        return "Error: No audio file received."
    try:
        full_text, _ = transcribe_with_segments(audio_path)
        return full_text
    except Exception as e:
        return f"Error during processing: {str(e)}"


# 2. FastAPI is the real server. The custom API routes live on it directly, so
# they are first-class (not shadowed by Gradio's catch-all) and are NOT subject
# to Gradio's cross-site form-POST protection. The Gradio UI is mounted under
# this app at the end.
app = FastAPI(title="Tachelhit ASR Service")


@app.get("/health")
def health():
    return {"status": "ok", "model": MODEL_ID}


@app.post("/transcribe")
async def transcribe_uploaded_file(audio_file: UploadFile = File(...)):
    try:
        suffix = os.path.splitext(audio_file.filename or "")[1] or ".mp4"

        # Save incoming video/audio binary data to temporary disk
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await audio_file.read()
            tmp.write(content)
            tmp_path = tmp.name

        try:
            # Run inference: full text + real timestamped segments
            full_text, segments = transcribe_with_segments(tmp_path)
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

        # Return payload in the shape main.py's task loops expect
        return {
            "rough_transcription": full_text,
            "corrected_transcription": full_text,
            "similarity_score": 1.0,
            "segments": segments,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 3. Gradio UI (used by the mobile microphone) mounted at the root path.
# Built with Blocks + an explicit api_name="predict" so the gradio_client
# endpoint is "/predict" — the backend's audio-record correction path
# (main.py) calls client.predict(..., api_name="/predict"). gr.Interface in
# Gradio 5/6 would auto-name the endpoint after the function instead.
# Mounting after the API routes means POST /transcribe still resolves to the
# explicit FastAPI route above.
with gr.Blocks(title="Tachelhit ASR Service") as demo:
    gr.Markdown("# Tachelhit ASR Service")
    audio_in = gr.Audio(type="filepath", label="Input Audio")
    text_out = gr.Textbox(label="Tachelhit Transcription")
    gr.Button("Transcribe").click(
        transcribe_audio_logic, inputs=audio_in, outputs=text_out, api_name="predict"
    )
app = gr.mount_gradio_app(app, demo, path="/")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)
