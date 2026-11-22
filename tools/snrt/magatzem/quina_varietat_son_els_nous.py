"""De quina varietat son els 27 capitols collits, abans d'entrenar-hi res.

En Pablo: «recorda que no volem coses en tarifit perque es una altra llengua».

El problema: `varietats.json` classifica els **25 capitols antics** (11 tachelhit, 11 tarifit,
3 de l'Atles central). Els 27 que s'han collit ara son **uns altres** i no estan classificats.
S'ha construit un corpus d'entrenament sense saber en quina llengua es, i un dels episodis
(`-SyzF2LtAEs`, el que es va traduir anit) parla de **Tafersit, que es al Rif**.

Es classifica amb el lexic diferencial (`lexic_diferencial.tsv`, 157 formes tretes dels
episodis antics). Per als nous es una prova **fora de mostra**: aquell lexic no els ha vist
mai.

La puntuacio: de les formes marcades que l'episodi diu, quina part son de cada banda, pesades
per la forca. Es diu tambe **quantes marques** s'han trobat, perque amb poques no es pot
decidir.

    quina_varietat_son_els_nous.py
"""
import csv
import io
import json
import os
import re
import unicodedata
from pathlib import Path

MAG = Path(r"E:/tamazight/_magatzem")
ARREL = Path(r"E:/tamazight/TD_TV")


def _tif():
    t = io.open(MAG / "acord_26.py", encoding="utf-8").read()
    i = t.index("TIF = {")
    d = {}
    exec(t[i:t.index("}", i) + 1], {}, d)
    return d["TIF"]


TIF = _tif()


def del_tifinag(t):
    fora = []
    for c in (t or ""):
        if c in TIF:
            fora.append(TIF[c])
        elif unicodedata.name(c, "").startswith("TIFINAGH"):
            fora.append("")
        else:
            fora.append(c)
    return "".join(fora)


def rica(t):
    t = unicodedata.normalize("NFC", (t or "").lower())
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", t, flags=re.UNICODE)).strip()


lex = {}
for r in csv.DictReader(io.open(MAG / "lexic_diferencial.tsv", encoding="utf-8", newline=""),
                        delimiter="\t"):
    lex[r["forma"]] = (r["banda"], float(r["forca"]))
print(f"{len(lex)} formes al lèxic diferencial "
      f"({sum(1 for b, _ in lex.values() if b == 'tachelhit')} tachelhit, "
      f"{sum(1 for b, _ in lex.values() if b == 'tarifit')} tarifit)\n")

print(f"{'capítol':<16}{'línies':>7}{'marques':>9}{'tachelhit':>11}{'tarifit':>9}  diu")
sortida = {}
for d in sorted(os.listdir(ARREL)):
    p = ARREL / d / "subtitols.jsonl"
    if not p.exists() or p.stat().st_size == 0:
        continue
    tc = tr = n = 0
    for l in io.open(p, encoding="utf-8"):
        if not l.strip():
            continue
        x = json.loads(l)
        if x.get("credits"):
            continue
        t = rica(del_tifinag(x.get("tifinag")))
        if not t:
            continue
        n += 1
        for w in t.split():
            b = lex.get(w)
            if b:
                if b[0] == "tachelhit":
                    tc += b[1]
                else:
                    tr += b[1]
    marques = sum(1 for _ in ())  # recompte de marques, no de força
    #: es torna a comptar quantes marques diferents hi ha (no la força) per saber si decidim
    vistes = set()
    for l in io.open(p, encoding="utf-8"):
        if not l.strip():
            continue
        x = json.loads(l)
        for w in rica(del_tifinag(x.get("tifinag"))).split():
            if w in lex:
                vistes.add(w)
    tot = tc + tr
    if len(vistes) < 5 or tot == 0:
        diu = "no es pot dir"
    elif tc / tot >= .65:
        diu = "TACHELHIT"
    elif tr / tot >= .65:
        diu = "tarifit"
    else:
        diu = "entremig"
    sortida[d] = {"linies": n, "marques": len(vistes),
                  "tachelhit": round(tc / tot, 3) if tot else 0,
                  "tarifit": round(tr / tot, 3) if tot else 0, "diu": diu}
    print(f"{d:<16}{n:>7}{len(vistes):>9}{sortida[d]['tachelhit']:>11.2f}"
          f"{sortida[d]['tarifit']:>9.2f}  {diu}")

json.dump(sortida, io.open(MAG / "varietat_dels_nous.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
from collections import Counter
c = Counter(v["diu"] for v in sortida.values())
print(f"\n{dict(c)}")
print("escrit varietat_dels_nous.json")
