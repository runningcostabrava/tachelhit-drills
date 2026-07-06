"""
Tachelhit NLP Space — ONE Space that does ASR + translation + OCR, so the app
needs fewer HuggingFace Spaces and stops fighting the free CPU quota (4 Spaces
-> 2: this + the image one).

Models are LAZY-loaded on first use, so the Space boots fast (health check passes
immediately) and memory only grows for the features you actually call:

  POST /transcribe (audio_file)              -> {rough_transcription, corrected_transcription, similarity_score, segments}
                                                 [SoufianeDahimi/whisper-small-tamazight]
  POST /translate  {text, src_lang, tgt_lang}-> {translation, tifinagh, latin}
                                                 [Tamazight-NLP/NLLB-200-600M-Tamazight-All-Data-3-epoch — needs HF_TOKEN]
  POST /ocr        (image)                    -> {results: [{text, confidence, script, box}]}
                                                 [EasyOCR latin + arabic]
  GET  /health

A Gradio UI is mounted at / with api_name "predict" (audio->text) and "translate"
so the old gradio_client call sites keep working.
"""
import io
import os
import tempfile
import threading

import gradio as gr
from fastapi import FastAPI, File, UploadFile, Body, HTTPException

HF_TOKEN = os.environ.get("HF_TOKEN")

# ---- lazy singletons -------------------------------------------------------
_lock = threading.Lock()
_asr = None
_nllb = None
_ocr = None


def _get_asr():
    global _asr
    if _asr is None:
        with _lock:
            if _asr is None:
                from transformers import pipeline
                model_id = os.getenv("ASR_MODEL_ID", "SoufianeDahimi/whisper-small-tamazight")
                print(f"[NLP] loading ASR {model_id} ...")
                _asr = pipeline(
                    "automatic-speech-recognition", model=model_id, device="cpu",
                    chunk_length_s=int(os.getenv("ASR_CHUNK_LENGTH_S", "30")),
                    stride_length_s=int(os.getenv("ASR_STRIDE_LENGTH_S", "5")),
                )
                print("[NLP] ASR ready.")
    return _asr


def _get_nllb():
    global _nllb
    if _nllb is None:
        with _lock:
            if _nllb is None:
                from transformers import NllbTokenizerFast, AutoModelForSeq2SeqLM
                model_name = os.getenv("NLLB_MODEL_ID", "Tamazight-NLP/NLLB-200-600M-Tamazight-All-Data-3-epoch")
                print(f"[NLP] loading NLLB {model_name} ...")
                tok = NllbTokenizerFast.from_pretrained(model_name, token=HF_TOKEN)
                mdl = AutoModelForSeq2SeqLM.from_pretrained(model_name, token=HF_TOKEN)
                mdl.to("cpu")
                _nllb = (tok, mdl)
                print("[NLP] NLLB ready.")
    return _nllb


def _get_ocr():
    global _ocr
    if _ocr is None:
        with _lock:
            if _ocr is None:
                import easyocr
                print("[NLP] loading EasyOCR ...")
                _ocr = {
                    "latin": easyocr.Reader(["en", "fr", "es"], gpu=False),
                    "arabic": easyocr.Reader(["ar", "en"], gpu=False),
                }
                print("[NLP] OCR ready.")
    return _ocr


# ---- ASR -------------------------------------------------------------------
def _transcribe_segments(audio_path):
    import librosa
    audio, sr = librosa.load(audio_path, sr=16000)
    duration = float(len(audio) / sr) if sr else 0.0
    result = _get_asr()(audio, return_timestamps=True)
    full_text = (result.get("text") or "").strip()
    segments, last_end = [], 0.0
    for chunk in (result.get("chunks") or []):
        text = (chunk.get("text") or "").strip()
        if not text:
            continue
        ts = chunk.get("timestamp") or (None, None)
        start = float(ts[0]) if ts[0] is not None else last_end
        end = float(ts[1]) if ts[1] is not None else max(start, duration)
        if end < start:
            end = start
        segments.append({"start": start, "end": end, "text": text})
        last_end = end
    if not segments and full_text:
        segments = [{"start": 0.0, "end": duration, "text": full_text}]
    return full_text, segments


