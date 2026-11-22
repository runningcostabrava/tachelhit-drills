"""La taula norma <-> parla, filtrada per REPETICIO en boques diferents.

El grau B son les paraules on l'orella esta segura (conf >= 0,85) i l'ull diu una altra cosa.
Aqui hi ha barrejades dues coses:

  - correspondencies de debo: el subtitol escriu la norma de l'IRCAM i l'actor diu la seva
    forma (`ⵉⵎⴰⵏⵏⴰⵢ` escrit, *imfarjn* dit);
  - errors de l'orella: sent malament una paraula i prou.

Es separen SENSE cap veritat humana, per repeticio: una correspondencia de llengua torna a
sortir, i en boques diferents. Un error de l'orella en un tall concret, no. Per aixo es compten
les parelles (forma escrita, forma sentida) i es demana que surtin almenys tres vegades i en
dos episodis o mes, que vol dir dos convidats diferents.

Surt `norma_parla.tsv`, ordenada per quantes vegades s'ha vist.
"""
import io, json, os, glob, sys
sys.path.insert(0, r"E:/tamazight/_magatzem")
from tria_el_millor_text import esquelet
from collections import defaultdict

MAG = r"E:/tamazight/_magatzem"
MIN_VEGADES, MIN_BOQUES = 3, 2

titols = {}
for p in glob.glob(r"E:/tamazight/_visor/*/estat.json"):
    s = os.path.basename(os.path.dirname(p))
    titols[s] = json.load(io.open(p, encoding="utf-8"))["titol"].replace("TADFI N TSKLA - ", "")

parelles = defaultdict(lambda: {"n": 0, "caps": set(), "exemples": []})
for l in io.open(f"{MAG}/ocurrencies_triat.jsonl", encoding="utf-8"):
    if not l.strip():
        continue
    x = json.loads(l)
    if x["grau"] != "B" or not x.get("norma") or x.get("dist") is None:
        continue
    #: dist > 0,35 ja ho diu el grau B; per sobre de 0,7 son paraules que no tenen res a veure
    if not (.35 < x["dist"] <= .7):
        continue
    #: i encara cal treure l'escombraria del 29-10: amb un esquelet d'UNA consonant, qualsevol
    #: paraula de tres hi cau a dins del 0,7 ( amb ). Es demanen tres consonants a
    #: cada banda i que no es diferencien en mes de dues: una variant dialectal d'una paraula
    #: te la mateixa mida, no el triple.
    eu, eo = esquelet(x["norma"]), x["esquelet"]
    if len(eu) < 3 or len(eo) < 3 or abs(len(eu) - len(eo)) > 2:
        continue
    k = (x["norma"], x["sentit"])
    d = parelles[k]
    d["n"] += 1
    d["caps"].add(x["capitol"])
    if len(d["exemples"]) < 2 and x.get("catala"):
        d["exemples"].append(x["catala"][:60])

bones = {k: v for k, v in parelles.items()
         if v["n"] >= MIN_VEGADES and len(v["caps"]) >= MIN_BOQUES}
print(f"parelles de grau B amb distancia entre 0,35 i 0,7: {len(parelles)}")
print(f"que es repeteixen {MIN_VEGADES}+ vegades en {MIN_BOQUES}+ boques: {len(bones)}")

with io.open(f"{MAG}/norma_parla.tsv", "w", encoding="utf-8", newline="\n") as f:
    f.write("escrit\tsentit\tvegades\tboques\texemple\n")
    for (norma, dit), v in sorted(bones.items(), key=lambda kv: -kv[1]["n"]):
        f.write(f"{norma}\t{dit}\t{v['n']}\t{len(v['caps'])}\t{v['exemples'][0] if v['exemples'] else ''}\n")

print(f"\n{'escrit':<16}{'sentit':<16}{'vegades':>8}{'boques':>8}")
for (norma, dit), v in sorted(bones.items(), key=lambda kv: -kv[1]["n"])[:25]:
    print(f"{norma[:15]:<16}{dit[:15]:<16}{v['n']:8d}{len(v['caps']):8d}")
print(f"\ndesat a {MAG}/norma_parla.tsv")
