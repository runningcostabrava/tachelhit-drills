"""Mostra gran per decidir si el cabilenc enten el tachelhit millor que l'adaptador de tachelhit.

Amb 55 talls per episodi, el cabilenc feia 41,8% i 44,4% als dos controls i el tachelhit 40,0%
i 35,2%: 47 encerts contra 41 sobre 109, que cap dins del soroll i no decideix res.

Val la pena decidir-ho perque si es cert es una millora gratuita de TOT el projecte: l'orella es
el coll d'ampolla de la resta (el corpus, la taula norma-parla, el cercle). El `kab` de l'MMS te
molta mes materia d'entrenament que el `shi` (el cabilenc te un Common Voice gros), aixi que no
seria estrany.

Es prenen 300 talls de cada un dels dotze episodis que l'orella SI que entén -- als altres deu
els dos adaptadors donen ~0% i no distingeixen res -- o sigui ~3.600 talls, que donen una
precisio d'un punt i mig i tanquen la questio.
"""
import io, json, os, random, shutil, tarfile, sys
from pathlib import Path

for l in io.open(r"C:\Users\josep\app2\tachelhit-drills\backend\.env", encoding="utf-8",
                 errors="replace"):
    l = l.strip()
    if l.startswith("HF_TOKEN") and "=" in l:
        os.environ["HF_TOKEN"] = l.split("=", 1)[1].strip().strip('"').strip("'")
from huggingface_hub import hf_hub_download, list_repo_files  # noqa: E402

sys.path.insert(0, r"E:/tamazight/_magatzem")
from tria_el_millor_text import esquelet  # noqa: E402

REPO = "josepabloucr/tamazight-tv-privat"
PER_EPISODI = 300
#: els dotze que l'orella entén (acord >= 6,9% amb el text triat)
BONS = ["bueyrhjvjyaleocf", "rqmiijbrstbomglg", "yjmvageehekczjwy", "wckionryvrwatrvs",
        "wvvizytgxfihllta", "yxonwqxvkcohkuch", "asywmmpqztvnotxd", "jerkqzqplguvpzoh",
        "zhdemwoqhnulxwqv", "hbkjilqmyknmftva", "caxyzjdttlgivxih", "lkspqtudppaofqde"]
DESTI = Path(r"E:/tamazight/_magatzem/prova_kab")
TMP = Path(os.environ.get("TEMP", ".")) / "so_snrt"

tok = os.environ["HF_TOKEN"]
fitxers = list_repo_files(REPO, repo_type="dataset", token=tok)
if DESTI.exists():
    shutil.rmtree(DESTI)
(DESTI / "dades" / "talls").mkdir(parents=True)

index = []
rnd = random.Random(2011)
for pref in BONS:
    slug = next((f.split("/")[1] for f in fitxers if f"capitols/{pref}" in f), None)
    if not slug:
        print(f"{pref}: no hi es"); continue
    p = TMP / slug
    if not (p / "talls").exists():
        tar = hf_hub_download(REPO, f"capitols/{slug}/talls.tar", repo_type="dataset", token=tok)
        p.mkdir(parents=True, exist_ok=True)
        with tarfile.open(tar) as z:
            try:
                z.extractall(p, filter="data")
            except TypeError:
                z.extractall(p)
    llegit = json.load(io.open(f"E:/tamazight/_magatzem/rellegit_bo/{slug}.json",
                               encoding="utf-8"))["llegit"]
    amb_text = [k for k, v in llegit.items() if len(esquelet(v)) >= 6]
    posats = 0
    for k in rnd.sample(amb_text, min(PER_EPISODI, len(amb_text))):
        w = p / "talls" / f"{slug}_{int(k):04d}.wav"
        if not w.exists():
            continue
        nom = f"{slug[:16]}_{int(k):04d}.wav"
        shutil.copy(w, DESTI / "dades" / "talls" / nom)
        index.append({"id": f"{slug}:{k}", "fitxer": f"talls/{nom}"})
        posats += 1
    print(f"{pref}: {posats} talls")

json.dump(index, io.open(DESTI / "dades" / "index.json", "w", encoding="utf-8"),
          ensure_ascii=False)
mida = sum(f.stat().st_size for f in (DESTI / "dades" / "talls").glob("*.wav"))
print(f"\n{len(index)} talls, {mida/1e6:.0f} MB a {DESTI}")
