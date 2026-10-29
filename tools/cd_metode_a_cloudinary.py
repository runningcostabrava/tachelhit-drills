"""Puja a Cloudinary els talls del CD del Mètode que ha sentit una persona (#495, ADR 0007).

    python tools/cd_metode_a_cloudinary.py CARPETA_DE_LES_PISTES [--prova]

CARPETA_DE_LES_PISTES té les cinc pistes del CD com a `<pista>.wav` (els noms de
`backend/data/cd_metode.json` → `_pistes`). Per a cada línia de `capitols` que encara apunta a
`/method/cd/...` (la ruta que només sona en aquesta màquina), talla el tros amb ffmpeg, el puja a
`tachelhit/cd_metode/` i hi escriu l'adreça https al fitxer. `per_comprovar` no es toca: allò no ha
de sonar. Amb --prova no puja res i diu què faria.

Les claus de Cloudinary surten de backend/.env.
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "backend" / "data" / "cd_metode.json"


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    pistes, prova = Path(sys.argv[1]), "--prova" in sys.argv
    from dotenv import load_dotenv
    load_dotenv(ROOT / "backend" / ".env")
    import cloudinary
    import cloudinary.uploader
    cloudinary.config(cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
                      api_key=os.getenv("CLOUDINARY_API_KEY"),
                      api_secret=os.getenv("CLOUDINARY_API_SECRET"), secure=True)

    dades = json.loads(INDEX.read_text(encoding="utf-8"))
    fets = 0
    for slug, linies in (dades.get("capitols") or {}).items():
        for on, d in linies.items():
            if not str(d.get("url", "")).startswith("/method/cd/"):
                continue
            font = pistes / f"{d['pista']}.wav"
            if not font.exists():
                sys.exit(f"falta la pista {font}")
            nom = f"{d['pista']}_{d['start']:.2f}_{d['end']:.2f}".replace(".", "-")
            print(f"{slug}/{on}: {d['pista']} {d['start']}–{d['end']} → cd_metode/{nom}")
            if prova:
                continue
            with tempfile.TemporaryDirectory() as tmp:
                tall = Path(tmp) / f"{nom}.mp3"
                subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{d['start']:.3f}",
                                "-to", f"{d['end']:.3f}", "-i", str(font), "-codec:a", "libmp3lame",
                                "-b:a", "96k", str(tall)], check=True)
                r = cloudinary.uploader.upload(str(tall), folder="tachelhit/cd_metode", public_id=nom,
                                               resource_type="video", overwrite=True)
            d["url"] = r["secure_url"]
            fets += 1
    if fets:
        INDEX.write_text(json.dumps(dades, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"pujats {fets}")


if __name__ == "__main__":
    main()
