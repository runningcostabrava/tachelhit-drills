"""La fitxa de cada forma: **per que te'n pots fiar**, no quant.

En Pablo: «per crear el diccionari hem de tenir indexs de fiabilitat». La temptacio es posar un
numero del 0 al 100, i seria mentida: els senyals diuen coses diferents i un sol numero els
amaga. Una forma dita 50 vegades per UNA boca i una dita 50 vegades per VINT no son igual de
fiables, i la mitjana no ho sap.

Sis senyals, cadascun amb el seu sentit:

  * **vegades** — quants cops s'ha sentit. Sol, no vol dir res: 50 cops pot ser 50 cops el
    mateix error del model.
  * **boques** — quants parlants diferents la diuen. Es el senyal que separa una paraula de la
    llengua d'una mania d'un parlant o del model.
  * **acord** — quantes vegades l'ull (el subtitol) hi va coincidir. **L'unic testimoni
    independent de l'orella** que tenim.
  * **confianca** — com de segur n'estava el model.
  * **diccionari** — si una persona ja la va escriure (Viccionari zgh, lexic de l'IRCAM).
  * **amb significat** — en quantes aparicions la replica tenia un catala confirmat.

I d'aqui surt un **veredicte amb motiu**, que es el que serveix per treballar:

  `solida`      moltes boques i acord: paraula de la llengua, encara que no sigui a cap diccionari
  `de llibre`   un diccionari la te (i normalment tambe la diem)
  `per mirar`   molt dita i poc corroborada: candidata a ser un error SISTEMATIC del model
  `poca cosa`   vista poc; no se'n pot dir res

La pila `per mirar` es la que val per al model: una forma que el model diu molt, amb acord baix i
que no es a cap diccionari, **es una al·lucinacio seva repetida** -- com el ġ~ḫ que vam trobar el
19-11 amb 377 paraules.

Surt `fitxa_fiabilitat.tsv`.
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

#: --- els diccionaris humans ---
#:
#: Es casa de DUES maneres, i no valen igual. Per **forma** (la paraula tal com s'escriu, sense
#: majuscules) es una troballa. Per **esquelet** -- nomes les consonants, perque la norma escriu
#: vocals que la parla no diu -- es una pista, i amb esquelets curts no es ni aixo: amb un minim
#: de dues consonants, claus com `ns` casen amb desenes de formes que no hi tenen res a veure, i
#: **3.104 de les 3.632 formes que es donaven per confirmades (el 85 %) hi eren per una
#: col·lisio d'aquesta mena**. El llindar no es tria a ull: `quina_llargada_val.py` compta,
#: per a cada llargada, quantes formes nostres casen amb el diccionari de debo i quantes amb un
#: diccionari FALS de la mateixa mida, les mateixes lletres i les mateixes llargades:
#:
#:   consonants   casen   per atzar   de debo
#:            2    1833        1479       354  (19 %)  <- gairebe tot casualitat
#:            3    1271        1070       201  (16 %)
#:            4     412         146       266  (65 %)  <- un de cada tres es casualitat
#:            5     111           6       105  (95 %)  <- aixo si
#:            6       5           0         5  (100 %)
#:
#: Per aixo **cinc consonants confirmen** (van amb les exactes) i **quatre nomes insinuen** (pila
#: a part, amb el seu avis). Tres o menys no diuen res i no es miren.
CONFIRMA, INSINUA = 5, 4
dicc_forma, dicc_esq = defaultdict(set), defaultdict(set)


def desa(f, font):
    f = (f or "").strip().lower()
    if not f:
        return
    dicc_forma[f].add(font)
    k = esquelet(f)
    if len(k) >= INSINUA:
        dicc_esq[k].add(font)


for e in json.load(io.open(WIKI, encoding="utf-8")).get("entrades", []):
    for f in (e.get("llati"), e.get("tifinag")):
        desa(f, "viccionari")
for r in csv.DictReader(io.open(MAG / "lexic_ircam_gramatical.tsv", encoding="utf-8", newline=""),
                        delimiter="\t"):
    for c in ("llati", "tifinag"):
        for f in (r.get(c) or "").split(" - "):
            desa(f, "ircam")

#: --- de les ocurrencies: en quantes aparicions la replica tenia significat, i a quines varietats
var = {r["capitol"][:16]: r["varietat"]
       for r in json.load(io.open(MAG / "varietats.json", encoding="utf-8"))}
amb_sentit = defaultdict(int)
varietats = defaultdict(set)
for l in io.open(MAG / "ocurrencies_triat.jsonl", encoding="utf-8"):
    if not l.strip():
        continue
    x = json.loads(l)
    f = (x.get("sentit") or "").strip()
    if not f:
        continue
    if (x.get("catala") or "").strip():
        amb_sentit[f] += 1
    v = var.get((x.get("capitol") or "")[:16])
    if v:
        varietats[f].add(v)

files = list(csv.DictReader(io.open(MAG / "index_paraules.tsv", encoding="utf-8", newline=""),
                            delimiter="\t"))
print(f"{len(files)} formes\n")

fitxes = []
for r in files:
    forma = (r.get("sentit") or "").strip()
    if not forma:
        continue
    k = esquelet(forma)
    vegades = int(r.get("vegades") or 0)
    boques = int(r.get("boques") or 0)
    acord_n = int(r.get("amb_acord") or 0)
    acord = acord_n / max(1, vegades)
    conf = float(r.get("confianca") or 0)
    on = sorted(dicc_forma.get(forma.lower(), ()))
    if not on and len(k) >= CONFIRMA:
        on = sorted(dicc_esq.get(k, ()))          #: cinc consonants: 95 % de debo
    on_esq = sorted(dicc_esq.get(k, ())) if not on and len(k) == INSINUA else []
    sentit = amb_sentit.get(forma, 0)
    vs = sorted(varietats.get(forma, ()))

    #: El primer repartiment posava TOT el que es diu molt i no casa amb el subtitol a «per
    #: mirar: candidata a error del model». Mirant-ho, era fals i del reves: `waḫḫa` (19 boques,
    #: confiança 0,94), `walakin`, `baš`, `ḥtta`, `kulši`, `aṭṭas`... son manlleus de l'arab i
    #: particules dialectals que la gent diu i **que la norma de l'IRCAM no escriu**. Dinou
    #: parlants diferents no repeteixen l'al·lucinacio d'un model.
    #:
    #: El que separa les dues coses son les BOQUES i la CONFIANCA, no l'acord: una forma que
    #: molta gent diu amb seguretat i que el subtitol no escriu es llengua viva; una que diu poca
    #: gent, amb poca confianca i sense cap suport, es cosa nostra.
    if on:
        verdicte, motiu = "de llibre", "+".join(on)
    elif on_esq:
        #: quatre consonants: un de cada tres es casualitat, i per aixo va a part
        verdicte, motiu = "potser al diccionari", "+".join(on_esq) + f", esquelet {k}"
    elif boques >= 5 and acord >= .25:
        verdicte, motiu = "sòlida", f"{boques} boques, acord {acord:.2f}"
    elif vegades >= 10 and boques >= 5 and conf >= .75 and acord < .15:
        verdicte, motiu = "la norma no l'escriu", (f"{boques} boques, confiança {conf:.2f}, "
                                                   f"però acord {acord:.2f}")
    elif vegades >= 10 and (acord < .1 or boques <= 2):
        verdicte, motiu = "per mirar", (f"{vegades} cops però acord {acord:.2f}"
                                        + (f" i només {boques} boques" if boques <= 2 else ""))
    else:
        verdicte, motiu = "poca cosa", f"{vegades} cops, {boques} boques"
    fitxes.append({"forma": forma, "escrit": r.get("escrit", ""), "verdicte": verdicte,
                   "motiu": motiu, "vegades": vegades, "boques": boques, "acord": round(acord, 3),
                   "confianca": round(conf, 3), "diccionari": ",".join(on),
                   "amb_significat": sentit, "varietats": ",".join(vs),
                   "exemple": (r.get("exemple") or "").replace("\t", " ")})

compte = defaultdict(int)
for f in fitxes:
    compte[f["verdicte"]] += 1
print(f"{'veredicte':<14}{'formes':>8}{'%':>7}")
for v in ("de llibre", "potser al diccionari", "sòlida", "la norma no l'escriu", "per mirar", "poca cosa"):
    print(f"{v:<14}{compte[v]:8d}{100*compte[v]/len(fitxes):7.1f}")

print("\nLes quinze que més diem i que LA NORMA NO ESCRIU — la llengua viva contra el llibre:")
for f in sorted((x for x in fitxes if x["verdicte"] == "la norma no l'escriu"),
                key=lambda x: -x["vegades"])[:15]:
    print(f"   {f['forma']:<16}{f['escrit']:<16}{f['vegades']:>5} cops {f['boques']:>3} boques"
          f"  acord {f['acord']:.2f}  conf {f['confianca']:.2f}")

print("\nI les que SÍ que fan mala espina (poques boques o poca confiança):")
for f in sorted((x for x in fitxes if x["verdicte"] == "per mirar"),
                key=lambda x: -x["vegades"])[:8]:
    print(f"   {f['forma']:<16}{f['escrit']:<16}{f['vegades']:>5} cops {f['boques']:>3} boques"
          f"  acord {f['acord']:.2f}  conf {f['confianca']:.2f}")

camps = ["forma", "escrit", "verdicte", "motiu", "vegades", "boques", "acord", "confianca",
         "diccionari", "amb_significat", "varietats", "exemple"]
with io.open(MAG / "fitxa_fiabilitat.tsv", "w", encoding="utf-8", newline="\n") as f:
    f.write("\t".join(camps) + "\n")
    for x in sorted(fitxes, key=lambda y: (y["verdicte"], -y["vegades"])):
        f.write("\t".join(str(x[c]) for c in camps) + "\n")
print(f"\nescrit fitxa_fiabilitat.tsv")
