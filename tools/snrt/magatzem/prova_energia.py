"""Cal un model de 4 GB per saber on comenca la veu, o n'hi ha prou amb l'energia?

L'alineacio forcada (MMS-1b-all, Viterbi sobre les probabilitats de CTC) triga ~25 h per als
20.547 talls. Si un metode d'energia troba les mateixes fronteres, el mateix retall es fa en
minuts -- i el guany mesurat (-0,2235 de CER) es tindria avui en comptes de dema.

⚠️ **Aquest metode es va descartar contra una referencia trencada** (quadern, §48). Les
fronteres del model gran amb que es va comparar venien d'una alineacio que no va rebre mai la
frase -- vocabulari llati, text en tifinag -- i per aixo l'energia hi queia lluny (0 % dins de
0,2 s). Refet contra les fronteres bones, l'energia encerta el **26 %**. Segueix sent poc per
fer-hi el retall, pero el 0 % no era seu. I el -0,2235 que es dona aqui com a premi tampoc no
mesura el que diu (§49): no prova que la frontera sigui bona, nomes que el so es mes curt.

**Com es comprova sense gastar res:** hi ha 6.369 talls amb la frontera de l'alineacio ja
calculada. Es calcula la frontera per energia dels mateixos talls i es comparen. Si cauen
aprop, el metode barat val; si no, no.

**El llindar d'energia** es relatiu a cada tall (no absolut): el soroll de fons d'un estudi no
es el d'un carrer. Es pren el percentil 20 de l'energia per finestra com a terra.

No toca res: nomes mesura.
"""
import io
import json
import statistics as s
from pathlib import Path

import numpy as np
import soundfile as sf

#: es pot passar per la linia d ordres: la mesura del 22-11 es va fer contra fronteres que
#: nomes alineaven els separadors de paraula (quadern, §48).
import sys
ALI = Path(sys.argv[1] if len(sys.argv) > 1
           else r"E:/tamazight/_magatzem/alineacio_ecs_v2.jsonl")
ARREL = Path(r"E:/tamazight/talls_ecs")
QUANTS = 400
FINESTRA = 0.02          # 20 ms, com els fotogrames del CTC


def fronteres_energia(x, sr, k=3.0):
    """Primera i ultima finestra amb energia prou per sobre del terra del propi tall."""
    n = max(1, int(FINESTRA * sr))
    talls = x[:len(x) - len(x) % n].reshape(-1, n)
    e = np.sqrt((talls ** 2).mean(axis=1) + 1e-12)
    terra = np.percentile(e, 20)
    sostre = np.percentile(e, 95)
    if sostre <= terra * 1.2:
        return None                      # tot pla: no se separar veu de fons
    llindar = terra + (sostre - terra) * 0.15
    viu = np.where(e > llindar)[0]
    if len(viu) == 0:
        return None
    return viu[0] * FINESTRA, (viu[-1] + 1) * FINESTRA


ali = {}
for l in io.open(ALI, encoding="utf-8"):
    if not l.strip():
        continue
    try:
        x = json.loads(l)
    except Exception:
        continue
    if x.get("veu_ini") is not None:
        ali[x["so"]] = x

print(f"{len(ali)} talls amb l'alineació bona")

dini, dfi, cap = [], [], 0
mirats = 0
for nom, a in list(ali.items())[:QUANTS]:
    w = ARREL / a["capitol"] / "talls" / nom
    if not w.exists():
        continue
    x, sr = sf.read(str(w))
    if x.ndim > 1:
        x = x.mean(axis=1)
    r = fronteres_energia(x, sr)
    mirats += 1
    if r is None:
        cap += 1
        continue
    dini.append(r[0] - a["veu_ini"])
    dfi.append(r[1] - a["veu_fi"])

if not dini:
    print("   cap tall comparable")
    raise SystemExit(1)

print(f"   {mirats} mirats · {cap} on l'energia no sap decidir\n")
print(f"   {'':<22}{'mediana':>9}{'|error| mitjà':>15}{'dins de 0,2 s':>15}")
for nom, d in (("inici", dini), ("final", dfi)):
    dins = 100 * sum(1 for v in d if abs(v) <= 0.2) / len(d)
    print(f"   {nom:<22}{s.median(d):>9.3f}{s.mean([abs(v) for v in d]):>15.3f}{dins:>14.0f} %")

tots = [abs(v) for v in dini] + [abs(v) for v in dfi]
print(f"\n   les dues fronteres dins de 0,2 s: "
      f"{100*sum(1 for i in range(len(dini)) if abs(dini[i])<=0.2 and abs(dfi[i])<=0.2)/len(dini):.0f} %")
print(f"   error mitjà global: {s.mean(tots):.3f} s")
