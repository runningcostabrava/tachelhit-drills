# -*- coding: utf-8 -*-
"""Etapa 02: del vídeo a les rèpliques llegides (àrab i tifinag), seguint §4 de l'especificació.

  python -X utf8 02_llegeix.py <carpeta_del_capitol> [--fils 6] [--fins SEGON] [--sense-tifinag] [--un-per-segon] [--lector-arab visio|propi]

1. `franges/NNNNN.png`: la franja de les dues línies, un fotograma per segon (el fotograma k és l'instant k−0,5).
2. **Comprovació de la geometria** amb 10 fotogrames: cal veure la línia del tifinag a y 588–608 i la de l'àrab a
   y 615–650 (en 720p) en almenys 3 dels 10; si no, l'etapa s'atura amb error a `estat.json`.
3. **El rellotge el posa el tifinag:** el segmentador de glifs (gratuït) diu quins segons seguits tenen els mateixos
   glifs a les mateixes posicions: un tram. De cada tram es llegeix l'àrab d'UN fotograma (el del mig) amb el lector
   de visió (qwen3-vl-plus mentre no hi hagi el propi), i un segon només si la lectura és buida, curta (< 6
   caràcters) o dona error. Les franges idèntiques a l'anterior se salten. Les lectures es desen per segon a
   `lectures.jsonl` i es reutilitzen (reprendre = no tornar a pagar). Els trams veïns que diuen el mateix s'ajunten.
   `--un-per-segon` és el mètode antic (totes les franges, vot entre fotogrames): el de la prova d'«Illy».
   `--lector-arab propi` (#601, §6.3): l'àrab es llegeix amb el CRNN propi (`lector_arab.py`), SENSE cap crida de visió, sobre un fotograma
   de 1080p (o 720p pujat, no mesurat) retallat a x 110–1560 (fora el logotip): dos fotogrames per tram (el del mig i un quart), i la rèplica
   porta `arab_lector` = «crnn-v4», `arab_conf` (mínima probabilitat dels símbols) i `arab_dubtos` (cert si les dues lectures discrepen, n'hi ha
   una de buida, el text és molt curt o `conf` < 0,60). Les lectures es desen a `lectures_crnn.jsonl` per segon i es reprenen. Candidat: no substitueix el visió.
4. El tifinag es llegeix al fotograma del mig de cada rèplica amb `lector_tifinag.llegeix_bandes` (per plantilles
   d'aslmdtv mentre no hi hagi el sintètic), sobre `video_1080.mp4` si hi és.
5. `credits`: més de 3 línies de text al fotograma, o text idèntic repetit més de 20 s en total (capçalera, rodolí).
Surt `subtitols.jsonl` amb els camps d'OCR de §3.3 (els ids `<slug>_<k:04d>` no canvien si es torna a córrer amb
les mateixes lectures: el càlcul és determinista) i `tif/<k>.png` (la franja del tifinag de cada rèplica).
"""
import argparse
import base64
import io
import json
import math
import os
import subprocess
import sys
import threading
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor

import numpy as np
from PIL import Image
from scipy import ndimage

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comu  # noqa: E402

ETAPA = "02_llegeix"
LECTOR_ARAB = os.environ.get("TD_MODEL_VISIO", "qwen3-vl-plus")
PREGUNTA = ("This image is a strip cut from the bottom of a Moroccan TV frame. It may contain one line of "
            "ARABIC subtitle (white letters). Copy the Arabic text exactly, letter by letter. Write ONLY the "
            "Arabic: no translation, no explanation, no quotes. If there is no readable Arabic subtitle, "
            "write a single dash: -")
CURTA = 6          # una lectura amb menys caràcters demana un segon fotograma
REPETIT_S = 20     # text idèntic repetit més d'això en total = capçalera o rodolí (credits)
MAX_LINIES = 3     # més línies de text que això al fotograma = crèdits


