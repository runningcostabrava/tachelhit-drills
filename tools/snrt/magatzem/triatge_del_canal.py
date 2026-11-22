"""Quins programes del canal porten SUBTITOLS de debo, i quantes hores en son.

**Primera versio, i per que estava malament.** Mesurava «tinta» i «canvi» sobre el cinque de
baix del fotograma sencer. El canvi que detectava era **el moviment de l'escena** -- gent que es
mou -- i no el del text: deia que PANORAMA porta subtitols quan jo havia mirat setze fotogrames
seus i no en tenien cap. Un detector que contradiu el que es veu mirant no es un detector.

La versio bona fa servir el que la fabrica ja te i esta calibrat per a aquest canal:
`linies_de_text` compta files de pixels **blancs amb vora fosca**, que es exactament com es
dibuixen aquests subtitols; una paret clara o un pla lluminos no ho son.

I per separar un subtitol d'un rotul fix es compara **nomes la mascara del text** entre dos
fotogrames separats tres segons, no la imatge:

  * `linies` ~ 0 a gairebe tots els fotogrames -> **sense text**
  * hi ha text pero la mascara no canvia mai -> **rotul fix** (el cas d'ASDAW: el titol del debat)
  * hi ha text i la mascara canvia -> **SUBTITOLS**

No es baixa cap video: tot va per l'adreca directa.

    triatge_del_canal.py [quants_programes]
"""
import io
import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

LLISTA = Path(r"C:/Users/josep/Veus-tachelhit/_escoltats/tamazight_tv_videos.txt")
FORA = Path(r"E:/tamazight/_magatzem/triatge_canal.json")
TMP = Path(os.environ.get("TEMP", ".")) / "triatge2"
PY = r"C:/Users/josep/app2/tachelhit-drills/backend/venv/Scripts/python.exe"
QUANTS = int(sys.argv[1]) if len(sys.argv) > 1 else 16
FINESTRES, PER_FINESTRA, PAS = 4, 7, 2.5   #: quatre finestres de set fotogrames cada 2,5 s


def mascara(cami):
    """Els píxels de text: blanc amb vora fosca (el dibuix dels subtítols d'aquest canal)."""
    g = np.asarray(Image.open(cami).convert("L"))
    return (g > 215) & ndimage.binary_dilation(g < 70, iterations=2), g


def linies(m):
    """Quantes línies de text: files amb prou píxels de text, agrupades de 3 en amunt."""
    files = m.sum(axis=1) >= .02 * m.shape[1]
    n, alt = 0, 0
    for v in files:
        if v:
            alt += 1
            if alt == 3:
                n += 1
        else:
            alt = 0
    return n


def fotograma(url, t, desti):
    subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t}", "-i", url, "-frames:v", "1",
                    "-vf", "crop=iw:ih/5:0:ih*4/5,scale=640:-1", "-y", str(desti)],
                   capture_output=True, timeout=180)
    return desti.exists() and desti.stat().st_size > 800


progs = defaultdict(list)
for l in io.open(LLISTA, encoding="utf-8", errors="replace"):
    p = l.rstrip("\n").split("|")
    if len(p) < 4:
        continue
    try:
        d = int(p[1])
    except ValueError:
        continue
    nom = re.split(r"\s*[-–|]\s*", "|".join(p[3:]).strip())[0].upper()[:28]
    progs[nom].append((d, p[0]))

ordre = sorted(progs.items(), key=lambda kv: -sum(d for d, _ in kv[1]))[:QUANTS]
TMP.mkdir(parents=True, exist_ok=True)
sortida = {}
if FORA.exists():
    sortida = {k: v for k, v in json.load(io.open(FORA, encoding="utf-8")).items()
               if v.get("versio") == 2}

print(f"{'programa':<30}{'vids':>5}{'hores':>7}{'línies':>8}{'ritme':>8}  diu", flush=True)
for nom, vids in ordre:
    if nom in sortida:
        continue
    hores = sum(d for d, _ in vids) / 3600
    d, vid = max(vids)
    u = subprocess.run([PY, "-m", "yt_dlp", "--js-runtimes", "node", "-g",
                        "-f", "136/bestvideo[height<=720]/best",
                        f"https://www.youtube.com/watch?v={vid}"],
                       capture_output=True, text=True, timeout=240)
    url = (u.stdout or "").strip().split("\n")[0]
    if not url.startswith("http"):
        print(f"{nom:<30}{len(vids):5d}{hores:7.1f}{'':>16}  sense adreça", flush=True)
        continue
    #: Quatre finestres repartides pel video; dins de cada finestra, set fotogrames cada 2,5 s.
    #: El que es compta es **quantes vegades canvia** el text dins de la finestra: un subtitol
    #: canvia gairebe a cada pas (cada frase dura 2-5 s), un rotul no canvia cap vegada encara
    #: que vagi alternant de subtema cada mig minut. A deu segons de distancia els dos es
    #: confonien, i per aixo ASDAW (que es un rotul) sortia «subtitols».
    n_linies, ritmes = [], []
    for f in range(1, FINESTRES + 1):
        t0 = d * f / (FINESTRES + 1)
        masc = []
        for i in range(PER_FINESTRA):
            a = TMP / f"f{i}.png"
            if fotograma(url, t0 + i * PAS, a):
                m, _ = mascara(a)
                masc.append(m)
                n_linies.append(linies(m))
        for x, y in zip(masc, masc[1:]):
            if x.shape != y.shape:
                continue
            tot = max(1, int(x.sum() + y.sum()))
            ritmes.append(1 if float((x ^ y).sum()) / tot >= .5 else 0)
    if not n_linies:
        print(f"{nom:<30}{len(vids):5d}{hores:7.1f}{'':>16}  sense fotogrames", flush=True)
        continue
    lin = sum(n_linies) / len(n_linies)
    canvi = sum(ritmes) / len(ritmes) if ritmes else 0.0
    if lin < .4:
        diu = "sense text"
    elif canvi >= .28:          #: calibrat amb TADFI (0,375, subtitols) i ASDAW (0,167, rotul)
        diu = "SUBTITOLS"
    elif canvi < .22:
        diu = "rètol fix"
    else:
        diu = "dubtós"
    sortida[nom] = {"versio": 2, "videos": len(vids), "hores": round(hores, 1),
                    "linies": round(lin, 2), "ritme": round(canvi, 3), "diu": diu, "mostra": vid}
    json.dump(sortida, io.open(FORA, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{nom:<30}{len(vids):5d}{hores:7.1f}{lin:8.2f}{canvi:8.3f}  {diu}", flush=True)

bons = sum(v["hores"] for v in sortida.values() if v["diu"] == "SUBTITOLS")
print(f"\nhores amb subtítols de debò, dels {len(sortida)} programes mirats: {bons:.0f}")
