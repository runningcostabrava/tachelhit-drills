"""Del grau A a un corpus que es pugui entrenar. És el que el cercle necessitava i no tenia.

El cercle entrenava amb talls triats pel subtítol, donant-lo per bo. Aquí la tria la fa l'ACORD
entre dues lectures independents —l'ull (OCR del tifinag cremat) i l'orella (el nostre ASR)—,
que no saben res l'una de l'altra. Coincidir en l'esquelet consonàntic d'una frase sencera per
casualitat és molt difícil.

Quin text es posa d'etiqueta: **el de l'ull**, el de la pantalla. Raó: va en la norma de
l'IRCAM, i un dels objectius és un transcriptor que escrigui en norma sentint parla dialectal.
L'orella serveix per CONFIRMAR que allò és el que sona, no per dictar com s'escriu.

El que NO entra, i per què:
  - res dels conjunts congelats de prova (es comprova pel capítol, no pel text);
  - res de grau B, C ni D: el B és material per a la taula estàndard ↔ dialecte, no per entrenar;
  - talls de menys de 0,8 s o de més de 14 s, com la recepta de sempre.

Surt `corpus_grau_a.jsonl` (una línia per tall) i un recompte per capítol. No puja res enlloc.
"""
import io
import json
import wave
from collections import Counter
from pathlib import Path

MAG = Path(r"E:\tamazight\_magatzem")
SO = Path(r"E:\tamazight\_sentit\dades_tots")
ACORD = MAG / "acord_26.jsonl"
DESTI = MAG / "corpus_grau_a.jsonl"
DURADA_MIN, DURADA_MAX = 0.8, 14.0

if not ACORD.exists():
    raise SystemExit(f"encara no hi ha {ACORD}: passa primer acord_26.py")

#: l'índex diu quin fitxer de so és cada `<slug>:<k>`
index = {x["id"]: x["fitxer"] for x in json.load(io.open(SO / "index.json", encoding="utf-8"))}

files, fora = [], Counter()
for l in io.open(ACORD, encoding="utf-8"):
    if not l.strip():
        continue
    r = json.loads(l)
    if r.get("grau") != "A":
        fora["no és grau A"] += 1
        continue
    rel = index.get(r["id"])
    if not rel:
        fora["sense fitxer de so"] += 1
        continue
    cami = SO / rel
    if not cami.exists():
        fora["el fitxer no hi és"] += 1
        continue
    try:
        with wave.open(str(cami)) as w:
            segons = w.getnframes() / float(w.getframerate() or 16000)
            canals, hz = w.getnchannels(), w.getframerate()
    except Exception:
        fora["el so no s'obre"] += 1
        continue
    if not (DURADA_MIN <= segons <= DURADA_MAX):
        fora["durada fora de marge"] += 1
        continue
    if hz != 16000 or canals != 1:
        fora["no és 16 kHz mono"] += 1
        continue
    files.append({"id": r["id"], "capitol": r["capitol"], "fitxer": rel,
                  "text": r["tifinag"], "sentit": r["sentit"], "cer_acord": r["cer"],
                  "conf": r.get("conf"), "catala": r.get("catala"),
                  "segons": round(segons, 2),
                  "font": "SNRT Tamazight TV · recerca, no republicar"})

with io.open(DESTI, "w", encoding="utf-8", newline="\n") as f:
    for x in files:
        f.write(json.dumps(x, ensure_ascii=False) + "\n")

hores = sum(x["segons"] for x in files) / 3600
print(f"corpus de grau A: {len(files)} talls · {hores:.2f} hores")
print(f"desat a {DESTI}\n")
print("descartats:")
for k, n in fora.most_common():
    print(f"   {k:24s} {n}")
print("\nper capítol:")
c = Counter(x["capitol"] for x in files)
for cap, n in c.most_common(10):
    print(f"   {cap[:20]}… {n}")
print(f"\ncapítols amb material: {len(c)}")
amb_cat = sum(1 for x in files if x.get("catala"))
print(f"talls amb significat (català de l'àrab): {amb_cat}")
