"""Puja els talls de la prova d'adaptadors i llança el quadern que els escolta amb sis orelles.

Les tres portes apreses a cops, totes tres respectades aqui:

1. **Crear o afegir versio es decideix MIRANT si el dataset hi es**, no pel text de l'error:
   demanar una versio d'un dataset que no existeix dona 403, no 404. I `dataset_list` public no
   ensenya els privats, per aixo es demana amb l'usuari.
2. **El titol del quadern ha de donar el mateix identificador** en fer-ne el pessic, o Kaggle en
   crea un altre i t'esperes davant d'un quadern que no corre.
3. **S'esborra la sortida d'abans i es comprova la marca** de l'execucio nova.

    puja_prova_adaptadors.py puja | llanca | estat | recull
"""
import io, json, os, shutil, sys, time
from pathlib import Path

AQUI = Path(r"E:\tamazight\_magatzem\prova_adaptadors")
NOM_DS = "snrt-prova-adaptadors"
NOM_KN = "snrt-adaptadors"
TITOL_KN = "SNRT adaptadors"

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

import kaggle  # noqa: E402

kaggle.api.authenticate()
U = os.environ["KAGGLE_USERNAME"]
ordre = sys.argv[1] if len(sys.argv) > 1 else "estat"

if ordre == "puja":
    #: el codi no ha de pujar dins del dataset: nomes el so i l'index
    dades = AQUI / "dades"
    dades.mkdir(exist_ok=True)
    if (AQUI / "talls").exists():
        if (dades / "talls").exists():
            shutil.rmtree(dades / "talls")
        shutil.move(str(AQUI / "talls"), str(dades / "talls"))
    if (AQUI / "index.json").exists():
        shutil.move(str(AQUI / "index.json"), str(dades / "index.json"))
    json.dump({"title": "SNRT prova adaptadors", "id": f"{U}/{NOM_DS}",
               "licenses": [{"name": "other"}]},
              io.open(dades / "dataset-metadata.json", "w", encoding="utf-8"), indent=1)
    ja = any(d.ref == f"{U}/{NOM_DS}" for d in kaggle.api.dataset_list(user=U, search=NOM_DS))
    print("ja existeix, hi afegeixo versio" if ja else "no existeix, el creo")
    if ja:
        kaggle.api.dataset_create_version(str(dades), "talls de 12 episodis", quiet=False,
                                          dir_mode="zip")
    else:
        kaggle.api.dataset_create_new(str(dades), public=False, quiet=False, dir_mode="zip")
    print(f"https://www.kaggle.com/datasets/{U}/{NOM_DS}")

elif ordre == "llanca":
    carp = AQUI / "quadern"
    carp.mkdir(exist_ok=True)
    codi = (AQUI / "sent_adaptadors.py").read_text(encoding="utf-8")
    marca = time.strftime("%Y%m%d-%H%M%S")
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
    print("marca d'aquesta execucio:", marca)

elif ordre == "estat":
    print(kaggle.api.kernels_status(f"{U}/{NOM_KN}"))

elif ordre == "recull":
    fora = AQUI / "sortida"
    if fora.exists():
        shutil.rmtree(fora)
    fora.mkdir()
    kaggle.api.kernels_output(f"{U}/{NOM_KN}", path=str(fora), force=True)
    r = json.load(io.open(fora / "resum.json", encoding="utf-8")) if (fora / "resum.json").exists() else {}
    esperada = (AQUI / "marca.txt").read_text(encoding="utf-8").strip() if (AQUI / "marca.txt").exists() else ""
    if esperada and r and r.get("run_id") != esperada:
        raise SystemExit(f"SORTIDA VELLA: diu {r.get('run_id')!r} i esperava {esperada!r}.")
    print("resum:", r)
    for p in sorted(fora.glob("sentit_*.jsonl")):
        print(f"  {p.name}: {sum(1 for _ in io.open(p, encoding='utf-8'))} linies")
else:
    raise SystemExit(__doc__)
