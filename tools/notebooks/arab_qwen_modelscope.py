"""L'àrab cremat del vídeo d'en Baba Ali, llegit per un model que MIRA

Per què es canvia d'eina. L'EasyOCR va llegir 2.200 franges i només **964 van tornar lletra**:
no és que llegís malament, és que el detector no hi trobava text. I el Tesseract encara pitjor
(«l'EasyOCR s'equivoca de lletra, el Tesseract s'equivoca de paraula»). Tots dos són OCR de
pàgina escanejada, i això no és una pàgina: és un subtítol cremat sobre la pel·lícula, lletra
de trenta píxels, cursiva, amb el fons movent-se al darrere.

El Qwen2.5-VL no és un OCR: és un model que mira la imatge i escriu què hi veu, i l'àrab el sap
de debò. (Compte: el seu germà de **veu** va llegir el nostre amazic a CER 0,77 i el vam
descartar ahir. Són models diferents; que l'un no senti la llengua no diu res de si l'altre
llegeix la lletra.)

## La primera feina no és llegir-ho tot, és triar la imatge

Les franges d'ahir anaven **binaritzades** —negre sobre blanc, llindar 185— perquè un OCR clàssic
ho necessita. Però el llindar és un ganivet: les parts primes de la lletra àrab (les unions i
els punts) poden haver-se perdut *abans* de llegir. Si fos així, el 56% de franges mudes no
mesurava l'EasyOCR sinó el llindar.

Per això aquí es llegeixen primer **295 franges en les dues versions** —la binaritzada i la de
color— i es compara. El que guanyi es fa servir per a les 2.647.

## El que en surt, i el que no

Surt `arab_qwen.jsonl` i **tot s'escriu també per pantalla**: un peó que només desa al seu disc
no ha fet res, i aquesta màquina no és nostra. El que NO fa: tocar la biblioteca, ni decidir què
vol dir cap frase.
"""

# %%
#: Quantes franges del tast. Amb 0 es fa el vídeo sencer amb la versió que hagi guanyat.
TAST = 295
#: Quina versió per a la passada llarga: "color", "tallats", o None per decidir-ho amb el tast.
VERSIO = None

# %%
import os
import subprocess
import sys

subprocess.run([sys.executable, "-m", "pip", "install", "-q",
                "modelscope", "transformers>=4.49", "accelerate", "qwen-vl-utils", "av"],
               check=False)
print("instal·lat", flush=True)

# %%
import glob
import json
import re
import unicodedata

ARREL = os.path.dirname(os.path.abspath("__file__")) if "__file__" not in dir() else "."
for cami in (".", "/mnt/workspace/arab", "/mnt/data/arab", os.path.expanduser("~/arab")):
    if os.path.isdir(os.path.join(cami, "tallats")):
        ARREL = cami
        break
print("paquet a:", ARREL, flush=True)
segments = json.load(open(os.path.join(ARREL, "segments.json"), encoding="utf-8"))
print("subtítols: %d" % len(segments), flush=True)

#: El que va llegir l'EasyOCR, per hora d'inici (no per índex: venia d'una altra retallada).
#: **No és una vara de mesurar.** Mirant-lo, el que va treure és en bona part escombraria
#: («لصو ييه تس ل ليان صصخ»), i assemblar-s'hi no seria cap mèrit. Es porta per veure QUÈ canvia,
#: no per puntuar.
VELL = {}
cami_vell = os.path.join(ARREL, "arab_votat.json")
if os.path.exists(cami_vell):
    for x in json.load(open(cami_vell, encoding="utf-8")):
        if (x.get("arab") or "").strip():
            VELL[int(round(float(x["de"])))] = x["arab"].strip()
print("franges que l'EasyOCR va llegir amb lletra: %d" % len(VELL), flush=True)

# %%
import torch
from modelscope import AutoProcessor, Qwen2_5_VLForConditionalGeneration

NOM = "Qwen/Qwen2.5-VL-7B-Instruct"
model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
    NOM, torch_dtype=torch.bfloat16, device_map="auto")
proc = AutoProcessor.from_pretrained(NOM)
print("carregat", flush=True)

#: En àrab i sense marge per xerrar: el que volem és la ratlla, no un comentari sobre la ratlla.
DEMANA = ("اكتب النص العربي الظاهر في هذه الصورة حرفياً، سطراً واحداً فقط، "
          "بدون ترجمة وبدون أي تعليق. إذا لم يكن هناك نص، اكتب: لا يوجد")


def llegeix(cami):
    msg = [{"role": "user", "content": [{"type": "image", "image": "file://" + os.path.abspath(cami)},
                                        {"type": "text", "text": DEMANA}]}]
    text = proc.apply_chat_template(msg, tokenize=False, add_generation_prompt=True)
    from qwen_vl_utils import process_vision_info
    imatges, videos = process_vision_info(msg)
    ent = proc(text=[text], images=imatges, videos=videos, padding=True, return_tensors="pt")
    ent = ent.to(model.device)
    with torch.no_grad():
        fora = model.generate(**ent, max_new_tokens=96, do_sample=False)
    tall = [o[len(i):] for i, o in zip(ent.input_ids, fora)]
    r = proc.batch_decode(tall, skip_special_tokens=True, clean_up_tokenization_spaces=False)[0]
    r = r.strip().split("\n")[0].strip()
    return "" if r in ("لا يوجد", "لا يوجد نص") else r