# ---- translation -----------------------------------------------------------
_TIF2LAT = {
    "ⴰ": "a", "ⴱ": "b", "ⴳ": "g", "ⴷ": "d", "ⴹ": "ḍ", "ⴻ": "e", "ⴼ": "f", "ⴽ": "k", "ⵀ": "h",
    "ⵃ": "ḥ", "ⵅ": "x", "ⵇ": "q", "ⵉ": "i", "ⵊ": "j", "ⵍ": "l", "ⵎ": "m", "ⵏ": "n", "ⵓ": "u",
    "ⵔ": "r", "ⵕ": "ṛ", "ⵖ": "ɣ", "ⵙ": "s", "ⵚ": "ṣ", "ⵛ": "š", "ⵜ": "t", "ⵟ": "ṭ", "ⵡ": "w",
    "ⵢ": "y", "ⵣ": "z", "ⵥ": "ẓ", "ⵯ": "w", "ⵒ": "p", "ⵠ": "v", "ⵞ": "č",
}


def _tif_to_latin(s):
    return "".join(_TIF2LAT.get(c, c) for c in s)


def _translate(text, src_lang, tgt_lang):
    text = (text or "").strip()
    if not text:
        return {"translation": "", "tifinagh": "", "latin": ""}
    tok, mdl = _get_nllb()
    tok.src_lang = src_lang
    inputs = tok(text, return_tensors="pt")
    tgt_id = tok.convert_tokens_to_ids(tgt_lang)
    out = mdl.generate(**inputs, forced_bos_token_id=tgt_id, max_length=128, num_beams=5, early_stopping=True)
    translation = tok.batch_decode(out, skip_special_tokens=True)[0]
    is_tif = any(c in _TIF2LAT for c in translation)
    return {"translation": translation, "tifinagh": translation if is_tif else "", "latin": _tif_to_latin(translation) if is_tif else ""}


# ---- FastAPI app -----------------------------------------------------------
app = FastAPI(title="Tachelhit NLP Service (ASR + translation + OCR)")


@app.get("/health")
def health():
    return {"status": "ok", "loaded": {"asr": _asr is not None, "nllb": _nllb is not None, "ocr": _ocr is not None}}


@app.post("/transcribe")
async def transcribe(audio_file: UploadFile = File(...)):
    suffix = os.path.splitext(audio_file.filename or "")[1] or ".mp4"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await audio_file.read())
        path = tmp.name
    try:
        full_text, segments = _transcribe_segments(path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(path):
            os.unlink(path)
    return {"rough_transcription": full_text, "corrected_transcription": full_text, "similarity_score": 1.0, "segments": segments}


@app.post("/translate")
def translate(text: str = Body(...), src_lang: str = Body("cat_Latn"), tgt_lang: str = Body("ber_Tfng")):
    try:
        return _translate(text, src_lang, tgt_lang)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ocr")
async def ocr(image: UploadFile = File(...)):
    import numpy as np
    from PIL import Image
    data = await image.read()
    arr = np.array(Image.open(io.BytesIO(data)).convert("RGB"))
    readers = _get_ocr()
    results, seen = [], set()
    for script, reader in (("latin", readers["latin"]), ("arabic", readers["arabic"])):
        for box, text, conf in reader.readtext(arr):
            text = (text or "").strip()
            if not text:
                continue
            k = text.lower()
            if k in seen:
                continue
            seen.add(k)
            results.append({"text": text, "confidence": round(float(conf), 3), "script": script, "box": [[int(x), int(y)] for x, y in box]})
    results.sort(key=lambda r: (r["box"][0][1], r["box"][0][0]))
    return {"results": results}


# ---- Gradio UI (keeps the gradio_client api_names alive) -------------------
def _asr_ui(audio_path):
    if not audio_path:
        return "Error: no audio."
    try:
        return _transcribe_segments(audio_path)[0]
    except Exception as e:
        return f"Error: {e}"


def _translate_ui(text, src_lang, tgt_lang):
    return _translate(text, src_lang, tgt_lang)["translation"]


with gr.Blocks(title="Tachelhit NLP Service") as demo:
    gr.Markdown("# Tachelhit NLP Service — ASR · Translation · OCR")
    with gr.Tab("Transcriu"):
        _a = gr.Audio(type="filepath", label="Àudio")
        _t = gr.Textbox(label="Transcripció")
        gr.Button("Transcriu").click(_asr_ui, inputs=_a, outputs=_t, api_name="predict")
    with gr.Tab("Tradueix"):
        _txt = gr.Textbox(label="Text")
        _src = gr.Dropdown(["cat_Latn", "ber_Tfng", "eng_Latn", "fra_Latn", "arb_Arab"], value="cat_Latn", label="Origen")
        _tgt = gr.Dropdown(["cat_Latn", "ber_Tfng", "eng_Latn", "fra_Latn", "arb_Arab"], value="ber_Tfng", label="Destí")
        _out = gr.Textbox(label="Traducció")
        gr.Button("Tradueix").click(_translate_ui, inputs=[_txt, _src, _tgt], outputs=_out, api_name="translate")

app = gr.mount_gradio_app(app, demo, path="/")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)
