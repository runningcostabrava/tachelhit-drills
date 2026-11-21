"""El punt de partida: que fa el model d'ara sobre el test de tifinag -> arab.

Sense aixo no es pot dir si afinar ha servit de res. Es mesura sobre **el test sencer** (1.682
parelles de quatre capitols retinguts), no sobre una mostra, perque es el numero que s'haura de
batre i ha de ser estable.

El model es el que tenim: NLLB afinat per treure **catala**. Se li demana arab, que es una
direccio que no ha entrenat mai.

    base_zgh_ar.py [quantes]
"""
import io
import json
import sys
import time
from pathlib import Path

MODEL = Path(r"E:/tamazight/TD_TV/models/nllb-ca-ct2")
TEST = Path(r"E:/tamazight/_magatzem/zgh_ar/test.jsonl")
sys.path.insert(0, r"C:/Users/josep/app2/tachelhit-drills.worktrees/tradueix/tools/snrt/fabrica")
from comu import chrf                                   # noqa: E402

import ctranslate2                                      # noqa: E402
import transformers                                     # noqa: E402

files = [json.loads(l) for l in io.open(TEST, encoding="utf-8") if l.strip()]
if len(sys.argv) > 1:
    files = files[:int(sys.argv[1])]
print(f"{len(files)} parelles de test")

tok = transformers.AutoTokenizer.from_pretrained(str(MODEL), src_lang="zgh_Tfng")
tr = ctranslate2.Translator(str(MODEL), device="cpu", compute_type="int8")
pref = tok.convert_ids_to_tokens(tok.convert_tokens_to_ids(["arb_Arab"]))

sortida, t0, LOT = [], time.time(), 24
for i in range(0, len(files), LOT):
    lot = files[i:i + LOT]
    fitxes = [tok.convert_ids_to_tokens(tok.encode(x["zgh"])) for x in lot]
    res = tr.translate_batch(fitxes, target_prefix=[pref] * len(lot), beam_size=4,
                             max_decoding_length=150)
    for r in res:
        h = r.hypotheses[0]
        if h and h[0] == "arb_Arab":
            h = h[1:]
        sortida.append(tok.decode(tok.convert_tokens_to_ids(h)).strip())
    if (i // LOT) % 10 == 0:
        print(f"   {min(i+LOT, len(files))}/{len(files)} · {time.time()-t0:.0f}s", flush=True)

cs = [chrf(x["ar"], s) for x, s in zip(files, sortida)]
per_cap = {}
for x, c in zip(files, cs):
    per_cap.setdefault(x["capitol"], []).append(c)

print(f"\nPUNT DE PARTIDA (sense cap entrenament cap a l'àrab)")
print(f"   chrF mitjà: {sum(cs)/len(cs):.4f}")
print(f"   per sobre de 0,5: {sum(1 for c in cs if c >= .5)} "
      f"({100*sum(1 for c in cs if c>=.5)/len(cs):.0f} %)")
print("   per capítol:")
for cap, v in sorted(per_cap.items()):
    print(f"      {cap}: {sum(v)/len(v):.4f}  ({len(v)} línies)")

json.dump([{"zgh": x["zgh"], "ar": x["ar"], "model": s, "chrf": round(c, 3)}
           for x, s, c in zip(files, sortida, cs)],
          io.open(r"E:/tamazight/_magatzem/zgh_ar/base.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("\nescrit zgh_ar/base.json")
