"""Al tros que el retall llenca, hi ha so o es silenci? -- mesurat amb energia, sense cap model.

**Per que aixi.** La pregunta de debo es si alla hi ha **una altra persona parlant**, i aixo
nomes ho pot dir una transcripcio (`que_hi_ha_al_tros_que_es_llenca.py`, que carrega 4 GB). Pero
hi ha una meitat de la pregunta que l'energia ja contesta, i costa un segon: **si alla no hi ha
res**, no hi ha ningu parlant i la transcripcio ni cal. Si hi ha so, aleshores si que cal.

**Com, i amb un control.** De cada tall es mesura el nivell (RMS en dB) de tres trossos:

    cap      [0, veu_ini - marge]            el que es llenca del davant
    cua      [veu_fi + marge, final]         el que es llenca del darrere
    control  de dins de la frase, la mateixa durada que el cap

El numero que decideix es la **distancia al control**: si el cap esta 20 dB per sota, era
silenci; si hi es a 3-6 dB, alla hi ha tant de so com a la frase. El nivell absolut no diu res,
perque un estudi i un carrer no tenen el mateix terra.

No toca res: llegeix i mesura.

    python hi_ha_so_al_tros_que_es_llenca.py [FITXER_ALINEACIO] [MARGE]
"""
import io
import json
import math
import statistics as st
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

AQUI = Path(r"E:/tamazight/_magatzem/prova_retall")
ALI = sys.argv[1] if len(sys.argv) > 1 else r"E:/tamazight/_magatzem/alineacio_ecs_v2.jsonl"
MARGE = float(sys.argv[2]) if len(sys.argv) > 2 else 0.15
MINIM = 0.25   #: per sota d'aixo el tros es massa curt per mesurar-ne el nivell


def db(x):
    if len(x) == 0:
        return None
    r = float(np.sqrt(np.mean(np.square(x.astype(np.float64)))))
    return 20 * math.log10(r) if r > 0 else -120.0


ali = {}
for l in io.open(ALI, encoding="utf-8"):
    if not l.strip():
        continue
    try:
        x = json.loads(l)
    except ValueError:
        continue
    if x.get("veu_ini") is not None and x.get("veu_fi") is not None:
        ali[x["so"]] = x

wavs = [w for w in sorted(AQUI.glob("so/*.wav")) if w.name in ali]
print(f"{len(wavs)} talls amb alineació · {Path(ALI).name} · marge {MARGE}\n")

files = []
for w in wavs:
    a = ali[w.name]
    x, sr = sf.read(str(w), dtype="float32")
    if x.ndim > 1:
        x = x.mean(axis=1)
    fi_so = len(x) / sr
    ini, fi = a["veu_ini"] - MARGE, a["veu_fi"] + MARGE
    trossos = {"cap": (0.0, max(0.0, ini)), "cua": (min(fi_so, fi), fi_so)}
    d = max(q - p for p, q in trossos.values())
    centre = (max(0.0, ini) + min(fi_so, fi)) / 2
    trossos["control"] = (max(0.0, centre - d / 2), min(fi_so, centre + d / 2))

    f = {"so": w.name}
    for nom, (p, q) in trossos.items():
        if q - p >= MINIM:
            v = db(x[int(p * sr):int(q * sr)])
            if v is not None:
                f[nom] = {"s": round(q - p, 2), "db": round(v, 1)}
    files.append(f)

json.dump(files, io.open(AQUI / "so_al_tros_llencat.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

print(f"   {'tros':<10}{'n':>5}{'durada':>9}{'nivell':>10}{'sota el control':>18}")
for nom in ("control", "cap", "cua"):
    v = [f[nom] for f in files if nom in f]
    if not v:
        continue
    sota = [f["control"]["db"] - f[nom]["db"] for f in files
            if nom in f and "control" in f]
    marca = f"{st.median(sota):>14.1f} dB" if nom != "control" and sota else " " * 17
    print(f"   {nom:<10}{len(v):>5}{st.median(x['s'] for x in v):>8.2f}s"
          f"{st.median(x['db'] for x in v):>9.1f}dB{marca}")

tots = [f["control"]["db"] - f[n]["db"] for f in files for n in ("cap", "cua")
        if n in f and "control" in f]
if tots:
    print(f"\n   {len(tots)} trossos llençats · mediana {st.median(tots):.1f} dB sota el control")
    for llindar, que in ((20, "silenci net"), (10, "molt mes fluix"), (6, "comparable")):
        n = sum(1 for v in tots if v >= llindar)
        print(f"   {100*n/len(tots):>5.0f} % a 20 dB o mes sota" if llindar == 20 else
              f"   {100*n/len(tots):>5.0f} % a {llindar} dB o mes sota ({que})")

print("\n   >=20 dB sota = silenci, no hi ha ningu parlant · <=6 dB = hi ha tant de so com a la frase")
