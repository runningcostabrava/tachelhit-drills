# -*- coding: utf-8 -*-
"""Ajunta les mesures per vídeo (`zouhir_mesura.py` pel Space, o `zouhir_de_kaggle.py` pel nucli) en
un sol test i un sol corpus.

  <carpeta>/mesura/*.json  →  <carpeta>/resum.md            (taula per vídeo + totals per canal i lector)
                              <carpeta>/veritat_zouhir.json  (tots els rètols: so, temps, tifinag, llatí,
                                                              en/ar/fr — per a H4 i la inducció de glosses)
Els rètols de pantalla (entrada i crèdits: veritat d'1-2 mots i cap lector no hi sent res) es
marquen «rètol» i no compten com a parla. Tampoc no hi compten els rètols la veritat dels quals
no és amazic en tifinag estàndard: els escrits en **lletres àrabs** (versos de l'Alcorà, o amazic
en grafia àrab, que el transliterador no sap llegir) van a «àrab», i els que després de
transliterar encara duen tifinag (ⵝ ⴺ ⵒ…: grafia cabilenca o rifenya) van a «altra grafia».
Tots dos es desen igualment al corpus, amb la seva mena, perquè un dia es puguin aprofitar.

ÚS: zouhir_resum.py <carpeta> [--titols videos.txt]
"""
import glob
import io
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import h3_puntua   # noqa: E402

LECTORS = ("transcribe_mms", "transcribe_mms_lm", "greedy", "beam", "lm_a0.1", "lm_a0.15")
ARAB = re.compile("[؀-ۿ]")
TIFINAG = re.compile("[ⴰ-⵿]")


def mena_de(v, lectors):
    """«parlat», o per què no compta: «àrab», «altra grafia» o «rètol» (de pantalla)."""
    if ARAB.search(v["veritat"]):
        return "àrab"
    if TIFINAG.search(v["veritat"]):
        return "altra grafia"
    if len(v["veritat"].split()) <= 2 and lectors and all(len(x.split()) <= 1 for x in lectors):
        return "rètol"
    return "parlat"


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
    rutes |= {k for k in LECTORS if any(v.get(k) is not None for v in d["versos"])}
    for v in d["versos"]:
        v.setdefault("canal", d.get("canal") or "zouhir")
        v["mena"] = mena_de(v, [v.get(r) for r in LECTORS if v.get(r) is not None])
    tots += d["versos"]
    parlats = [v for v in d["versos"] if v["mena"] == "parlat"]
    p = {r: h3_puntua.puntua(parlats, r, "parlat", plegat=False) for r in LECTORS
         if any(v.get(r) is not None for v in parlats)}
    files.append((d["video"], len(parlats), sum(v["a"] - v["de"] for v in parlats) / 60, p, d.get("canal") or "zouhir",
                  len(d["versos"]) - len(parlats)))
rutes = [r for r in LECTORS if r in rutes]
menes = {m: sum(1 for v in tots if v["mena"] == m) for m in ("rètol", "àrab", "altra grafia")}
with io.open(os.path.join(carpeta, "resum.md"), "w", encoding="utf-8") as g:
    g.write(f"# Vídeos amb pista amaziga humana: el nostre lector contra la pista ({len(files)} vídeos, "
            f"{sum(x[1] for x in files)} rètols parlats, {sum(x[2] for x in files):.1f} min; exclosos: "
            f"{menes['rètol']} rètols de pantalla, {menes['àrab']} en lletres àrabs, {menes['altra grafia']} en altra grafia)\n\n")
    g.write("| vídeo | canal: títol | rètols | exclosos | min | " + " | ".join(f"CER {r} | WER {r}" for r in rutes) + " |\n")
    g.write("|---|---|---|---|---|" + "---|---|" * len(rutes) + "\n")
    for vid, n, m, p, canal, excl in sorted(files, key=lambda x: (x[4], x[0])):
        g.write(f"| `{vid}` | {canal}: {titols.get(vid, '')[:40]} | {n} | {excl} | {m:.1f} | " +
                " | ".join(f"{p[r]['cer']:.3f} | {p[r]['wer']:.3f}" if p.get(r) else " | " for r in rutes) + " |\n")
    canals = sorted({x[4] for x in files})
    for canal in canals + (["tots"] if len(canals) > 1 else []):
        sel = [v for v in tots if canal == "tots" or v.get("canal") == canal]
        g.write(f"\n## Total {canal} (mitjana per rètol parlat)\n\n| lector | n | CER | WER | WER només de frontera | CER plegat |\n|---|---|---|---|---|---|\n")
        for r in rutes:
            p = h3_puntua.puntua(sel, r, "parlat", plegat=False)
            q = h3_puntua.puntua(sel, r, "parlat", plegat=True)
            if p:
                g.write(f"| `{r}` | {p['n']} | {p['cer']:.3f} | {p['wer']:.3f} | {p['wer_frontera']:.3f} | {q['cer']:.3f} |\n")
                print(f"{canal:7} {r:18} n={p['n']:4} CER {p['cer']:.3f} WER {p['wer']:.3f} plegat {q['cer']:.3f}")
json.dump([{k: v for k, v in x.items() if k in ("video", "canal", "pista", "n", "de", "a", "mena", "tifinag", "veritat", "en", "ar", "fr", "en-US")} for x in tots],
          io.open(os.path.join(carpeta, "veritat_zouhir.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
print(len(files), "vídeos ·", len(tots), "rètols · amb en/ar/fr:",
      sum(1 for x in tots if x.get("en") and x.get("ar") and x.get("fr")), "· exclosos:", menes,
      "· desat resum.md i veritat_zouhir.json")
