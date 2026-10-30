"""The second reader in this Space: facebook/mms-1b-all with our fine-tuned `shi` adapter.

On the first test set that is clean of every training source and speaker (Common Voice zgh test,
256 clips, 26 speakers, 29-10-2026), MMS with our adapter (corpus v3, «c»→š and «x»→ḫ so the
targets are not erased) reads at a CER of 0.154, against 0.210 for MMS alone and 0.230 for the
wav2vec2 model we had. Since ADR 0009 the adapter is trained on the rich letters instead of text
folded to 26: CER 0.144 on that same test and 0.291 against 0.339 on test-fora, measured unfolded.
It writes Latin in the MMS `shi` alphabet, where ɣ is ġ and ɛ is ε; ṛ is not in it.

It lives next to NeMo instead of replacing it: NeMo writes Tifinagh, /align is built on it, and
parts of the backend expect that output. HuggingFace no longer lets a free account create a new
Docker Space, so this one hosts both. The base model is 3.9 GB: it loads in a background thread at
start-up, and /transcribe_mms answers 503 until it is ready instead of blocking NeMo's routes.

Output is a proposal: downstream it goes to `*_suggested`, never to a speaker's text.
"""
import math
import os
import threading

import librosa
import numpy as np
import torch

BASE = "facebook/mms-1b-all"
LANG = "shi"
ADAPTER = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"adaptador_{LANG}_ric.pt")
MODEL_ID = f"{BASE}+adaptador_{LANG}_ric(tamazight-drills, corpus sencer)"
SR = 16000
#: MMS was trained on utterances: a long file is read in windows that overlap a little, so a
#: word cut at one edge is heard whole in the other.
WINDOW_S, STRIDE_S = 30.0, 28.0
FRAME_S = 0.02          # wav2vec2: one output frame per 320 samples at 16 kHz
PAUSE_S = 0.6

_state = {"proc": None, "model": None, "error": None}
_lock = threading.Lock()


def _load():
    try:
        from transformers import AutoModelForCTC, AutoProcessor
        proc = AutoProcessor.from_pretrained(BASE)
        proc.tokenizer.set_target_lang(LANG)
        model = AutoModelForCTC.from_pretrained(BASE)
        model.load_adapter(LANG)
        adapter = torch.load(ADAPTER, map_location="cpu")
        known = dict(model.named_parameters())
        unknown = [k for k in adapter if k not in known]
        if unknown:
            raise RuntimeError(f"adapter keys the model does not have: {unknown[:5]}")
        model.load_state_dict(adapter, strict=False)
        model.eval()
        _state.update(proc=proc, model=model)
        print("[MMS] model + shi adapter loaded")
    except Exception as e:  # NeMo keeps working; this route reports why it cannot
        _state["error"] = str(e)
        print(f"[MMS] failed to load: {e}")


def start():
    threading.Thread(target=_load, daemon=True).start()


def status() -> dict:
    return {"model": MODEL_ID, "ready": _state["model"] is not None, "error": _state["error"]}


def _decode(ids, probs, t0, vocab, blank, space):
    words, conf, cur, start, last, prev = [], [], [], None, None, None
    for k, (i, p) in enumerate(zip(ids, probs)):
        if i == prev:
            continue
        prev = i
        if i == blank:
            continue
        tok = vocab.get(int(i), "")
        conf.append(float(p))
        t = t0 + k * FRAME_S
        if tok in (space, " "):
            if cur:
                words.append({"text": "".join(cur), "start": round(start, 2), "end": round(last + FRAME_S, 2)})
            cur, start = [], None
            continue
        if start is None:
            start = t
        last = t
        cur.append(tok)
    if cur:
        words.append({"text": "".join(cur), "start": round(start, 2), "end": round(last + FRAME_S, 2)})
    return words, conf


def transcribe(path: str, max_secs: float) -> dict:
    proc, model = _state["proc"], _state["model"]
    if model is None:
        raise RuntimeError(_state["error"] or "MMS is still loading")
    wav, _ = librosa.load(path, sr=SR, mono=True)
    if len(wav) / SR > max_secs:
        raise ValueError(f"audio longer than {max_secs:.0f} s")
    vocab = {v: k for k, v in proc.tokenizer.get_vocab().items()}
    blank, space = proc.tokenizer.pad_token_id, proc.tokenizer.word_delimiter_token
    words, conf = [], []
    w, s, off = int(WINDOW_S * SR), int(STRIDE_S * SR), 0
    while True:
        ent = proc(wav[off:off + w], sampling_rate=SR, return_tensors="pt")
        with _lock, torch.no_grad():
            best = model(**ent).logits[0].softmax(-1).max(-1)
        ww, cc = _decode(best.indices.tolist(), best.values.tolist(), off / SR, vocab, blank, space)
        if words:
            ww = [x for x in ww if x["start"] >= words[-1]["end"] - 0.05]
        words += ww
        conf += cc
        if off + w >= len(wav):
            break
        off += s
    text = " ".join(x["text"] for x in words).strip()
    segs, cur = [], []
    for x in words:
        if cur and x["start"] - cur[-1]["end"] > PAUSE_S:
            segs.append(cur)
            cur = []
        cur.append(x)
    if cur:
        segs.append(cur)
    # Mean probability of the characters it wrote: a ranking hint for the review queue, not a
    # promise. No characters, no number.
    c = round(float(math.exp(np.mean(np.log(np.clip(conf, 1e-6, 1.0))))), 3) if conf else None
    return {"text": text, "words": words, "confidence": c, "model": MODEL_ID, "alphabet": "latin-shi",
            "segments": [{"start": g[0]["start"], "end": g[-1]["end"], "text": " ".join(x["text"] for x in g)} for g in segs]}