# ---------- franges i geometria ----------
def treu_franges(video, carpeta, ample, alt, durada, log):
    fr = os.path.join(carpeta, "franges")
    os.makedirs(fr, exist_ok=True)
    n = len([f for f in os.listdir(fr) if f.endswith(".png")])
    if n >= math.floor(durada) - 1:
        comu.diu(log, f"franges: ja n'hi ha {n}")
        return n
    y0, y1 = comu.BANDA_720
    s = comu.escala(alt)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", video, "-vf", f"fps=1,crop={ample}:{round((y1 - y0) * s)}:0:{round(y0 * s)}",
                    os.path.join(fr, "%05d.png")], check=True)
    n = len([f for f in os.listdir(fr) if f.endswith(".png")])
    comu.diu(log, f"franges: {n} (una per segon)")
    return n


def fotograma_gris_petit(video, t, ample_petit=640):
    """El fotograma sencer a {t} s, en gris i petit, pel tub (sense desar-lo): per comptar línies de text."""
    out = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.2f}", "-i", video, "-frames:v", "1", "-vf",
                          f"scale={ample_petit}:-1,format=gray", "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True).stdout
    if not out:
        return None
    return np.asarray(Image.open(io.BytesIO(out)))


def linies_de_text(gris):
    """Quantes línies de text hi ha al fotograma: files amb prou píxels blancs TOCANT píxels foscos (lletra amb vora,
    no una paret clara), agrupades, i només els grups de 3 files o més. Calibrat a l'entrevista (640 px d'ample):
    diàleg 1–2, targeta del títol 3, rodolí de crèdits de moltes línies > 3. Un rodolí d'UNA línia per nom (com el final
    d'aquesta entrevista) no es distingeix del diàleg per la forma: per això hi ha `credits_limits`."""
    if gris is None:
        return 0
    blanc = gris > 215
    vora = blanc & ndimage.binary_dilation(gris < 70, iterations=2)
    files = vora.sum(axis=1) >= 0.02 * gris.shape[1]
    n, alt = 0, 0
    for v in files:
        if v:
            alt += 1
            if alt == 3:
                n += 1
        else:
            alt = 0
    return n


def decideix_ordre(carpeta, video, ample, alt, durada, log):
    """#601: quina línia és tifinag i quina àrab, pel tipus de caràcter i no per la posició (hi ha sèries amb l'àrab a dalt). Si l'ordre és invertit, les franges
    d'aquest capítol es calculen amb la geometria detectada i es desa `geometria.json` (la 05 la fa servir). Si no es pot decidir, OrdreIndecis atura l'etapa."""
    import ordre_linies
    if comu.carrega_geometria(carpeta):
        comu.diu(log, "ordre de les línies: geometria.json del capítol (ja decidida)")
        return "invertit"
    r = ordre_linies.ordre_del_video(video, ample, alt, durada, log=lambda m: comu.diu(log, m))
    if r["ordre"] == "invertit":
        g = comu.geometria_de_linies(r["geometria"]["tifinag_720"], r["geometria"]["arab_720"])
        comu.aplica_geometria(g)
        comu.desa_geometria(carpeta, g)
        comu.diu(log, f"AVÍS: l'àrab és a dalt i el tifinag a sota: geometria del capítol {g}")
    return r["ordre"]


