"""Quines de les nostres formes estan confirmades per un diccionari fet per PERSONES.

En Pablo: «arribes a catalogar vocabulari nou quan vegis que està molt ben establert i utilitzat
de forma reiterada?». La resposta honesta es que **repetit no vol dir correcte**: una forma
sentida cinquanta vegades pot ser el mateix error del model repetit cinquanta vegades (el 20-11
el Qwen va escriure el logotip del canal com si fos text 82 vegades al mateix episodi).

El que si que es pot fer sense cap parlant es creuar el que hem sentit amb el que **una persona
ja va escriure en un diccionari**:

  * el **Viccionari en amazic estandard** (zgh.wiktionary.org, 1.033 entrades, CC BY-SA 4.0,
    atribucio als col·laboradors);
  * el **lexic gramatical de l'IRCAM** (733 termes, tifinag i llati).

El creuament no es per forma exacta sino per **esquelet de consonants**, perque el diccionari
escriu la norma i l'orella escriu la parla: `tmaziġt` i `ⵜⴰⵎⴰⵣⵉⵖⵜ` son la mateixa paraula amb
vocals diferents, i comparades lletra per lletra no casen.

Surten tres piles:

  1. **confirmada**: la diem i un diccionari la te. Vocabulari de debo.
  2. **establerta pero sense diccionari**: repetida, de boques diferents i amb l'ull d'acord,
     pero enlloc mes. Es el que val la pena ensenyar a algu que parli la llengua.
  3. la resta: vista poc o sense acord.

Surt `lexic_confirmat.tsv`.
"""
import csv
import io
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, r"E:/tamazight/_magatzem")
from tria_el_millor_text import esquelet  # noqa: E402

MAG = Path(r"E:/tamazight/_magatzem")
WIKI = Path(r"C:/Users/josep/Veus-tachelhit/_escoltats/wikimawal/wikimawal.json")
IRCAM = MAG / "lexic_ircam_gramatical.tsv"
#: el que compta com a «establerta» sense diccionari: dit sovint, per boques diferents, i amb
#: l'ull d'acord almenys un cop de cada tres
VEGADES, BOQUES, ACORD = 5, 3, .33

diccionari = defaultdict(set)      #: esquelet -> {d'on surt}
n_wiki = n_ircam = 0
dades = json.load(io.open(WIKI, encoding="utf-8"))
for e in dades.get("entrades", []):
    for forma in (e.get("llati"), e.get("tifinag")):
        k = esquelet(forma or "")
        if len(k) >= 2:
            diccionari[k].add("viccionari")
            n_wiki += 1
for r in csv.DictReader(io.open(IRCAM, encoding="utf-8", newline=""), delimiter="\t"):
    for camp in ("llati", "tifinag"):
        for forma in (r.get(camp) or "").split(" - "):
            k = esquelet(forma.strip())
            if len(k) >= 2:
                diccionari[k].add("ircam")
                n_ircam += 1
print(f"diccionaris: {len(diccionari)} esquelets diferents "
      f"({n_wiki} formes del viccionari, {n_ircam} de l'IRCAM)\n")

files = list(csv.DictReader(io.open(MAG / "index_paraules.tsv", encoding="utf-8", newline=""),
                            delimiter="\t"))
print(f"{len(files)} formes nostres\n")

piles = defaultdict(list)
for r in files:
    sentit = (r.get("sentit") or "").strip()
    k = esquelet(sentit)
    if len(k) < 2:
        continue
    vegades = int(r.get("vegades") or 0)
    boques = int(r.get("boques") or 0)
    amb_acord = int(r.get("amb_acord") or 0)
    acord = amb_acord / max(1, vegades)
    on = diccionari.get(k)
    if on:
        piles["confirmada"].append((r, sorted(on)))
    elif vegades >= VEGADES and boques >= BOQUES and acord >= ACORD:
        piles["establerta"].append((r, []))
    else:
        piles["resta"].append((r, []))

for nom in ("confirmada", "establerta", "resta"):
    p = piles[nom]
    print(f"{nom:<14}{len(p):7d}  {100*len(p)/len(files):5.1f}%")

print(f"\nLes deu confirmades que més diem:")
for r, on in sorted(piles["confirmada"], key=lambda x: -int(x[0].get("vegades") or 0))[:10]:
    print(f"   {r['sentit']:<16}{r['escrit']:<18}{r['vegades']:>5} cops, {r['boques']:>3} boques"
          f"   [{', '.join(on)}]")

print(f"\nLes deu establertes que més diem i que NO són a cap diccionari:")
for r, _ in sorted(piles["establerta"], key=lambda x: -int(x[0].get("vegades") or 0))[:10]:
    print(f"   {r['sentit']:<16}{r['escrit']:<18}{r['vegades']:>5} cops, {r['boques']:>3} boques"
          f"   «{(r.get('exemple') or '')[:40]}»")

with io.open(MAG / "lexic_confirmat.tsv", "w", encoding="utf-8", newline="\n") as f:
    f.write("pila\tsentit\tescrit\tvegades\tboques\tamb_acord\tconfianca\tdiccionaris\texemple\n")
    for nom in ("confirmada", "establerta"):
        for r, on in sorted(piles[nom], key=lambda x: -int(x[0].get("vegades") or 0)):
            f.write("\t".join([nom, r.get("sentit", ""), r.get("escrit", ""),
                               r.get("vegades", ""), r.get("boques", ""),
                               r.get("amb_acord", ""), r.get("confianca", ""),
                               ",".join(on), (r.get("exemple") or "").replace("\t", " ")]) + "\n")
print(f"\nescrit lexic_confirmat.tsv")
print("\nAvís: «confirmada» vol dir que una persona va escriure aquesta paraula en un diccionari,")
print("no que nosaltres l'hàgim sentida bé. Són dues coses i totes dues calen.")
