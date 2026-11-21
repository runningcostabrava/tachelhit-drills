"""Desfer una cadena enganxada **a partir del significat**, no del diccionari sencer.

En Pablo: «si el resultat de l'escolta del nostre model es una cadena llarga podries fer el cami
invers, ja que tenim la traduccio de l'arab intentar esbrinar les paraules que hi ha en aquella
cadena llarga».

El primer intent (`talla_les_cadenes.py`) buscava **per tot el lexic** quines paraules podien
compondre la cadena, i disparava en 6 de 1.709 rèpliques: amb un lexic petit, trobar una
particio sencera es gairebe impossible.

Aquest es un altre punt de vista, i es el seu: **el significat diu quines poques formes s'hi han
de buscar**. Si l'arab diu «on vas?», dins de la cadena hi ha d'haver la forma de «on» i la de
«anar» -- dues candidates, no quaranta mil. I no cal partir la cadena sencera: trobar-hi una
paraula ja val.

**D'on surten les candidates.** La biblioteca de l'aplicacio son **6.628 parelles amazic-catala**
fetes per persones. D'aqui s'indueix quin mot amazic va amb quin mot catala per coocurrencia
(Dice): si `aman` surt en vint frases i `aigua` en vint-i-dues, i divuit vegades surten juntes,
la parella es bona. S'hi suma el Viccionari amazic, que ja porta les traduccions escrites.

**Com es comprova.** No pel mateix cami: el **tifinag cremat al video** es un testimoni
independent (l'ull, no l'orella). Si la forma que el significat ens fa buscar dins la cadena
tambe surt al tifinag d'aquella replica, l'encert no es nostre invent.

    el_cami_invers.py [llargada_minima_de_cadena]
"""
import io
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, r"E:/tamazight/_magatzem")

def _taula_tifinag():
    """La taula de lletres d'`acord_26.py`, llegida sense executar-lo.

    Importar-lo l'executa sencer -- llegeix `sys.argv` i es pot aturar -- i aqui nomes cal el
    mapa de lletres."""
    t = io.open(r"E:/tamazight/_magatzem/acord_26.py", encoding="utf-8").read()
    i = t.index("TIF = {")
    j = t.index("}", i) + 1
    d = {}
    exec(t[i:j], {}, d)
    return d["TIF"]


TIF = _taula_tifinag()
from tria_el_millor_text import esquelet, lev  # noqa: E402

MAG = Path(r"E:/tamazight/_magatzem")
BIBLIO = Path(r"E:/tamazight/_entrenament/manifest_v3.jsonl")
WIKI = Path(r"C:/Users/josep/Veus-tachelhit/_escoltats/wikimawal/wikimawal.json")
MIN_CADENA = int(sys.argv[1]) if len(sys.argv) > 1 else 11
#: Buscar AMPLE i deixar que l'ull filtri. Mesurat amb `mes_candidates.py`: el filtre estret
#: (2 / 0,22) toca el 7,3 % de les cadenes amb un 73 % d'encert -> ~316 formes confirmades; el
#: filtre ample (1 / 0,10) toca el 15,8 % amb un 63 % -> **~797**. Quan hi ha un verificador
#: independent, el que compta no es la precisio de la cerca sino quantes troballes confirmades
#: en treus, i l'ull no ha sentit res. El que es desa es nomes el que l'ull confirma.
MIN_COPS, MIN_DICE = 1, 0.10
#: TOLERA: acceptar la forma a una errada de distancia. **Desactivat**, i mesurat: afegeix 189
#: troballes de les quals l'ull nomes en confirma el 26 %, contra el 73 % de les exactes. Tres
#: quartes parts serien invencio nostra. S'hi arriba amb --tolera per tornar-ho a mirar.
TOLERA = "--tolera" in sys.argv

#: mots catalans que no diuen res sobre quina forma buscar
BUIDES = set("""el la els les un una uns unes de del dels d a al als en amb per per què que qui
com on quan i o ni no pas em et es ens us se li li hi ho meu meva teu teva seu seva nostre vostre
aquest aquesta aquests aquestes aquell aquella això allò ja molt més menys tan tant també
sí doncs però sinó perquè si quin quina quins quines hi ha he has ha hem heu han era eres
som sou son és ser estar fer dir va van vaig vas vam vau cap tot tota tots totes altre altra
me te se nos vos lo los les ara abans després sobre sota entre fins des cada algun alguna
""".split())


def net(t):
    t = (t or "").lower()
    return [w for w in re.findall(r"[a-zàáèéíïòóúüçñ']+", t) if len(w) > 1]


def amaz(t):
    return [w for w in re.findall(r"[^\W\d_]+", (t or "").lower(), re.UNICODE) if len(w) > 1]


def del_tifinag(t):
    return "".join(TIF.get(c, c if not unicodedata.name(c, "").startswith("TIFINAGH") else "")
                   for c in (t or ""))


# ---------------------------------------------------------------- 1. les candidates
print("induint el lèxic de la biblioteca...", flush=True)
parelles = []
for l in io.open(BIBLIO, encoding="utf-8"):
    if not l.strip():
        continue
    x = json.loads(l)
    c, a = net(x.get("catala")), amaz(x.get("text"))
    if c and a and len(a) <= 12:
        parelles.append((c, a))
