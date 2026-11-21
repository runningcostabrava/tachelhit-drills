"""Pot el model traduir amazic -> ARAB? Es pot provar sense entrenar res.

En Pablo: «la traduccio al catala es important, pero molt mes important la traduccio a l'arab,
perque si el model es capac de traduir perfectament del tifinag a l'arab, despres la traduccio
de l'arab al catala es trivial».

Te rao, i el que no s'havia vist es que **ja tenim el banc de proves fet**: cada replica porta
el tifinag i l'arab **cremats al mateix fotograma**. Son 14.201 parelles alineades sense haver
alineat res, i l'arab fa de referencia.

Aqui es mesura el punt de partida: que fa el model **que ja tenim** (afinat per treure catala)
quan se li demana arab. No es un model entrenat per a aixo; el numero diu d'on es surt.

Es mesura chrF contra l'arab de la pantalla, i es compara amb el mateix model cap al catala
sobre les MATEIXES linies, perque els dos numeros siguin llegibles l'un al costat de l'altre.

    cap_a_l_arab.py [quantes]
"""
import io
import json
import os
import random
import sys
import time
from pathlib import Path

ARREL = Path(r"E:/tamazight/TD_TV")
MODEL = ARREL / "models" / "nllb-ca-ct2"
QUANTES = int(sys.argv[1]) if len(sys.argv) > 1 else 200
sys.path.insert(0, r"C:/Users/josep/app2/tachelhit-drills.worktrees/tradueix/tools/snrt/fabrica")
from comu import chrf                                   # noqa: E402

import ctranslate2                                      # noqa: E402
import transformers                                     # noqa: E402

#: nomes les que passen les portes de la fabrica: si el tifinag esta mal llegit, no es una
#: prova del traductor sino del lector
bones = []
for d in sorted(os.listdir(ARREL)):
    p = ARREL / d / "subtitols.jsonl"
    if not p.exists() or p.stat().st_size == 0:
        continue
    for l in io.open(p, encoding="utf-8"):
        if not l.strip():
            continue
        x = json.loads(l)
        tif, ar = (x.get("tifinag") or "").strip(), (x.get("arab") or "").strip()
        if (tif and ar and not x.get("credits")
                and (x.get("tifinag_conf") or 0) >= 0.85
                and (x.get("tifinag_dubtosos") or 0) <= 2):
            bones.append({"tifinag": tif, "arab": ar,
                          "catala": (x.get("catala") or "").strip()})
print(f"{len(bones)} parelles tifinag↔àrab que passen les portes")
random.Random(20261121).shuffle(bones)
mostra = bones[:QUANTES]
amb_catala = [x for x in mostra if x["catala"]]
print(f"mostra: {len(mostra)} ({len(amb_catala)} amb català per comparar)\n")

tok = transformers.AutoTokenizer.from_pretrained(str(MODEL), src_lang="zgh_Tfng")
tr = ctranslate2.Translator(str(MODEL), device="cpu", compute_type="int8")


def cap_a(llengua, textos):
    pref = tok.convert_ids_to_tokens(tok.convert_tokens_to_ids([llengua]))
    fora, t0, LOT = [], time.time(), 16
    for i in range(0, len(textos), LOT):
        lot = textos[i:i + LOT]
        fitxes = [tok.convert_ids_to_tokens(tok.encode(t)) for t in lot]
        res = tr.translate_batch(fitxes, target_prefix=[pref] * len(lot), beam_size=4,
                                 max_decoding_length=150)
        for r in res:
            h = r.hypotheses[0]
            if h and h[0] == llengua:
                h = h[1:]
            fora.append(tok.decode(tok.convert_tokens_to_ids(h)).strip())
    print(f"   {llengua}: {len(fora)} en {time.time()-t0:.0f}s", flush=True)
    return fora


tifs = [x["tifinag"] for x in mostra]
ar_msa = cap_a("arb_Arab", tifs)
ar_dar = cap_a("ary_Arab", tifs)
cat = cap_a("cat_Latn", tifs)

print(f"\n{'cap a':<28}{'chrF contra la pantalla':>26}{'>= 0,5':>10}")
for nom, sortida, ref in (("àrab estàndard (arb)", ar_msa, [x["arab"] for x in mostra]),
                          ("àrab marroquí (ary)", ar_dar, [x["arab"] for x in mostra])):
    cs = [chrf(r, s) for r, s in zip(ref, sortida)]
    print(f"{nom:<28}{sum(cs)/len(cs):>26.3f}"
          f"{sum(1 for v in cs if v >= .5):>7} ({100*sum(1 for v in cs if v>=.5)/len(cs):.0f} %)")
if amb_catala:
    idx = [i for i, x in enumerate(mostra) if x["catala"]]
    cs = [chrf(mostra[i]["catala"], cat[i]) for i in idx]
    print(f"{'català (per comparar)':<28}{sum(cs)/len(cs):>26.3f}"
          f"{sum(1 for v in cs if v >= .5):>7} ({100*sum(1 for v in cs if v>=.5)/len(cs):.0f} %)")

json.dump([{"tifinag": x["tifinag"], "arab_pantalla": x["arab"], "arb": a, "ary": b, "cat": c}
           for x, a, b, c in zip(mostra, ar_msa, ar_dar, cat)],
          io.open(r"E:/tamazight/_magatzem/cap_a_l_arab.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

parells = sorted(zip([chrf(x["arab"], s) for x, s in zip(mostra, ar_msa)], mostra, ar_msa),
                 key=lambda t: -t[0])
print("\nles tres on més encerta l'àrab:")
for c, x, s in parells[:3]:
    print(f"   {c:.2f}  pantalla: {x['arab'][:50]}")
    print(f"          model: {s[:50]}")
print("\nles tres on menys:")
for c, x, s in parells[-3:]:
    print(f"   {c:.2f}  pantalla: {x['arab'][:50]}")
    print(f"          model: {s[:50]}")
