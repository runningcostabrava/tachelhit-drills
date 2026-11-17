# -*- coding: utf-8 -*-
"""La nit: encadena 02 → 05 per a una llista de carpetes de vídeo, i continua on era.

  python nit.py <carpeta> [<carpeta> ...] [--refes] [--credits A,B] [--fils 6] [--arrel DIR]

Per a cada carpeta corre, en ordre, 02_llegeix, 03_talla, 04_tradueix i 05_informe amb el mateix intèrpret;
una etapa que `estat.json` ja dona per feta es salta (amb `--refes` es torna a fer; cada etapa, a més, reprèn
per dins). Si una etapa falla, s'apunta a `nit.log` i es passa a la carpeta següent. `--arrel DIR` agafa totes
les subcarpetes de DIR que tinguin un vídeo. A l'ECS: `tmux new -s nit` i deixar-ho córrer.
"""
import argparse
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comu  # noqa: E402

ETAPES = ["02_llegeix", "03_talla", "04_tradueix", "05_informe"]


def te_video(c):
    return os.path.isdir(c) and any(f.lower().endswith((".mp4", ".mkv", ".webm")) for f in os.listdir(c))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("carpetes", nargs="*")
    ap.add_argument("--arrel", default=None)
    ap.add_argument("--refes", action="store_true")
    ap.add_argument("--credits", default=None)
    ap.add_argument("--fils", type=int, default=6)
    a = ap.parse_args()
    carpetes = [os.path.abspath(c) for c in a.carpetes]
    if a.arrel:
        carpetes += sorted(os.path.join(a.arrel, d) for d in os.listdir(a.arrel) if te_video(os.path.join(a.arrel, d)))
    if not carpetes:
        sys.exit("cap carpeta")
    log = open(os.path.join(a.arrel or os.path.dirname(carpetes[0]), "nit.log"), "a", encoding="utf-8")
    comu.diu(log, f"==== nit {time.strftime('%Y-%m-%d %H:%M')} {len(carpetes)} carpetes")
    for c in carpetes:
        if not te_video(c):
            comu.diu(log, f"-- {c}: sense vídeo, salto"); continue
        comu.diu(log, f"-- {os.path.basename(c)}")
        for etapa in ETAPES:
            if not a.refes and comu.etapa_feta(c, etapa):
                comu.diu(log, f"   {etapa}: ja feta"); continue
            cmd = [comu.PY, "-X", "utf8", os.path.join(comu.AQUI, etapa + ".py"), c]
            if etapa == "02_llegeix":
                cmd += ["--fils", str(a.fils)]
            if etapa == "03_talla" and a.credits:
                cmd += ["--credits", a.credits]
            t0 = time.time()
            r = subprocess.run(cmd)
            comu.diu(log, f"   {etapa}: {'bé' if r.returncode == 0 else 'ERROR ' + str(r.returncode)} en {time.time() - t0:.0f} s")
            if r.returncode != 0:
                break
    comu.diu(log, f"==== nit acabada {time.strftime('%Y-%m-%d %H:%M')}")


if __name__ == "__main__":
    main()
