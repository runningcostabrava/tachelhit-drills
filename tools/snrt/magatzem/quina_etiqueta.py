"""Amb quina etiqueta de llengua s'ha d'entrar el tifinag: zgh_Tfng o tzm_Tfng?

El NLLB te etiquetes separades per a l'amazic estandard (`zgh_Tfng`) i el tamazight de l'Atles
central (`tzm_Tfng`). Nosaltres cridem el model amb `zgh_Tfng`; el guio d'afinament que ja
teniem feia servir `tzm_Tfng`. Si no son equivalents, tot el que mesurem amb l'una i entrenem
amb l'altra queda tort, i es una linia de codi.

Es prova sobre una mostra del dev (no del test: el test no es toca fins al final).

    quina_etiqueta.py [quantes]
"""
import io
import json
import sys
import time
from pathlib import Path

MODEL = Path(r"E:/tamazight/TD_TV/models/nllb-ca-ct2")
DEV = Path(r"E:/tamazight/_magatzem/zgh_ar/dev.jsonl")
N = int(sys.argv[1]) if len(sys.argv) > 1 else 150
sys.path.insert(0, r"C:/Users/josep/app2/tachelhit-drills.worktrees/tradueix/tools/snrt/fabrica")
from comu import chrf                                   # noqa: E402

import ctranslate2                                      # noqa: E402
import transformers                                     # noqa: E402

files = [json.loads(l) for l in io.open(DEV, encoding="utf-8") if l.strip()][:N]
print(f"{len(files)} parelles del dev\n")

tr = ctranslate2.Translator(str(MODEL), device="cpu", compute_type="int8")
print(f"{'origen':<12}{'destí':<12}{'chrF':>9}{'>= 0,5':>9}")
for origen in ("zgh_Tfng", "tzm_Tfng"):
    tok = transformers.AutoTokenizer.from_pretrained(str(MODEL), src_lang=origen)
    for desti in ("arb_Arab",):
        pref = tok.convert_ids_to_tokens(tok.convert_tokens_to_ids([desti]))
        sortida, t0 = [], time.time()
        for i in range(0, len(files), 24):
            lot = files[i:i + 24]
            fitxes = [tok.convert_ids_to_tokens(tok.encode(x["zgh"])) for x in lot]
            res = tr.translate_batch(fitxes, target_prefix=[pref] * len(lot), beam_size=4,
                                     max_decoding_length=150)
            for r in res:
                h = r.hypotheses[0]
                if h and h[0] == desti:
                    h = h[1:]
                sortida.append(tok.decode(tok.convert_tokens_to_ids(h)).strip())
        cs = [chrf(x["ar"], s) for x, s in zip(files, sortida)]
        print(f"{origen:<12}{desti:<12}{sum(cs)/len(cs):>9.4f}"
              f"{sum(1 for c in cs if c >= .5):>6} ({100*sum(1 for c in cs if c>=.5)/len(cs):.0f} %)"
              f"   {time.time()-t0:.0f}s")
print("\nSi les dues donen el mateix, l'etiqueta és indiferent i es pot triar la que es vulgui.")
