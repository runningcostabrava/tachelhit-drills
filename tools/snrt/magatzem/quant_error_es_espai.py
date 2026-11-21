"""Quina part del nostre error son nomes els espais.

En Pablo: «sovint veig que [el model] no sap distingir els espais entre paraules».

Si l'orella encerta les lletres i falla els espais, part del CER que mesurem no es sentir
malament: es **no saber on s'acaba una paraula**. Es mesura directament -- el mateix CER amb els
espais **trets dels dos costats** -- i la diferencia es el que costen els espais.

Tambe es mira al reves: el **WER** (error per paraula) contra el CER. Si la diferencia entre
sentir i segmentar es gran, el WER sera molt mes alt que el CER, perque una sola frontera mal
posada espatlla dues paraules senceres.

    quant_error_es_espai.py
"""
import io
import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

SORTIDA = Path(r"E:/tamazight/_magatzem/ronda/sortida/snrt_B_sortides.json")
TEXT = Path(r"E:/tamazight/_magatzem/text_triat.jsonl")


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


print(f"{'prova':<16}{'talls':>7}{'CER':>8}{'sense espais':>14}{'n’és':>8}"
      f"{'WER':>8}{'WER/CER':>9}")
per = defaultdict(lambda: {"ea": 0, "n": 0, "es": 0, "ns": 0, "ew": 0, "nw": 0})
for x in json.load(io.open(SORTIDA, encoding="utf-8")):
    if (x.get("model") or "").startswith("abans"):
        continue
    o, d = rica(x.get("or")), rica(x.get("dit"))
    if not o:
        continue
    p = per[x["prova"]]
    p["ea"] += lev(o, d)
    p["n"] += len(o)
    os_, ds = o.replace(" ", ""), d.replace(" ", "")
    p["es"] += lev(os_, ds)
    p["ns"] += len(os_)
    p["ew"] += lev(o.split(), d.split())
    p["nw"] += len(o.split())

for prova, p in sorted(per.items()):
    cer = p["ea"] / max(1, p["n"])
    sen = p["es"] / max(1, p["ns"])
    wer = p["ew"] / max(1, p["nw"])
    part = 100 * (cer - sen) / cer if cer else 0
    print(f"{prova:<16}{p['nw']:>7}{cer:>8.4f}{sen:>14.4f}{part:>7.0f}%"
          f"{wer:>8.4f}{wer/max(1e-9,cer):>9.1f}")

#: i el mateix sobre el material del SNRT, que es on s'entrena
ea = n = es = ns = ew = nw = 0
for l in io.open(TEXT, encoding="utf-8"):
    if not l.strip():
        continue
    x = json.loads(l)
    o, d = rica(x.get("tifinag")), rica(x.get("sentit"))
    if not o or not d:
        continue
    ea += lev(o, d)
    n += len(o)
    es += lev(o.replace(" ", ""), d.replace(" ", ""))
    ns += len(o.replace(" ", ""))
    ew += lev(o.split(), d.split())
    nw += len(o.split())
cer, sen, wer = ea / max(1, n), es / max(1, ns), ew / max(1, nw)
print(f"\nSNRT (ull contra orella, {nw} paraules): CER {cer:.4f} · sense espais {sen:.4f} "
      f"({100*(cer-sen)/cer:.0f} % de l'error són els espais) · WER {wer:.4f}")

#: quantes vegades l'orella enganxa o parteix, comptat de la manera mes simple
mes = menys = igual = 0
for l in io.open(TEXT, encoding="utf-8"):
    if not l.strip():
        continue
    x = json.loads(l)
    o, d = rica(x.get("tifinag")).split(), rica(x.get("sentit")).split()
    if not o or not d:
        continue
    if len(d) < len(o):
        menys += 1
    elif len(d) > len(o):
        mes += 1
    else:
        igual += 1
t = mes + menys + igual
print(f"paraules per rèplica: l'orella en diu MENYS que l'ull {menys} vegades "
      f"({100*menys/t:.0f} %), més {mes} ({100*mes/t:.0f} %), igual {igual} "
      f"({100*igual/t:.0f} %)")