def net(t):
    """Per comparar dues lectures: sense punts, sense vocals curtes, sense espais."""
    t = unicodedata.normalize("NFKC", t or "")
    t = re.sub(r"[ً-ْـ]", "", t)        # harakat i la ratlla d'allargar
    t = t.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا").replace("ى", "ي")
    return "".join(c for c in t if c.isalnum())


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


def acord(a, b):
    a, b = net(a), net(b)
    if not a or not b:
        return 0.0
    return round(1 - distancia(a, b) / max(len(a), len(b)), 3)


# %%
#: EL TAST: les mateixes franges en les dues versions.
quines = sorted(int(os.path.basename(f)[1:5])
                for f in glob.glob(os.path.join(ARREL, "color", "s*.jpg")))[:TAST]
print("=== tast: %d franges, cadascuna en color i binaritzada ===" % len(quines), flush=True)

PER_I = {s["i"]: s for s in segments}


def sembla_arab(t):
    """Això són paraules o són lletres escampades?

    La diferència entre llegir i al·lucinar es veu en la forma: l'àrab escrit de debò fa
    paraules de dues a set lletres; el que surt d'un detector perdut fa lletres soltes amb
    espais pel mig. Es compta la part de paraules de dues lletres o més. No diu si el text és
    CORRECTE —això només es veu mirant la imatge—, però sí si pot ser-ho.
    """
    mots = [m for m in re.split(r"\s+", (t or "").strip()) if m]
    if not mots:
        return 0.0
    return round(sum(1 for m in mots if len(net(m)) >= 2) / len(mots), 3)


tast = []
for n, i in enumerate(quines, 1):
    s = PER_I.get(i) or {}
    fila = {"i": i, "de": s.get("de"), "easyocr": VELL.get(int(round(s.get("de") or -1)), "")}
    for versio, patro in (("color", "color/s%04d.jpg"), ("tallats", "tallats/s%04d.png")):
        cami = os.path.join(ARREL, patro % i)
        if not os.path.exists(cami):
            continue
        try:
            fila[versio] = llegeix(cami)
        except Exception as e:
            print("  s%04d %s ha fallat: %s" % (i, versio, str(e)[:70]), flush=True)
            fila[versio] = None
    tast.append(fila)
    if n <= 10 or n % 25 == 0:
        print("%3d/%d  s%04d  color «%s» | binari «%s» | easyocr «%s»"
              % (n, len(quines), i, (fila.get("color") or "—")[:30],
                 (fila.get("tallats") or "—")[:30], (fila["easyocr"] or "—")[:30]), flush=True)
    json.dump(tast, open("arab_tast.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

print("\n=== quina versió de la imatge es llegeix millor ===", flush=True)
print("(«paraules» = quina part del que torna són paraules de dues lletres o més, no lletres", flush=True)
print(" soltes; l'acord amb l'EasyOCR és informatiu, no una nota: el vell és mig escombraria)", flush=True)
for versio in ("color", "tallats"):
    amb = [f for f in tast if (f.get(versio) or "").strip()]
    comp = [f for f in tast if (f.get(versio) or "").strip() and f["easyocr"]]
    mitja = sum(acord(f[versio], f["easyocr"]) for f in comp) / max(1, len(comp))
    paraules = sum(sembla_arab(f[versio]) for f in amb) / max(1, len(amb))
    print("  %-8s torna lletra en %3d de %3d (%.0f%%) | paraules %.2f | acord amb el vell %.3f (n=%d)"
          % (versio, len(amb), len(tast), 100.0 * len(amb) / max(1, len(tast)),
             paraules, mitja, len(comp)), flush=True)

#: Les dues versions llegides per separat: on diuen el mateix, hi ha poc a discutir.
totes_dues = [f for f in tast if (f.get("color") or "").strip() and (f.get("tallats") or "").strip()]
iguals = [f for f in totes_dues if acord(f["color"], f["tallats"]) >= 0.8]
print("\nllegides en les dues versions: %d | diuen el mateix: %d"
      % (len(totes_dues), len(iguals)), flush=True)
print("aquestes %d són les que es poden ensenyar sense demanar perdó." % len(iguals), flush=True)

print("\n--- deu per mirar amb els ulls (la imatge al costat del que n'ha llegit) ---", flush=True)
for f in totes_dues[:10]:
    print("  s%04d (%ss)  color: %s" % (f["i"], f.get("de"), (f.get("color") or "")[:46]), flush=True)
    print("              binari: %s" % (f.get("tallats") or "")[:46], flush=True)

#: Les que l'EasyOCR va deixar mudes i el Qwen sí que llegeix: aquesta és la raó de tot plegat.
noves = [f for f in tast if not f["easyocr"] and (f.get("color") or f.get("tallats"))]
print("\nfranges que l'EasyOCR va deixar en blanc i el Qwen llegeix: %d" % len(noves), flush=True)
for f in noves[:12]:
    print("  s%04d  %s" % (f["i"], (f.get("color") or f.get("tallats"))[:56]), flush=True)
print("\n(desat a arab_tast.json — copia'l abans de tancar la màquina)", flush=True)
