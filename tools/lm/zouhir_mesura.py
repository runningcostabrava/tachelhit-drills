# -*- coding: utf-8 -*-
"""Vídeos amb pista amaziga HUMANA en tifinag (penjada sota un codi de llengua qualsevol: «ak»,
«af»…) alineada rètol a rètol amb anglès, àrab i francès. Dues coses alhora:

  1. la mesura: cada rètol es talla del so i es passa pel nostre lector (greedy i feix amb lèxic),
     i es compara amb la pista humana transliterada → CER/WER, el mateix codi que a H3;
  2. el corpus paral·lel: (so, tifinag, llatí, en, ar, fr) per rètol, en un JSON, per a H4 i per
     a l'inducció de glosses. No entra res a la biblioteca: és material de tercers.

ÚS: zouhir_mesura.py <carpeta> <video_id> --pista ak [--ruta /transcribe_mms_lm] [--space URL]
    <carpeta>/wav/<id>.wav i <carpeta>/subs/<id>.<pista>.vtt (+ .en/.ar/.fr.vtt si hi són)
    → <carpeta>/mesura/<id>.json
"""
import io
import json
import os
import re
import subprocess
import sys
import tempfile

ARREL = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ARREL, "backend"))
sys.path.insert(0, os.path.join(ARREL, "tools", "lm"))
from dotenv import load_dotenv      # noqa: E402
load_dotenv(os.path.join(ARREL, "backend", ".env"))
from transliteration import to_forms    # noqa: E402
import h3_puntua                        # noqa: E402

SPACE = "https://josepabloucr-huggingface-asr-space.hf.space"


def arg(nom, defecte=None):
    a = sys.argv
    return a[a.index(nom) + 1] if nom in a else defecte


def segons(t):
    h, m, s = t.replace(",", ".").split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def vtt(cami):
    """[(de, a, text)] — els rètols, amb les etiquetes fora i les línies ajuntades."""
    if not cami or not os.path.exists(cami):
        return []
    fora, de = [], None
    for l in io.open(cami, encoding="utf-8"):
        l = l.strip()
        m = re.match(r"(\d\d:\d\d:\d\d\.\d+) --> (\d\d:\d\d:\d\d\.\d+)", l)
        if m:
            de = (segons(m.group(1)), segons(m.group(2)))
            fora.append([de[0], de[1], ""])
        elif de and l and not l.startswith(("WEBVTT", "Kind:", "Language:")):
            fora[-1][2] = (fora[-1][2] + " " + re.sub(r"<[^>]+>", "", l)).strip()
    return [tuple(x) for x in fora if x[2]]


def casa(base, altres):
    """El rètol d'una altra pista que més se solapa en temps amb el rètol base."""
    millor, score = "", 0
    for de, a, t in altres:
        s = min(a, base[1]) - max(de, base[0])
        if s > score:
            millor, score = t, s
    return millor


def talla(wav, de, a, fora):
    subprocess.run(["ffmpeg", "-v", "quiet", "-y", "-ss", f"{max(0, de - 0.1):.3f}", "-to", f"{a + 0.1:.3f}",
                    "-i", wav, "-ac", "1", "-ar", "16000", fora], check=True)


def sent(cami, ruta, caps):
    import requests
    with io.open(cami, "rb") as f:
        r = requests.post(SPACE_URL + ruta, files={"audio_file": ("c.wav", f.read(), "audio/wav")},
                          headers=caps, timeout=300)
    r.raise_for_status()
    return (r.json().get("text") or "").strip()


if __name__ == "__main__":
    carpeta, vid = sys.argv[1], sys.argv[2]
    pista = arg("--pista", "ak")
    rutes = arg("--ruta", "/transcribe_mms,/transcribe_mms_lm").split(",")
    SPACE_URL = arg("--space", SPACE)
    caps = {"Authorization": "Bearer " + os.environ["HF_TOKEN"]} if os.environ.get("HF_TOKEN") else {}
    wav = os.path.join(carpeta, "wav", vid + ".wav")
    sub = lambda l: vtt(os.path.join(carpeta, "subs", f"{vid}.{l}.vtt"))
    amazic = sub(pista)
    altres = {l: sub(l) for l in ("en", "ar", "fr", "en-US")}
    print(f"{vid}: {len(amazic)} rètols amazics · " + " ".join(f"{l}={len(x)}" for l, x in altres.items() if x))
    versos = []
    tmp = tempfile.mkdtemp()
    for i, (de, a, tif) in enumerate(amazic):
        f = to_forms(tif)
        v = {"video": vid, "n": i, "de": round(de, 3), "a": round(a, 3), "tifinag": tif,
             "veritat": f["clean_latin"], "mena": "parlat"}
        for l, xs in altres.items():
            if xs:
                v[l] = casa((de, a), xs)
        tros = os.path.join(tmp, f"{i}.wav")
        talla(wav, de, a, tros)
        for ruta in rutes:
            try:
                v[ruta.strip("/")] = sent(tros, ruta, caps)
            except Exception as e:
                v[ruta.strip("/")] = None
                print("  ", i, ruta, type(e).__name__, str(e)[:60])
        versos.append(v)
        print(f"{i:3} {v['veritat'][:48]:48} | {(v.get('transcribe_mms_lm') or v.get('transcribe_mms') or '')[:48]}", flush=True)
    os.makedirs(os.path.join(carpeta, "mesura"), exist_ok=True)
    res = {"video": vid, "pista": pista, "versos": versos, "puntuacio": {}}
    for ruta in rutes:
        clau = ruta.strip("/")
        amb = [v for v in versos if v.get(clau) is not None]
        if amb:
            res["puntuacio"][clau] = h3_puntua.puntua(amb, clau, "parlat", plegat=False)
    json.dump(res, io.open(os.path.join(carpeta, "mesura", vid + ".json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(res["puntuacio"], ensure_ascii=False))
