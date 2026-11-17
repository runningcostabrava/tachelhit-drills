# -*- coding: utf-8 -*-
"""Els ítems del coneixement del professor que l'auditor ha dit TRIA, posats en la forma de sortida
de `mina_transcrits.py` (una línia per vídeo amb els seus ítems), perquè `mina_vs_lexic.py` els pugui
comparar amb el nostre lèxic tal com fa amb el minat sencer.

ÚS: confirmats_a_mina.py <coneixement_darija.jsonl> <coneixement_auditat.jsonl> <sortida.jsonl> [veredicte]
     veredicte: tria (per defecte) | fora | no-ho-se
"""
import collections
import io
import json
import sys

if __name__ == "__main__":
    con, aud, fora = sys.argv[1], sys.argv[2], sys.argv[3]
    volgut = sys.argv[4] if len(sys.argv) > 4 else "tria"
    veredictes = {}
    for l in io.open(aud, encoding="utf-8"):
        if l.strip():
            v = json.loads(l)
            veredictes[v["clau"]] = v["veredicte"]
    per_video = collections.OrderedDict()
    n = 0
    for l in io.open(con, encoding="utf-8"):
        x = json.loads(l)
        if veredictes.get(f"{x['video']}:{x['idx']}") != volgut:
            continue
        d = per_video.setdefault(x["video"], {"video": x["video"], "titol": x.get("titol"), "model": x.get("model"), "items": []})
        d["items"].append({k: x.get(k) for k in ("amazic_ar", "amazic_llati", "significat_ar", "significat_ca", "mena", "on")})
        n += 1
    with io.open(fora, "w", encoding="utf-8") as g:
        for d in per_video.values():
            g.write(json.dumps(d, ensure_ascii=False) + "\n")
    print(f"{n} ítems «{volgut}» de {len(per_video)} vídeos → {fora}")
