# -*- coding: utf-8 -*-
"""Puja els capítols de Tamazight TV (SNRT) al visor PRIVAT d'administradors (docs/adr/0012).

Només text i temps (tifinag, àrab, català de màquina). No puja so ni vídeo. Cal un compte d'ADMINISTRADOR: el token surt del
navegador (localStorage `user_token`) i es passa per l'entorn, mai per la línia d'ordres ni pel xat:

    set VISOR_TOKEN=...            (PowerShell: $env:VISOR_TOKEN="...")
    python tools/snrt/puja_al_visor_privat.py <carpeta_amb_capitols> --api https://<l'api> [--nomes slug1,slug2] [--prova]

`<carpeta_amb_capitols>` conté una carpeta per capítol amb `subtitols.jsonl`, `estat.json` i, si hi és, `video.json`
(el que baixa la còpia privada d'HF o `~/tamazight_tv` de l'ECS). `--prova` només compta, no puja res.
"""
import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request


def carrega(carpeta):
    est = json.load(open(os.path.join(carpeta, "estat.json"), encoding="utf-8"))
    vid = {}
    p = os.path.join(carpeta, "video.json")
    if os.path.exists(p):
        vid = json.load(open(p, encoding="utf-8"))
    linies = []
    for n, l in enumerate(x for x in open(os.path.join(carpeta, "subtitols.jsonl"), encoding="utf-8") if x.strip()):
        r = json.loads(l)
        if r.get("t_ini") is None or r.get("t_fi") is None or not (r.get("tifinag") or r.get("arab")):
            continue
        linies.append({"k": r.get("k", n), "t_ini": r["t_ini"], "t_fi": r["t_fi"], "tifinag": r.get("tifinag"),
                       "arab": r.get("arab"), "catala": r.get("catala") or None, "catala_estat": r.get("catala_estat")})
    url = vid.get("url_pagina")
    yt = None
    m = re.search(r"(?:youtu\.be/|v=)([\w-]{11})", url or "")
    if m:
        yt = m.group(1)
    return {"titol": est.get("titol") or os.path.basename(carpeta), "url_pagina": url, "video_youtube": yt,
            "durada": est.get("durada"), "linies": linies}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("carpeta")
    ap.add_argument("--api", required=True)
    ap.add_argument("--nomes")
    ap.add_argument("--prova", action="store_true")
    a = ap.parse_args()
    token = os.environ.get("VISOR_TOKEN", "")
    if not token and not a.prova:
        sys.exit("Falta VISOR_TOKEN (el token d'un administrador) a l'entorn.")
    triats = set((a.nomes or "").split(",")) - {""}
    tot = 0
    for slug in sorted(os.listdir(a.carpeta)):
        c = os.path.join(a.carpeta, slug)
        if not os.path.exists(os.path.join(c, "subtitols.jsonl")) or (triats and slug not in triats):
            continue
        d = carrega(c)
        if not d["linies"]:
            continue
        ca = sum(1 for l in d["linies"] if l["catala"])
        print(f"{slug[:12]}… {d['titol']}: {len(d['linies'])} línies, {ca} amb català", flush=True)
        tot += len(d["linies"])
        if a.prova:
            continue
        req = urllib.request.Request(f"{a.api.rstrip('/')}/snrt-privat/{slug}/importa", data=json.dumps(d).encode("utf-8"),
                                     headers={"Content-Type": "application/json", "X-User-Token": token}, method="POST")
        try:
            urllib.request.urlopen(req, timeout=120).read()
        except urllib.error.HTTPError as e:
            sys.exit(f"{slug}: HTTP {e.code} {e.read()[:200]!r}")
    print("total línies:", tot, "(prova: no s'ha pujat res)" if a.prova else "pujades")


if __name__ == "__main__":
    main()
