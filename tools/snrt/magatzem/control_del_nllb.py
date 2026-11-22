"""El control que falta: quant acorda el NLLB amb una traduccio que ja sabem bona.

Sobre l'episodi que vaig traduir jo, l'acord entre les dues vies va donar **chrF 0,310** i nomes
un 12 % de linies confirmades. Aixo no diu de qui es la culpa: pot ser que la meva traduccio
sigui dolenta, o que el NLLB no arribi.

Es separa amb un control. S'agafen les linies dels episodis vells on el catala ja esta
**confirmat** (dos traductors de pagament hi van coincidir), se'ls passa el tifinag pel NLLB, i
es mira quant hi acorda. Aquell numero es **el sostre del NLLB**: el que dona quan la traduccio
de l'altra banda es bona per definicio.

  * si el control surt ~0,31 -> el 0,310 de la meva traduccio es el nivell normal del NLLB, i
    la meva queda neta;
  * si el control surt molt mes alt -> llavors el problema es meu i s'ha de mirar.

Es tria una mostra de la mateixa mida (411) i amb la mateixa distribucio de llargada que
l'episodi meu, perque la comparacio valgui: les frases curtes acorden diferent de les llargues.

    control_del_nllb.py
"""
import io
import json
import random
import sys
import time
from collections import Counter
from pathlib import Path

ARREL = Path(r"E:/tamazight/TD_TV")
MAG = Path(r"E:/tamazight/_magatzem")
MODEL = ARREL / "models" / "nllb-ca-ct2"
MEU = "-SyzF2LtAEs"
sys.path.insert(0, r"C:/Users/josep/app2/tachelhit-drills.worktrees/tradueix/tools/snrt/fabrica")
from comu import chrf                                   # noqa: E402

import ctranslate2                                      # noqa: E402
import transformers                                     # noqa: E402

#: --- el meu episodi, per saber quina forma te la mostra ---
meu = [json.loads(l) for l in io.open(ARREL / MEU / "subtitols.jsonl", encoding="utf-8")
       if l.strip()]
meu = [x for x in meu if x.get("chrf_vies") is not None]
perfil = Counter(min(len((x.get("catala") or "").split()), 20) for x in meu)
print(f"el meu episodi: {len(meu)} línies · chrF mitjà "
      f"{sum(x['chrf_vies'] for x in meu)/len(meu):.3f}")

#: --- les linies ja confirmades dels episodis vells ---
#:
#: `catala_estat` no es al cataleg (`text_triat.jsonl`): es al `subtitols.jsonl` de cada
#: episodi, que es on la fabrica el va escriure. I l'episodi que he traduit jo queda FORA del
#: control, que si no em compararia amb mi mateix.
import os                                              # noqa: E402,PLC0415

bones = []
for d in sorted(os.listdir(ARREL)):
    if d == MEU or not (ARREL / d / "subtitols.jsonl").exists():
        continue
    for l in io.open(ARREL / d / "subtitols.jsonl", encoding="utf-8"):
        if not l.strip():
            continue
        x = json.loads(l)
        if (x.get("catala_estat") in ("confirmat", "creuat")
                and (x.get("tifinag") or "").strip() and (x.get("catala") or "").strip()):
            bones.append(x)
print(f"{len(bones)} línies amb català ja confirmat, de {MEU} enfora")
if len(bones) < 100:
    raise SystemExit("massa poques per a un control")

#: mostra amb la mateixa distribucio de llargada
rnd = random.Random(20261121)
per_llarg = {}
for x in bones:
    per_llarg.setdefault(min(len(x["catala"].split()), 20), []).append(x)
mostra = []
for n, quants in perfil.items():
    hi_ha = per_llarg.get(n, [])
    if not hi_ha:
        continue
    rnd.shuffle(hi_ha)
    mostra += hi_ha[:quants]
print(f"mostra del control: {len(mostra)} línies, amb la mateixa forma de llargades\n")

tok = transformers.AutoTokenizer.from_pretrained(str(MODEL), src_lang="zgh_Tfng")
tr = ctranslate2.Translator(str(MODEL), device="cpu", compute_type="int8")
desti = tok.convert_ids_to_tokens(tok.convert_tokens_to_ids(["cat_Latn"]))

t0, sortida, LOT = time.time(), [], 16
for i in range(0, len(mostra), LOT):
    lot = mostra[i:i + LOT]
    fitxes = [tok.convert_ids_to_tokens(tok.encode(x["tifinag"])) for x in lot]
    res = tr.translate_batch(fitxes, target_prefix=[desti] * len(lot), beam_size=4,
                             max_decoding_length=120)
    for r in res:
        t = r.hypotheses[0]
        if t and t[0] == "cat_Latn":
            t = t[1:]
        sortida.append(tok.decode(tok.convert_tokens_to_ids(t)).strip())
    if (i // LOT) % 6 == 0:
        print(f"   {min(i+LOT, len(mostra))}/{len(mostra)} · {time.time()-t0:.0f}s", flush=True)

acords = [(chrf(x["catala"], n), x, n) for x, n in zip(mostra, sortida)]
mitjana = sum(c for c, _, _ in acords) / max(1, len(acords))
conf = sum(1 for c, _, _ in acords if c >= .5)
meu_mitjana = sum(x["chrf_vies"] for x in meu) / len(meu)
meu_conf = sum(1 for x in meu if x["chrf_vies"] >= .5)

print(f"\n{'':<34}{'chrF mitjà':>12}{'confirmades':>14}")
print(f"{'CONTROL (traducció ja confirmada)':<34}{mitjana:>12.3f}"
      f"{conf:>8} ({100*conf/len(acords):.0f} %)")
print(f"{'la meva traducció':<34}{meu_mitjana:>12.3f}"
      f"{meu_conf:>8} ({100*meu_conf/len(meu):.0f} %)")

dif = meu_mitjana - mitjana
print(f"\ndiferència: {dif:+.3f}")
if abs(dif) < 0.05:
    print("-> el 0,310 és el NIVELL NORMAL del NLLB. La meva traducció no hi queda per sota.")
elif dif < 0:
    print("-> la meva traducció acorda MENYS que una de confirmada: el problema és meu.")
else:
    print("-> la meva traducció acorda MÉS que una de confirmada.")

json.dump([{"catala": x["catala"], "nllb": n, "chrf": round(c, 3)} for c, x, n in acords],
          io.open(MAG / "control_nllb.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("\nTres exemples del control:")
for c, x, n in acords[:3]:
    print(f"   {c:.2f}  confirmat: {x['catala'][:50]}")
    print(f"              nllb: {n[:50]}")
