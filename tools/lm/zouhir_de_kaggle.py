# -*- coding: utf-8 -*-
"""El resultat del nucli de Kaggle (`zouhir_resultats.json`: un rètol per entrada, amb els textos de
cada descodificació) → els mateixos `mesura/<video>.json` que escriu `zouhir_mesura.py`, perquè
`zouhir_resum.py` els ajunti i puntuï sense saber d'on vénen. Les claus de descodificació del nucli
(greedy, beam, lm_a0.1, lm_a0.15) es mantenen; `transcribe_mms` i `transcribe_mms_lm` del Space
hi queden al costat si el vídeo ja tenia mesura del Space (no es perden).

ÚS: zouhir_de_kaggle.py <zouhir_resultats.json> <carpeta de sortida amb mesura/>
"""
import collections
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import h3_puntua  # noqa: E402

d = json.load(io.open(sys.argv[1], encoding="utf-8"))
cues = d["cues"]
claus = [k for k in ("greedy", "beam", "lm_a0.1", "lm_a0.15") if any(k in c for c in cues)]
per_video = collections.defaultdict(list)
for c in cues:
    per_video[c["video"]].append(c)
fora = os.path.join(sys.argv[2], "mesura")
os.makedirs(fora, exist_ok=True)
for vid, vs in per_video.items():
    cami = os.path.join(fora, vid + ".json")
    vell = {}
    if os.path.exists(cami):
        for v in json.load(io.open(cami, encoding="utf-8"))["versos"]:
            vell[v["n"]] = v
    versos = []
    for c in vs:
        v = dict(vell.get(c["n"], {}))
        v.update({k: c[k] for k in ("video", "n", "de", "a", "tifinag", "veritat", "en", "ar", "fr", "pista", "canal") if k in c})
        v.setdefault("mena", "parlat")
        for k in claus:
            if k in c:
                v[k] = c[k]
        versos.append(v)
    punt = {k: h3_puntua.puntua(versos, k, "parlat", plegat=False) for k in claus + ["transcribe_mms", "transcribe_mms_lm"]
            if any(v.get(k) is not None for v in versos)}
    json.dump({"video": vid, "pista": vs[0].get("pista"), "canal": vs[0].get("canal"), "versos": versos, "puntuacio": punt},
              io.open(cami, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(len(per_video), "vídeos escrits a", fora, "· claus:", claus)
