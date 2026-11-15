# -*- coding: utf-8 -*-
"""veritat_zouhir.json (rètols amb pista amaziga HUMANA + en/ar/fr) → parells.jsonl per a
`induccio.py`, que espera {video, de, a, asr, en, ar}. Aquí «asr» NO és cap lectura de màquina:
és la pista humana transliterada al llatí; el nom del camp es manté per no bifurcar l'eina.
Només els rètols parlats (els rètols de pantalla no porten cap frase).

ÚS: zouhir_parells.py <veritat_zouhir.json> <parells.jsonl>
"""
import io
import json
import sys

versos = json.load(io.open(sys.argv[1], encoding="utf-8"))
n = 0
with io.open(sys.argv[2], "w", encoding="utf-8") as g:
    for v in versos:
        if v.get("mena") == "rètol" or not v.get("veritat"):
            continue
        g.write(json.dumps({"video": v["video"], "de": v["de"], "a": v["a"], "asr": v["veritat"],
                            "en": v.get("en") or "", "ar": v.get("ar") or "", "fr": v.get("fr") or "",
                            "tifinag": v.get("tifinag") or ""}, ensure_ascii=False) + "\n")
        n += 1
print(n, "parells humans →", sys.argv[2])
