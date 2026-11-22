"""Els TRES camins cap al significat, sobre les mateixes frases confirmades.

L'ADR 0014 en descrivia tres i nomes se n'havien construit dos:

  A  l'arab -> catala          (el que llegeix l'ull, traduit)
  B  el tifinag -> catala      (el que llegeix l'ull, per l'altra banda)
  C  **el que sent l'orella -> catala**   <- aquest no s'havia fet mai

El C es el que de debo importa: diu **quant significat sobreviu a la nostra orella**. El CER
mesura lletres; aixo mesura si, despres de tot, s'enten el que es diu.

Es mesura contra el catala **ja confirmat** (dos traductors de pagament hi van coincidir), que
fa de veritat. Les tres linies surten de la mateixa frase, aixi que els numeros son comparables.

**Un avis sobre el context, que en Pablo va assenyalar.** El NLLB tradueix **una linia aillada**;
quan jo tradueixo, tinc l'episodi sencer al davant i se qui parla i de que. Per aixo aqui es
mesura tambe amb **context**: la linia amb la de davant i la de darrere enganxades, i es mira si
el numero puja. Si puja, bona part del que semblava error del traductor era falta de context.

    tres_camins_al_significat.py [quantes]
"""
import io
import json
import os
import random
import sys
import time
from pathlib import Path

ARREL = Path(r"E:/tamazight/TD_TV")
MAG = Path(r"E:/tamazight/_magatzem")
MODEL = ARREL / "models" / "nllb-ca-ct2"
MEU = "-SyzF2LtAEs"
QUANTES = int(sys.argv[1]) if len(sys.argv) > 1 else 300
sys.path.insert(0, r"C:/Users/josep/app2/tachelhit-drills.worktrees/tradueix/tools/snrt/fabrica")
from comu import chrf                                   # noqa: E402

import ctranslate2                                      # noqa: E402
import transformers                                     # noqa: E402

#: Les tres fonts son a la mateixa fila de `text_triat.jsonl`: el tifinag i l'arab que va
#: llegir l'ull, el catala que en va sortir, i el `sentit`, que es el que diu l'orella. Els
#: `subtitols.jsonl` de TD_TV son episodis DIFERENTS (els collits de nou) i no tenen `sentit`:
#: l'orella encara no hi ha passat.
#:
#: Avis: aqui el catala de referencia es el que hi ha, que ve de la canonada de pagament. No hi
#: ha marca de «confirmat» en aquest fitxer, aixi que la referencia no esta tan garantida com
#: al control; els numeros valen per COMPARAR els tres camins entre ells, que es el que es vol,
#: no com a mesura absoluta de cap d'ells.
files = [json.loads(l) for l in io.open(MAG / "text_triat.jsonl", encoding="utf-8")
         if l.strip()]
per_capitol = {}
for x in files:
    per_capitol.setdefault(x.get("capitol"), []).append(x)

bones = []
for cap, linies in per_capitol.items():
    for i, x in enumerate(linies):
        if all((x.get(k) or "").strip() for k in ("tifinag", "catala", "sentit")):
            bones.append({
                "catala": x["catala"], "tifinag": x["tifinag"], "sentit": x["sentit"],
                "tif_context": " ".join(
                    (linies[j].get("tifinag") or "") for j in (i - 1, i, i + 1)
                    if 0 <= j < len(linies)).strip(),
            })
print(f"{len(bones)} línies amb les tres fonts, de {len(per_capitol)} capítols")
if len(bones) < 50:
    raise SystemExit("massa poques")

random.Random(20261121).shuffle(bones)
mostra = bones[:QUANTES]
print(f"mostra: {len(mostra)}\n")

tok = transformers.AutoTokenizer.from_pretrained(str(MODEL), src_lang="zgh_Tfng")
tr = ctranslate2.Translator(str(MODEL), device="cpu", compute_type="int8")
desti = tok.convert_ids_to_tokens(tok.convert_tokens_to_ids(["cat_Latn"]))


def tradueix(textos, nom):
    fora, t0, LOT = [], time.time(), 16
    for i in range(0, len(textos), LOT):
        lot = textos[i:i + LOT]
        fitxes = [tok.convert_ids_to_tokens(tok.encode(t or " ")) for t in lot]
        res = tr.translate_batch(fitxes, target_prefix=[desti] * len(lot), beam_size=4,
                                 max_decoding_length=150)
        for r in res:
            h = r.hypotheses[0]
            if h and h[0] == "cat_Latn":
                h = h[1:]
            fora.append(tok.decode(tok.convert_tokens_to_ids(h)).strip())
    print(f"   {nom}: {len(fora)} en {time.time()-t0:.0f}s", flush=True)
    return fora


b = tradueix([x["tifinag"] for x in mostra], "B · del tifinag")
c = tradueix([x["sentit"] for x in mostra], "C · del que sent l'orella")
bc = tradueix([x["tif_context"] for x in mostra], "B amb context (3 línies)")

print(f"\n{'camí':<36}{'chrF mitjà':>12}{'>= 0,5':>10}")
res = {}
SOL = "B · del tifinag (una línia)"
CTX = "B · del tifinag (amb context)"
ORELLA = "C · del que sent l'orella"
for nom, sortida in ((SOL, b), (CTX, bc), (ORELLA, c)):
    cs = [chrf(x["catala"], s) for x, s in zip(mostra, sortida)]
    m = sum(cs) / len(cs)
    res[nom] = m
    print(f"{nom:<36}{m:>12.3f}{sum(1 for v in cs if v >= .5):>7} "
          f"({100*sum(1 for v in cs if v>=.5)/len(cs):.0f} %)")


print(f"\nEl context aporta: {res[CTX] - res[SOL]:+.3f}")
print(f"L'orella contra l'ull: {res[ORELLA] - res[SOL]:+.3f}")

json.dump([{"confirmat": x["catala"], "B": bb, "B_context": cc, "C": c3}
           for x, bb, cc, c3 in zip(mostra, b, bc, c)],
          io.open(MAG / "tres_camins.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("\nescrit tres_camins.json")
