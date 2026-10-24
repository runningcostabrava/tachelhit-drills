"""Tachelhit ASR + forced-alignment Space (Docker, CPU).

Model: ayymen/stt_zgh_fastconformer_ctc_small (NeMo FastConformer CTC, Common Voice zgh,
CC BY 4.0, 51 MB) — the model behind the Tamazight-NLP ASR and NeMo-Forced-Aligner Spaces.
It writes Tifinagh. It replaces the Whisper fine-tune that wrote Arabic and hallucinated
other languages.

Routes (FastAPI, first-class so Gradio's catch-all never shadows them):
  GET  /health
  POST /transcribe   audio_file                      -> {"text", "segments":[{start,end,text}]}
  POST /align        audio_file, text, split_on_newline -> {"text", "segments":[{start,end,text,words}]}
Gradio (for gradio_client): api_name="predict" (audio -> text) and api_name="align".

Timestamps come from NeMo Forced Aligner (align.py + utils/, copied from
NVIDIA/NeMo tools/nemo_forced_aligner, Apache 2.0): /align aligns the text you give
(lines separated by newlines, or by "|"); /transcribe aligns the model's own transcript
and groups words into segments at pauses.
"""
import json
import math
import os
import tempfile
import threading
import uuid

import gradio as gr
import librosa
import soundfile
import torch
from fastapi import FastAPI, File, Form, UploadFile, HTTPException

from nemo.collections.asr.models import ASRModel
from align import AlignmentConfig, CTMFileConfig, main as nfa_main

torch.set_num_threads(max(1, os.cpu_count() or 1))
MODEL_ID = os.getenv("ASR_MODEL_ID", "ayymen/stt_zgh_fastconformer_ctc_small")
SAMPLE_RATE = 16000
MAX_SECS = float(os.getenv("ASR_MAX_SECS", "600"))
PAUSE_SECS = float(os.getenv("ASR_SEGMENT_PAUSE_SECS", "0.6"))
MAX_WORDS_PER_SEGMENT = int(os.getenv("ASR_SEGMENT_MAX_WORDS", "12"))

print(f"[ASR] Loading NeMo model {MODEL_ID} on CPU...")
model = ASRModel.from_pretrained(model_name=MODEL_ID, map_location="cpu")
model.eval()
print("[ASR] Model loaded.")
_lock = threading.Lock()  # one NeMo call at a time on a 2-vCPU Space


def _to_wav(src_path: str, dst_path: str) -> float:
    """Decode anything ffmpeg/librosa can read into mono 16 kHz wav; returns duration in s."""
    data, sr = librosa.load(src_path, sr=SAMPLE_RATE, mono=True)
    duration = float(len(data)) / SAMPLE_RATE
    if duration > MAX_SECS:
        raise HTTPException(status_code=413, detail=f"audio longer than {MAX_SECS:.0f} s")
    soundfile.write(dst_path, data, SAMPLE_RATE)
    return duration


def _transcribe(wav_path: str):
    """The text, and how sure the model says it is (0..1, or None when it will not say).

    The number matters downstream: the app keeps a queue of recordings nobody has written yet,
    and a transcript is only ever a PROPOSAL there. Without a confidence, the clean recording
    and the unintelligible one sit in that queue weighing the same, and whoever confirms them
    has to find out by listening to each. With it, the likely ones come first.

    NeMo's CTC hypothesis carries `score`, the sum of the log-probabilities of the path it took.
    Summed, it punishes long sentences for being long, so it is averaged per character and
    turned back into a probability-like number with exp(). Best effort on purpose: an older NeMo
    that does not take `return_hypotheses`, or a hypothesis without a score, simply gives no
    number — never an error, and never a made-up 1.0.
    """
    hyp = None
    with _lock:
        try:
            out = model.transcribe([wav_path], batch_size=1, verbose=False,
                                   return_hypotheses=True)
            hyp = out[0][0] if isinstance(out, (list, tuple)) and isinstance(out[0], (list, tuple)) else out[0]
        except TypeError:
            out = model.transcribe([wav_path], batch_size=1, verbose=False)
            hyp = out[0]
    text = hyp
    if isinstance(text, (list, tuple)):
        text = text[0]
    if hasattr(text, "text"):
        text = text.text
    text = (text or "").strip()

    conf = None
    score = getattr(hyp, "score", None)
    if score is not None and text:
        try:
            conf = round(float(math.exp(float(score) / max(1, len(text)))), 3)
            conf = max(0.0, min(1.0, conf))
        except (TypeError, ValueError, OverflowError):
            conf = None
    return text, conf


