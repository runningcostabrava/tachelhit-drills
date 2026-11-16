# -*- coding: utf-8 -*-
r"""Repara els identificadors de TutlAit (16/17-11-2026). treu_dades.py reiniciava el comptador a cada
parquet, i el «train» en té tres: 1.375 identificadors sortien repetits (2.812 talls). El segon tall de
cada parella no tenia so propi (apuntava al so del primer) i les traduccions i els veredictes dels
auditors, que van per identificador, quedaven barrejats.

Què fa: torna a recórrer els parquets en el mateix ordre que treu_dades.py, calcula l'identificador
vell (comptador per fitxer) i el nou (comptador per split, el que ara fa treu_dades.py), i:
- reescriu metadades.jsonl amb els identificadors nous i el so de cada tall amb el seu nom nou
  (els talls que compartien identificador reben cadascun el seu so, tret del parquet);
- a traduccions.jsonl, veredictes.jsonl i veredictes_tercer.jsonl canvia l'identificador vell pel nou
  quan el vell era únic (i l'àrab coincideix); les files d'identificadors repetits es treuen, perquè
  no se sap de quin tall eren: la cadena les tornarà a traduir i a auditar;
- esborra pendents.json, canvis.json i resum.md perquè la cadena els refaci.
Res a producció. ÚS: repara_ids.py [<carpeta tutlait>] [<carpeta auditors>] [--de-debo]
(sense --de-debo només compta)"""
import glob, io, json, os, shutil, sys
import duckdb

args = [a for a in sys.argv[1:] if not a.startswith("--")]
DE_DEBO = "--de-debo" in sys.argv
CARPETA = args[0] if len(args) > 0 else r"C:\Users\josep\Veus-tachelhit\_paquets\tutlait"
AUDIT = args[1] if len(args) > 1 else r"C:\Users\josep\Veus-tachelhit\_escoltats\traduccions\auditors_tutlait"
CATALEG = r"C:\Users\josep\Veus-tachelhit\_escoltats\traduccions\auditors\cataleg_prod.json"
VARIETAT = {"atlas": ("tzm", "Atles Central (corpus TutlAit)"), "souss": ("shi", "Souss (corpus TutlAit)")}
AUDIO = os.path.join(CARPETA, "audio")

ja = set()
if os.path.exists(CATALEG):
    for x in json.load(io.open(CATALEG, encoding="utf-8")):
        if "tutlait" in (x.get("tag") or ""):
            ja.add(((x.get("text_arabic") or "").strip(), (x.get("speaker") or "").replace("TutlAit · ", "").strip()))

# 1. Recórrer els parquets: ident vell → ident nou, i les files noves de metadades.
con = duckdb.connect()
fitxers = sorted(glob.glob(os.path.join(CARPETA, "hf", "data", "*.parquet")))
files, vells = [], {}
comptador_split = {}
for f in fitxers:
    split = os.path.basename(f).split("-")[0]
    cur = con.execute("SELECT text, accent, speaker_id, gender, verified, duration, audio.path, audio.bytes FROM read_parquet(?)", [f])
    i = 0
    while True:
        lot = cur.fetchmany(200)
        if not lot:
            break
        for text, accent, spk, gen, ver, dur, path, so in lot:
            i += 1
            if accent not in VARIETAT:
                continue
            comptador_split[split] = comptador_split.get(split, 0) + 1
            vell = f"tl_{split}_{i:05d}_{spk}"
            nou = f"tl_{split}_{comptador_split[split]:05d}_{spk}"
            ext = os.path.splitext(path or "")[1].lower() or ".flac"
            var, reg = VARIETAT[accent]
            fila = {"id": nou, "split": split, "text_arabic": (text or "").strip(), "accent": accent, "variety": var,
                    "region": reg, "speaker": f"TutlAit · {spk}", "gender": gen, "verified": bool(ver),
                    "duration": round(float(dur or 0), 2), "audio": os.path.join(AUDIO, nou + ext), "path_original": path,
                    "ja_a_produccio": ((text or "").strip(), spk) in ja}
            files.append((vell, nou, ext, fila, so))
            vells.setdefault(vell, []).append(nou)

