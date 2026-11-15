# -*- coding: utf-8 -*-
"""Ajunta les mesures per vídeo de `zouhir_mesura.py` en un sol test i un sol corpus.

  <carpeta>/mesura/*.json  →  <carpeta>/resum.md            (taula per vídeo + total, per lector)
                              <carpeta>/veritat_zouhir.json  (tots els rètols: so, temps, tifinag,
                                                              llatí, en/ar/fr — el que H4 i la
                                                              inducció de glosses necessiten)
ÚS: zouhir_resum.py <carpeta> [--titols videos.txt]
"""
import glob
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import h3_puntua   # noqa: E402

carpeta = sys.argv[1]
titols = {}
if "--titols" in sys.argv:
    for l in io.open(sys.argv[sys.argv.index("--titols") + 1], encoding="utf-8"):
        p = l.rstrip("\n").split("|")
        if len(p) >= 2:
            titols[p[0]] = p[1]
tots, files = [], []
rutes = set()
for f in sorted(glob.glob(os.path.join(carpeta, "mesura", "*.json"))):
    d = json.load(io.open(f, encoding="utf-8"))
    rutes |= set(d.get("puntuacio") or {})
    tots += d["versos"]
    p = d.get("puntuacio") or {}
    files.append((d["video"], len(d["versos"]), sum(v["a"] - v["de"] for v in d["versos"]) / 60, p))
rutes = sorted(rutes)
with io.open(os.path.join(carpeta, "resum.md"), "w", encoding="utf-8") as g:
    g.write(f"# Vídeos amb pista amaziga humana: el nostre lector contra la pista ({len(files)} vídeos, {len(tots)} rètols, "
            f"{sum(x[2] for x in files):.1f} min de rètol)\n\n")
    g.write("| vídeo | títol | rètols | min | " + " | ".join(f"CER {r} | WER {r}" for r in rutes) + " |\n")
    g.write("|---|---|---|---|" + "---|---|" * len(rutes) + "\n")
    for vid, n, m, p in files:
        g.write(f"| `{vid}` | {titols.get(vid, '')[:40]} | {n} | {m:.1f} | " +
                " | ".join(f"{p[r]['cer']:.3f} | {p[r]['wer']:.3f}" if p.get(r) else " | " for r in rutes) + " |\n")
    g.write("\n## Total (mitjana per rètol)\n\n| lector | n | CER | WER | WER només de frontera | CER plegat |\n|---|---|---|---|---|---|\n")
    for r in rutes:
        p = h3_puntua.puntua(tots, r, "parlat", plegat=False)
        q = h3_puntua.puntua(tots, r, "parlat", plegat=True)
        if p:
            g.write(f"| `{r}` | {p['n']} | {p['cer']:.3f} | {p['wer']:.3f} | {p['wer_frontera']:.3f} | {q['cer']:.3f} |\n")
            print(r, p, "plegat", round(q["cer"], 3))
json.dump([{k: v for k, v in x.items() if k in ("video", "n", "de", "a", "tifinag", "veritat", "en", "ar", "fr", "en-US")} for x in tots],
          io.open(os.path.join(carpeta, "veritat_zouhir.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
print(len(files), "vídeos ·", len(tots), "rètols · amb en/ar/fr:",
      sum(1 for x in tots if x.get("en") and x.get("ar") and x.get("fr")), "· desat resum.md i veritat_zouhir.json")
