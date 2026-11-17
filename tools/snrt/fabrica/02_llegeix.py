# -*- coding: utf-8 -*-
"""Etapa 02: del vídeo als subtítols llegits (àrab amb vot entre fotogrames, tifinag amb el lector).

  python 02_llegeix.py <carpeta> [--fils 6] [--fins SEGON] [--sense-tifinag] [--video-tifinag ALTRE.mp4]

1. `franges/NNNNN.png`: la franja de les dues línies, un fotograma per segon (ffmpeg fps=1; el fotograma k és
   l'instant k−0,5 s). Si ja hi són, no es repeteix.
2. L'àrab: cada franja es llegeix amb el model de visió de Model Studio (qwen3-vl-plus, ~170 fitxes per
   franja). Les franges idèntiques a l'anterior no s'envien (es copia la lectura). Reprèn per segon des de
   `lectures.jsonl`. Els segons seguits que diuen el mateix (≥ 0,75 de semblança) són un subtítol, i la línia es
   queda amb la lectura més votada: `linies_arab.json` (t, fi, ar, lectures, dacord).
3. El tifinag: al fotograma del mig de cada subtítol es retalla la línia de dalt (del vídeo de la carpeta o del
   `--video-tifinag`, que pot ser el mateix capítol a 1080p) i es llegeix amb `lector_tifinag.llegeix_bandes`:
   `tifinag.json`. Reprèn: els retalls ja fets a `tif/` no es tornen a treure.

Mètode de Baba Ali (tools/notebooks/llegeix_episodi_arab.py): decidir on comença i acaba un subtítol comptant
píxels no funciona; qui pot dir si dos fotogrames diuen el mateix és qui els llegeix.
"""
import argparse
import io
import json
import math
import os
import sys
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

import numpy as np
from PIL import Image
from scipy import ndimage

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comu  # noqa: E402

ETAPA = "02_llegeix"
PREGUNTA = ("This image is a strip cut from the bottom of a Moroccan TV frame. It may contain one line of "
            "ARABIC subtitle (white letters). Copy the Arabic text exactly, letter by letter. Write ONLY the "
            "Arabic: no translation, no explanation, no quotes. If there is no readable Arabic subtitle, "
            "write a single dash: -")


def treu_franges(video, carpeta, ample, alt, durada, log):
    fr = os.path.join(carpeta, "franges")
    os.makedirs(fr, exist_ok=True)
    n = len([f for f in os.listdir(fr) if f.endswith(".png")])
    if n >= math.floor(durada) - 1:
        comu.diu(log, f"franges: ja n'hi ha {n}")
        return n
    y0, y1 = comu.BANDA_720
    s = comu.escala(alt)
    import subprocess
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", video, "-vf", f"fps=1,crop={ample}:{round((y1 - y0) * s)}:0:{round(y0 * s)}",
                    os.path.join(fr, "%05d.png")], check=True)
    n = len([f for f in os.listdir(fr) if f.endswith(".png")])
    comu.diu(log, f"franges: {n} (una per segon)")
    return n


def retall_arab(alt):
    """La línia àrab dins la franja desada."""
    s = comu.escala(alt)
    return (0, round((comu.ARAB_720[0] - comu.BANDA_720[0]) * s), None, round((comu.ARAB_720[1] - comu.BANDA_720[0]) * s))


def imatge_arab(carpeta, seg, alt):
    im = Image.open(os.path.join(carpeta, "franges", f"{seg:05d}.png")).convert("RGB")
    x0, y0, _, y1 = retall_arab(alt)
    return im.crop((x0, y0, im.width, y1))


