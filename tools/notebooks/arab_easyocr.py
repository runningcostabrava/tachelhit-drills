"""L'àrab cremat del vídeo d'en Baba Ali, llegit sencer amb l'EasyOCR

A la comparació de models d'àrab, l'**EasyOCR** va ser l'únic que treia frases llegibles
(«فقد تأذرت حثيرا شات الفأس», «الذهب والفضة والثو يتابر الناس») mentre el Tesseract treia soroll
amb forma de lletra. Aquí es passa per **tot** el vídeo, un fotograma per segon, en color i al
doble de mida — no la imatge binaritzada que es menjava els traços fins.

## Per què la mesura d'aquest quadern sí que val

La vegada anterior la constància va sortir 0,000 a tots els models per una raó vergonyosa:
havia mostrejat un fotograma cada vuit segons i després mesurava la coincidència entre segons
*consecutius*, que al mostreig no existien. Aquí hi ha **tots** els segons, i per tant:

- dos segons seguits amb el mateix subtítol han de donar el mateix text: **constància**;
- un subtítol és una tirada de segons seguits que diuen prou el mateix, i la seva lectura és
  **la del mig** (la que menys contradiuen les altres) — amb l'acord com a mesura de confiança.

Res d'això diu que el text sigui *correcte*: diu que és *estable*. Per saber si és correcte cal
una persona que llegeixi àrab, i aquest fitxer li deixa la feina ordenada: primer els segurs.

## Com surt el vídeo

El quadern se'l baixa ell mateix amb `yt-dlp` (Colab té accés a YouTube). Si el client normal
diu que el vídeo no està disponible —passa amb vídeos públics perfectament sans—, es reintenta
amb el client d'Android abans de donar-lo per mort.

El resultat puja al dataset de HuggingFace si hi ha `HF_TOKEN`; si no, es queda al disc del
Colab i s'imprimeix el resum, que és el mínim per no perdre-ho tot si la sessió cau.
"""

# %%
VIDEO_ID = "ihwiZk1WmJM"
#: Amb 0 es llegeixen tots els segons. Un número petit serveix per veure que la canonada va.
QUANTS = 0
#: On cau el subtítol: del 80% al 97% de l'alçada del fotograma, i dins d'aquesta franja, del
#: 33% al 80%. Mesurat al vídeo de 1080p.
FRANJA = (0.80, 0.97)
RATLLA = (0.33, 0.80)

# %%
import subprocess
import sys

subprocess.run([sys.executable, "-m", "pip", "install", "-q", "easyocr", "yt-dlp",
                "huggingface_hub"], check=False)
print("instal·lat")

# %%
import json
import os
import shutil

VIDEO = "/content/video.mp4"
BANDES = "/content/bandes"
FORA = "/content/arab_easyocr.jsonl"


def secret(nom):
    if os.environ.get(nom):
        return os.environ[nom]
    try:
        from google.colab import userdata
        return userdata.get(nom)
    except Exception:
        return None


HF_TOKEN = secret("HF_TOKEN")
print("token de HuggingFace:", "sí" if HF_TOKEN else "no (els resultats es quedaran aquí)")


def baixa_video():
    if os.path.exists(VIDEO) and os.path.getsize(VIDEO) > 10_000_000:
        return True
    url = "https://www.youtube.com/watch?v=" + VIDEO_ID
    # Només imatge i a 1080p: l'àudio no cal per llegir subtítols.
    for extra in ([], ["--extractor-args", "youtube:player_client=android"]):
        r = subprocess.run([sys.executable, "-m", "yt_dlp", "-f", "137/248/bestvideo[height<=1080]",
                            "--no-playlist", "--quiet", "--no-warnings", "-o", VIDEO, *extra, url],
                           capture_output=True, text=True)
        if os.path.exists(VIDEO) and os.path.getsize(VIDEO) > 10_000_000:
            print("vídeo baixat%s: %d MB" % (" (client android)" if extra else "",
                                            os.path.getsize(VIDEO) // 1_000_000))
            return True
        print("no ha baixat%s: %s" % (" (client android)" if extra else "", (r.stderr or "")[-200:]))
    return False


if not baixa_video():
    raise SystemExit("sense vídeo no hi ha res a llegir")

# %%
w, h = [int(x) for x in subprocess.run(
    ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
     "-of", "csv=p=0", VIDEO], capture_output=True, text=True).stdout.strip().split(",")[:2]]
dalt = int(h * FRANJA[0]) // 2 * 2
alt = int(h * (FRANJA[1] - FRANJA[0])) // 2 * 2
# I dins de la franja, només la ratlla: la resta és pel·lícula, que es mou tant com el text.
r_dalt = int(alt * RATLLA[0]) // 2 * 2
r_alt = int(alt * (RATLLA[1] - RATLLA[0])) // 2 * 2
print("vídeo %dx%d → ratlla del subtítol %dx%d a y=%d" % (w, h, w, r_alt, dalt + r_dalt))

if not os.path.isdir(BANDES) or len(os.listdir(BANDES)) < 100:
    shutil.rmtree(BANDES, ignore_errors=True)
    os.makedirs(BANDES)
    # Un fotograma per segon, retallat a la ratlla, al doble de mida, en color.
    r = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", VIDEO,
                        "-vf", "fps=1,crop=%d:%d:0:%d,scale=%d:%d" % (w, r_alt, dalt + r_dalt, w * 2, r_alt * 2),
                        "-frame_pts", "true", "-q:v", "3", os.path.join(BANDES, "%06d.jpg")],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit("ffmpeg: " + (r.stderr or "")[:300])
