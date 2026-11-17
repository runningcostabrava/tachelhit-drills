# -*- coding: utf-8 -*-
"""Etapa 03: els subtítols en una taula i els talls de so.

  python 03_talla.py <carpeta> [--credits A,B] [--marge 0.25] [--prefix NOM]

Ajunta `linies_arab.json` i `tifinag.json` en `subtitols.jsonl` (una fila per subtítol, amb `credits` si cau abans
del segon A o des del segon B: títols del principi i del final, que no són diàleg), treu `audio16k.wav` (mono,
16 kHz) i talla `talls/<prefix>_NNNN.wav` per a cada subtítol. El fotograma k del fps=1 és l'instant k−0,5: el
subtítol comença entre t−0,5 i t+0,5 i acaba entre fi−0,5 i fi+0,5; es talla amb `--marge` segons a cada banda
sense trepitjar el veí. Reprèn: els talls que ja hi són no es refan.
"""
import argparse
import io
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comu  # noqa: E402

ETAPA = "03_talla"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("carpeta")
    ap.add_argument("--credits", default=None, help="A,B: crèdits abans del segon A i des del segon B (Illy: 150,1700)")
    ap.add_argument("--marge", type=float, default=0.25)
    ap.add_argument("--prefix", default=None, help="prefix dels ids i dels talls (per omissió, el nom de la carpeta)")
    a = ap.parse_args()
    carpeta = os.path.abspath(a.carpeta)
    video = comu.video_de(carpeta)
    prefix = a.prefix or os.environ.get("TD_PREFIX") or os.path.basename(carpeta.rstrip("\\/"))
    est = comu.estat_llegeix(carpeta)
    if a.credits:
        credits = tuple(float(v) for v in a.credits.split(","))
    else:
        credits = tuple(est.get("credits") or (0.0, 1e9))
    log = io.open(os.path.join(carpeta, "fabrica.log"), "a", encoding="utf-8")
    comu.diu(log, f"== {ETAPA} {time.strftime('%Y-%m-%d %H:%M')} prefix {prefix} crèdits {credits}")
    t0 = time.time()
    audio = os.path.join(carpeta, "audio16k.wav")
    if not os.path.exists(audio):
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", video, "-vn", "-ac", "1", "-ar", "16000", audio], check=True)
    with io.open(os.path.join(carpeta, "linies_arab.json"), encoding="utf-8") as f:
        linies = json.load(f)
    p_tif = os.path.join(carpeta, "tifinag.json")
    tif = {}
    if os.path.exists(p_tif):
        with io.open(p_tif, encoding="utf-8") as f:
            tif = {d["k"]: d for d in json.load(f)}
    talls = os.path.join(carpeta, "talls")
    os.makedirs(talls, exist_ok=True)
    files = []
    nous = 0
    for k, L in enumerate(linies):
        T = tif.get(k, {})
        ini = max(L["t"] - a.marge, linies[k - 1]["fi"] if k else 0.0)
        fin = min(L["fi"] + a.marge, linies[k + 1]["t"] if k + 1 < len(linies) else 1e9)
        nom = f"{prefix}_{k:04d}.wav"
        desti = os.path.join(talls, nom)
        if not os.path.exists(desti):
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{ini:.2f}", "-to", f"{fin:.2f}", "-i", audio, "-ac", "1", "-ar", "16000", desti], check=True)
            nous += 1
        files.append({"k": k, "id": f"{prefix}_{k:04d}", "t": L["t"], "fi": L["fi"], "durada": L["fi"] - L["t"],
                      "arab": L["ar"], "arab_lectures": L["lectures"], "arab_dacord": L["dacord"],
                      "arab_acord": round(L["dacord"] / max(1, L["lectures"]), 3),
                      "tifinag": T.get("tifinag", ""), "tifinag_glifs": T.get("n_glifs", 0), "tifinag_dubtosos": T.get("n_dubtosos", 0),
                      "tifinag_conf": T.get("conf_mitjana"),
                      "credits": bool(L["t"] < credits[0] or L["t"] >= credits[1]),
                      "tall": "talls/" + nom, "tall_de": round(ini, 2), "tall_a": round(fin, 2)})
    comu.jsonl_escriu(os.path.join(carpeta, "subtitols.jsonl"), files)
    dial = [f for f in files if not f["credits"]]
    so = round(sum(f["tall_a"] - f["tall_de"] for f in dial), 1)
    comu.diu(log, f"{len(files)} subtítols ({len(dial)} de diàleg), {nous} talls nous, {so} s de so de diàleg, {time.time() - t0:.0f} s")
    comu.estat_desa(carpeta, credits=list(credits), prefix=prefix)
    comu.estat_desa(carpeta, ETAPA, subtitols=len(files), dialeg=len(dial), talls=len(files), segons_so_dialeg=so,
                    segons=round(time.time() - t0), fet=True)


if __name__ == "__main__":
    main()
