# -*- coding: utf-8 -*-
r"""Comprova que el so de cada tall de TutlAit al disc és el del parquet (byte a byte), i el torna a
escriure si falta o no coincideix. Serveix després de repara_ids.py (els canvis de nom en cadena poden
deixar un tall sense so o amb el so d'un altre) i sempre abans de carregar.
ÚS: comprova_so.py [<carpeta tutlait>] [--arregla]   (sense --arregla només compta)"""
import glob, hashlib, io, json, os, sys
import duckdb

args = [a for a in sys.argv[1:] if not a.startswith("--")]
ARREGLA = "--arregla" in sys.argv
CARPETA = args[0] if args else r"C:\Users\josep\Veus-tachelhit\_paquets\tutlait"
VARIETAT = {"atlas", "souss"}

meta = {}
for l in io.open(os.path.join(CARPETA, "metadades.jsonl"), encoding="utf-8"):
    if l.strip():
        x = json.loads(l)
        meta[x["id"]] = x

con = duckdb.connect()
comptador, be, falten, diferents, sense_fila = {}, 0, 0, 0, 0
for f in sorted(glob.glob(os.path.join(CARPETA, "hf", "data", "*.parquet"))):
    split = os.path.basename(f).split("-")[0]
    cur = con.execute("SELECT text, accent, speaker_id, audio.path, audio.bytes FROM read_parquet(?)", [f])
    while True:
        lot = cur.fetchmany(200)
        if not lot:
            break
        for text, accent, spk, path, so in lot:
            if accent not in VARIETAT:
                continue
            comptador[split] = comptador.get(split, 0) + 1
            ident = f"tl_{split}_{comptador[split]:05d}_{spk}"
            m = meta.get(ident)
            if not m or m["text_arabic"] != (text or "").strip():
                sense_fila += 1
                continue
            so = bytes(so)
            p = m["audio"]
            if not os.path.exists(p):
                falten += 1
            elif hashlib.md5(io.open(p, "rb").read()).digest() != hashlib.md5(so).digest():
                diferents += 1
            else:
                be += 1
                continue
            if ARREGLA:
                io.open(p, "wb").write(so)
print(f"talls {sum(comptador.values())}: bé {be}, faltaven {falten}, diferents {diferents}, sense fila a metadades {sense_fila}"
      + (" → tots escrits del parquet" if ARREGLA and (falten or diferents) else ("" if ARREGLA else " (prova en sec; --arregla per escriure)")))
sys.exit(1 if sense_fila else 0)
