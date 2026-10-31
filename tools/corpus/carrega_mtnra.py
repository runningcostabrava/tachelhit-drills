"""El MTNRA a la biblioteca: 1.801 drills de taixelhit, en tres escriptures, amb la veu.

## Com es cataloga cada drill

  text_tachelhit         el tifinag del corpus (escrit per persones, no per maquina)
  text_tachelhit_latin   el llati del corpus, tal qual (amb ɣ ɛ ḥ...: no es plega)
  text_arabic            l'escriptura arab del corpus, tal qual
  variety / region       shi · «Souss (taixelhit, MTNRA)»
  speaker                «MTNRA · parlant no identificat pel corpus»: el corpus no en diu res,
                         i es diu en comptes de deixar-ho buit (buit vol dir «no ho hem mirat»)
  source_*               MTNRA, amb l'enllac al dataset
  tag                    mtnra, veu-que-llegeix, font externa
  text_catalan           buit: no tenim el significat i no s'inventa

L'audio es WAV de 48 kHz (634 MB); es passa a mp3 mono de 64 kbps, que es el que ja serveix la
biblioteca, i viatja en base64 dins de JSON de menys de 9 MB, com el Common Voice.
"""
import base64, io, json, os, subprocess

S = os.path.dirname(os.path.abspath(__file__))
F = json.load(io.open(os.path.join(S, "mtnra_talls", "mtnra.json"), encoding="utf-8"))
import pyarrow.parquet as pq
T = {r["id"]: r for r in pq.ParquetFile(os.path.join(S, "mtnra", "train-00000-of-00001.parquet"))
     .read(columns=["id", "text_tifinagh", "text_latin", "text_arabic"]).to_pylist()}
ON = os.path.join(S, "carrega_mtnra")
MP3 = os.path.join(ON, "mp3")
os.makedirs(MP3, exist_ok=True)
for f in os.listdir(ON):
    if f.endswith(".json"):
        os.remove(os.path.join(ON, f))

items, mida, n, buits = [], 0, 0, 0
for r in F:
    t = T[r["id"]]
    tif, lat, ar = (t["text_tifinagh"] or "").strip(), (t["text_latin"] or "").strip(), (t["text_arabic"] or "").strip()
    if not (tif or lat or ar):
        buits += 1
        continue
    mp3 = os.path.join(MP3, r["fitxer"][:-4] + ".mp3")
    if not os.path.exists(mp3):
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", os.path.join(S, "mtnra_talls", r["fitxer"]),
                        "-ac", "1", "-ar", "24000", "-b:a", "64k", mp3], check=True)
    b = open(mp3, "rb").read()
    cos = {"text_tachelhit": tif or None, "text_tachelhit_latin": lat or None, "text_arabic": ar or None,
           "variety": "shi", "region": "Souss (taixelhit, MTNRA)",
           "speaker": "MTNRA · parlant no identificat pel corpus", "source_channel": "MTNRA",
           "source_title": "MTNRA-Amazigh-IA/test_data · #%d" % r["id"],
           "source_url": "https://huggingface.co/datasets/MTNRA-Amazigh-IA/test_data",
           "tag": "mtnra, veu-que-llegeix, font externa"}
    items.append({"clau": "mtnra-%04d.mp3" % r["id"], "mp3": base64.b64encode(b).decode("ascii"),
                  "cos": {k: v for k, v in cos.items() if v is not None}})
    mida += len(items[-1]["mp3"])
    if mida > 8_500_000:
        json.dump(items, io.open(os.path.join(ON, "mt_%02d.json" % n), "w", encoding="utf-8"), ensure_ascii=False)
        n, items, mida = n + 1, [], 0
if items:
    json.dump(items, io.open(os.path.join(ON, "mt_%02d.json" % n), "w", encoding="utf-8"), ensure_ascii=False)
    n += 1
for f in sorted(os.listdir(ON)):
    if f.endswith(".json"):
        print("%s  %.1f MB" % (f, os.path.getsize(os.path.join(ON, f)) / 1e6))
print("fitxers: %d · drills: %d · sense cap text: %d" % (n, len(F) - buits, buits))
