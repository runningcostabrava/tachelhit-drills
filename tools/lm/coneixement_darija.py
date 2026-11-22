# -*- coding: utf-8 -*-
"""El que el professor de Tamazight For All explica en dàrija, posat en forma llegible i lligat
al moment del vídeo on ho diu: la parella veu – transcripció – traducció que en Pablo demana.

Entrada: `mina_*.jsonl` (sortida de mina_transcrits.py) i la carpeta dels vtt automàtics.
Per a cada ítem es busca el rètol del vtt que conté la frase `on` (o el seu tros més llarg) i se
li posa l'instant (de–a) del vídeo. Sortida:
  · <sortida>.jsonl: un ítem per línia amb video, idx (posició de l'ítem al minat: la clau que fa
    servir l'auditoria), model (el que l'ha extret), de, a, amazic_ar, amazic_llati, significat_ca,
    significat_ar, mena, on, url (youtube amb &t=)
  · <sortida>.md: el coneixement per vídeo i mena (regles i afixos primer), amb l'enllaç al moment

ÚS: coneixement_darija.py <mina.jsonl> [<mina2.jsonl> …] --vtt <carpeta> --fora <sortida sense extensió>
"""
import glob
import io
import json
import os
import re
import sys


def cues(path):
    txt = io.open(path, encoding="utf-8", errors="replace").read()
    out, vist = [], set()
    for blk in re.split(r"\n\s*\n", txt):
        m = re.search(r"(\d+):(\d\d):(\d\d)[.,](\d+)\s*-->\s*(\d+):(\d\d):(\d\d)[.,](\d+)", blk)
        if not m:
            continue
        g = [int(x) for x in m.groups()]
        de = g[0] * 3600 + g[1] * 60 + g[2] + g[3] / 1000
        a = g[4] * 3600 + g[5] * 60 + g[6] + g[7] / 1000
        text = " ".join(re.sub(r"<[^>]+>", "", l).strip() for l in blk.split("\n")[1:] if "-->" not in l)
        text = " ".join(text.split())
        if text and text not in vist:
            vist.add(text)
            out.append((de, a, text))
    return out


def troba(on, rets):
    """El rètol que millor conté la frase `on`: per la finestra de 4 paraules seguides més llarga."""
    mots = on.split()
    millor = None
    for n in range(min(6, len(mots)), 2, -1):
        for i in range(len(mots) - n + 1):
            tros = " ".join(mots[i:i + n])
            for de, a, t in rets:
                if tros in t:
                    return de, a, t
    return millor


if __name__ == "__main__":
    args = sys.argv[1:]
    vtt = args[args.index("--vtt") + 1]
    fora = args[args.index("--fora") + 1]
    fitxers = [a for a in args if a.endswith(".jsonl")]
    per_video = {}
    for f in fitxers:
        for l in io.open(f, encoding="utf-8"):
            d = json.loads(l)
            per_video.setdefault(d["video"], d)
    n_items = n_temps = 0
    linies_md = ["# El que el professor explica en dàrija, amb el moment del vídeo\n",
                 "Cada línia: el que diu (transcrit automàtic, lletres àrabs), la forma llatina si es pot deduir, "
                 "el significat que ell dóna, i l'enllaç al segon on ho diu. Material de tercers: per aprendre'n, no per copiar-lo.\n"]
    with io.open(fora + ".jsonl", "w", encoding="utf-8") as g:
        for vid, d in per_video.items():
            items = d.get("items") or []
            if not items:
                continue
            cami = os.path.join(vtt, vid + ".ar-orig.vtt")
            rets = cues(cami) if os.path.exists(cami) else []
            linies_md.append(f"\n## {d.get('titol') or vid} — `{vid}` ({len(items)} ítems)\n")
            for mena in ("regla", "afix", "expressió", "paraula"):
                xs = [(i, it) for i, it in enumerate(items) if it.get("mena") == mena]
                if not xs:
                    continue
                linies_md.append(f"\n**{mena}**\n")
                for idx, it in xs:
                    n_items += 1
                    t = troba(it.get("on") or "", rets) if rets else None
                    de, a = (round(t[0], 1), round(t[1], 1)) if t else (None, None)
                    if t:
                        n_temps += 1
                    url = f"https://www.youtube.com/watch?v={vid}&t={int(de)}s" if de is not None else ""
                    fila = {"video": vid, "idx": idx, "model": d.get("model") or "deepseek-chat", "titol": d.get("titol"),
                            "de": de, "a": a, "amazic_ar": it.get("amazic_ar"),
                            "amazic_llati": it.get("amazic_llati") or "", "significat_ca": it.get("significat_ca"),
                            "significat_ar": it.get("significat_ar"), "mena": mena, "on": it.get("on"), "url": url}
                    g.write(json.dumps(fila, ensure_ascii=False) + "\n")
                    lat = f" *{it.get('amazic_llati')}*" if it.get("amazic_llati") else ""
                    enll = f" [{int(de)//60}:{int(de)%60:02d}]({url})" if url else ""
                    linies_md.append(f"- **{it.get('amazic_ar')}**{lat} — {it.get('significat_ca')}{enll}")
    io.open(fora + ".md", "w", encoding="utf-8").write("\n".join(linies_md) + "\n")
    print(f"{len(per_video)} vídeos · {n_items} ítems · {n_temps} amb el moment del vídeo ({100*n_temps/max(1,n_items):.0f} %) → {fora}.md / .jsonl")
