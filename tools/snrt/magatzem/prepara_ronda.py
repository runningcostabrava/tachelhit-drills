"""Prepara la ronda d'entrenament del cercle amb el corpus de grau A refet.

Per què ara i no abans: el nucli d'entrenament (`tools/lm/kaggle/transcriptor_snrt.py`) ja porta
el filtre de qualitat, però compara text RIC (amb vocals) contra un subtítol que no les escriu,
i el 17-11 es va mesurar que només passava el **0,9 %** dels talls (4 de 466), de manera que el
train quedava buit. El grau A d'ara compara **esquelets de consonants**, que és l'arranjament
d'això mateix, i en passen el 14,3 %: **2.190 rèpliques** en comptes de 4.

Disseny de la ronda, i el que n'espero dit abans de mesurar-ho:

  - **test**: quatre capítols SENCERS que no entrenen, dos que l'orella entén (Akounad, Zahour)
    i dos que no (Khbiza, Abarnous), sense cap filtre, perquè el filtre és de l'ASR d'ara i
    afavoriria el test.
  - **train**: el grau A dels altres vint-i-un.
  - **dev**: una desena part del train, de capítols del train.

Espero que els dos retinguts bons millorin i que els dos dolents **no es moguin**: el train surt
de rèpliques que el model ja encerta a mitges, i els deu convidats que no entén hi aporten entre
2 i 10 rèpliques cada un. Si els dolents també milloren, el límit és el domini i no el parlant,
i llavors el pla canvia.

Surt `ronda/dades/` amb `rows.json` i els talls, tal com el nucli els vol.
"""
import io
import json
import os
import random
import shutil
import tarfile
import sys
from pathlib import Path

for l in io.open(r"C:\Users\josep\app2\tachelhit-drills\backend\.env", encoding="utf-8",
                 errors="replace"):
    l = l.strip()
    if l.startswith("HF_TOKEN") and "=" in l:
        os.environ["HF_TOKEN"] = l.split("=", 1)[1].strip().strip('"').strip("'")
from huggingface_hub import hf_hub_download, list_repo_files  # noqa: E402

sys.path.insert(0, r"E:/tamazight/_magatzem")

REPO = "josepabloucr/tamazight-tv-privat"
MAG = Path(r"E:/tamazight/_magatzem")
TMP = Path(os.environ.get("TEMP", ".")) / "so_snrt"
#: cada brac escriu a la SEVA carpeta: `prepara_ronda.py` esborra el desti en comencar
#: i el brac de 0,35 ja ha corregut (`ronda/sortida` en guarda l'adaptador).
DESTI = Path(os.getenv("RONDA", str(MAG / "ronda"))) / "dades"
#: els quatre retinguts, pels seus prefixos
RETINGUTS = {"jerkqzqplguvpzoh": "bo (Zahour)", "wckionryvrwatrvs": "bo (Akounad)",
             "hmssyuzoyqzywbaj": "dolent (Khbiza)", "oeeljuwkqlqtebzr": "dolent (Abarnous)"}
TEST_PER_CAPITOL = 300
PART_DEV = 0.1

tok = os.environ["HF_TOKEN"]
fitxers = list_repo_files(REPO, repo_type="dataset", token=tok)
slugs = sorted({f.split("/")[1] for f in fitxers if f.startswith("capitols/")})


def talls_de(slug):
    """La carpeta de talls del capítol, baixant-la si no hi és."""
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


#: Quin llindar d'esquelet entra al train. Per defecte el de la ronda 1 (grau A = 0,35); amb
#: `LLINDAR=0.20` es fa el braç estret, que és la pregunta oberta del §20.7 del DESXIFRAT: a
#: 0,20 les etiquetes són millors (CER ric 0,151 -> 0,127 a les proves amb veritat humana) però
#: el SNRT es queda amb 924 talls en comptes de 2.190. Els dos braços surten de M0 i de la
#: mateixa recepta: l'única diferència ha de ser el corpus.
LLINDAR = float(os.getenv("LLINDAR", "0.35"))

#: el grau A amb significat, per capítol
grau_a = {}
for l in io.open(MAG / "acord_triat.jsonl", encoding="utf-8"):
    if not l.strip():
        continue
    r = json.loads(l)
    if r["cer"] <= LLINDAR:
        grau_a.setdefault(r["capitol"], []).append(r)

#: totes les rèpliques amb text, per als retinguts
totes = {}
for l in io.open(MAG / "text_triat.jsonl", encoding="utf-8"):
    if not l.strip():
        continue
    x = json.loads(l)
    if (x.get("tifinag") or "").strip():
        totes.setdefault(x["capitol"], []).append(x)

if DESTI.exists():
    shutil.rmtree(DESTI)
(DESTI / "talls").mkdir(parents=True)

rnd = random.Random(2011)
rows, compte = [], {"train": 0, "dev": 0, "test": 0}
for slug in slugs:
    if slug.startswith("baba_ali") or slug.startswith("tadfi_"):
        continue
    pref = slug[:16]
    retingut = pref in RETINGUTS
    files = (rnd.sample(totes.get(slug, []), min(TEST_PER_CAPITOL, len(totes.get(slug, []))))
             if retingut else grau_a.get(slug, []))
    if not files:
        continue
    carpeta = talls_de(slug)
    posats = 0
    for i, r in enumerate(files):
        k = r["id"].split(":")[1]
        w = carpeta / f"{slug}_{int(k):04d}.wav"
        if not w.exists():
            continue
        nom = f"{pref}_{int(k):04d}.wav"
        shutil.copy(w, DESTI / "talls" / nom)
        if retingut:
            split = "test"
        else:
            split = "dev" if rnd.random() < PART_DEV else "train"
        rows.append({"split": split, "fitxer": f"talls/{nom}", "tifinag": r["tifinag"],
                     "slug": slug, "id": r["id"]})
        compte[split] += 1
        posats += 1
    print(f"{pref} {'RETINGUT ' + RETINGUTS[pref] if retingut else 'train':<22}{posats:5d} talls")

json.dump(rows, io.open(DESTI / "rows.json", "w", encoding="utf-8"), ensure_ascii=False)
mida = sum(f.stat().st_size for f in (DESTI / "talls").glob("*.wav"))
print(f"\ntrain {compte['train']} · dev {compte['dev']} · test {compte['test']} "
      f"· {len(rows)} talls · {mida/1e6:.0f} MB a {DESTI}")
