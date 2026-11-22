"""Prepara el conjunt per provar quin adaptador de l'MMS enten cada convidat.

Deu dels vint-i-dos convidats del programa son inaccessibles al model amb l'adaptador de
tachelhit, i ja s'ha descartat tot el que no era el model (l'ull, l'index, el temps, la llengua
del subtitol, la llargada, el so). Queda la hipotesi de la VARIETAT: son escriptors de llocs
diferents i cadascu parla la seva.

Es mostreja so dels episodis dolents i de dos bons de control, i es puja un sol conjunt per
passar-lo per diversos adaptadors. S'hi posa `ary` (arab marroqui) com a control: aixi la
hipotesi de l'arab es prova amb l'eina bona i no amb un esquelet fet per mi.

Nomes es mostregen replicas on l'ull te text, perque si no no hi ha res amb que comparar.
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
PER_EPISODI = 55
DOLENTS = ["hmssyuzoyqzywbaj", "oeeljuwkqlqtebzr", "nknrztnktbvaxnrs", "agnkrfivlpeuwzme",
           "jzawuozpghwwdanp", "tecepvdrorfpeapy", "kzckfzkejpvanodk", "lzvdtikcqbpplfks",
           "murpbmcssuwhrysy", "gunpjctjuowarcaq"]
CONTROLS = ["bueyrhjvjyaleocf", "rqmiijbrstbomglg"]
DESTI = Path(r"E:/tamazight/_magatzem/prova_adaptadors")
TMP = Path(os.environ.get("TEMP", ".")) / "so_snrt"

tok = os.environ["HF_TOKEN"]
fitxers = list_repo_files(REPO, repo_type="dataset", token=tok)
if DESTI.exists():
    shutil.rmtree(DESTI)
(DESTI / "talls").mkdir(parents=True)

index, resum = [], []
rnd = random.Random(2011)
for pref in DOLENTS + CONTROLS:
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
    tria = rnd.sample(amb_text, min(PER_EPISODI, len(amb_text)))
    posats = 0
    for k in tria:
        w = p / "talls" / f"{slug}_{int(k):04d}.wav"
        if not w.exists():
            continue
        nom = f"{slug[:16]}_{int(k):04d}.wav"
        shutil.copy(w, DESTI / "talls" / nom)
        index.append({"id": f"{slug}:{k}", "fitxer": f"talls/{nom}"})
        posats += 1
    resum.append((pref, posats, len(amb_text)))
    print(f"{pref}: {posats} talls de {len(amb_text)} amb text")

json.dump(index, io.open(DESTI / "index.json", "w", encoding="utf-8"), ensure_ascii=False)
mida = sum(f.stat().st_size for f in (DESTI / "talls").glob("*.wav"))
print(f"\n{len(index)} talls, {mida/1e6:.0f} MB a {DESTI}")
