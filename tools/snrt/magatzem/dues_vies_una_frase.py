"""Les dues vies cap al significat, sobre el mateix episodi.

En Pablo em va dir «tradueix tu», i vaig traduir les 411 linies d'un episodi **des de l'arab**,
sense mirar el tifinag. Hi ha una segona via que no ha vist l'arab: el nostre NLLB afinat, que
tradueix **del tifinag** al catala. Son dos camins independents cap a la mateixa frase, que es
justament el disseny de l'ADR 0014.

El que es mesura es l'**acord** (chrF): quan les dues vies diuen el mateix, el significat esta
confirmat per dos testimonis i no per la meva paraula. Quan no, val la pena mirar-ho.

El llindar de 0,5 es el que la fabrica ja fa servir per a `confirmat`.

    dues_vies_una_frase.py [slug]
"""
import io
import json
import sys
import time
from pathlib import Path

SLUG = sys.argv[1] if len(sys.argv) > 1 else "-SyzF2LtAEs"
ARREL = Path(r"E:/tamazight/TD_TV")
MODEL = ARREL / "models" / "nllb-ca-ct2"
FAB = r"C:/Users/josep/app2/tachelhit-drills.worktrees/tradueix/tools/snrt/fabrica"
sys.path.insert(0, FAB)
from comu import chrf                                   # noqa: E402

import ctranslate2                                      # noqa: E402
import transformers                                     # noqa: E402

files = [json.loads(l) for l in io.open(ARREL / SLUG / "subtitols.jsonl", encoding="utf-8")
         if l.strip()]
feina = [x for x in files
         if (x.get("tifinag") or "").strip() and (x.get("catala") or "").strip()]
print(f"{SLUG}: {len(files)} línies · {len(feina)} amb tifinag i amb el meu català\n")

tok = transformers.AutoTokenizer.from_pretrained(str(MODEL), src_lang="zgh_Tfng")
tr = ctranslate2.Translator(str(MODEL), device="cpu", compute_type="int8")
desti = tok.convert_ids_to_tokens(tok.convert_tokens_to_ids(["cat_Latn"]))

t0 = time.time()
sortida = []
LOT = 16
for i in range(0, len(feina), LOT):
    lot = feina[i:i + LOT]
    fitxes = [tok.convert_ids_to_tokens(tok.encode(x["tifinag"])) for x in lot]
    res = tr.translate_batch(fitxes, target_prefix=[desti] * len(lot), beam_size=4,
                             max_decoding_length=120)
    for r in res:
        t = r.hypotheses[0]
        if t and t[0] == "cat_Latn":
            t = t[1:]
        sortida.append(tok.decode(tok.convert_tokens_to_ids(t)).strip())
    if (i // LOT) % 5 == 0:
        print(f"   {min(i+LOT, len(feina))}/{len(feina)} · {time.time()-t0:.0f}s", flush=True)

#: l'acord entre les dues vies
acords = []
for x, nllb in zip(feina, sortida):
    acords.append((chrf(x["catala"], nllb), x, nllb))
acords.sort(key=lambda a: -a[0])

confirmats = sum(1 for c, _, _ in acords if c >= .5)
mitjana = sum(c for c, _, _ in acords) / max(1, len(acords))
print(f"\nchrF mitjà entre les dues vies: {mitjana:.3f}")
print(f"confirmats (chrF >= 0,5): {confirmats} de {len(acords)} "
      f"({100*confirmats/max(1,len(acords)):.0f} %)")

print("\nEls cinc on més coincideixen (el significat queda confirmat per dues vies):")
for c, x, n in acords[:5]:
    print(f"   {c:.2f}  jo: {x['catala'][:52]}")
    print(f"         nllb: {n[:52]}")
print("\nEls cinc on més discrepen (val la pena mirar-los):")
for c, x, n in acords[-5:]:
    print(f"   {c:.2f}  jo: {x['catala'][:52]}")
    print(f"         nllb: {n[:52]}")

#: desar l'acord a cada linia, que es el que fa servir la fabrica
per_k = {x["k"]: (c, n) for c, x, n in acords}
for x in files:
    if x.get("k") in per_k:
        c, n = per_k[x["k"]]
        x["catala_nllb"] = n
        x["chrf_vies"] = round(c, 3)
        if c >= .5:
            x["catala_estat"] = "creuat"
io.open(ARREL / SLUG / "subtitols.jsonl", "w", encoding="utf-8", newline="\n").write(
    "\n".join(json.dumps(x, ensure_ascii=False) for x in files) + "\n")
print(f"\ndesat l'acord a {SLUG}/subtitols.jsonl")