def comprova_geometria(video, ample, alt, durada, log):
    """§4: 10 fotogrames repartits; en ≥ 3 hi ha d'haver text blanc a la línia del tifinag i a la de l'àrab."""
    s = comu.escala(alt)
    # Les franges de cada línia, derivades de la geometria vigent (les per defecte donen 584–612, 613–656 i «sobre» 540–580; en una sèrie amb l'ordre invertit, les detectades)
    tif = (round((comu.TIFINAG_720[0] + 4) * s), round((comu.TIFINAG_720[1] - 2) * s))
    ara = (round((comu.ARAB_720[0] + 1) * s), round(comu.ARAB_720[1] * s))
    sobre = (round((comu.BANDA_720[0] - 36) * s), round((comu.BANDA_720[0] + 4) * s))
    bones = 0
    for k in range(1, 11):
        t = durada * k / 11
        out = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.2f}", "-i", video, "-frames:v", "1", "-f", "image2pipe",
                              "-vcodec", "png", "-"], capture_output=True).stdout
        if not out:
            continue
        a = np.asarray(Image.open(io.BytesIO(out)).convert("RGB")).astype(int)
        blanc = (a.min(axis=2) > 200) & ((a.max(axis=2) - a.min(axis=2)) < 45)
        prof = blanc.sum(axis=1)
        te_tif = prof[tif[0]:tif[1]].max() >= 8 if tif[1] <= len(prof) else False
        te_ara = prof[ara[0]:ara[1]].max() >= 8 if ara[1] <= len(prof) else False
        # i que la franja de SOBRE el tifinag sigui buida: si hi ha text més amunt, no és la geometria coneguda
        buit_sobre = prof[sobre[0]:sobre[1]].max() < 8
        if te_tif and te_ara and buit_sobre:
            bones += 1
    comu.diu(log, f"geometria: {bones} de 10 fotogrames amb les dues línies on toca")
    return bones


# ---------- àrab ----------
def retall_arab(alt):
    s = comu.escala(alt)
    return (round((comu.ARAB_720[0] - comu.BANDA_720[0]) * s), round((comu.ARAB_720[1] - comu.BANDA_720[0]) * s))


def retall_tifinag(alt):
    s = comu.escala(alt)
    return (round((comu.TIFINAG_720[0] - comu.BANDA_720[0]) * s), round((comu.TIFINAG_720[1] - comu.BANDA_720[0]) * s))


def franja(carpeta, seg):
    return Image.open(os.path.join(carpeta, "franges", f"{seg:05d}.png")).convert("RGB")


def imatge_arab(carpeta, seg, alt):
    im = franja(carpeta, seg)
    y0, y1 = retall_arab(alt)
    return im.crop((0, y0, im.width, y1))


def b64(im):
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def llegeix_franja(carpeta, seg, alt):
    t0 = time.time()
    try:
        text, u = comu.xat(LECTOR_ARAB, [{"role": "user", "content": [
            {"type": "image_url", "image_url": {"url": b64(imatge_arab(carpeta, seg, alt))}}, {"type": "text", "text": PREGUNTA}]}],
            max_tokens=120, temperature=0.0)
        return {"segon": seg, "cru": text, "diu": comu.nomes_arab(text), "fitxes": u.get("total_tokens", 0),
                "s": round(time.time() - t0, 1), "lector": LECTOR_ARAB}
    except Exception as e:
        return {"segon": seg, "cru": "", "diu": "", "fitxes": 0, "s": round(time.time() - t0, 1), "error": str(e)[:160], "lector": LECTOR_ARAB}


class Lectures:
    """La memòria de lectures per segon (lectures.jsonl): el que ja s'ha pagat no es torna a pagar."""

    def __init__(self, carpeta, alt):
        self.carpeta, self.alt = carpeta, alt
        self.p = os.path.join(carpeta, "lectures.jsonl")
        self.fets = {x["segon"]: x for x in comu.jsonl_llegeix(self.p) if not x.get("error")}
        self.out = io.open(self.p, "a", encoding="utf-8")
        self.pany = threading.Lock()
        self.noves = 0
        self.fitxes_noves = 0

    def te(self, seg):
        return seg in self.fets

    def llegeix(self, seg):
        if seg in self.fets:
            return self.fets[seg]
        r = llegeix_franja(self.carpeta, seg, self.alt)
        with self.pany:
            self.out.write(json.dumps(r, ensure_ascii=False) + "\n"); self.out.flush()
            self.noves += 1; self.fitxes_noves += r.get("fitxes", 0)
            if not r.get("error"):
                self.fets[seg] = r
        return r

    def copia(self, seg, de):
        r = dict(self.fets[de], segon=seg, fitxes=0, s=0, copiada=True)
        with self.pany:
            self.out.write(json.dumps(r, ensure_ascii=False) + "\n"); self.out.flush()
            self.fets[seg] = r
        return r


