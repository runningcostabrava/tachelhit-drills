"""La geometria de la franja, capítol per capítol. Sense això, rellegir no val res.

La fàbrica mesura on és la línia del tifinag a cada capítol i ho desa a `geometria.json`. Jo
retallava sempre al mateix lloc (y 870 de 1080p, la geometria estàndard) i en un capítol amb
`"estandard": false` escapçava els signes: en rellegir-lo sortia A=0 quan amb el text de la
fàbrica és el millor de tots (37,3 %).

Això baixa el `geometria.json` de cada capítol de la còpia privada d'HF i en deixa una taula.
També es desa `font` i `alt` de `numeros.json`: val la pena saber de quin vídeo es va fer cada
capítol i a quina alçada, encara que la durada coincideixi amb la del nostre.
"""
import io
import json
import os
import tarfile
import tempfile
from collections import Counter
from pathlib import Path

VISOR = Path(r"E:\tamazight\_visor")
DESTI = Path(r"E:\tamazight\_magatzem\geometries.json")
REPO = "josepabloucr/tamazight-tv-privat"

for l in io.open(r"C:\Users\josep\app2\tachelhit-drills\backend\.env", encoding="utf-8",
                 errors="replace"):
    l = l.strip()
    if l.startswith("HF_TOKEN") and "=" in l:
        os.environ["HF_TOKEN"] = l.split("=", 1)[1].strip().strip('"').strip("'")

from huggingface_hub import hf_hub_download  # noqa: E402

slugs = sorted(d.name for d in VISOR.iterdir()
               if (d / "subtitols.jsonl").exists() and len(d.name) == 40)
print(f"capítols: {len(slugs)}")

taula, menes, alts, geo = {}, Counter(), Counter(), Counter()
for n, slug in enumerate(slugs, 1):
    try:
        t = hf_hub_download(REPO, f"capitols/{slug}/dades.tar", repo_type="dataset",
                            token=os.environ["HF_TOKEN"])
    except Exception as e:
        print(f"   {slug[:14]}… no es baixa ({type(e).__name__})")
        continue
    with tempfile.TemporaryDirectory() as tmp:
        with tarfile.open(t) as z:
            try:
                z.extractall(tmp, filter="data")
            except TypeError:
                z.extractall(tmp)
        arrel = Path(tmp)
        g = next(arrel.rglob("geometria.json"), None)
        nu = next(arrel.rglob("numeros.json"), None)
        d = json.load(io.open(g, encoding="utf-8")) if g else {}
        num = json.load(io.open(nu, encoding="utf-8")) if nu else {}
    tif = d.get("TIFINAG_720") or [580, 614]
    taula[slug] = {"TIFINAG_720": tif, "BANDA_720": d.get("BANDA_720"),
                   "estandard": d.get("estandard"), "cos_tifinag_1080": d.get("cos_tifinag_1080"),
                   "font": num.get("font"), "alt": num.get("alt"),
                   "durada": num.get("durada_video")}
    menes[num.get("font")] += 1
    alts[num.get("alt")] += 1
    geo["estàndard" if d.get("estandard") else "NO estàndard"] += 1
    marca = "" if d.get("estandard") else "   <- NO estàndard"
    print(f"   [{n}/{len(slugs)}] {slug[:14]}…  tifinag_720 {tif}  "
          f"font {num.get('font')}  alt {num.get('alt')}{marca}", flush=True)

json.dump(taula, io.open(DESTI, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"\ndesat a {DESTI}")
print("fonts:", dict(menes))
print("alçades:", dict(alts))
print("geometria:", dict(geo))
#: quantes geometries diferents hi ha: si n'hi ha moltes, la meva franja fixa no podia funcionar
print("franges diferents:", Counter(tuple(v["TIFINAG_720"]) for v in taula.values()))
