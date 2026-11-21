"""Quin adaptador de l'MMS enten cada convidat del programa.

El quadern ha passat el MATEIX so per sis orelles. Aqui es mesura, per episodi i per adaptador,
quantes replicas casen amb el que hi ha escrit a la pantalla. Les regles son les de sempre:
esquelet de consonants i distancia d'edicio <= 0,35, sense cap veritat humana.

Dos detalls que importen:

  - L'`ary` (arab marroqui) escriu en alfabet arab, aixi que NO es pot comparar amb el tifinag:
    es compara amb el subtitol ARAB, i amb la seva propia regla (esquelet de consonants arabs).
    Es el control de la hipotesi «el convidat parla arab».
  - Els dos episodis de control (que ja anaven be amb `shi`) han de seguir guanyant amb `shi`.
    Si un altre adaptador els guanyes, voldria dir que la mesura no mesura el que crec.
"""
import io, json, os, sys, glob, unicodedata
from pathlib import Path
sys.path.insert(0, r"E:/tamazight/_magatzem")
from tria_el_millor_text import esquelet, lev  # noqa: E402
from parla_arab_o_amazic import esquelet_arab  # noqa: E402

SORTIDA = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(r"E:/tamazight/_magatzem/prova_adaptadors/sortida")
CONTROLS = {"bueyrhjvjyaleocf", "rqmiijbrstbomglg"}


def taxa(a, b):
    return lev(a, b) / max(len(a), len(b)) if a and b else 1.0


#: l'ull: el text triat, i l'arab del visor
ull, arab, titols = {}, {}, {}
for l in io.open(r"E:/tamazight/_magatzem/text_triat.jsonl", encoding="utf-8"):
    if l.strip():
        x = json.loads(l)
        ull[x["id"]] = x.get("tifinag") or ""
        arab[x["id"]] = x.get("arab") or ""
for p in glob.glob(r"E:/tamazight/_visor/*/estat.json"):
    s = os.path.basename(os.path.dirname(p))
    titols[s[:16]] = json.load(io.open(p, encoding="utf-8"))["titol"].replace("TADFI N TSKLA - ", "")

fitxers = sorted(SORTIDA.glob("sentit_*.jsonl"))
if not fitxers:
    raise SystemExit(f"encara no hi ha sortida a {SORTIDA}")
llengues = [p.stem.split("_", 1)[1] for p in fitxers]

#: taula[episodi][llengua] = (encerts, total)
taula = {}
for p, lang in zip(fitxers, llengues):
    for l in io.open(p, encoding="utf-8"):
        if not l.strip():
            continue
        x = json.loads(l)
        ident, dit = x["id"], (x.get("sentit") or "").strip()
        ep = ident.split(":")[0][:16]
        if lang in ("ary", "ara"):
            #: l'arab es compara amb l'arab, i amb la seva regla
            e_dit, e_ref = esquelet_arab(dit), esquelet_arab(arab.get(ident, ""))
        else:
            e_dit, e_ref = esquelet(dit), esquelet(ull.get(ident, ""))
        if not e_dit or not e_ref:
            continue
        c = taula.setdefault(ep, {}).setdefault(lang, [0, 0])
        c[1] += 1
        c[0] += taxa(e_dit, e_ref) <= .35

amplada = max(9, max(len(l) for l in llengues) + 2)
print(f"{'convidat':<26}" + "".join(f"{l:>{amplada}}" for l in llengues) + "   guanya")
for ep in sorted(taula, key=lambda e: -(taula[e].get("shi", [0, 1])[0] / max(1, taula[e].get("shi", [0, 1])[1]))):
    fila = taula[ep]
    def pc(l):
        a, n = fila.get(l, [0, 0])
        return 100 * a / n if n else float("nan")
    guanya = max((l for l in llengues if fila.get(l, [0, 0])[1]), key=pc, default="-")
    marca = " (control)" if ep in CONTROLS else ""
    millor = f"{guanya} {pc(guanya):.0f}%" if pc(guanya) > pc("shi") + 2 else "shi"
    print(f"{titols.get(ep, ep)[:24]:<26}" + "".join(f"{pc(l):>{amplada-1}.1f}%" for l in llengues)
          + f"   {millor}{marca}")

print("\nen conjunt:")
for l in llengues:
    a = sum(f.get(l, [0, 0])[0] for f in taula.values())
    n = sum(f.get(l, [0, 0])[1] for f in taula.values())
    print(f"   {l:<5}{100*a/max(1,n):6.1f}%  ({a} de {n})")
