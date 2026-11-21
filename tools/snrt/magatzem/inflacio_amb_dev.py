"""La inflacio de seleccio, mesurada amb el control bo: els `dev`.

**Que es la inflacio.** Si el model M1 tria ell mateix quins talls entren al seu entrenament,
pot triar justament els que ja li van be, i llavors el seu resultat sembla millor del que es.
Es mesura comparant el que fa sobre talls que ha vist contra talls que no.

**El control que es feia servir** eren els **capitols retinguts**: quatre capitols sencers que
no entren a train. Pero un capitol retingut te una altra veu, un altre so i un altre tema, i per
tant la diferencia barreja la inflacio amb el fet de ser un capitol diferent.

**El control bo son els `dev`**: surten dels **mateixos capitols**, de la **mateixa tallada**,
amb el mateix lector d'ull i el mateix tot -- i el model no hi ha fet cap pas de gradient. La
diferencia train vs dev es la inflacio i prou.

I al reves: els dos guions que la mesuraven **barrejaven els dev dins del grup «vistos»** (113
dels 1.210 talls tachelhit), que es llencar justament el control.

    inflacio_amb_dev.py
"""
import io
import json
import random
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

MAG = Path(r"E:/tamazight/_magatzem")
ROWS = Path(r"E:/tamazight/_entrenament/rows.json")
VEGADES = 2000


def lev(a, b):
    if not a or not b:
        return max(len(a), len(b))
    ant = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        act = [i]
        for j, cb in enumerate(b, 1):
            act.append(min(ant[j] + 1, act[j - 1] + 1, ant[j - 1] + (ca != cb)))
        ant = act
    return ant[-1]


def rica(t):
    t = unicodedata.normalize("NFC", (t or "").lower())
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", t, flags=re.UNICODE)).strip()


files = json.load(io.open(ROWS, encoding="utf-8"))
if isinstance(files, dict):
    files = files.get("rows") or files.get("files") or []
print(f"{len(files)} files a rows.json")

grups = defaultdict(list)
for x in files:
    s = x.get("split")
    if s in ("train", "dev"):
        grups[s].append(x)
print("per split: " + ", ".join(f"{k} {len(v)}" for k, v in sorted(grups.items())))

camps = sorted({k for x in files[:50] for k in x})
print(f"camps: {camps[:12]}")

#: el que diu el model despres d'entrenar, per tall
sortida = {}
for nom in ("sentit_m1.jsonl", "sortida_m1.jsonl"):
    p = MAG / nom
    if p.exists():
        for l in io.open(p, encoding="utf-8"):
            if l.strip():
                y = json.loads(l)
                if y.get("id"):
                    sortida[y["id"]] = y.get("sentit") or y.get("dit") or ""
        print(f"sortida de M1: {len(sortida)} talls ({nom})")
        break
if not sortida:
    raise SystemExit("no trobo la sortida de M1 per tall; cal el fitxer amb el que diu "
                     "el model entrenat (sentit_m1.jsonl)")


def cer_del_grup(g):
    e = n = 0
    for x in g:
        ref = rica(x.get("text") or x.get("tifinag"))
        dit = rica(sortida.get(x.get("id"), ""))
        if not ref:
            continue
        e += lev(ref, dit)
        n += len(ref)
    return e / max(1, n), n


for k in ("train", "dev"):
    c, n = cer_del_grup(grups[k])
    print(f"   {k:<6}{len(grups[k]):5d} talls · {n:7d} lletres · CER {c:.4f}")

tr, _ = cer_del_grup(grups["train"])
dv, _ = cer_del_grup(grups["dev"])
print(f"\ninflació (dev − train) = {dv - tr:+.4f}")

rnd = random.Random(20261120)
reps = []
for _ in range(VEGADES):
    a = [grups["train"][rnd.randrange(len(grups["train"]))] for _ in grups["train"]]
    b = [grups["dev"][rnd.randrange(len(grups["dev"]))] for _ in grups["dev"]]
    reps.append(cer_del_grup(b)[0] - cer_del_grup(a)[0])
reps.sort()
lo, hi = reps[int(.025 * VEGADES)], reps[int(.975 * VEGADES) - 1]
diu = "HI HA INFLACIÓ" if lo > 0 else ("no es pot dir" if hi > 0 else "cap inflació")
print(f"interval 95 %: [{lo:+.4f}, {hi:+.4f}]  ->  {diu}")
