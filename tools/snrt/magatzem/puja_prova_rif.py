"""Llanca l'orella de rifeny sobre el dataset de talls que ja hi es.

No puja cap dada nova: fa servir `snrt-prova-adaptadors`, els mateixos 639 talls (55 per
episodi, deu dolents i dos controls) que ja han passat per `shi`, `kab`, `taq` i `ara`. Mateix
so, mateixa regla, una orella mes.

El nom del quadern ha de ser diferent del d'un dataset meu: Kaggle dona 409 si xoquen.

    puja_prova_rif.py llanca | estat | recull
"""
import io
import json
import os
import shutil
import sys
import time
from pathlib import Path

AQUI = Path(r"E:\tamazight\_magatzem\prova_rif")
NOM_DS = "snrt-prova-adaptadors"
NOM_KN = "snrt-orella-rifenya"
TITOL_KN = "SNRT orella rifenya"

for cami in (r"C:\Users\josep\app2\tachelhit-drills\backend\.env",
             r"C:\Users\josep\app2\tachelhit-drills.worktrees\ios-prep\backend\.env"):
    p = Path(cami)
    if not p.exists():
        continue
    for l in io.open(p, encoding="utf-8", errors="replace"):
        l = l.strip()
        if l.startswith("KAGGLE_") and "=" in l:
            k, v = l.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

U = os.environ["KAGGLE_USERNAME"]
import kaggle  # noqa: E402

kaggle.api.authenticate()
ordre = sys.argv[1] if len(sys.argv) > 1 else "estat"

if ordre == "llanca":
    carp = AQUI / "quadern"
    carp.mkdir(parents=True, exist_ok=True)
    marca = time.strftime("%Y%m%d-%H%M%S")
    codi = (AQUI / "sent_rif.py").read_text(encoding="utf-8")
    (carp / f"{NOM_KN}.py").write_text(codi.replace('RUN_ID = ""', f'RUN_ID = "{marca}"'),
                                       encoding="utf-8")
    json.dump({"id": f"{U}/{NOM_KN}", "title": TITOL_KN, "code_file": f"{NOM_KN}.py",
               "language": "python", "kernel_type": "script", "is_private": True,
               "enable_gpu": True, "enable_internet": True,
               "dataset_sources": [f"{U}/{NOM_DS}"],
               "competition_sources": [], "kernel_sources": []},
              io.open(carp / "kernel-metadata.json", "w", encoding="utf-8"), indent=1)
    (AQUI / "marca.txt").write_text(marca, encoding="utf-8")
    print(kaggle.api.kernels_push(str(carp)))
    print("marca:", marca)

elif ordre == "estat":
    print(kaggle.api.kernels_status(f"{U}/{NOM_KN}"))

elif ordre == "recull":
    fora = AQUI / "sortida"
    if fora.exists():
        shutil.rmtree(fora)
    fora.mkdir()
    kaggle.api.kernels_output(f"{U}/{NOM_KN}", path=str(fora), force=True)
    r = json.load(io.open(fora / "resum.json", encoding="utf-8")) if (fora / "resum.json").exists() else {}
    esperada = (AQUI / "marca.txt").read_text(encoding="utf-8").strip()
    if r and r.get("run_id") != esperada:
        raise SystemExit(f"SORTIDA VELLA: diu {r.get('run_id')!r} i esperava {esperada!r}.")
    print("resum:", r)
    #: la sortida va a la carpeta de la prova d'adaptadors, perque la comparacio les llegeix totes
    p = fora / "sentit_rif.jsonl"
    if p.exists():
        d = Path(r"E:\tamazight\_magatzem\prova_adaptadors\sortida") / "sentit_rif.jsonl"
        shutil.copy(p, d)
        n = sum(1 for _ in io.open(p, encoding="utf-8"))
        print(f"{n} linies · copiat a {d}")
else:
    raise SystemExit(__doc__)
