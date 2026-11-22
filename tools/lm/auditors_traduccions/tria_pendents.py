# -*- coding: utf-8 -*-
"""Del catàleg de producció (cataleg_prod.json, de baixa_cataleg.py) en treu les frases que encara
porten «traduit-per-maquina» sense «traduccio-descartada», amb text amazic, d'MTNRA i Common Voice:
pendents.json, l'entrada d'audita.py.
ÚS: tria_pendents.py [<carpeta de dades>]"""
import collections, io, json, os, sys

AQUI = sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\josep\Veus-tachelhit\_escoltats\traduccions\auditors"
d = json.load(io.open(os.path.join(AQUI, "cataleg_prod.json"), encoding="utf-8"))
p = [x for x in d if "traduit-per-maquina" in (x.get("tag") or "") and "traduccio-descartada" not in (x.get("tag") or "")
     and (x.get("text_tachelhit") or "").strip() and ("mtnra" in x["tag"] or "common-voice" in x["tag"])]
camps = ["id", "tag", "text_tachelhit", "text_tachelhit_latin", "text_catalan", "text_arabic", "text_catalan_suggested", "source_title"]
json.dump([{k: x.get(k) for k in camps} for x in p], io.open(os.path.join(AQUI, "pendents.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=0)
print(len(p), collections.Counter(x["tag"] for x in p))