def iguals_a_l_anterior(carpeta, segons, alt):
    """Franja de l'àrab idèntica a la del segon anterior (soroll de compressió a part): no cal llegir-la.
    Llindar mesurat sobre «Illy»: 0 canvis de text saltats."""
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


# ---------- el rellotge del tifinag ----------
def trams_del_tifinag(carpeta, segons, alt, log):
    """Segons seguits amb els mateixos glifs a les mateixes posicions a la línia de dalt = un tram. Els segons sense
    cap glif no són cap subtítol. Mesurat (Illy, 1080p; entrevista, 720p): el rellotge parteix de més (1,7–2,4 trams per
    subtítol) i salta pocs canvis de text; els trams veïns que diuen el mateix s'ajunten després."""
    import lector_tifinag
    y0, y1 = retall_tifinag(alt)

    def firma(seg):
        im = franja(carpeta, seg)
        gs, _, _ = lector_tifinag.segmenta(np.asarray(im.crop((0, y0, im.width, y1))).astype(int))
        return (len(gs), tuple(round(g["caixa"][0] / 3) for g in gs)) if gs else None

    def iguals(a, b):
        if a is None or b is None:
            return a is None and b is None
        return a[0] == b[0] and sum(1 for x, y in zip(a[1], b[1]) if abs(x - y) <= 1) >= 0.9 * a[0]

    trams, act, prev = [], [], None
    for s in segons:
        f = firma(s)
        if act and s == act[-1] + 1 and iguals(prev, f):
            act.append(s)
        else:
            if act and prev is not None:
                trams.append(act)
            act = [s]
        prev = f
    if act and prev is not None:
        trams.append(act)
    comu.diu(log, f"rellotge del tifinag: {len(trams)} trams amb glifs en {len(segons)} segons")
    return trams


