"""Que hi ha, de debo, als talls d'audio que va escoltar l'orella.

Descartat tot el que es podia descartar amb el text (index, temps, llengua, llargada), queda el
so mateix. L'orella no va escoltar els meus videos: va escoltar els talls que la fabrica va fer
i va desar al conjunt privat. Si aquells talls son silenci, musica o el moment equivocat, el
model treu text que no casa amb res -- que es exactament el que es veu.

Es baixa el `dades.tar` d'un episodi dolent i d'un bo i es mira que hi ha dins.
"""
import io, os, tarfile, tempfile
from pathlib import Path

for l in io.open(r"C:\Users\josep\app2\tachelhit-drills\backend\.env", encoding="utf-8",
                 errors="replace"):
    l = l.strip()
    if l.startswith("HF_TOKEN") and "=" in l:
        os.environ["HF_TOKEN"] = l.split("=", 1)[1].strip().strip('"').strip("'")

from huggingface_hub import hf_hub_download, list_repo_files  # noqa: E402

REPO = "josepabloucr/tamazight-tv-privat"
tok = os.environ["HF_TOKEN"]
fitxers = list_repo_files(REPO, repo_type="dataset", token=tok)
print(f"{len(fitxers)} fitxers al conjunt")
for pref in ("hmssyuzoyqzywbaj", "bueyrhjvjyaleocf"):
    meus = [f for f in fitxers if pref in f]
    print(f"\n{pref}: {len(meus)} fitxers")
    for f in meus[:12]:
        print("   ", f)
