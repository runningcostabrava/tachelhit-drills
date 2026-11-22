"""Puja la ronda i llança el nucli d'entrenament del cercle (#601).

El nucli és `tools/lm/kaggle/transcriptor_snrt.py` de la branca `feat/601-cercle-virtuos`, tal
com és: no se'n toca ni la recepta ni la mesura. L'únic que canvia és **d'on surt el train**.

  - Abans: el nucli triava ell mateix les rèpliques amb el seu filtre de CER sobre text RIC
    (amb vocals) contra un subtítol que no les escriu. El 17-11 es va mesurar que passava el
    0,9 % dels talls i el train quedava buit; per això el filtre va quedar apagat i el train
    entrava sencer, bo i dolent barrejat.
  - Ara: el train ve TRIAT de fora, amb la regla de l'esquelet de consonants (grau A), que és
    l'arranjament d'aquell biaix. 1.678 talls de train, 171 de dev.

La mesura és la del nucli, sense tocar-la: cinc proves «abans -> després» amb els mateixos talls
i la mateixa regla, i els quatre capítols retinguts hi entren sencers com a `snrt-retingut`.

Recepta B (SNRT + les dades d'H4b): les d'H4b hi són perquè el model no oblidi el que ja sabia,
que és el que protegeix `tfa-226` i `zouhir-tests` de l'exigència que cap prova no empitjori.

    puja_ronda.py puja | llanca | estat | recull
"""
import io
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

#: `RONDA` tria el braç: el de 0,35 (per defecte, que ja ha corregut) o `ronda_020`. El dataset i
#: el quadern porten noms diferents perquè els dos resultats han de poder conviure: comparar-los
#: és tot el sentit d'aquesta ronda.
AQUI = Path(os.getenv("RONDA", r"E:\tamazight\_magatzem\ronda"))
SUFIX = "" if AQUI.name == "ronda" else "-" + AQUI.name.replace("_", "-")
REPO = Path(r"C:\Users\josep\app2\tachelhit-drills")
COMMIT = "c2044c4"
NUCLI_AL_REPO = "tools/lm/kaggle/transcriptor_snrt.py"
NOM_DS = "snrt-ronda-grau-a" + SUFIX
NOM_KN = "snrt-ronda-mesura" + SUFIX
TITOL_KN = "SNRT ronda mesura" + SUFIX
DATASETS_NUCLI = ["josepabloucr/adaptador-shi-zouhir-b", "josepabloucr/tfa-veritat-h3",
                  "josepabloucr/corpus-v4-amb-cv-zgh", "josepabloucr/cv-zgh-test-256",
                  "josepabloucr/zouhir-veritat"]

for cami in (REPO / "backend" / ".env",
             Path(r"C:\Users\josep\app2\tachelhit-drills.worktrees\ios-prep\backend\.env")):
    if not cami.exists():
        continue
    for l in io.open(cami, encoding="utf-8", errors="replace"):
        l = l.strip()
        if l.startswith("KAGGLE_") and "=" in l:
            k, v = l.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

import kaggle  # noqa: E402

kaggle.api.authenticate()
U = os.environ["KAGGLE_USERNAME"]
ordre = sys.argv[1] if len(sys.argv) > 1 else "estat"

if ordre == "puja":
    dades = AQUI / "dades"
    json.dump({"title": "SNRT ronda grau A" + SUFIX, "id": f"{U}/{NOM_DS}",
               "licenses": [{"name": "other"}]},
              io.open(dades / "dataset-metadata.json", "w", encoding="utf-8"), indent=1)
    ja = any(d.ref == f"{U}/{NOM_DS}" for d in kaggle.api.dataset_list(user=U, search=NOM_DS))
    print("ja existeix, hi afegeixo versio" if ja else "no existeix, el creo")
    if ja:
        kaggle.api.dataset_create_version(str(dades), "ronda de grau A", quiet=False,
                                          dir_mode="zip")
    else:
        kaggle.api.dataset_create_new(str(dades), public=False, quiet=False, dir_mode="zip")
    print(f"https://www.kaggle.com/datasets/{U}/{NOM_DS}")