def llegeix_trams(carpeta, trams, alt, igual, fils, log):
    """Un fotograma per tram (el del mig), un segon si cal. Torna rèpliques (abans d'ajuntar)."""
    L = Lectures(carpeta, alt)
    migs = []
    for t in trams:
        mig = t[len(t) // 2]
        # si la franja del mig és idèntica a l'anterior i aquella ja és llegida, reutilitza-la
        while igual.get(mig) and (mig - 1) in L.fets and mig - 1 >= t[0]:
            mig -= 1
        migs.append(mig)
    pendents = [m for m in set(migs) if not L.te(m)]
    comu.diu(log, f"àrab: {len(trams)} trams, {len(pendents)} fotogrames a llegir (la resta ja llegits)")
    with ThreadPoolExecutor(max_workers=fils) as ex:
        list(ex.map(L.llegeix, pendents))
    fora = []
    for t, mig in zip(trams, migs):
        r = L.fets.get(mig) or L.llegeix(mig)
        diu = comu.nomes_arab(r.get("cru", "")) if not r.get("error") else ""
        dits = [diu]
        if len(diu) < CURTA or r.get("error"):
            alt2 = t[0] if mig != t[0] else t[-1]
            if alt2 != mig:
                r2 = L.llegeix(alt2)
                d2 = comu.nomes_arab(r2.get("cru", "")) if not r2.get("error") else ""
                dits.append(d2)
                if len(d2) > len(diu):
                    diu = d2
        if not diu:
            continue
        dacord = sum(1 for d in dits if d and (d == diu or comu.s_assemblen(d, diu)))
        fora.append({"t_ini": t[0] - 1, "t_fi": t[-1], "arab": diu, "arab_lectures": len([d for d in dits if d]), "arab_dacord": dacord})
    return fora, {"crides_visio": L.noves, "fitxes_visio": L.fitxes_noves, "fotogrames_llegits": len(set(migs))}


# ---------- l'àrab amb el lector propi (sense visió) ----------
LECTURES_PROPI = "lectures_crnn.jsonl"


def instants_del_tram(t):
    """Dos fotogrames per tram: el del mig i el d'un quart (si el tram té ≥ 2 segons). Surten segons de l'etapa (instant = segon − 0,5)."""
    mig = t[len(t) // 2]
    quart = t[len(t) // 4] if len(t) >= 2 else mig
    if quart == mig and len(t) >= 2:
        quart = t[-1] if mig != t[-1] else t[0]
    return [mig] if quart == mig else [mig, quart]


def fotograma_banda(video, seg, alt, y0_720, lector_arab):
    """La banda d'àrab del fotograma de l'instant seg−0,5, pel tub, en PIL (retall del `lector_arab`)."""
    out = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{max(0.0, seg - 0.5):.2f}", "-i", video, "-frames:v", "1", "-vf",
                          lector_arab.retall_ffmpeg(alt, y0_720), "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True).stdout
    return Image.open(io.BytesIO(out)).convert("RGB") if out else None


def llegeix_trams_propi(carpeta, trams, video_arab, alt, fils, log):
    """Un fotograma d'àrab per tram (dos si el tram dura ≥ 2 s) llegit amb el CRNN propi, sense cap crida de visió. Torna rèpliques abans d'ajuntar."""
    import lector_arab
    p = os.path.join(carpeta, LECTURES_PROPI)
    fets = {x["segon"]: x for x in comu.jsonl_llegeix(p) if not x.get("error")}
    pany = threading.Lock()
    punts = {s for t in trams for s in instants_del_tram(t)}
    pendents = sorted(s for s in punts if s not in fets)
    comu.diu(log, f"àrab (lector propi {lector_arab.NOM}): {len(trams)} trams, {len(pendents)} fotogrames a llegir (la resta ja llegits)")
    out = io.open(p, "a", encoding="utf-8")
    lector_arab.carrega()   # un cop, abans dels fils

    def un(seg):
        t0 = time.time()
        try:
            im = fotograma_banda(video_arab, seg, alt, comu.ARAB_720[0], lector_arab)
            if im is None:
                raise RuntimeError("ffmpeg no ha tret el fotograma")
            r = lector_arab.llegeix_arab(im)
            fila = {"segon": seg, "cru": r["arab"], "diu": comu.nomes_arab(r["arab"]), "conf": round(r["conf"], 4),
                    "conf_mitjana": round(r["conf_mitjana"], 4), "lector": lector_arab.NOM, "alt_video": alt, "s": round(time.time() - t0, 2)}
        except Exception as e:
            fila = {"segon": seg, "cru": "", "diu": "", "conf": 0.0, "error": str(e)[:160], "lector": lector_arab.NOM}
        with pany:
            out.write(json.dumps(fila, ensure_ascii=False) + "\n"); out.flush()
            if not fila.get("error"):
                fets[seg] = fila
        return fila

    with ThreadPoolExecutor(max_workers=max(1, min(fils, 4))) as ex:
        list(ex.map(un, pendents))
    fora = []
    for t in trams:
        lect = [{"arab": fets[s]["diu"], "conf": fets[s]["conf"]} if s in fets else {"arab": "", "conf": 0.0} for s in instants_del_tram(t)]
        diu, conf, dubtos, n, dacord = lector_arab.decideix(lect)
        if not diu:
            continue
        fora.append({"t_ini": t[0] - 1, "t_fi": t[-1], "arab": diu, "arab_lectures": n, "arab_dacord": dacord, "arab_conf": round(conf, 4), "arab_dubtos": dubtos})
    return fora, {"crides_visio": 0, "fitxes_visio": 0, "fotogrames_llegits": len(punts), "fotogrames_nous": len(pendents), "lector_arab": lector_arab.NOM}


def llegeix_un_per_segon(carpeta, segons, alt, igual, fils, log):
    """El mètode de la prova d'«Illy»: totes les franges, vot entre fotogrames (car: 1 fotograma per segon)."""
    L = Lectures(carpeta, alt)
    pendents = [s for s in segons if not L.te(s) and not igual[s]]
    comu.diu(log, f"àrab (1 per segon): {len(pendents)} franges a llegir, {sum(igual.values())} idèntiques")
    with ThreadPoolExecutor(max_workers=fils) as ex:
        list(ex.map(L.llegeix, pendents))
    for s in segons:
        if not L.te(s):
            if igual[s] and L.te(s - 1):
                L.copia(s, s - 1)
            else:
                L.llegeix(s)
    linies, grup = [], []
    for s in segons:
        r = L.fets.get(s)
        diu = comu.nomes_arab(r.get("cru", "")) if r and not r.get("error") else ""
        if len(diu) < 2:
            if grup:
                linies.append(grup); grup = []
            continue
        if grup and comu.s_assemblen(grup[-1][1], diu) and s - grup[-1][0] <= 2:
            grup.append((s, diu, r.get("copiada", False)))
        else:
            if grup:
                linies.append(grup)
            grup = [(s, diu, r.get("copiada", False))]
    if grup:
        linies.append(grup)
    fora = []
    for g in linies:
        comptes = Counter(d for _, d, c in g if not c) or Counter(d for _, d, _ in g)
        diu, quants = comptes.most_common(1)[0]
        fora.append({"t_ini": g[0][0] - 1, "t_fi": g[-1][0], "arab": diu, "arab_lectures": sum(comptes.values()), "arab_dacord": quants})
    return fora, {"crides_visio": L.noves, "fitxes_visio": L.fitxes_noves, "fotogrames_llegits": len(segons) - sum(igual.values())}


def ajunta(repliques):
    """Trams veïns que diuen el mateix (≥ 0,75, buit ≤ 1 s) són una sola rèplica."""
    fora = []
    for r in sorted(repliques, key=lambda x: x["t_ini"]):
        if fora and comu.s_assemblen(fora[-1]["arab"], r["arab"]) and r["t_ini"] - fora[-1]["t_fi"] <= 1:
            u = fora[-1]
            u["t_fi"] = max(u["t_fi"], r["t_fi"]); u["arab_lectures"] += r["arab_lectures"]; u["arab_dacord"] += r["arab_dacord"]
            if "arab_dubtos" in r:   # lector propi: la rèplica ajuntada és dubtosa si ho era algun tram, i en conserva la pitjor confiança
                u["arab_dubtos"] = bool(u.get("arab_dubtos")) or r["arab_dubtos"]
                u["arab_conf"] = min(u["arab_conf"], r["arab_conf"])
            if len(r["arab"]) > len(u["arab"]):
                u["arab"] = r["arab"]
        else:
            fora.append(dict(r))
    return fora


# ---------- tifinag i crèdits ----------
def llegeix_tifinag(carpeta, repliques, video, video720, log):
    import lector_tifinag
    ample, alt, _ = comu.mida_video(video)
    cx = comu.caixa(comu.TIFINAG_720, alt, ample)
    tifdir = os.path.join(carpeta, "tif")
    os.makedirs(tifdir, exist_ok=True)
    imatges, n_linies = [], []
    for k, r in enumerate(repliques):
        t = (r["t_ini"] + r["t_fi"]) / 2
        desti = os.path.join(tifdir, f"{k:04d}.png")
        if not os.path.exists(desti):
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", video, "-frames:v", "1", "-vf",
                            f"crop={cx[2] - cx[0]}:{cx[3] - cx[1]}:{cx[0]}:{cx[1]}", desti], check=False)
        try:
            imatges.append(np.asarray(Image.open(desti).convert("RGB")))
        except Exception:
            imatges.append(None)
        n_linies.append(linies_de_text(fotograma_gris_petit(video720, t)))
        if k % 200 == 0:
            comu.diu(log, f"  tifinag: {k}/{len(repliques)} retalls")
    lect = lector_tifinag.llegeix_bandes(imatges, log=lambda s: comu.diu(log, s))
    for r, x, nl in zip(repliques, lect, n_linies):
        r["tifinag"] = x["tifinag"]; r["tifinag_conf"] = x["conf_mitjana"]; r["tifinag_dubtosos"] = x["n_dubtosos"]
        r["tifinag_glifs"] = x["n_glifs"]; r["tifinag_lector"] = lector_tifinag.NOM; r["linies_text"] = nl
    return alt


def fitxa_del_cataleg(slug):
    p = os.path.join(comu.td_tv(), "cataleg", "capitols.jsonl")
    for x in comu.jsonl_llegeix(p):
        if slug in (x.get("slug"), x.get("slug_forja"), x.get("youtube_id")):
            return x
    return {}


def marca_credits(repliques, limits=None):
    """§4: més de 3 línies de text al fotograma, o text idèntic repetit més de 20 s en total. A més, si el catàleg o
    `estat.json` porten `credits_limits` [A, B] (segons), tot el que és abans d'A o des de B és crèdit: els rodolins
    d'una línia per nom no es distingeixen del diàleg per la forma (afegit respecte a l'especificació, apuntat al LLEGEIX-ME)."""
    durada_per_text = defaultdict(float)
    quants = Counter()
    for r in repliques:
        durada_per_text[r["arab"]] += r["t_fi"] - r["t_ini"]; quants[r["arab"]] += 1
    for r in repliques:
        repetit = quants[r["arab"]] > 1 and durada_per_text[r["arab"]] > REPETIT_S
        fora = bool(limits) and (r["t_ini"] < limits[0] or r["t_ini"] >= limits[1])
        r["credits"] = bool(r.get("linies_text", 0) > MAX_LINIES or repetit or fora)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("carpeta")
    ap.add_argument("--fils", type=int, default=6)
    ap.add_argument("--fins", type=int, default=0, help="només fins a aquest segon (per provar)")
    ap.add_argument("--sense-tifinag", action="store_true")
    ap.add_argument("--un-per-segon", action="store_true", help="el mètode antic: totes les franges amb vot (car)")
    ap.add_argument("--lector-arab", choices=["visio", "propi"], default=os.environ.get("TD_LECTOR_ARAB", "visio"),
                    help="visio (qwen3-vl-plus, gasta quota) o propi (CRNN, sense visió; candidat: marca arab_dubtos)")
    a = ap.parse_args()
    comu.carrega_env()
    carpeta = os.path.abspath(a.carpeta)
    slug = comu.slug_de(carpeta)
    log = comu.obre_log(carpeta)
    comu.etapa_inici(carpeta, ETAPA)
    t0 = time.time()
    try:
        video = comu.video_de(carpeta)
        if not video:
            raise RuntimeError("sense video.mp4")
        ample, alt, durada = comu.mida_video(video)
        comu.diu(log, f"== {ETAPA} {comu.ara()} {slug} {os.path.basename(video)} {ample}x{alt} {durada:.0f} s")
        comu.estat_desa(carpeta, slug=slug, video=os.path.basename(video), ample=ample, alt=alt, durada=round(durada, 1))
        comptes = {"ordre_linies": decideix_ordre(carpeta, video, ample, alt, durada, log)}
        comptes["franges"] = treu_franges(video, carpeta, ample, alt, durada, log)
        comptes["geometria_ok"] = comprova_geometria(video, ample, alt, durada, log)
        if comptes["geometria_ok"] < 3:
            raise RuntimeError(f"geometria: només {comptes['geometria_ok']} de 10 fotogrames amb les dues línies on toca")
        segons = list(range(1, comptes["franges"] + 1))
        if a.fins:
            segons = [s for s in segons if s <= a.fins]
        igual = iguals_a_l_anterior(carpeta, segons, alt)
        comptes["franges_identiques"] = sum(igual.values())
        if a.lector_arab == "propi":
            if a.un_per_segon:
                raise RuntimeError("--lector-arab propi no es combina amb --un-per-segon (el lector propi llegeix 2 fotogrames per tram)")
            v1080 = comu.video_de(carpeta, 1080)
            if not v1080:
                comu.diu(log, "AVÍS: no hi ha video_1080.mp4: l'àrab es llegeix de 720p pujat a 1450×64 (el lector només s'ha mesurat a 1080p)")
            va = v1080 or video
            ha = comu.mida_video(va)[1]
            trams = trams_del_tifinag(carpeta, segons, alt, log)
            comptes["trams"] = len(trams)
            crues, c = llegeix_trams_propi(carpeta, trams, va, ha, a.fils, log)
            comptes["metode"] = "rellotge del tifinag, 2 fotogrames per tram, lector propi (sense visió)"
            comptes["alt_arab"] = ha
        elif a.un_per_segon:
            crues, c = llegeix_un_per_segon(carpeta, segons, alt, igual, a.fils, log)
            comptes["metode"] = "1 fotograma per segon"
        else:
            trams = trams_del_tifinag(carpeta, segons, alt, log)
            comptes["trams"] = len(trams)
            crues, c = llegeix_trams(carpeta, trams, alt, igual, a.fils, log)
            comptes["metode"] = "rellotge del tifinag, 1 fotograma per tram"
        comptes.update(c)
        repliques = ajunta(crues)
        for k, r in enumerate(repliques):
            r["k"] = k; r["id"] = f"{slug}_{k:04d}"; r["slug"] = slug; r["durada"] = r["t_fi"] - r["t_ini"]
            r["arab_acord"] = round(r["arab_dacord"] / max(1, r["arab_lectures"]), 3)
            r["arab_lector"] = comptes["lector_arab"] if a.lector_arab == "propi" else LECTOR_ARAB
        if a.lector_arab == "propi":
            comptes["arab_dubtoses"] = sum(1 for r in repliques if r.get("arab_dubtos"))
        comu.diu(log, f"àrab: {len(repliques)} rèpliques, {comptes['crides_visio']} crides noves, {comptes['fitxes_visio']} fitxes noves"
                 + (f", {comptes['arab_dubtoses']} dubtoses" if a.lector_arab == "propi" else ""))
        if a.sense_tifinag:
            for r in repliques:
                r.update(tifinag="", tifinag_conf=None, tifinag_dubtosos=0, tifinag_glifs=0, tifinag_lector=None, linies_text=0)
        else:
            v1080 = comu.video_de(carpeta, 1080)
            comptes["tifinag_alt"] = llegeix_tifinag(carpeta, repliques, v1080 or video, video, log)
            confs = [r["tifinag_conf"] for r in repliques if r.get("tifinag_conf")]
            comptes["tifinag_conf_mitjana"] = round(float(np.mean(confs)), 3) if confs else None
            comptes["tifinag_amb_text"] = sum(1 for r in repliques if r.get("tifinag"))
            if comptes["tifinag_conf_mitjana"] is not None and comptes["tifinag_conf_mitjana"] < 0.9 and not v1080:
                comptes["avis"] = "confiança del tifinag sota 0,9 a 720p: cal video_1080.mp4 (§4)"
                comu.diu(log, "AVÍS: " + comptes["avis"])
        limits = comu.estat_llegeix(carpeta).get("credits_limits")
        if not limits:
            cap = fitxa_del_cataleg(slug)
            if cap.get("credits"):
                limits = [float(v) for v in str(cap["credits"]).split(",")]
                comu.estat_desa(carpeta, credits_limits=limits)
        marca_credits(repliques, limits)
        comptes["credits"] = sum(1 for r in repliques if r["credits"])
        # fusiona amb el que ja hi hagi (04 hi afegeix els catalans): per id
        vells = {x["id"]: x for x in comu.subtitols(carpeta)}
        files = []
        for r in repliques:
            fila = dict(vells.get(r["id"], {}))
            fila.update(r)
            fila.pop("arab_dacord", None)
            files.append(fila)
        comu.desa_subtitols(carpeta, files)
        comptes["subtitols"] = len(files)
        comptes["segons"] = round(time.time() - t0)
        comu.etapa_fi(carpeta, ETAPA, comptes)
        comu.diu(log, f"{ETAPA}: {len(files)} rèpliques ({comptes['credits']} de crèdits) en {comptes['segons']} s")
    except Exception as e:
        comu.etapa_fi(carpeta, ETAPA, {"segons": round(time.time() - t0)}, error=f"{type(e).__name__}: {e}")
        comu.diu(log, f"{ETAPA}: ERROR {type(e).__name__}: {e}")
        raise


if __name__ == "__main__":
    main()
