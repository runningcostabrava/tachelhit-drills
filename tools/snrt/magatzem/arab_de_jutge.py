"""L'àrab com a jutge: ¿l'ull llegeix poc, o llegeix bé i diuen coses diferents?

La taxa d'acord barreja dues avaries molt diferents i per això no serveix sola:

  (a) l'OCR llegeix poc o malament (fons carregat, binarització fallida);
  (b) l'OCR llegeix bé i la parla diu una altra cosa (el fenomen norma ↔ dialecte).

Les dues donen acord baix i volen coses oposades: la (a) s'ha d'arreglar, la (b) s'ha
d'aprofitar.

L'àrab cremat les separa i no costa res. És una tercera lectura, independent de les altres dues,
i sabem que va bé (el lector d'àrab està mesurat: CER 0,0059). La idea: la quantitat de text
que hi ha a cada rèplica la marca l'àrab. Si l'ull en treu molt menys del que l'àrab fa esperar,
és que ha perdut text — avaria (a). Si en treu una quantitat normal i tot i així no casa amb
l'orella, és (b).

No es compara el CONTINGUT (són llengües diferents): només **quant** n'hi ha, que és el que
distingeix «no ho he llegit» de «diu una altra cosa».
"""
import io
import json
import statistics
from collections import defaultdict
from pathlib import Path

ACORD = Path(r"E:/tamazight/_magatzem/acord_26.jsonl")
VISOR = Path(r"E:/tamazight/_visor")

#: lletres amazigues per caràcter àrab, mesurat als capítols que van bé
per_cap = defaultdict(lambda: {"A": 0, "n": 0, "tif": 0, "ar": 0, "buides": 0})
grau = {}
for l in io.open(ACORD, encoding="utf-8"):
    if l.strip():
        r = json.loads(l)
        grau[r["id"]] = r["grau"]

for carpeta in sorted(VISOR.iterdir()):
    p = carpeta / "subtitols.jsonl"
    if not p.exists() or len(carpeta.name) != 40:
        continue
    for i, l in enumerate(io.open(p, encoding="utf-8")):
        if not l.strip():
            continue
        x = json.loads(l)
        ident = f"{carpeta.name}:{x.get('k', i)}"
        g = grau.get(ident)
        c = per_cap[carpeta.name]
        c["n"] += 1
        c["A"] += g == "A"
        tif = len([ch for ch in (x.get("tifinag") or "") if "\u2d30" <= ch <= "\u2d7f"])
        ar = len([ch for ch in (x.get("arab") or "") if ch.strip()])
        c["tif"] += tif
        c["ar"] += ar
        if ar >= 10 and tif < 3:
            c["buides"] += 1

files = []
for cap, c in per_cap.items():
    if c["n"] < 50 or not c["ar"]:
        continue
    files.append((c["A"] / c["n"], cap, c["tif"] / c["ar"], c["buides"] / c["n"], c["n"]))
files.sort(reverse=True)

#: el que és «normal» el diuen els capítols que van bé, no jo
normal = statistics.median([f[2] for f in files[:6]])
print(f"lletres amazigues per caràcter àrab als 6 millors: {normal:.3f} (la referència)\n")
print(f"{'capítol':<18}{'acord':>7}{'tif/àrab':>10}{'del normal':>12}{'rèpliques mudes':>17}  diagnòstic")
for a, cap, rel, buid, n in files:
    prop = rel / normal if normal else 0
    if prop < 0.75:
        diag = "(a) l'ull ha perdut text"
    elif a < 0.05:
        diag = "(b) llegeix bé i NO casa"
    else:
        diag = "va bé"
    print(f"{cap[:16]:<18}{100*a:6.1f}%{rel:10.3f}{100*prop:11.0f}%{100*buid:16.1f}%  {diag}")
