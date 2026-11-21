"""El text de la fabrica esta DESPLAÇAT respecte de les linies?

Mirant les relectures ha sortit que al capitol asywmm el text vell de la linia k es el text
correcte d'una altra linia, unes quantes files mes amunt. Si aixo es cert, el 0,0% d'acord
d'aquells capitols no ve nomes de llegir malament: ve de desar la lectura a la linia
equivocada, que es una averia de comptabilitat i no d'OCR.

No ho havia provat: la prova de desplaçament de fa una estona comparava la RELECTURA amb
l'orella, i aqui es compara el text VELL amb la relectura, que es la mateixa imatge llegida dues
vegades. Si el vell esta al seu lloc, el millor acord sera a d=0.
"""
import io, json, os, glob, sys
sys.path.insert(0, r"E:/tamazight/_magatzem")
from tria_el_millor_text import esquelet, lev  # noqa: E402


def taxa(a, b):
    return lev(a, b) / max(len(a), len(b)) if a and b else 1.0


titols = {}
for p in glob.glob(r"E:/tamazight/_visor/*/estat.json"):
    s = os.path.basename(os.path.dirname(p))
    titols[s] = json.load(io.open(p, encoding="utf-8"))["titol"].replace("TADFI N TSKLA - ", "")

print(f"{'capitol':<24}" + "".join(f"{d:>7}" for d in range(-6, 7)) + "   millor")
for p in sorted(glob.glob(r"E:/tamazight/_magatzem/rellegit_bo/*.json")):
    slug = os.path.splitext(os.path.basename(p))[0]
    nou = json.load(io.open(p, encoding="utf-8"))["llegit"]
    if len(nou) < 100:
        continue
    vell = {}
    for i, l in enumerate(io.open(f"E:/tamazight/_visor/{slug}/subtitols.jsonl", encoding="utf-8")):
        if l.strip():
            x = json.loads(l)
            vell[str(x.get("k", i))] = (x.get("tifinag") or "").strip()
    fila = []
    for d in range(-6, 7):
        a = n = 0
        for k, t in nou.items():
            try:
                k2 = str(int(k) + d)
            except ValueError:
                continue
            en, ev = esquelet(t), esquelet(vell.get(k2, ""))
            if len(en) < 4 or len(ev) < 4:
                continue
            n += 1
            a += taxa(en, ev) <= .35
        fila.append(100 * a / max(1, n))
    millor = max(range(13), key=lambda i: fila[i]) - 6
    print(f"{titols.get(slug, slug)[:22]:<24}" + "".join(f"{v:6.0f}%" for v in fila)
          + f"   d={millor:+d}" + ("  <- DESPLAÇAT" if millor else ""))
