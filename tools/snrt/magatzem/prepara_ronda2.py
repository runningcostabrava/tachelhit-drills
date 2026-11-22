"""Els candidats de la ronda 2: talls que M1 NO ha vist i que podrien creuar el llindar.

Decidit amb en Pablo (20-11): adoptar M1 pero triar el corpus de la ronda 2 nomes d'allo que M1
no ha vist, de manera que el cercle no es pugui donar la rao sol. El problema que surt en
comptar-ho: **no hi ha cap tall no vist per sota de 0,35** fora dels capitols retinguts -- el
train de la ronda 1 se'ls va endur tots. O sigui que tot el corpus nou ha de sortir de talls que
avui son per sobre del llindar i que M1 ha de promoure.

Aixo es una pregunta, no un pla: si M1 en promou pocs, la ronda 2 no te material i val mes
saber-ho abans de muntar-la. Per aixo primer es passa M1 (i M0, per comparar) per tots els
candidats de CER <= 0,60, i despres es compta.

PREDICCIO: la millora de M1 als talls que NO ha vist era d'uns 0,015 al tram alt. Amb aixo
creuarien nomes els que avui son entre 0,35 i 0,365, que son molt pocs. Espero una promocio
petita -- unes desenes --, i si es aixi la conclusio es que el SNRT s'ha esgotat a aquest
llindar i el guany seguent ha de venir d'un altre lloc.
"""
import io
import json
import os
import shutil
import sys
import tarfile
from pathlib import Path

from huggingface_hub import hf_hub_download, list_repo_files

sys.path.insert(0, r"E:/tamazight/_magatzem")

MAG = Path(r"E:/tamazight/_magatzem")
DESTI = MAG / "ronda2" / "dades"

for l in io.open(r"C:\Users\josep\app2\tachelhit-drills\backend\.env", encoding="utf-8",
                 errors="replace"):
    l = l.strip()
    if l.startswith("HF_TOKEN") and "=" in l:
        os.environ["HF_TOKEN"] = l.split("=", 1)[1].strip().strip('"').strip("'")

REPO = "josepabloucr/tamazight-tv-privat"
tok = os.environ["HF_TOKEN"]
TMP = Path(os.environ.get("TEMP", ".")) / "so_snrt"

RETINGUTS = {"jerkqzqplguvpzoh", "wckionryvrwatrvs", "hmssyuzoyqzywbaj", "oeeljuwkqlqtebzr"}
vist = {r["id"] for r in json.load(
    io.open(MAG / "ronda" / "dades" / "rows.json", encoding="utf-8"))
    if r["split"] in ("train", "dev")}
vistos = []
for l in io.open(MAG / "acord_triat.jsonl", encoding="utf-8"):
    if not l.strip():
        continue
    x = json.loads(l)
    if x["id"] in vist or x["capitol"][:16] in RETINGUTS or x["cer"] > .60:
        continue
    if not (x.get("tifinag") or "").strip():
        continue
    vistos.append({"id": x["id"], "slug": x["capitol"], "split": "candidat",
                   "tifinag": x["tifinag"], "cer_m0": x["cer"]})
print(f"{len(vistos)} candidats (no vistos, fora dels retinguts, CER de M0 <= 0,60)")

list_repo_files(REPO, repo_type="dataset", token=tok)   #: comprova el token aviat


def talls_de(slug):
    p = TMP / slug
    if not (p / "talls").exists():
        tar = hf_hub_download(REPO, f"capitols/{slug}/talls.tar", repo_type="dataset", token=tok)
        p.mkdir(parents=True, exist_ok=True)
        with tarfile.open(tar) as z:
            try:
                z.extractall(p, filter="data")
            except TypeError:
                z.extractall(p)
    return p / "talls"


if DESTI.exists():
    shutil.rmtree(DESTI)
(DESTI / "talls").mkdir(parents=True)

#: l'adaptador que va sortir de la ronda: ha d'anar amb els talls perque el nucli el trobi
m1 = MAG / "ronda" / "sortida" / "adaptador_shi_snrt_B.pt"
assert m1.exists(), m1
shutil.copy(m1, DESTI / "adaptador_shi_snrt_B.pt")

sortida, faltats = [], 0
carpetes = {}
for r in vistos:
    slug = r["slug"]
    if slug not in carpetes:
        carpetes[slug] = talls_de(slug)
    k = int(r["id"].split(":")[1])
    w = carpetes[slug] / f"{slug}_{k:04d}.wav"
    if not w.exists():
        faltats += 1
        continue
    nom = f"{slug[:16]}_{k:04d}.wav"
    shutil.copy(w, DESTI / "talls" / nom)
    sortida.append({"fitxer": f"talls/{nom}", "id": r["id"], "slug": slug,
                    "split": r["split"], "tifinag": r["tifinag"], "cer_m0": r["cer_m0"]})

json.dump(sortida, io.open(DESTI / "rows.json", "w", encoding="utf-8"), ensure_ascii=False)
mida = sum(f.stat().st_size for f in (DESTI / "talls").glob("*.wav"))
print(f"{len(sortida)} talls ({faltats} sense fitxer) · {mida/1e6:.0f} MB a {DESTI}")
