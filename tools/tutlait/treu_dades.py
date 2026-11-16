# -*- coding: utf-8 -*-
r"""TutlAit v1 (Ma-OpenHub, CC BY 4.0): dels parquets baixats de HuggingFace en treu les metadades i el
so de cada tall. Només l'Atles («atlas» → tzm) i el Souss («souss» → shi); el Rif i Cabília queden
fora. Marca els talls que ja són a producció (mateix àrab i mateix parlant).
Entrada: <carpeta>\hf\data\*.parquet (snapshot_download). Sortida: <carpeta>\metadades.jsonl i
<carpeta>\audio\<id>.<ext>.
ÚS: treu_dades.py [<carpeta>] [<cataleg_prod.json>]"""
import glob, io, json, os, sys
import duckdb

CARPETA = sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\josep\Veus-tachelhit\_paquets\tutlait"
CATALEG = sys.argv[2] if len(sys.argv) > 2 else r"C:\Users\josep\Veus-tachelhit\_escoltats\traduccions\auditors\cataleg_prod.json"
VARIETAT = {"atlas": ("tzm", "Atles Central (corpus TutlAit)"), "souss": ("shi", "Souss (corpus TutlAit)")}

ja = set()
if os.path.exists(CATALEG):
    for x in json.load(io.open(CATALEG, encoding="utf-8")):
        if "tutlait" in (x.get("tag") or ""):
            ja.add(((x.get("text_arabic") or "").strip(), (x.get("speaker") or "").replace("TutlAit · ", "").strip()))
print("ja a producció:", len(ja))

os.makedirs(os.path.join(CARPETA, "audio"), exist_ok=True)
con = duckdb.connect()
fitxers = sorted(glob.glob(os.path.join(CARPETA, "hf", "data", "*.parquet")))
n = 0
comptes = {}
# El comptador és per split, no per fitxer: el «train» ve en tres parquets i amb un comptador per
# fitxer els identificadors es repetien (1.375 repetits el 16-11-2026; repara_ids.py ho va arreglar).
comptador = {}
with io.open(os.path.join(CARPETA, "metadades.jsonl"), "w", encoding="utf-8") as out:
    for f in fitxers:
        split = os.path.basename(f).split("-")[0]
        cur = con.execute("SELECT text, accent, speaker_id, gender, verified, duration, audio.path, audio.bytes FROM read_parquet(?)", [f])
        while True:
            files = cur.fetchmany(200)
            if not files:
                break
            for text, accent, spk, gen, ver, dur, path, so in files:
                comptes[accent] = comptes.get(accent, 0) + 1
                if accent not in VARIETAT:
                    continue
                comptador[split] = comptador.get(split, 0) + 1
                ext = os.path.splitext(path or "")[1].lower() or ".flac"
                ident = f"tl_{split}_{comptador[split]:05d}_{spk}"
                desti = os.path.join(CARPETA, "audio", ident + ext)
                if not os.path.exists(desti):
                    io.open(desti, "wb").write(bytes(so))
                var, reg = VARIETAT[accent]
                out.write(json.dumps({"id": ident, "split": split, "text_arabic": (text or "").strip(), "accent": accent, "variety": var,
                                      "region": reg, "speaker": f"TutlAit · {spk}", "gender": gen, "verified": bool(ver),
                                      "duration": round(float(dur or 0), 2), "audio": desti, "path_original": path,
                                      "ja_a_produccio": ((text or "").strip(), spk) in ja}, ensure_ascii=False) + "\n")
                n += 1
        print(f, comptador, "files", flush=True)
print("talls escrits", n, "accents", comptes)
