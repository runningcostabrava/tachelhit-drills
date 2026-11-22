# -*- coding: utf-8 -*-
"""Baixa només els fitxers petits (.json i el registre) de la sortida d'un nucli de Kaggle, sense els pesos del model.
ÚS: baixa_sortides.py <usuari/nucli> <carpeta>"""
import io, os, sys

import requests
from kaggle.api.kaggle_api_extended import KaggleApi

ref, carpeta = sys.argv[1], sys.argv[2]
os.makedirs(carpeta, exist_ok=True)
api = KaggleApi()
api.authenticate()
usuari, nucli = ref.split("/")
res = api.kernel_output(usuari, nucli)
fitxers = getattr(res, "files", None) or (res.get("files") if isinstance(res, dict) else [])
log = getattr(res, "log", None) or (res.get("log") if isinstance(res, dict) else "")
if log:
    io.open(os.path.join(carpeta, "registre.txt"), "w", encoding="utf-8").write(log if isinstance(log, str) else str(log))
for f in fitxers:
    nom = getattr(f, "file_name", None) or f.get("fileName") or f.get("file_name")
    url = getattr(f, "url", None) or f.get("url")
    mida = getattr(f, "total_bytes", None) or f.get("totalBytes") or 0
    if not nom.endswith(".json") and not nom.endswith(".txt"):
        print("salto", nom, mida)
        continue
    r = requests.get(url, timeout=600)
    r.raise_for_status()
    open(os.path.join(carpeta, os.path.basename(nom)), "wb").write(r.content)
    print("baixat", nom, len(r.content))