repetits = {v for v, ns in vells.items() if len(ns) > 1}
mapa = {v: ns[0] for v, ns in vells.items() if len(ns) == 1}  # vell únic → nou
arab_de = {fila["id"]: fila["text_arabic"] for _, _, _, fila, _ in files}
print(f"talls {len(files)}, identificadors vells {len(vells)}, repetits {len(repetits)} "
      f"({sum(len(vells[v]) for v in repetits)} talls), únics {len(mapa)}, canvien de nom {sum(1 for v, n in mapa.items() if v != n)}")
assert len({n for _, n, _, _, _ in files}) == len(files), "els identificadors nous no són únics"


def reescriu(p, ambdos=False):
    """Canvia l'id a cada línia d'un jsonl; treu les d'identificadors repetits o amb l'àrab que no casa."""
    if not os.path.exists(p):
        return
    fora, canviades, iguals, linies = 0, 0, 0, []
    for l in io.open(p, encoding="utf-8"):
        if not l.strip():
            continue
        x = json.loads(l)
        nou = mapa.get(x["id"])
        if nou is None:
            fora += 1
            continue
        if "text_arabic" in x and x["text_arabic"].strip() != arab_de[nou]:
            fora += 1
            continue
        if nou != x["id"]:
            canviades += 1
        else:
            iguals += 1
        x["id"] = nou
        linies.append(json.dumps(x, ensure_ascii=False))
    print(f"  {os.path.basename(p)}: queden {len(linies)} (iguals {iguals}, renombrades {canviades}), fora {fora}")
    if DE_DEBO:
        shutil.copy(p, p + ".abans")
        io.open(p, "w", encoding="utf-8").write("\n".join(linies) + ("\n" if linies else ""))


print("fitxers de la cadena:")
reescriu(os.path.join(CARPETA, "traduccions.jsonl"))
reescriu(os.path.join(AUDIT, "veredictes.jsonl"))
reescriu(os.path.join(AUDIT, "veredictes_tercer.jsonl"))

if not DE_DEBO:
    print("prova en sec: res tocat; afegeix --de-debo")
    sys.exit(0)

# 2. El so: renombra els únics, escriu els repetits des del parquet, treu els fitxers vells que sobrin.
shutil.copy(os.path.join(CARPETA, "metadades.jsonl"), os.path.join(CARPETA, "metadades.jsonl.abans"))
renombrats = escrits = 0
for vell, nou, ext, fila, so in files:
    desti = fila["audio"]
    if vell in repetits:
        io.open(desti, "wb").write(bytes(so))
        escrits += 1
    elif vell != nou:
        origen = os.path.join(AUDIO, vell + ext)
        if os.path.exists(origen) and not os.path.exists(desti):
            os.replace(origen, desti)
            renombrats += 1
        elif not os.path.exists(desti):
            io.open(desti, "wb").write(bytes(so))
            escrits += 1
noms_nous = {os.path.basename(fila["audio"]) for _, _, _, fila, _ in files}
sobrants = [f for f in os.listdir(AUDIO) if f not in noms_nous]
for f in sobrants:
    os.remove(os.path.join(AUDIO, f))
print(f"so: renombrats {renombrats}, escrits del parquet {escrits}, fitxers vells trets {len(sobrants)}, al disc {len(os.listdir(AUDIO))}")

# 3. metadades.jsonl nou.
with io.open(os.path.join(CARPETA, "metadades.jsonl"), "w", encoding="utf-8") as out:
    for _, _, _, fila, _ in files:
        out.write(json.dumps(fila, ensure_ascii=False) + "\n")
for nom in ("pendents.json", "canvis.json", "resum.md"):
    p = os.path.join(AUDIT, nom)
    if os.path.exists(p):
        os.remove(p)
for nom in ("import.jsonl",):
    p = os.path.join(CARPETA, nom)
    if os.path.exists(p):
        os.remove(p)
print("metadades.jsonl reescrit amb", len(files), "files; pendents/canvis/resum/import esborrats perquè la cadena els refaci")
