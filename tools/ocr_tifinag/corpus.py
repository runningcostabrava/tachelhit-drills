"""corpus.py — ajunta totes les transcripcions (vídeo 1 + els llegits amb llegeix.py) en
corpus_aslmdtv.json i escriu/reemplaça la secció «Lot del canal aslmdtv» d'INFORME.md
(taula per vídeo a partir de lot_estat.json). Ús: python -X utf8 corpus.py"""
import collections, glob, json, os

AQUI = os.path.dirname(os.path.abspath(__file__))
estat_p = os.path.join(AQUI, "lot_estat.json")
estat = json.load(open(estat_p, encoding="utf-8")) if os.path.exists(estat_p) else {}
llista = {v["id"]: v for v in json.load(open(os.path.join(AQUI, "lot_llista.json"), encoding="utf-8"))}
primers = {"ZlG8Bp_rwKc": ("ⵜⵓⵍⵍⵉⵙⵜ: ⴰⵎⵓⵛⵛ ⴰⴱⵕⴱⴰⵛ", "conte"),
           "MTDbi14_5cU": ("ⵜⵓⵍⵍⵉⵙⵜ ⵏ ⵜⵉⵔⴰⵔⵜ ⵏ ⵜⵉⵖⵉⵍⵜ", "conte"),
           "ihZ5sVr482o": ("ⴰⵎⵓⴷⴷⵓ ⵏ ⵟⴰⵕⵉⵇ", "lectura")}
corpus = []
fitxers = {"ZlG8Bp_rwKc": os.path.join(AQUI, "transcripcio.json")}
for p in glob.glob(os.path.join(AQUI, "transcripcio_*.json")):
    fitxers[os.path.basename(p)[len("transcripcio_"):-5]] = p
for vid, p in sorted(fitxers.items()):
    T = json.load(open(p, encoding="utf-8"))
    if vid in primers:
        titol, mena = primers[vid]
    else:
        titol, mena = llista.get(vid, {}).get("titol", ""), llista.get(vid, {}).get("mena", "")
    for r in T:
        lletres_r = sum(1 for ch in r["tifinag"] if "ⴰ" <= ch <= "⵿" and ch != "ⵯ")
        if lletres_r < 3 or (r["n_glifs"] - r.get("n_nous", 0)) < 0.6 * r["n_glifs"]:
            continue  # brossa (mateix filtre que llegeix.py; els primers lots no el tenien)
        corpus.append({"video": vid, "titol": titol, "mena": mena, "pagina": r["pagina"], "fila": r["fila"],
                       "de": r["de"], "a": r["a"], "tifinag": r["tifinag"], "llati": r["llati"],
                       "dubtes": r.get("dubtes", []) + (["□ = glif no reconegut"] if "□" in r["tifinag"] else []),
                       "n_glifs": r["n_glifs"], "n_nous": r.get("n_nous", 0), "fotograma": r["fotograma"]})
json.dump(corpus, open(os.path.join(AQUI, "corpus_aslmdtv.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
vids = sorted({c["video"] for c in corpus})
lletres = collections.Counter(ch for c in corpus for ch in c["tifinag"] if "ⴰ" <= ch <= "⵿")
paraules = sum(len(c["tifinag"].split()) for c in corpus)
amb_box = sum(1 for c in corpus if "□" in c["tifinag"])
print(f"corpus_aslmdtv.json: {len(corpus)} files de {len(vids)} vídeos, {paraules} paraules, "
      f"{sum(c['n_glifs'] for c in corpus)} glifs, {len(lletres)} lletres distintes, {amb_box} files amb algun □")

lin = ["| Vídeo | Mena | Mode | Pàg. | Glifs triats | % acceptats | Files finals | A ull (bé/total) | Lletres noves / rares | Temps |",
       "|---|---|---|---|---|---|---|---|---|---|"]
for vid, r in estat.items():
    if r.get("estat") != "fet":
        lin.append(f"| {vid} | {r.get('mena', '')} | - | - | - | - | - | - | {r.get('estat')} | {r.get('segons', '')} s |")
        continue
    rars = " ".join(f"{k}×{v}" for k, v in (r.get("rars") or {}).items())
    lin.append(f"| {vid} | {r.get('mena', '')} | {r.get('mode', '')} | {r.get('pagines', '')} | {r.get('glifs_triats', '')} | "
               f"{r.get('pct', '')} % | {r.get('files_finals', '')} | {r.get('a_ull', 'no mirat')} | {rars} {r.get('lletres_noves', '')} | {r.get('segons', '')} s |")
notes = [f"- {vid}: {r['a_ull_nota']}" for vid, r in estat.items() if r.get("a_ull_nota")]
sec = ("\n\n## Lot del canal aslmdtv (`lot.py`)\n\n"
       f"Corpus: `corpus_aslmdtv.json` amb **{len(corpus)} files** de **{len(vids)} vídeos** (els 3 primers inclosos), "
       f"{paraules} paraules, {sum(c['n_glifs'] for c in corpus)} glifs, {len(lletres)} lletres distintes "
       f"({' '.join(k for k, _ in lletres.most_common())}); {amb_box} files amb algun glif no reconegut (□).\n\n"
       + "\n".join(lin) + "\n\nNotes de la comprovació a ull (3 files per vídeo, llavor 1114):\n" + "\n".join(notes) + "\n")
inf = open(os.path.join(AQUI, "INFORME.md"), encoding="utf-8").read()
marca = "\n\n## Lot del canal aslmdtv"
if marca in inf:
    inf = inf[:inf.index(marca)]
open(os.path.join(AQUI, "INFORME.md"), "w", encoding="utf-8").write(inf + sec)
print("\n".join(lin))
