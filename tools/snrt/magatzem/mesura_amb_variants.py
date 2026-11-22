"""Quant del nostre error es que el model diu la forma d'un altre dialecte?

El CER compara el que sent el model amb el text de referencia lletra per lletra. Si el parlant
diu `nnš` i la referencia escriu `nnk`, comptem un error -- pero el model **ha encertat**: ha
escrit el que s'ha dit, en la varietat que s'ha dit. Castigar-lo per aixo es mesurar malament, i
a mes empeny el cercle cap a la norma i en contra de la parla, que es el contrari del que volem.

Amb la taula de variants (`taula_variants.tsv`, feta per evidencia: dues formes que s'alineen
moltes vegades amb el mateix signe escrit) es pot mesurar d'una altra manera: **abans de comparar,
si la paraula que diu el model es una variant coneguda de la paraula de la referencia, es compta
com a encert.**

L'honestedat de la prova: la taula surt del SNRT, i per aixo es mesura **a les proves amb veritat
humana** (`zouhir-tests`, `tfa-226`, `test-fora`, `cv-zgh-test`), on la taula es material de fora.
Mesurar-la damunt del SNRT seria donar-se la rao amb la propia taula.

Es diu el CER d'abans i el de despres. La diferencia **no es una millora del model**: es la part
de l'error que no era error.
"""
import csv
import io
import json
import random
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

MAG = Path(r"E:/tamazight/_magatzem")
PROVES = ("zouhir-tests", "tfa-226", "test-fora", "cv-zgh-test")
VEGADES = 2000

TIF_RIC = {"ⴰ": "a", "ⴱ": "b", "ⴳ": "g", "ⴷ": "d", "ⴹ": "ḍ", "ⴻ": "e", "ⴼ": "f", "ⴽ": "k",
           "ⵀ": "h", "ⵃ": "ḥ", "ⵄ": "ε", "ⵅ": "ḫ", "ⵇ": "q", "ⵉ": "i", "ⵊ": "j", "ⵍ": "l",
           "ⵎ": "m", "ⵏ": "n", "ⵓ": "u", "ⵔ": "r", "ⵕ": "r", "ⵖ": "ġ", "ⵙ": "s", "ⵚ": "ṣ",
           "ⵛ": "š", "ⵜ": "t", "ⵟ": "ṭ", "ⵡ": "w", "ⵢ": "y", "ⵣ": "z", "ⵥ": "ẓ", "ⵯ": "w"}
LLATI_RIC = {"ɣ": "ġ", "γ": "ġ", "ɛ": "ε", "ṛ": "r", "c": "š", "x": "ḫ", "χ": "ḫ", "ž": "j",
             "ǧ": "j", "ʷ": "w", "v": "f", "p": "b", "o": "u"}


def rica(t):
    t = unicodedata.normalize("NFC", (t or "")).strip().lower()
    t = "".join(TIF_RIC.get(c, c) for c in t)
    t = "".join(LLATI_RIC.get(c, c) for c in t)
    t = re.sub(r"[^a-zġεḥḍṭṣẓḫš ]+", "", t)
    return re.sub(r" +", " ", t).strip()


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


#: --- la taula: forma -> {les seves germanes} ---
germanes = defaultdict(set)
for r in csv.DictReader(io.open(MAG / "taula_variants.tsv", encoding="utf-8", newline=""),
                        delimiter="\t"):
    f = rica(r["forma"])
    for g in (r.get("altres_formes") or "").split(","):
        g = rica(g)
        if f and g and f != g:
            germanes[f].add(g)
    #: la forma escrita tambe compta: el model pot encertar la norma i la referencia la variant
    e = rica(r["escrit"])
    if f and e and f != e:
        germanes[f].add(e)
        germanes[e].add(f)
print(f"{len(germanes)} formes amb germanes conegudes\n")


def cer_parells(o, d, amb_variants):
    """Errors i lletres d'una frase. Amb variants, una paraula germana compta com a encert."""
    po, pd = rica(o).split(), rica(d).split()
    if not amb_variants:
        a, b = " ".join(po), " ".join(pd)
        return lev(a, b), len(a)
    #: substitucio paraula a paraula nomes quan la llargada casa: no es un alineament, es un
    #: perdo els casos clars i prou (i per aixo el resultat es un MINIM del que es guanyaria)
    if len(po) == len(pd):
        pd = [o_ if d_ in germanes.get(o_, ()) else d_ for o_, d_ in zip(po, pd)]
    a, b = " ".join(po), " ".join(pd)
    return lev(a, b), len(a)


files = json.load(io.open(MAG / "ronda" / "sortida" / "snrt_B_sortides.json", encoding="utf-8"))
rnd = random.Random(20261120)
print(f"{'prova':<16}{'frases':>7}{'CER':>9}{'amb variants':>14}{'canvi':>9}{'interval 95 %':>22}")
for prova in PROVES:
    fil = [x for x in files if x.get("prova") == prova
           and not (x.get("model") or "").startswith("abans")]
    dades = []
    for x in fil:
        o, d = (x.get("or") or "").strip(), (x.get("dit") or "").strip()
        if not o:
            continue
        e0, n = cer_parells(o, d, False)
        e1, _ = cer_parells(o, d, True)
        dades.append((e0, e1, n))
    if len(dades) < 30:
        continue
    c0 = sum(x[0] for x in dades) / max(1, sum(x[2] for x in dades))
    c1 = sum(x[1] for x in dades) / max(1, sum(x[2] for x in dades))
    reps = []
    for _ in range(VEGADES):
        m = [dades[rnd.randrange(len(dades))] for _ in dades]
        n = max(1, sum(x[2] for x in m))
        reps.append(sum(x[1] for x in m) / n - sum(x[0] for x in m) / n)
    reps.sort()
    lo, hi = reps[int(.025 * VEGADES)], reps[int(.975 * VEGADES)]
    print(f"{prova:<16}{len(dades):7d}{c0:9.4f}{c1:14.4f}{c1-c0:+9.4f}   [{lo:+.4f}, {hi:+.4f}]")
print("\nLa diferència NO és una millora del model: és la part de l'error que no era error.")