elif ordre == "llanca":
    carp = AQUI / "quadern"
    carp.mkdir(exist_ok=True)
    #: el nucli es treu del commit, no d'una copia a ma: aixi es sap quin codi ha corregut
    codi = subprocess.run(["git", "show", f"{COMMIT}:{NUCLI_AL_REPO}"], cwd=str(REPO),
                          capture_output=True, text=True, encoding="utf-8").stdout
    assert "RECEPTA" in codi, "no he pogut treure el nucli del commit"
    marca = time.strftime("%Y%m%d-%H%M%S")
    codi = codi.replace('RECEPTA = "A"', 'RECEPTA = "B"').replace('RUN_ID = ""',
                                                                  f'RUN_ID = "{marca}"')
    (carp / f"{NOM_KN}.py").write_text(codi, encoding="utf-8")
    json.dump({"id": f"{U}/{NOM_KN}", "title": TITOL_KN, "code_file": f"{NOM_KN}.py",
               "language": "python", "kernel_type": "script", "is_private": True,
               "enable_gpu": True, "enable_internet": True,
               "dataset_sources": [f"{U}/{NOM_DS}"] + DATASETS_NUCLI,
               "competition_sources": [], "kernel_sources": []},
              io.open(carp / "kernel-metadata.json", "w", encoding="utf-8"), indent=1)
    (AQUI / "marca.txt").write_text(marca, encoding="utf-8")
    print(kaggle.api.kernels_push(str(carp)))
    print("marca d'aquesta execucio:", marca)

elif ordre == "estat":
    print(kaggle.api.kernels_status(f"{U}/{NOM_KN}"))

elif ordre == "recull":
    fora = AQUI / "sortida"
    if fora.exists():
        shutil.rmtree(fora)
    fora.mkdir()
    kaggle.api.kernels_output(f"{U}/{NOM_KN}", path=str(fora), force=True)
    #: la marca de debo es la del CODI que ha corregut, no la del meu fitxer local: cada intent
    #: de llançament l'escriu, i aquesta nit n'hi va haver que van fallar DESPRES del que va
    #: entrar, de manera que el fitxer local rebutjaria un resultat bo dient-li vell.
    esperada = (AQUI / "marca.txt").read_text(encoding="utf-8").strip()
    tira = AQUI / "codi_que_ha_corregut"
    try:
        if tira.exists():
            shutil.rmtree(tira)
        tira.mkdir()
        kaggle.api.kernels_pull(f"{U}/{NOM_KN}", path=str(tira), metadata=False)
        for p in tira.glob("*.py"):
            for l in io.open(p, encoding="utf-8", errors="replace"):
                if l.startswith("RUN_ID = "):
                    del_codi = l.split("=", 1)[1].strip().strip('"').strip("'")
                    if del_codi and del_codi != esperada:
                        print(f"la marca del codi que ha corregut es {del_codi!r} i la del meu "
                              f"fitxer {esperada!r}: val la del codi")
                        esperada = del_codi
                    break
    except Exception as e:
        print(f"no he pogut llegir el codi que ha corregut ({type(e).__name__}): "
              f"em quedo amb la marca local")
    for p in sorted(fora.glob("*.json")):
        try:
            r = json.load(io.open(p, encoding="utf-8"))
        except Exception:
            continue
        if isinstance(r, dict) and "run_id" in r:
            if r["run_id"] != esperada:
                raise SystemExit(f"SORTIDA VELLA a {p.name}: diu {r['run_id']!r} "
                                 f"i esperava {esperada!r}.")
            print(f"{p.name}: marca correcta")
    for p in sorted(fora.iterdir()):
        print(f"  {p.name}  {p.stat().st_size/1e6:.1f} MB")
else:
    raise SystemExit(__doc__)
