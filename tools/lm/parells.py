# -*- coding: utf-8 -*-
"""Parells (text ASR amazic ↔ subtítol humà anglès/àrab) per a cada rètol dels vídeos de
Tamazight For All amb subtítols humans.

Per a cada rètol humà (en o ar) es pren el text de l'ASR que cau dins del seu interval de temps.
Dues entrades possibles:
  · una carpeta de transcripcions del kernel (JSON amb `greedy` = paraules amb start/end, i les
    variants amb lèxic), o
  · `veritat_parlat.json` (els 226 versos, camp `shi`), per provar-ho ara mateix amb els 8 vídeos.

Això és un corpus paral·lel sorollós: el que Pablo demanava quan deia «I think you can train a
translation model… catalog and analyze». Res no entra a la biblioteca: material de tercers.

ÚS: parells.py <subs_humans> <transcripcions|veritat_parlat.json> <parells.jsonl> [clau=greedy]
"""
import glob
import io
import json
import os
import re
import sys


def cues(path):
    txt = io.open(path, encoding="utf-8").read()
    out = []
    for blk in re.split(r"\n\s*\n", txt):
        m = re.search(r"(\d+):(\d\d):(\d\d)[.,](\d+)\s*-->\s*(\d+):(\d\d):(\d\d)[.,](\d+)", blk)
        if not m:
            continue
        g = [int(x) for x in m.groups()]
        de = g[0] * 3600 + g[1] * 60 + g[2] + g[3] / 1000
        a = g[4] * 3600 + g[5] * 60 + g[6] + g[7] / 1000
        text = " ".join(l.strip() for l in blk.split("\n")[1:] if "-->" not in l and not l.strip().isdigit())
        text = re.sub(r"<[^>]+>", "", text).strip()
        if text:
            out.append((de, a, text))
    return out


def text_entre(paraules, de, a, clau="text"):
    """Les paraules de l'ASR que solapen l'interval [de, a] en més de la meitat de la seva durada."""
    fora = []
    for w in paraules:
        s, e = w["start"], w["end"]
        sol = min(e, a) - max(s, de)
        if sol > 0 and sol >= 0.5 * max(0.02, e - s):
            fora.append(w[clau])
    return " ".join(fora)


def carrega_asr(cami, clau):
    """{video: [paraules amb start/end]} de la carpeta del kernel o del fitxer de veritat."""
    per_video = {}
    if cami.endswith(".json"):
        for v in json.load(io.open(cami, encoding="utf-8")):
            if v.get("shi"):
                #: un vers sencer com a una «paraula» amb el seu interval: prou per a rètols
                per_video.setdefault(v["video"], []).append({"start": v["de"], "end": v["a"], "text": v["shi"]})
        return per_video
    for f in glob.glob(os.path.join(cami, "*.json")):
        d = json.load(io.open(f, encoding="utf-8"))
        per_video[d["video"]] = d.get(clau) or []
    return per_video


if __name__ == "__main__":
    subs, asr_cami, fora = sys.argv[1], sys.argv[2], sys.argv[3]
    clau = sys.argv[4] if len(sys.argv) > 4 else "greedy"
    asr = carrega_asr(asr_cami, clau)
    n = buits = 0
    with io.open(fora, "w", encoding="utf-8") as g:
        for vid, paraules in sorted(asr.items()):
            en = cues(os.path.join(subs, vid + ".en.vtt")) if os.path.exists(os.path.join(subs, vid + ".en.vtt")) else []
            ar = cues(os.path.join(subs, vid + ".ar.vtt")) if os.path.exists(os.path.join(subs, vid + ".ar.vtt")) else []
            base = en or ar
            for de, a, t in base:
                am = text_entre(paraules, de, a)
                if not am.strip():
                    buits += 1
                    continue
                fila = {"video": vid, "de": round(de, 2), "a": round(a, 2), "asr": am,
                        "en": t if base is en else "",
                        "ar": t if base is ar else " | ".join(x[2] for x in ar if x[0] < a and x[1] > de)}
                if base is en and ar:
                    fila["ar"] = " | ".join(x[2] for x in ar if x[0] < a and x[1] > de)
                g.write(json.dumps(fila, ensure_ascii=False) + "\n")
                n += 1
    print(f"{n} parells · {buits} rètols sense text ASR · {len(asr)} vídeos")
