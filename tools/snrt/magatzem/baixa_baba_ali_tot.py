"""Tots els Baba Ali del canal, al disc E. Feina de nit, reprenible.

En Pablo: «els capitols de Baba Ali son extremadament utils per mi, mira de descarregar tots els
episodis de totes les temporades».

El que hi ha al canal, comptat el 20-11-2026: **133 videos**, 20,3 hores. D'aquests, **37 son
episodis sencers** (≥5 minuts) i **96 son retalls curts** («Funny Moments», 1-2 minuts). Les
temporades que hi surten son la 4 (gairebe sencera) i cinc de la 3: **les temporades 1 i 2 no son
en aquest canal**, i aixo caldra buscar-ho en un altre lloc.

Es baixa tot -- tambe els retalls, que son Baba Ali igualment i costen poc -- a
`E:/tamazight/_videos_baba/`, amb el nom `baba_sNN_eNN_<id>.mp4` quan el titol en diu la
temporada i l'episodi, i `<id>.mp4` quan no. Al costat, un `.json` amb el titol i l'adreca.

**Reprenible**: el que ja hi es no es torna a baixar. **Poc paral·lel** (dos alhora) a posta:
mentre aixo corre hi ha una altra collita baixant i llegint episodis de Tadfi, i la xarxa es
compartida.

    baixa_baba_ali_tot.py [quants_alhora]
"""
import io
import json
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

LLISTA = Path(r"E:/tamazight/_magatzem/baba_ali_tots.txt")
DESTI = Path(r"E:/tamazight/_videos_baba")
PY = r"C:/Users/josep/app2/tachelhit-drills/backend/venv/Scripts/python.exe"
ALHORA = int(sys.argv[1]) if len(sys.argv) > 1 else 2

ARAB = {"الأول": "01", "الثاني": "02", "الثالث": "03", "الرابع": "04", "الخامس": "05"}


def nom_de(vid, titol):
    t = titol
    ms = re.search(r"Season\s*(\d+)", t, re.I)
    temporada = ms.group(1).zfill(2) if ms else None
    if not temporada:
        ma = re.search(r"الموسم\s*(\S+)", t)
        if ma:
            temporada = ARAB.get(ma.group(1).strip())
    me = re.search(r"Episode\s*(\d+)", t, re.I) or re.search(r"الحلقة\s*(\d+)", t)
    episodi = me.group(1).zfill(2) if me else None
    if temporada and episodi:
        return f"baba_s{temporada}_e{episodi}_{vid}"
    return f"baba_{vid}"


files = []
for l in io.open(LLISTA, encoding="utf-8"):
    if not l.strip():
        continue
    vid, dur, titol = l.rstrip("\n").split("|", 2)
    files.append((vid, int(dur), titol))
#: primer els episodis sencers: si la nit s'acaba, val mes tenir els llargs
files.sort(key=lambda x: -x[1])
DESTI.mkdir(parents=True, exist_ok=True)
print(f"{len(files)} vídeos · {sum(d for _, d, _ in files)/3600:.1f} h · {ALHORA} alhora",
      flush=True)

fets = saltats = errors = 0
t0 = time.time()


def baixa(x):
    global fets, saltats, errors
    vid, dur, titol = x
    nom = nom_de(vid, titol)
    mp4 = DESTI / (nom + ".mp4")
    if mp4.exists() and mp4.stat().st_size > 10 ** 6:
        saltats += 1
        return
    r = subprocess.run([PY, "-m", "yt_dlp", "--js-runtimes", "node",
                        "-f", "136+140/bestvideo[height<=720]+bestaudio/best[height<=720]",
                        "--merge-output-format", "mp4", "--no-progress",
                        "-o", str(DESTI / (nom + ".%(ext)s")),
                        f"https://www.youtube.com/watch?v={vid}"],
                       capture_output=True, text=True, timeout=3600)
    if mp4.exists():
        fets += 1
        json.dump({"id": vid, "titol": titol, "durada": dur,
                   "url": f"https://www.youtube.com/watch?v={vid}",
                   "permis": "SNRT: recerca sí, republicar no (docs/PERMISOS.md)"},
                  io.open(DESTI / (nom + ".json"), "w", encoding="utf-8"), ensure_ascii=False)
    else:
        errors += 1
        print(f"   falla {vid}: {(r.stderr or '')[-90:]}", flush=True)
    if (fets + saltats + errors) % 10 == 0:
        mida = sum(f.stat().st_size for f in DESTI.glob("*.mp4"))
        print(f"{fets+saltats+errors}/{len(files)} · {fets} baixats · {saltats} ja hi eren · "
              f"{errors} errors · {mida/1e9:.1f} GB · {(time.time()-t0)/60:.0f} min", flush=True)


with ThreadPoolExecutor(max_workers=ALHORA) as ex:
    list(ex.map(baixa, files))

mida = sum(f.stat().st_size for f in DESTI.glob("*.mp4"))
print(f"\nFET: {fets} baixats · {saltats} ja hi eren · {errors} errors · {mida/1e9:.1f} GB "
      f"· {(time.time()-t0)/60:.0f} min", flush=True)
