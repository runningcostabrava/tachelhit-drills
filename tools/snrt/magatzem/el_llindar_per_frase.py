"""SUPERAT (20-11). No el facis servir: `el_llindar_honest.py` el substitueix.

Dues coses el fan mentir. (a) Mesura la parella (veritat humana, sortida del
model), pero l'etiqueta que portara el train es el **subtitol**, que en aquestes
quatre proves no existeix: el seu «CER ric de l'etiqueta» es l'error del model, no
la qualitat de l'etiqueta. (b) Estratifica per una funcio de les MATEIXES dues
cadenes que mesura, de manera que la relacio que troba es certa per construccio.

Els seus numeros (0,151 al llindar 0,35 i 0,127 al 0,20) es van fer servir per
justificar el brac de 0,20. La taula bona es a DESXIFRAT.md §28.
"""

"""Per frase: quant val una frase que passa el filtre d'esquelet?

El train de la ronda es tria per REPLICA, no per paraula: entra la frase sencera si el seu
esquelet de consonants casa amb el de l'ull per sota de 0,35. La mesura del llindar per paraula
(`que_compra_el_grau_a.py`) no respon aixo: una frase pot tenir un esquelet global que casa i
tres paraules equivocades a dins.

Aqui es mira el que importa de debo per a entrenar: **de les frases que el filtre deixa passar,
com de bo es el text que portaran com a etiqueta**. Mesurat contra veritat humana a les quatre
proves que en tenen, i amb el CER ric (vocals incloses), que es el que el model aprendra.

PREDICCIO: espero que el CER ric creixi de pressa amb el d'esquelet i que el llindar de 0,35
deixi entrar frases amb un CER ric per sobre de 0,3, que es brossa per a una etiqueta. Si el CER
ric es queda baix a tot arreu, el llindar de 0,35 esta be i no cal tocar la ronda 2.
"""
import io
import json
import sys
from pathlib import Path

sys.path.insert(0, r"E:/tamazight/_magatzem")
from tria_el_millor_text import esquelet, lev  # noqa: E402

SORTIDA = Path(r"E:/tamazight/_magatzem/ronda/sortida/snrt_B_sortides.json")
AMB_VERITAT = ("zouhir-tests", "tfa-226", "cv-zgh-test", "test-fora")
TRAMS = ((0.0, 0.001), (0.001, 0.10), (0.10, 0.20), (0.20, 0.35), (0.35, 0.60), (0.60, 1.01))


def cer(a, b):
    return 1.0 if not a else lev(a, b) / len(a)


files = json.load(io.open(SORTIDA, encoding="utf-8"))
frases = []
for x in files:
    if x.get("prova") not in AMB_VERITAT or (x.get("model") or "").startswith("abans"):
        continue
    v, o = (x.get("or") or "").strip(), (x.get("dit") or "").strip()
    ev, eo = esquelet(v), esquelet(o)
    if not ev or not eo:
        continue
    frases.append((lev(ev, eo) / max(len(ev), len(eo)), cer(v.lower(), o.lower())))

frases.sort()
print(f"{len(frases)} frases amb veritat humana\n")
print(f"{'CER esquelet':>16}{'frases':>8}{'%':>7}{'CER ric mitja':>15}{'CER ric mediana':>17}")
for lo, hi in TRAMS:
    tram = [r for e, r in frases if lo <= e < hi]
    if not tram:
        continue
    tram_ord = sorted(tram)
    print(f"{lo:7.2f}-{hi:<8.2f}{len(tram):8d}{100*len(tram)/len(frases):7.1f}"
          f"{sum(tram)/len(tram):15.3f}{tram_ord[len(tram_ord)//2]:17.3f}")

print(f"\n{'llindar':>9}{'frases':>9}{'%':>7}{'CER ric mitja':>15}  el que entraria al train")
for L in (0.60, 0.35, 0.20, 0.10, 0.001):
    passen = [r for e, r in frases if e <= L]
    if not passen:
        continue
    print(f"{L:9.3f}{len(passen):9d}{100*len(passen)/len(frases):7.1f}"
          f"{sum(passen)/len(passen):15.3f}")
print("\n(CER ric = sobre el text sencer, vocals incloses: es el que el model aprendra)")