def _read_ctm(path: str):
    rows = []
    if not os.path.exists(path):
        return rows
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            parts = line.rstrip("\n").split(" ", 4)
            if len(parts) < 5:
                continue
            start, dur, tok = float(parts[2]), float(parts[3]), parts[4]
            rows.append({"start": round(start, 2), "end": round(start + dur, 2), "text": tok.replace("<space>", " ")})
    return rows


def _align(wav_path: str, text: str, tmpdir: str) -> dict:
    """Run NeMo Forced Aligner on one wav with the given text ('|' separates segments)."""
    utt_id = f"u{uuid.uuid4().hex[:10]}"
    audio_path = os.path.join(tmpdir, f"{utt_id}.wav")
    os.replace(wav_path, audio_path)
    manifest = os.path.join(tmpdir, f"{utt_id}_manifest.json")
    with open(manifest, "w", encoding="utf-8") as fh:
        fh.write(json.dumps({"audio_filepath": audio_path, "text": text}, ensure_ascii=False) + "\n")
    out_dir = os.path.join(tmpdir, "nfa")
    cfg = AlignmentConfig(
        pretrained_name=MODEL_ID,
        manifest_filepath=manifest,
        output_dir=out_dir,
        audio_filepath_parts_in_utt_id=1,
        batch_size=1,
        use_local_attention=True,
        additional_segment_grouping_separator="|",
        transcribe_device="cpu",
        viterbi_device="cpu",
        save_output_file_formats=["ctm"],
        ctm_file_config=CTMFileConfig(remove_blank_tokens=True),
    )
    with _lock:
        nfa_main(cfg)
    words = _read_ctm(os.path.join(out_dir, "ctm", "words", f"{utt_id}.ctm"))
    segs = _read_ctm(os.path.join(out_dir, "ctm", "segments", f"{utt_id}.ctm"))
    for s in segs:
        s["words"] = [w for w in words if w["start"] >= s["start"] - 0.01 and w["end"] <= s["end"] + 0.01]
    return {"text": text.replace("|", "\n"), "segments": segs, "words": words}


def _segments_from_words(words, duration: float, full_text: str):
    """Group aligned words into segments at pauses (for /transcribe's segment output)."""
    if not words:
        return [{"start": 0.0, "end": round(duration, 2), "text": full_text}] if full_text else []
    segs, cur = [], [words[0]]
    for prev, w in zip(words, words[1:]):
        if w["start"] - prev["end"] > PAUSE_SECS or len(cur) >= MAX_WORDS_PER_SEGMENT:
            segs.append(cur); cur = []
        cur.append(w)
    segs.append(cur)
    return [{"start": c[0]["start"], "end": c[-1]["end"], "text": " ".join(w["text"] for w in c)} for c in segs]


def transcribe_file(src_path: str) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        wav = os.path.join(tmp, "in.wav")
        duration = _to_wav(src_path, wav)
        text, conf = _transcribe(wav)
        if not text:
            return {"text": "", "segments": [], "confidence": None, "model": MODEL_ID}
        try:
            al = _align(wav, text, tmp)
            segments = _segments_from_words(al["words"], duration, text)
        except Exception as e:  # alignment is best-effort; the transcript still goes out
            print(f"[ASR] alignment failed: {e}")
            segments = [{"start": 0.0, "end": round(duration, 2), "text": text}]
        return {"text": text, "segments": segments, "confidence": conf, "model": MODEL_ID}


