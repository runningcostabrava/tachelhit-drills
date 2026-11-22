"""Tornar a baixar el video dels episodis collits, perque es puguin mirar al visor.

`cull_gratis.sh` esborrava el video un cop llegit, per estalviar disc. Tenia sentit quan el
visor no existia: el que interessava era el text. Pero ara **els episodis de Tadfi son els
unics que porten tifinag**, i son justament els que no es poden mirar.

Compta: 21 episodis a 289 MB de mitjana son **5,9 GB**, i al disc E n'hi ha 263 de lliures.

Va d'un en un i es pot reprendre: el que ja hi es no es torna a baixar.

    recupera_els_videos.py
"""
import io
import json
import os
import subprocess
import time
from pathlib import Path

ARREL = Path(r"E:/tamazight/TD_TV")
PY = r"C:/Users/josep/app2/tachelhit-drills/backend/venv/Scripts/python.exe"

falten = []
for d in sorted(os.listdir(ARREL)):
    sub = ARREL / d / "subtitols.jsonl"
    vid = ARREL / d / "video.mp4"
    if sub.exists() and sub.stat().st_size > 0 and not vid.exists():
        falten.append(d)
print(f"{len(falten)} episodis amb subtítols i sense vídeo", flush=True)

fets = errors = 0
t0 = time.time()
for i, d in enumerate(falten, 1):
    carpeta = ARREL / d
    r = subprocess.run([PY, "-m", "yt_dlp", "--js-runtimes", "node",
                        "-f", "136+140/bestvideo[height<=720]+bestaudio/best[height<=720]",
                        "--merge-output-format", "mp4", "--no-progress",
                        "-o", str(carpeta / "video.%(ext)s"),
                        f"https://www.youtube.com/watch?v={d}"],
                       capture_output=True, text=True, timeout=3600)
    if (carpeta / "video.mp4").exists():
        fets += 1
        json.dump({"id": d, "url": f"https://www.youtube.com/watch?v={d}",
                   "permis": "SNRT: recerca sí, republicar no (docs/PERMISOS.md)"},
                  io.open(carpeta / "video.json", "w", encoding="utf-8"), ensure_ascii=False)
    else:
        errors += 1
        print(f"   falla {d}: {(r.stderr or '')[-90:]}", flush=True)
    if i % 5 == 0 or i == len(falten):
        gb = sum(f.stat().st_size for f in ARREL.glob("*/video.mp4")) / 2 ** 30
        print(f"{i}/{len(falten)} · {fets} baixats · {errors} errors · {gb:.1f} GB al disc · "
              f"{(time.time()-t0)/60:.0f} min", flush=True)

print(f"\nFET: {fets} baixats · {errors} errors · {(time.time()-t0)/60:.0f} min", flush=True)
