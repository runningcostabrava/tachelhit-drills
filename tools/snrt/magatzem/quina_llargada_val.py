"""A partir de quantes consonants casar amb el diccionari vol dir alguna cosa.

El casament per esquelet existeix per una rao bona: el diccionari escriu vocals que la parla no
diu (`tanemmirt` / `tanmmirt`). Pero amb esquelets curts casa tot amb tot: amb un minim de dues
consonants, el 85 % de les formes que es donaven per confirmades hi eren per col·lisio.

Exigir la forma **exacta** es passar-se de l'altre costat: la nostra orella no escriu les vocals
com el llibre, i de 3.632 es baixa a 160.

Aqui el llindar no es tria: es **mesura**. Per a cada llargada d'esquelet es compta quantes
formes nostres casen amb el diccionari de debo, i quantes casen amb **un diccionari fals** de la
mateixa mida i amb la mateixa distribucio de llargades, fet amb les mateixes consonants. El que
casa amb el fals es la casualitat que s'ha de descomptar.

    quina_llargada_val.py
"""
import collections
import csv
import io
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, r"E:/tamazight/_magatzem")
from tria_el_millor_text import esquelet  # noqa: E402

MAG = Path(r"E:/tamazight/_magatzem")
WIKI = Path(r"C:/Users/josep/Veus-tachelhit/_escoltats/wikimawal/wikimawal.json")
VEGADES = 20

#: --- el diccionari de debo, per esquelet ---
esq_dicc = set()
formes_dicc = []
for e in json.load(io.open(WIKI, encoding="utf-8")).get("entrades", []):
    for f in (e.get("llati"), e.get("tifinag")):
        k = esquelet(f or "")
        if k:
            esq_dicc.add(k)
            formes_dicc.append(k)
for r in csv.DictReader(io.open(MAG / "lexic_ircam_gramatical.tsv", encoding="utf-8", newline=""),
                        delimiter="\t"):
    for c in ("llati", "tifinag"):
        for f in (r.get(c) or "").split(" - "):
            k = esquelet(f.strip())
            if k:
                esq_dicc.add(k)
                formes_dicc.append(k)

#: les consonants que fa servir el diccionari, amb la seva frequencia: el diccionari fals
#: s'ha de fer amb les mateixes lletres i les mateixes llargades, o la comparacio no val
lletres = collections.Counter(c for k in formes_dicc for c in k)
pes = list(lletres.keys())
prob = [lletres[c] for c in pes]
llargades = [len(k) for k in formes_dicc]

nostres = []
for r in csv.DictReader(io.open(MAG / "index_paraules.tsv", encoding="utf-8", newline=""),
                        delimiter="\t"):
    f = (r.get("sentit") or "").strip()
    if f:
        nostres.append((f, esquelet(f), int(r.get("boques") or 0)))
print(f"{len(nostres)} formes nostres · {len(esq_dicc)} esquelets al diccionari\n")

rnd = random.Random(20261120)
print(f"{'consonants':>11}{'formes':>8}{'casen':>8}{'per atzar':>11}{'de debò':>9}  què vol dir")
for L in range(2, 9):
    quines = [x for x in nostres if len(x[1]) == L]
    if not quines:
        continue
    casen = sum(1 for _, k, _ in quines if k in esq_dicc)
    falsos = []
    for _ in range(VEGADES):
        fals = set()
        while len(fals) < len(esq_dicc):
            n = rnd.choice(llargades)
            fals.add("".join(rnd.choices(pes, weights=prob, k=n)))
        falsos.append(sum(1 for _, k, _ in quines if k in fals))
    atzar = sum(falsos) / len(falsos)
    net = casen - atzar
    part = (net / casen * 100) if casen else 0
    diu = ("tot casualitat" if part < 25 else
           "mig i mig" if part < 60 else
           "es pot fer servir")
    print(f"{L:>11}{len(quines):>8}{casen:>8}{atzar:>11.1f}{net:>9.0f}  {diu} ({part:.0f} % net)")

print("\nI amb el mínim de boques, per a les llargades que valen:")
for L in (4, 5):
    for b in (1, 3, 5):
        q = [x for x in nostres if len(x[1]) >= L and x[2] >= b]
        casen = sum(1 for _, k, _ in q if k in esq_dicc)
        print(f"   esquelet >= {L}, boques >= {b}: {casen} formes confirmades de {len(q)}")
