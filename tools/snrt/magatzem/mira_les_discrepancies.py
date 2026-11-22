"""Quan els camins no diuen el mateix, qui s'equivoca.

En Pablo: «quan hi hagi discrepancies en les traduccions, en aquells casos t'ho has de mirar
especialment».

Una discrepancia sola no diu de qui es la culpa. El que ho diu es el **patro**: amb tres camins
cap a la mateixa frase, qui queda sol es el sospitos.

  A  l'arab -> catala      (el que jo tradueixo, o la canonada de pagament)
  B  el tifinag -> catala  (el NLLB sobre el que llegeix l'ull)
  C  el que sent l'orella -> catala

  A=B, C fora   -> l'ORELLA ha sentit una altra cosa. Es el cas util: marca el tall.
  A=C, B fora   -> el LECTOR DE TIFINAG o el NLLB. Si l'orella i l'arab coincideixen, el text
                   amazic escrit es el que no casa.
  B=C, A fora   -> la TRADUCCIO DE L'ARAB. L'ull i l'orella diuen el mateix i la via de l'arab
                   no: o l'arab estava trencat per l'OCR o la traduccio es dolenta.
  cap acord     -> la frase es curta, o es brossa. Es mira a part.

I una cosa que s'ha de dir al costat de qualsevol numero d'aquests: **el NLLB tradueix una
linia aillada i jo tradueixo amb l'episodi al davant**. Una bona part del que sembla error seu
es falta de context, i per aixo es mesura tambe la versio amb context.

    mira_les_discrepancies.py [fitxer.json] [llindar]
"""
import io
import json
import sys
from pathlib import Path

MAG = Path(r"E:/tamazight/_magatzem")
FITXER = Path(sys.argv[1]) if len(sys.argv) > 1 else MAG / "tres_camins.json"
LLINDAR = float(sys.argv[2]) if len(sys.argv) > 2 else 0.35
sys.path.insert(0, r"C:/Users/josep/app2/tachelhit-drills.worktrees/tradueix/tools/snrt/fabrica")
from comu import chrf                                   # noqa: E402

files = json.load(io.open(FITXER, encoding="utf-8"))
print(f"{len(files)} frases · llindar d'acord {LLINDAR}\n")

menes = {"A=B, l'orella fora": [], "A=C, el tifinag fora": [],
         "B=C, la traducció de l'àrab fora": [], "tots tres d'acord": [],
         "cap acord": []}
for x in files:
    a, b, c = x.get("confirmat", ""), x.get("B_context") or x.get("B", ""), x.get("C", "")
    ab, ac, bc = chrf(a, b), chrf(a, c), chrf(b, c)
    alt = [ab >= LLINDAR, ac >= LLINDAR, bc >= LLINDAR]
    if all(alt):
        k = "tots tres d'acord"
    elif ab >= LLINDAR and ac < LLINDAR:
        k = "A=B, l'orella fora"
    elif ac >= LLINDAR and ab < LLINDAR:
        k = "A=C, el tifinag fora"
    elif bc >= LLINDAR and ab < LLINDAR and ac < LLINDAR:
        k = "B=C, la traducció de l'àrab fora"
    else:
        k = "cap acord"
    menes[k].append((x, round(ab, 2), round(ac, 2), round(bc, 2)))

print(f"{'patró':<36}{'frases':>8}{'%':>7}  què vol dir")
diu = {
    "tots tres d'acord": "el significat és segur",
    "A=B, l'orella fora": "l'orella ha sentit una altra cosa -> marca el tall",
    "A=C, el tifinag fora": "el text amazic escrit no casa",
    "B=C, la traducció de l'àrab fora": "l'àrab o la seva traducció",
    "cap acord": "frase curta o brossa; a part",
}
for k, v in menes.items():
    print(f"{k:<36}{len(v):>8}{100*len(v)/max(1,len(files)):>6.0f}%  {diu[k]}")

for k in ("A=B, l'orella fora", "B=C, la traducció de l'àrab fora", "A=C, el tifinag fora"):
    v = menes[k]
    if not v:
        continue
    print(f"\n--- {k} ({len(v)}), les tres primeres:")
    for x, ab, ac, bc in v[:3]:
        print(f"   A: {x.get('confirmat','')[:58]}")
        print(f"   B: {(x.get('B_context') or x.get('B',''))[:58]}")
        print(f"   C: {x.get('C','')[:58]}")
        print(f"      A-B {ab} · A-C {ac} · B-C {bc}")

fora = MAG / "discrepancies.json"
json.dump({k: [x for x, *_ in v] for k, v in menes.items()},
          io.open(fora, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"\nescrit {fora.name}")
