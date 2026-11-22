"""Inventari i esborrat de la carpeta `tachelhit/` de Cloudinary.

Context (comprovat el 20-11-2026 abans de tocar res):
  * la biblioteca **no apunta enlloc a Cloudinary**: 11.531 `audio_url`, 5.843 `audio_tts_url`,
    2.874 `audio_tts_shi_url`, 784 `image_url` i 204 `video_url` van tots a `/mitjans/` (R2);
  * la migracio del #577 esta registrada a `reescriptura_a_r2.csv` (21.036 files) i verificada
    sobre una mostra a l'atzar: **16 de 16 baixen de R2**;
  * Cloudinary esborra els fitxers el 5 de desembre de 2026 igualment.

ES IRREVERSIBLE. Per aixo aquest guio fa dues coses en dos passos, i la primera **sempre**:

    esborra_cloudinary.py inventari   -> escriu `cloudinary_inventari.jsonl` amb TOT el que hi ha
    esborra_cloudinary.py esborra     -> esborra, i nomes si l'inventari ja existeix

Si algun dia falta un fitxer, l'inventari diu exactament que hi havia i amb quina mida.
"""
import io
import json
import os
import sys
from pathlib import Path

AQUI = Path(r"E:/tamazight/_magatzem")
INVENTARI = AQUI / "cloudinary_inventari.jsonl"
PREFIX = "tachelhit/"
MENES = ["image", "video", "raw"]

for l in io.open(r"C:/Users/josep/app2/tachelhit-drills/backend/.env", encoding="utf-8",
                 errors="replace"):
    l = l.strip()
    if l.startswith("CLOUDINARY_") and "=" in l:
        k, v = l.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

import cloudinary  # noqa: E402
import cloudinary.api  # noqa: E402

cloudinary.config(cloud_name=os.environ["CLOUDINARY_CLOUD_NAME"],
                  api_key=os.environ["CLOUDINARY_API_KEY"],
                  api_secret=os.environ["CLOUDINARY_API_SECRET"])

ordre = sys.argv[1] if len(sys.argv) > 1 else "inventari"

if ordre == "inventari":
    n = 0
    bytes_tot = 0
    with io.open(INVENTARI, "w", encoding="utf-8", newline="\n") as f:
        for mena in MENES:
            cursor = None
            while True:
                r = cloudinary.api.resources(type="upload", resource_type=mena, prefix=PREFIX,
                                             max_results=500, next_cursor=cursor)
                for x in r.get("resources", []):
                    f.write(json.dumps({"public_id": x.get("public_id"), "mena": mena,
                                        "format": x.get("format"), "bytes": x.get("bytes"),
                                        "creat": x.get("created_at"),
                                        "url": x.get("secure_url")}, ensure_ascii=False) + "\n")
                    n += 1
                    bytes_tot += int(x.get("bytes") or 0)
                cursor = r.get("next_cursor")
                print(f"   {mena}: {n} acumulats", flush=True)
                if not cursor:
                    break
    print(f"\nINVENTARI: {n} fitxers, {bytes_tot/1e9:.2f} GB  ->  {INVENTARI}")

elif ordre == "esborra":
    if not INVENTARI.exists():
        raise SystemExit("primer l'inventari: esborra_cloudinary.py inventari")
    abans = sum(1 for _ in io.open(INVENTARI, encoding="utf-8"))
    print(f"l'inventari diu {abans} fitxers. Esborrant {PREFIX}…", flush=True)
    fets = 0
    for mena in MENES:
        while True:
            r = cloudinary.api.delete_resources_by_prefix(PREFIX, resource_type=mena)
            quants = len(r.get("deleted", {}))
            fets += quants
            print(f"   {mena}: {quants} en aquesta tanda ({fets} en total)", flush=True)
            if quants == 0 or not r.get("partial"):
                break
    print(f"\nESBORRATS {fets} fitxers de {abans} inventariats.")
else:
    raise SystemExit(__doc__)
