# -*- coding: utf-8 -*-
"""Abans/després del lector amb lèxic sobre la mostra fixa de 40 (llavor 1114), a cegues.

Per a cada un dels 40 trossos (vídeo, inici): el tros vell (greedy, taules del 14-11, carpeta
`escoltats/`) i el nou (feix amb lèxic, taules del 15-11, carpeta `escoltats_lm/`), aparellats
pel mateix instant d'inici (els talls surten dels silencis, no del text, i per tant coincideixen).

Surten dos fitxers:
  · `ab40_full.json`: el full del jutge, amb els 80 (+16 duplicats plantats) en ordre barrejat i
    sense dir de quina banda és cadascun: el text de l'ASR, la interlineal (token → casella) i la
    frase si n'hi ha. El jutge diu, per tros: quantes caselles plenes són FALSES (no poden voler
    dir això), i de la frase: bo / a mitges / fals / cap.
  · `ab40_clau.json`: la clau (id → vell/nou, n, duplicat de), que no s'obre fins després.

ÚS: abans_despres40.py <mostra40.json> <escoltats> <escoltats_lm> <carpeta de sortida>
"""
import glob
import io
import json
import os
import random
import sys


def carrega(carpeta):
    per_video = {}
    for f in glob.glob(os.path.join(carpeta, "*.json")):
        if "_v1" in f:
            continue
        d = json.load(io.open(f, encoding="utf-8"))
        per_video[d["video"]] = d
    return per_video


def tros_a(d, de):
    if not d:
        return None
    millor = min(d["emissions"], key=lambda e: abs(e["de"] - de))
    return millor if abs(millor["de"] - de) <= 0.6 else None


def vista(e):
    fe = e.get("fets") or {}
    toks = (e.get("hi_sent") or "").split()
    inter = fe.get("interlineal") or []
    return {"am": e.get("hi_sent") or "", "glosses": e.get("paraules") or [],
            "interlineal": [f"{t} → {c}" for t, c in zip(toks, inter)] if inter else [],
            "frase": fe.get("frase") or "", "tema": (fe.get("marc") or {}).get("tema") or "",
            "cita": fe.get("cita") or ""}


if __name__ == "__main__":
    mostra = json.load(io.open(sys.argv[1], encoding="utf-8"))
    vell, nou = carrega(sys.argv[2]), carrega(sys.argv[3])
    fora = sys.argv[4]
    os.makedirs(fora, exist_ok=True)
    items, falten = [], []
    for n, m in enumerate(mostra, 1):
        ev, en = tros_a(vell.get(m["vid"]), m["de"]), tros_a(nou.get(m["vid"]), m["de"])
        if not ev or not en:
            falten.append((n, m["vid"], m["de"], bool(ev), bool(en)))
            continue
        items.append({"n": n, "col": "vell", "vid": m["vid"], "de": m["de"], **vista(ev)})
        items.append({"n": n, "col": "nou", "vid": m["vid"], "de": m["de"], **vista(en)})
    rnd = random.Random(1114)
    dups = rnd.sample(range(len(items)), min(16, len(items)))
    plegats = items + [dict(items[i], _dup_de=i) for i in dups]
    ordre = list(range(len(plegats)))
    rnd.shuffle(ordre)
    full, clau = [], []
    for pos, idx in enumerate(ordre, 1):
        it = plegats[idx]
        full.append({"id": pos, "am": it["am"], "glosses": it["glosses"], "interlineal": it["interlineal"],
                     "tema": it["tema"], "cita": it["cita"], "frase": it["frase"]})
        clau.append({"id": pos, "n": it["n"], "col": it["col"], "vid": it["vid"], "de": it["de"],
                     "dup_de": it.get("_dup_de")})
    json.dump(full, io.open(os.path.join(fora, "ab40_full.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump(clau, io.open(os.path.join(fora, "ab40_clau.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{len(items)//2} trossos aparellats · {len(full)} fitxes al full (16 duplicats) · falten {len(falten)}: {falten[:5]}")
    #: i el recompte mecànic, sense jutge: tokens, caselles plenes, frases, i quants tokens canvien
    for col in ("vell", "nou"):
        xs = [i for i in items if i["col"] == col]
        toks = sum(len(i["am"].split()) for i in xs)
        plenes = sum(1 for i in xs for c in i["interlineal"] if not c.endswith("→ ?"))
        print(f"  {col}: {toks} tokens · {plenes} caselles plenes · {sum(1 for i in xs if i['frase'])} frases · "
              f"{sum(1 for i in xs if i['tema'])} temes · {sum(1 for i in xs if i['cita'])} cites")
    iguals = sum(1 for a, b in zip(items[0::2], items[1::2]) if a["am"] == b["am"])
    print(f"  text de l'ASR idèntic en {iguals} de {len(items)//2} trossos")
