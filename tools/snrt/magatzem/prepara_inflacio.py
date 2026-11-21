"""Adoptar M1 inflaria el filtre? Els talls que ha vist contra els que no ha vist mai.

Si la ronda 2 sent el SNRT amb M1, M1 encertara mes als 1.849 talls que va fer servir per
entrenar-se -- perque hi te el text del subtitol com a etiqueta -- i el filtre d'acord els
deixara passar mes facilment. El cercle es donaria la rao sol. La pregunta es QUANT.

**El primer disseny no s'aguantava i val la pena deixar-ho escrit.** Volia aparellar cada tall
vist amb un de no vist del mateix capitol i amb el mateix CER de partida. No es pot: el train es
va endur TOTS els talls de grau A de cada capitol, de manera que dins d'un capitol «vist» vol dir
«CER baix» i «no vist» vol dir «CER alt» per construccio. De 1.849 vistos nomes en sortien 337
parelles, i totes al limit.

El control bo ja existeix i no costa cap GPU: **els quatre capitols retinguts**. Els seus talls
de grau A son exactament «talls que casaven amb el subtitol sota M0 i que el model no ha vist
mai», i M0 i M1 ja hi han passat tots dos (`ronda/sortida/snrt_B_sortides.json`). El que falta,
doncs, es nomes passar M0 i M1 pels talls VISTOS.

    inflacio = (quant baixa el CER als vistos) - (quant baixa als retinguts de grau A)

Si l'interval d'aquesta diferencia passa per zero, adoptar M1 i tornar a sentir tot el SNRT no
infla el filtre. Si no hi passa, la ronda 2 ha de triar el corpus nomes del que M1 no ha vist.

Avis que anira al resultat: els retinguts son capitols SENCERS diferents, o sigui que a la
diferencia hi ha, a mes de la memoritzacio, el que separa uns capitols dels altres. Per aixo la
comparacio principal es fa **nomes amb els capitols tachelhit de les dues bandes**.
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
DESTI = MAG / "inflacio" / "dades"

for l in io.open(r"C:\Users\josep\app2\tachelhit-drills\backend\.env", encoding="utf-8",
                 errors="replace"):
    l = l.strip()
    if l.startswith("HF_TOKEN") and "=" in l:
        os.environ["HF_TOKEN"] = l.split("=", 1)[1].strip().strip('"').strip("'")

REPO = "josepabloucr/tamazight-tv-privat"
tok = os.environ["HF_TOKEN"]
TMP = Path(os.environ.get("TEMP", ".")) / "so_snrt"

rows = json.load(io.open(MAG / "ronda" / "dades" / "rows.json", encoding="utf-8"))
vistos = [r for r in rows if r["split"] in ("train", "dev")]
print(f"{len(vistos)} talls vistos pel model, de {len({r['slug'] for r in vistos})} capitols")

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
                    "split": r["split"], "tifinag": r["tifinag"]})

json.dump(sortida, io.open(DESTI / "rows.json", "w", encoding="utf-8"), ensure_ascii=False)
mida = sum(f.stat().st_size for f in (DESTI / "talls").glob("*.wav"))
print(f"{len(sortida)} talls ({faltats} sense fitxer) · {mida/1e6:.0f} MB a {DESTI}")