nc, na = Counter(), Counter()
junts = defaultdict(Counter)
for c, a in parelles:
    for w in set(c):
        nc[w] += 1
        for f in set(a):
            junts[w][f] += 1
    for f in set(a):
        na[f] += 1

candidates = defaultdict(set)
for w, fs in junts.items():
    if w in BUIDES or nc[w] < MIN_COPS:
        continue
    for f, n in fs.items():
        if n >= MIN_COPS and 2 * n / (nc[w] + na[f]) >= MIN_DICE and len(f) >= 3:
            candidates[w].add(f)
induides = sum(len(v) for v in candidates.values())

#: el Viccionari ja porta les traduccions escrites a ma
for e in json.load(io.open(WIKI, encoding="utf-8")).get("entrades", []):
    forma = (e.get("llati") or "").strip().lower()
    if len(forma) < 3:
        continue
    for t in (e.get("traduccions") or {}).values() if isinstance(e.get("traduccions"), dict) \
            else (e.get("traduccions") or []):
        for w in net(t if isinstance(t, str) else str(t)):
            if w not in BUIDES:
                candidates[w].add(forma)
print(f"   {len(parelles)} parelles · {induides} candidates induïdes · "
      f"{sum(len(v) for v in candidates.values())} amb el Viccionari\n", flush=True)

# ---------------------------------------------------------------- 2. el camí invers
files = [json.loads(l) for l in io.open(MAG / "text_triat.jsonl", encoding="utf-8") if l.strip()]
cadenes = tocades = trobades = confirmades = amb_ull = 0
per_mena = {"exacta": [0, 0, 0], "amb una errada": [0, 0, 0]}
confirmat = []
exemples = []
for x in files:
    llargues = [w for w in amaz(x.get("sentit")) if len(w) >= MIN_CADENA]
    if not llargues or not (x.get("catala") or "").strip():
        continue
    cadenes += len(llargues)
    ull = esquelet(del_tifinag(x.get("tifinag") or ""))
    vol = [w for w in net(x.get("catala")) if w not in BUIDES and w in candidates]
    if not vol:
        continue
    for cad in llargues:
        ec = esquelet(cad)
        dins = []
        for w in vol:
            for f in candidates[w]:
                ef = esquelet(f)
                if len(ef) < 3:
                    continue
                #: la forma ha de ser DINS de la cadena, i prou llarga perque no sigui casualitat
                if ef in ec:
                    dins.append((w, f, ef, "exacta"))
                elif TOLERA and len(ef) >= 4:
                    #: l'orella es menja o canvia una consonant molt sovint: es mira si la forma
                    #: hi es a una errada de distancia, en alguna finestra de la cadena. Nomes
                    #: amb quatre consonants o mes, que amb tres una errada ho casa tot.
                    if any(lev(ef, ec[i:i + len(ef)]) <= 1
                           for i in range(max(0, len(ec) - len(ef) + 1))):
                        dins.append((w, f, ef, "amb una errada"))
        if not dins:
            continue
        tocades += 1
        for w, f, ef, com in dins:
            trobades += 1
            per_mena[com][0] += 1
            if ull:
                amb_ull += 1
                per_mena[com][1] += 1
                if ef in ull:
                    confirmades += 1
                    per_mena[com][2] += 1
        for w, f, ef, com in dins:
            if ull and ef in ull:
                confirmat.append({"cadena": cad, "forma": f, "vol_dir": w,
                                  "esquelet": ef, "com": com,
                                  "capitol": (x.get("capitol") or "")[:16],
                                  "catala": (x.get("catala") or "")[:80]})
        if len(exemples) < 6:
            exemples.append((cad, x.get("catala", "")[:52], dins[:3],
                             (x.get("tifinag") or "")[:28]))

print(f"{cadenes} cadenes de {MIN_CADENA}+ lletres amb significat")
print(f"   el significat hi fa buscar alguna cosa i la troba: {tocades} "
      f"({100*tocades/max(1,cadenes):.1f} %)")
print(f"   formes trobades dins de cadenes: {trobades}")
if amb_ull:
    print(f"   de les {amb_ull} que l'ull podia comprovar, **{confirmades} hi surten també "
          f"({100*confirmades/amb_ull:.0f} %)**")
for com, (t, u, c) in per_mena.items():
    if t:
        print(f"      {com:<16}{t:5d} trobades · {c}/{u} confirmades per l'ull "
              f"({100*c/max(1,u):.0f} %)")
#: el producte: les formes que el significat ha fet buscar i que l'ull confirma
import collections  # noqa: E402,PLC0415
quants = collections.Counter((c["forma"], c["vol_dir"]) for c in confirmat)
json.dump(confirmat, io.open(r"E:/tamazight/_magatzem/formes_pel_significat.json", "w",
                             encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"\ndesades {len(confirmat)} troballes confirmades per l'ull "
      f"({len(quants)} parelles forma-significat diferents) a formes_pel_significat.json")
print("les deu que surten més:")
for (f, w), n in quants.most_common(10):
    print(f"   {f:<16}= {w:<16}{n} vegades")
print("\nexemples:")
for cad, cat, dins, tif in exemples:
    print(f"   cadena «{cad}»")
    print(f"      vol dir: {cat}")
    print("      hi trobo: " + ", ".join(f"{f} (= {w}, {c})" for w, f, _, c in dins))
    if tif:
        print(f"      l'ull hi diu: {tif}")