def iguals_a_l_anterior(carpeta, segons, alt):
    """Franja idèntica a la del segon anterior (soroll de compressió a part): no cal llegir-la. Llindar mesurat
    sobre «Illy»: 0 canvis de text saltats."""
    igual, prev = {}, None
    for s in segons:
        a = np.asarray(imatge_arab(carpeta, s, alt).convert("L")).astype(np.float32)
        if prev is not None and prev[0] == s - 1 and prev[1].shape == a.shape:
            d = np.abs(a - prev[1])
            igual[s] = bool(d.mean() < 2.0 and ndimage.uniform_filter(d, 5).max() < 20)
        else:
            igual[s] = False
        prev = (s, a)
    return igual


def b64(im):
    import base64
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def llegeix_franja(carpeta, seg, alt, model):
    im = imatge_arab(carpeta, seg, alt)
    t0 = time.time()
    try:
        text, u = comu.xat(model, [{"role": "user", "content": [
            {"type": "image_url", "image_url": {"url": b64(im)}}, {"type": "text", "text": PREGUNTA}]}],
            max_tokens=120, temperature=0.0)
        return {"segon": seg, "cru": text, "diu": comu.nomes_arab(text), "fitxes": u.get("total_tokens", 0), "s": round(time.time() - t0, 1)}
    except Exception as e:
        return {"segon": seg, "cru": "", "diu": "", "fitxes": 0, "s": round(time.time() - t0, 1), "error": str(e)[:160]}


def agrupa(lectures):
    """Segons seguits que diuen el mateix són un subtítol; es queda la lectura més repetida (les còpies no voten)."""
    linies, grup = [], []
    for L in sorted(lectures, key=lambda x: x["segon"]):
        L["diu"] = comu.nomes_arab(L.get("cru", ""))
        if not L["diu"] or len(L["diu"]) < 2:
            if grup:
                linies.append(grup); grup = []
            continue
        if grup and comu.s_assemblen(grup[-1]["diu"], L["diu"]) and L["segon"] - grup[-1]["segon"] <= 2:
            grup.append(L)
        else:
            if grup:
                linies.append(grup)
            grup = [L]
    if grup:
        linies.append(grup)
    fora = []
    for g in linies:
        comptes = Counter(x["diu"] for x in g if not x.get("copiada")) or Counter(x["diu"] for x in g)
        diu, quants = comptes.most_common(1)[0]
        if quants == 1 and len(g) > 1:
            diu = max((x["diu"] for x in g), key=len)
        #: el fotograma k és l'instant k−0,5: el subtítol comença entre t−0,5 i t+0,5 i acaba entre fi−0,5 i fi+0,5
        fora.append({"t": g[0]["segon"] - 1, "fi": g[-1]["segon"], "ar": diu, "lectures": sum(comptes.values()),
                     "dacord": quants, "fotogrames": len(g)})
    return fora


def rellotge_tifinag(carpeta, segons, alt):
    """El segmentador de glifs del tifinag (gratuït) com a rellotge: dos segons seguits amb els mateixos glifs a les
    mateixes posicions són el mateix subtítol. Torna {segon: True si és igual a l'anterior}. Mesurat sobre «Illy»
    contra les 1.820 lectures de l'àrab: −44 % de crides, 2 canvis de text de diàleg perduts de 650."""
    import lector_tifinag
    s_ = comu.escala(alt)
    y0 = round((comu.TIFINAG_720[0] - comu.BANDA_720[0]) * s_)
    y1 = round((comu.TIFINAG_720[1] - comu.BANDA_720[0]) * s_)

    def firma(seg):
        im = Image.open(os.path.join(carpeta, "franges", f"{seg:05d}.png")).convert("RGB")
        gs, _, _ = lector_tifinag.segmenta(np.asarray(im.crop((0, y0, im.width, y1))).astype(int))
        return (len(gs), tuple(round(g["caixa"][0] / 3) for g in gs)) if gs else None

    def iguals(a, b):
        if a is None or b is None:
            return a is None and b is None
        return a[0] == b[0] and sum(1 for x, y in zip(a[1], b[1]) if abs(x - y) <= 1) >= 0.9 * a[0]

    igual, prev = {}, None
    for s in segons:
        f = firma(s)
        igual[s] = prev is not None and prev[0] == s - 1 and iguals(prev[1], f)
        prev = (s, f)
    return igual


