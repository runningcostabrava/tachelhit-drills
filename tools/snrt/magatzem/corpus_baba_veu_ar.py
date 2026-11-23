"""Baba Ali com a material de VEU -> ARAB: el so de cada repl ica i el seu subtitol arab.

**Per que** (pla dels models, pas 2b; idea d'en Pablo del 23-11): el subtitol arab d'una serie
l'escriu un subtitulador a partir del dialeg. Es traduccio humana, com l'arab del TutlAit, i
per a la via 3 (veu -> arab) es pot fer servir com a material confirmat. **Per a l'ASR no**
(no es transcripcio), ni com a `verified` a l'app, ni al cataleg public (permis de la SNRT:
recerca si, republicar no).

Baba Ali es una serie de la mateixa cadena (Tamazight TV), del **Souss**: la varietat que mes
falta a la via 3. Ja es llegit: `E:/tamazight/_visor/baba_ali_*/subtitols.jsonl` (13 episodis,
3.621 linies amb l'arab i l'hora); els videos son a `E:/tamazight/_videos/`.

**Tot va a l'ENTRENAMENT.** Es una sola serie i els mateixos actors surten a tots els
episodis: partir-la per episodi posaria la mateixa veu a l'entrenament i al test. Aixi els
tests de la primera tirada queden intactes, i la segona tirada canvia **nomes** una cosa: si hi
ha Baba Ali o no. La diferencia als tests fixos diu quant aporta el material de serie.

**El tall** es fa a l'hora del subtitol, tal qual, igual que els talls de la SNRT de la
primera tirada. Ajustar-lo a la veu es el pas 3 del pla, i es jutja a part.

No toca el cataleg ni res de produccio: llegeix els fitxers locals i escriu talls nous.

    python corpus_baba_veu_ar.py
"""
import io
import json
import subprocess
from pathlib import Path

VISOR = Path(r"E:/tamazight/_visor")
VIDEOS = Path(r"E:/tamazight/_videos")
FORA = Path(r"E:/tamazight/_magatzem/baba_veu_ar")
DUR_MIN, DUR_MAX = 1.0, 20.0     #: les mateixes portes que la resta del corpus

(FORA / "so").mkdir(parents=True, exist_ok=True)
files, fallats = [], 0
episodis = sorted(d.name for d in VISOR.iterdir()
                  if d.name.startswith("baba_ali") and (d / "subtitols.jsonl").exists()
                  and (VIDEOS / f"{d.name}.mp4").exists())
print(f"{len(episodis)} episodis amb linies i video", flush=True)

for ep in episodis:
    video = VIDEOS / f"{ep}.mp4"
    for l in io.open(VISOR / ep / "subtitols.jsonl", encoding="utf-8"):
        if not l.strip():
            continue
        x = json.loads(l)
        ar = (x.get("arab") or "").strip()
        ini, fi = float(x["t_ini"]), float(x["t_fi"])
        d = fi - ini
        if not (DUR_MIN <= d <= DUR_MAX) or len(ar.split()) < 2:
            continue
        nom = f"{ep}_{int(x['k']):05d}.wav"
        desti = FORA / "so" / nom
        if not desti.exists():
            r = subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y",
                                "-ss", f"{ini:.3f}", "-t", f"{d:.3f}", "-i", str(video),
                                "-vn", "-ac", "1", "-ar", "16000", str(desti)],
                               capture_output=True)
            if r.returncode != 0 or not desti.exists() or desti.stat().st_size < 2000:
                fallats += 1
                desti.unlink(missing_ok=True)
                continue
        files.append({"so": nom, "font": "baba_ali", "ar": ar, "grup": ep,
                      "varietat": "shi", "durada": round(d, 2)})
    print(f"   {ep}: {len(files)} talls fins ara", flush=True)

with io.open(FORA / "train.jsonl", "w", encoding="utf-8", newline="\n") as f:
    for x in files:
        f.write(json.dumps(x, ensure_ascii=False) + "\n")
h = sum(x["durada"] for x in files) / 3600
print(f"\n{len(files)} talls · {h:.2f} h · {fallats} fallats -> {FORA}")
