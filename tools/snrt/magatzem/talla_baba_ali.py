"""Talla so del Baba Ali per saber de quina varietat es.

Per que val la pena: el classificador per lexic nomes necessita el que sent l'orella, no el
tifinag (que al Baba Ali gairebe no es llegeix). I el Baba Ali son **30 episodis**: si fos de
l'Atles central, serien unes 7.500 repliques de la varietat que aquest projecte documenta.

Els talls no son al conjunt privat (nomes hi ha els 25 de Tadfi), pero els videos i les marques
de temps son aqui. Es tallen amb ffmpeg a 16 kHz mono, que es el que vol l'MMS.

    talla_baba_ali.py [talls_per_episodi] [episodis]
"""
import io
import json
import random
import subprocess
import sys
from pathlib import Path

VISOR = Path(r"E:/tamazight/_visor")
VIDEOS = Path(r"E:/tamazight/_videos")
DESTI = Path(r"E:/tamazight/_magatzem/prova_baba/dades")
PER_EPISODI = int(sys.argv[1]) if len(sys.argv) > 1 else 60
QUANTS = int(sys.argv[2]) if len(sys.argv) > 2 else 3
MIN_SEG, MAX_SEG = 1.0, 12.0

(DESTI / "talls").mkdir(parents=True, exist_ok=True)
episodis = sorted(d.name for d in VISOR.iterdir()
                  if d.name.startswith("baba_ali") and (d / "subtitols.jsonl").exists()
                  and (VIDEOS / f"{d.name}.mp4").exists())
print(f"episodis del Baba Ali amb vídeo i línies: {len(episodis)}")
tria = episodis[:QUANTS]

index = []
rnd = random.Random(2011)
for slug in tria:
    linies = []
    for i, l in enumerate(io.open(VISOR / slug / "subtitols.jsonl", encoding="utf-8")):
        if not l.strip():
            continue
        x = json.loads(l)
        if x.get("t_ini") is None or x.get("t_fi") is None:
            continue
        dur = float(x["t_fi"]) - float(x["t_ini"])
        #: nomes repliques amb significat i de durada raonable: les mudes no diuen res
        if MIN_SEG <= dur <= MAX_SEG and (x.get("catala") or "").strip():
            linies.append((str(x.get("k", i)), float(x["t_ini"]), dur, x.get("catala")))
    tr = rnd.sample(linies, min(PER_EPISODI, len(linies)))
    fets = 0
    for k, t0, dur, cat in tr:
        nom = f"{slug}_{int(k):04d}.wav"
        p = DESTI / "talls" / nom
        if not p.exists():
            subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t0:.3f}", "-t", f"{dur:.3f}",
                            "-i", str(VIDEOS / f"{slug}.mp4"), "-ac", "1", "-ar", "16000",
                            "-y", str(p)], check=False)
        if p.exists() and p.stat().st_size > 2000:
            index.append({"id": f"{slug}:{k}", "fitxer": f"talls/{nom}", "catala": cat})
            fets += 1
    print(f"{slug}: {fets} talls de {len(linies)} amb significat")

json.dump(index, io.open(DESTI / "index.json", "w", encoding="utf-8"), ensure_ascii=False)
mida = sum(f.stat().st_size for f in (DESTI / "talls").glob("*.wav"))
print(f"\n{len(index)} talls, {mida/1e6:.0f} MB a {DESTI}")