def tria_amb_rellotge(segons, igual):
    """Dels trams de segons iguals, el del mig (i un altre si el tram dura ≥ 3 s, per poder votar)."""
    trams, act = [], []
    for s in segons:
        if act and igual.get(s) and s == act[-1] + 1:
            act.append(s)
        else:
            if act:
                trams.append(act)
            act = [s]
    if act:
        trams.append(act)
    triats, font = set(), {}
    for t in trams:
        mig = t[len(t) // 2]
        triats.add(mig)
        if len(t) >= 3:
            triats.add(t[0] if len(t) < 5 else t[1])
        for s in t:
            font[s] = mig
    return triats, font


def llegeix_arab(carpeta, alt, segons, fils, model, log, rellotge=None):
    sortida = os.path.join(carpeta, "lectures.jsonl")
    fets = {x["segon"]: x for x in comu.jsonl_llegeix(sortida) if not x.get("error")}
    igual = iguals_a_l_anterior(carpeta, segons, alt)
    font = {}
    if rellotge == "tifinag":
        ig_t = rellotge_tifinag(carpeta, segons, alt)
        triats, font = tria_amb_rellotge(segons, ig_t)
        for s in segons:
            if s not in triats:
                igual[s] = True
        comu.diu(log, f"àrab: rellotge del tifinag, {len(triats)} fotogrames triats de {len(segons)}")
    feines = [s for s in segons if s not in fets and not igual[s]]
    comu.diu(log, f"àrab: {len(segons)} franges, {sum(igual.values())} idèntiques a l'anterior, {len(fets)} ja llegides, {len(feines)} a llegir")
    pany = threading.Lock()
    t0 = time.time()
    n = 0
    with io.open(sortida, "a", encoding="utf-8") as out, ThreadPoolExecutor(max_workers=fils) as ex:
        for r in ex.map(lambda s: llegeix_franja(carpeta, s, alt, model), feines):
            with pany:
                out.write(json.dumps(r, ensure_ascii=False) + "\n"); out.flush()
                if not r.get("error"):
                    fets[r["segon"]] = r
                n += 1
                if n % 200 == 0:
                    comu.diu(log, f"  {n}/{len(feines)} {time.time() - t0:.0f} s  {r['segon']}s {r['diu'][:40]}")
        for s in segons:   # les idèntiques: còpia; si l'anterior va fallar, es llegeix de debò
            if s in fets:
                continue
            if igual[s] and (s - 1) in fets:
                r = dict(fets[s - 1], segon=s, fitxes=0, s=0, copiada=True)
            else:
                r = llegeix_franja(carpeta, s, alt, model)
            out.write(json.dumps(r, ensure_ascii=False) + "\n"); out.flush()
            if not r.get("error"):
                fets[s] = r
    lectures = [fets[s] for s in segons if s in fets]
    linies = agrupa(lectures)
    with io.open(os.path.join(carpeta, "linies_arab.json"), "w", encoding="utf-8") as f:
        json.dump(linies, f, ensure_ascii=False, indent=1)
    fitxes = sum(x.get("fitxes", 0) for x in lectures)
    comu.diu(log, f"àrab: {len(linies)} subtítols, {fitxes} fitxes, {len(segons) - len(lectures)} franges sense lectura, {time.time() - t0:.0f} s")
    return linies, {"lectures": len(lectures), "copiades": sum(1 for x in lectures if x.get("copiada")), "fitxes_visio": fitxes,
                    "errors": len(segons) - len(lectures), "subtitols": len(linies), "model_visio": model}


def llegeix_tifinag(carpeta, linies, video, log):
    import subprocess
    import lector_tifinag
    ample, alt, _ = comu.mida_video(video)
    caixa = comu.caixa(comu.TIFINAG_720, alt, ample)
    tifdir = os.path.join(carpeta, "tif")
    os.makedirs(tifdir, exist_ok=True)
    imatges = []
    for k, L in enumerate(linies):
        t = (L["t"] + L["fi"]) / 2
        desti = os.path.join(tifdir, f"{k:04d}.png")
        if not os.path.exists(desti):
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", video, "-frames:v", "1", "-vf",
                            f"crop={caixa[2] - caixa[0]}:{caixa[3] - caixa[1]}:{caixa[0]}:{caixa[1]}", desti], check=False)
        try:
            imatges.append(np.asarray(Image.open(desti).convert("RGB")))
        except Exception:
            imatges.append(None)
    lect = lector_tifinag.llegeix_bandes(imatges, log=lambda s: comu.diu(log, s))
    for k, (L, r) in enumerate(zip(linies, lect)):
        r["k"] = k; r["t_mig"] = (L["t"] + L["fi"]) / 2
    with io.open(os.path.join(carpeta, "tifinag.json"), "w", encoding="utf-8") as f:
        json.dump(lect, f, ensure_ascii=False, indent=1)
    amb = sum(1 for r in lect if r["tifinag"])
    glifs = sum(r["n_glifs"] for r in lect)
    dubt = sum(r["n_dubtosos"] for r in lect)
    comu.diu(log, f"tifinag: {amb} de {len(lect)} subtítols amb text, {glifs} glifs, {dubt} dubtosos (< {lector_tifinag.LLINDAR}), vídeo de {alt}p")
    return {"tifinag_amb_text": amb, "tifinag_glifs": glifs, "tifinag_dubtosos": dubt, "tifinag_alt": alt,
            "lector_tifinag": "plantilles aslmdtv"}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("carpeta")
    ap.add_argument("--fils", type=int, default=6)
    ap.add_argument("--fins", type=int, default=0, help="només fins a aquest segon (per provar)")
    ap.add_argument("--model", default=os.environ.get("TD_MODEL_VISIO", "qwen3-vl-plus"))
    ap.add_argument("--sense-tifinag", action="store_true")
    ap.add_argument("--video-tifinag", default=None, help="un altre fitxer del mateix capítol (1080p) per al tifinag")
    ap.add_argument("--rellotge", default=None, choices=[None, "tifinag"],
                    help="«tifinag»: només llegir l'àrab d'un fotograma per tram de glifs iguals (−44 %% de crides)")
    a = ap.parse_args()
    comu.carrega_env()
    carpeta = os.path.abspath(a.carpeta)
    video = comu.video_de(carpeta)
    ample, alt, durada = comu.mida_video(video)
    log = io.open(os.path.join(carpeta, "fabrica.log"), "a", encoding="utf-8")
    comu.diu(log, f"== {ETAPA} {time.strftime('%Y-%m-%d %H:%M')} {os.path.basename(video)} {ample}x{alt} {durada:.0f} s")
    comu.estat_desa(carpeta, video=os.path.basename(video), ample=ample, alt=alt, durada=round(durada, 1))
    t0 = time.time()
    n = treu_franges(video, carpeta, ample, alt, durada, log)
    segons = list(range(1, n + 1))
    if a.fins:
        segons = [s for s in segons if s <= a.fins]
    linies, est = llegeix_arab(carpeta, alt, segons, a.fils, a.model, log, rellotge=a.rellotge)
    est["franges"] = n
    est["rellotge"] = a.rellotge or "1 fotograma per segon"
    if not a.sense_tifinag:
        vt = os.path.abspath(a.video_tifinag) if a.video_tifinag else video
        est.update(llegeix_tifinag(carpeta, linies, vt, log))
    est["segons"] = round(time.time() - t0)
    est["fet"] = not a.fins
    comu.estat_desa(carpeta, ETAPA, **est)
    comu.diu(log, f"{ETAPA}: fet en {est['segons']} s")


if __name__ == "__main__":
    main()
