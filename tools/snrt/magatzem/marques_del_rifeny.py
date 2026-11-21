"""Els convidats que l'orella no enten parlen rifeny?

Dues coses encaixen i val la pena provar-les juntes:

  - la š que l'orella posa on la pantalla escriu ⵏⵏⴽ («teu») surt gairebé tota d'aquesta paraula
    i es CONCENTRA en uns pocs episodis -- i son els de poc acord;
  - a la taula de variacio hi havia `wawal/wawar` i `umaḍal/umaḍar`, o sigui l -> r.

`nnš` i l -> r son les dues marques conegudes del **rifeny**, i l'MMS no porta adaptador de
rifeny: aixo explicaria d'una sola vegada per que aquells deu convidats li son inaccessibles.

La prova: si els MATEIXOS episodis fan les dues coses, dues marques independents assenyalen el
mateix i la hipotesi es sosté. Si cada marca assenyala uns episodis diferents, no.

Es compten, per episodi i nomes a les paraules que casen (si no, no se sap de quina paraula
parla cadascu):

    k -> š   a les paraules que la pantalla escriu amb k
    l -> r   a les paraules que la pantalla escriu amb l

i es mira si les dues proporcions van juntes.
"""
import io
import json
import glob
import os
import statistics
import sys
from collections import defaultdict

sys.path.insert(0, r"E:/tamazight/_magatzem")
from tria_el_millor_text import esquelet, lev  # noqa: E402
from alinea_paraules import alinea  # noqa: E402


def prop(a, b):
    return 1.0 if not a or not b else lev(a, b) / max(len(a), len(b))


titols = {}
for p in glob.glob(r"E:/tamazight/_visor/*/estat.json"):
    s = os.path.basename(os.path.dirname(p))
    titols[s] = json.load(io.open(p, encoding="utf-8"))["titol"].replace("TADFI N TSKLA - ", "")

acord = defaultdict(lambda: [0, 0])
for l in io.open(r"E:/tamazight/_magatzem/acord_triat.jsonl", encoding="utf-8"):
    if l.strip():
        r = json.loads(l)
        acord[r["capitol"]][1] += 1
        acord[r["capitol"]][0] += r["grau"] == "A"

sentit = {}
for l in io.open(r"E:/tamazight/_sentit/sortida_26/sentit.jsonl", encoding="utf-8"):
    if l.strip():
        x = json.loads(l)
        sentit[x["id"]] = x

#: per episodi: [k, š, l, r]
c = defaultdict(lambda: {"k": 0, "š": 0, "l": 0, "r": 0})
for l in io.open(r"E:/tamazight/_magatzem/text_triat.jsonl", encoding="utf-8"):
    if not l.strip():
        continue
    x = json.loads(l)
    s = sentit.get(x["id"], {})
    paraules = [w["p"] for w in (s.get("paraules") or [])]
    escrites = [w for w in (x.get("tifinag") or "").split() if w.strip()]
    if not paraules or not escrites:
        continue
    for i, j in alinea(paraules, escrites):
        if j is None:
            continue
        eo, ee = esquelet(paraules[i]), esquelet(escrites[j])
        if not eo or not ee or prop(eo, ee) > .35:
            continue
        d = c[x["capitol"]]
        if "k" in ee:
            d["k" if "k" in eo else ("š" if "š" in eo else "k")] += 1
        if "l" in ee:
            d["l" if "l" in eo else ("r" if "r" in eo else "l")] += 1

files = []
for cap, d in c.items():
    nk, nl = d["k"] + d["š"], d["l"] + d["r"]
    if nk < 5 or nl < 10:
        continue
    a, n = acord[cap]
    files.append((d["š"] / nk, d["r"] / nl, 100 * a / max(1, n), titols.get(cap, cap), nk, nl))

files.sort(reverse=True)
print(f"{'convidat':<26}{'acord':>7}{'k->š':>8}{'l->r':>8}")
for s_, r_, ac, t, nk, nl in files:
    print(f"{t[:24]:<26}{ac:6.1f}%{100*s_:7.0f}%{100*r_:7.0f}%")

if len(files) > 3:
    xs = [f[0] for f in files]
    ys = [f[1] for f in files]
    mx, my = statistics.mean(xs), statistics.mean(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    den = (sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys)) ** .5
    print(f"\ncorrelacio k->š amb l->r: {num/den if den else 0:+.2f}")
    print("(alta = les dues marques assenyalen els mateixos convidats, i la hipotesi es sosté)")
    zs = [f[2] for f in files]
    mz = statistics.mean(zs)
    num2 = sum((x - mx) * (z - mz) for x, z in zip(xs, zs))
    den2 = (sum((x - mx) ** 2 for x in xs) * sum((z - mz) ** 2 for z in zs)) ** .5
    print(f"correlacio k->š amb l'acord: {num2/den2 if den2 else 0:+.2f}")
    print("(negativa = els que fan la marca son els que l'orella no enten)")