fotogrames = sorted(f for f in os.listdir(BANDES) if f.endswith(".jpg"))
if QUANTS:
    fotogrames = fotogrames[:QUANTS]
print("fotogrames (un per segon):", len(fotogrames))

# %%
import numpy as np
from PIL import Image
import easyocr

lector = easyocr.Reader(["ar"], gpu=True)
print("EasyOCR carregat")


def nomes_arab(t):
    return " ".join("".join(c for c in (t or "") if "؀" <= c <= "ۿ" or c == " ").split())


def distancia(a, b):
    if a == b:
        return 0
    if not a or not b:
        return max(len(a), len(b))
    ant = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        act = [i]
        for j, cb in enumerate(b, 1):
            act.append(min(ant[j] + 1, act[j - 1] + 1, ant[j - 1] + (ca != cb)))
        ant = act
    return ant[-1]


def prop(a, b):
    if not a or not b:
        return 0.0
    return 1 - distancia(a, b) / max(len(a), len(b))


def puja(cami):
    """Que no visqui només al disc del Colab, que mor amb la sessió."""
    if not HF_TOKEN:
        return
    try:
        from huggingface_hub import HfApi
        HfApi().upload_file(path_or_fileobj=cami, path_in_repo=os.path.basename(cami),
                            repo_id="josepabloucr/tamazight-corpus", repo_type="dataset",
                            token=HF_TOKEN)
        print("   (pujat)", flush=True)
    except Exception as e:
        print("   (no s'ha pogut pujar: %s)" % str(e)[:80], flush=True)


fets = {}
if os.path.exists(FORA):
    for l in open(FORA, encoding="utf-8"):
        try:
            d = json.loads(l)
            fets[d["segon"]] = d["text"]
        except Exception:
            pass

fallades = 0
amb = 0
muts = 0
with open(FORA, "a", encoding="utf-8") as fh:
    for k, nom in enumerate(fotogrames, 1):
        segon = int(nom[:-4])
        if segon in fets:
            continue
        try:
            im = np.array(Image.open(os.path.join(BANDES, nom)).convert("RGB"))
            text = nomes_arab(" ".join(lector.readtext(im, detail=0, paragraph=True)))
            fallades = 0
        except Exception as e:
            fallades += 1
            print("   %ds ha fallat: %s" % (segon, str(e)[:80]), flush=True)
            # Una fila buida no és una resposta; tres fallades seguides, el problema no és el tall.
            if fallades >= 3:
                print("tres fallades seguides: m'aturo", flush=True)
                break
            continue
        if len(text.replace(" ", "")) < 6:
            muts += 1               # sense lletra: no es desa com a lectura, només es compta
            continue
        amb += 1
        fh.write(json.dumps({"segon": segon, "text": text}, ensure_ascii=False) + "\n")
        fh.flush()
        if k <= 5 or k % 200 == 0:
            print("%5d/%d  amb lletra %d · sense %d   | %ds  %s"
                  % (k, len(fotogrames), amb, muts, segon, text[:50]), flush=True)
        if k % 500 == 0:
            puja(FORA)
puja(FORA)
print("\nllegits %d amb lletra, %d sense" % (amb, muts))

# %%
# Constància i subtítols. Ara sí: hi ha tots els segons, i els consecutius existeixen.
lectures = {}
for l in open(FORA, encoding="utf-8"):
    try:
        d = json.loads(l)
        lectures[d["segon"]] = d["text"]
    except Exception:
        pass
segons = sorted(lectures)

parelles = [prop(lectures[a], lectures[b]) for a, b in zip(segons, segons[1:]) if b - a == 1]
constancia = sum(parelles) / len(parelles) if parelles else 0.0
print("constància entre segons consecutius: %.3f sobre %d parelles" % (constancia, len(parelles)))

# Un subtítol = segons seguits que diuen prou el mateix. La lectura és la del mig.
subtitols = []
for s in segons:
    t = lectures[s]
    if subtitols and s - subtitols[-1]["a"] <= 1 and prop(t, subtitols[-1]["lectures"][-1]) >= 0.6:
        subtitols[-1]["a"] = s
        subtitols[-1]["lectures"].append(t)
    else:
        subtitols.append({"de": s, "a": s, "lectures": [t]})
for st in subtitols:
    ls = st["lectures"]
    millor, punts = ls[0], -1.0
    for x in ls:
        p = sum(prop(x, y) for y in ls if y is not x)
        if p > punts:
            millor, punts = x, p
    st["arab"] = millor
    st["lectures_n"] = len(ls)
    st["acord"] = round(sum(prop(millor, y) for y in ls if y is not millor) / max(1, len(ls) - 1), 3)
    st["dura"] = st["a"] - st["de"] + 1
    del st["lectures"]
json.dump(subtitols, open("/content/subtitols_easyocr.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
puja("/content/subtitols_easyocr.json")
segurs = [x for x in subtitols if x["lectures_n"] >= 3 and x["acord"] >= 0.8]
print("subtítols: %d · amb tres lectures o més que coincideixen: %d" % (len(subtitols), len(segurs)))
print("(«coincideixen» vol dir estables, no correctes: això ho ha de dir una persona que llegeixi àrab)")
for x in segurs[:10]:
    print("  %5ds %2ds  acord %.2f (%d)  %s" % (x["de"], x["dura"], x["acord"], x["lectures_n"], x["arab"][:56]))