def align_file(src_path: str, text: str, split_on_newline: bool = True) -> dict:
    text = (text or "").strip()
    with tempfile.TemporaryDirectory() as tmp:
        wav = os.path.join(tmp, "in.wav")
        duration = _to_wav(src_path, wav)
        if not text:
            text, _ = _transcribe(wav)
            if not text:
                return {"text": "", "segments": [], "words": [], "model": MODEL_ID, "note": "no speech detected"}
        if split_on_newline:
            text = "|".join(l.strip() for l in text.splitlines() if l.strip())
        out = _align(wav, text, tmp)
        out.update({"duration": round(duration, 2), "model": MODEL_ID})
        return out


app = FastAPI(title="Tachelhit ASR + alignment service")


@app.get("/health")
def health():
    return {"status": "ok", "model": MODEL_ID, "routes": ["/transcribe", "/align"]}


async def _save_upload(upload: UploadFile) -> str:
    suffix = os.path.splitext(upload.filename or "")[1] or ".bin"
    fd, path = tempfile.mkstemp(suffix=suffix)
    with os.fdopen(fd, "wb") as fh:
        while True:
            chunk = await upload.read(1 << 20)
            if not chunk:
                break
            fh.write(chunk)
    return path


@app.post("/transcribe")
async def transcribe_uploaded_file(audio_file: UploadFile = File(...), language: str = Form(None)):
    path = await _save_upload(audio_file)
    try:
        return transcribe_file(path)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ASR failed: {e}")
    finally:
        try:
            os.remove(path)
        except OSError:
            pass


@app.post("/align")
async def align_uploaded_file(audio_file: UploadFile = File(...), text: str = Form(""),
                              split_on_newline: bool = Form(True)):
    path = await _save_upload(audio_file)
    try:
        return align_file(path, text, split_on_newline)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"alignment failed: {e}")
    finally:
        try:
            os.remove(path)
        except OSError:
            pass


# Gradio API for gradio_client callers: api_name="predict" (audio -> text) kept from the
# Whisper version; api_name="align" added. Mounted after the routes above.
def _gr_predict(audio_path):
    if not audio_path:
        return ""
    try:
        return transcribe_file(audio_path)["text"]
    except Exception as e:
        return f"Error during processing: {e}"


def _gr_align(audio_path, text, split_on_newline):
    if not audio_path:
        return {"error": "no audio"}
    try:
        return align_file(audio_path, text or "", bool(split_on_newline))
    except Exception as e:
        return {"error": str(e)}


with gr.Blocks(title="Tachelhit ASR + alignment") as demo:
    gr.Markdown(f"# Tachelhit ASR + forced alignment\nModel `{MODEL_ID}` (NeMo, CC BY 4.0). "
                "API: `POST /transcribe`, `POST /align` (audio_file, text, split_on_newline).")
    with gr.Tab("Transcribe"):
        a1 = gr.Audio(type="filepath", label="Audio")
        t1 = gr.Textbox(label="Transcription (Tifinagh)")
        gr.Button("Transcribe").click(_gr_predict, inputs=a1, outputs=t1, api_name="predict")
    with gr.Tab("Align"):
        a2 = gr.Audio(type="filepath", label="Audio")
        x2 = gr.Textbox(label="Text (one line per segment; empty = use the model's transcript)", lines=6)
        s2 = gr.Checkbox(True, label="Split on new lines")
        j2 = gr.JSON(label="Segments and words with times")
        gr.Button("Align").click(_gr_align, inputs=[a2, x2, s2], outputs=j2, api_name="align")

app = gr.mount_gradio_app(app, demo, path="/")
