"""L'àrab cremat d'un episodi sencer, llegit per segons i ajuntat en línies (#493).

Els episodis 2-15 del Baba Ali tenen 3.621 línies a la biblioteca. L'1 i el 14 no en tenen cap,
i del 16 al 30 tampoc. Aquest guió fa el camí sencer per a un episodi: de la franja del subtítol
a una llista de línies amb el seu segon.

## La decisió que ja estava presa, i que jo vaig tornar a equivocar

Decidir on comença i on acaba cada subtítol **comptant píxels no funciona**. Ja està escrit a
`llegir_imatges_qwen.py`: dues passades i dues respostes impossibles (351 subtítols en 52
minuts, i després 2.647). El 13-11-2026 ho vaig tornar a provar amb l'episodi 1 i van sortir 25
i després 17, quan l'episodi 2 en té 210. Amb un llindar de blanc, un cel clar compta tant com
una lletra.

**Qui pot dir si dos fotogrames diuen el mateix és qui els llegeix.** Es llegeix un fotograma
per segon i després s'ajunten els que diuen el mateix: el rellotge surt sol i no hi ha cap
llindar triat a ull.

## I una cosa que surt de franc

Un subtítol que dura quatre segons es llegeix **quatre vegades**, i cada lectura és
independent. La línia es queda amb la que més es repeteix, no amb la primera: on el model dubta
per un fotograma mal retallat, les altres tres el corregeixen. També es desa quantes n'hi
estaven d'acord, que és el número que diu de quina et pots refiar.

## El rellotge val per a YouTube

Per a l'episodi 1, el fitxer del disc (`baba-ali-01-02.mp4`, 3.118 s) ÉS la pujada
`ihwiZk1WmJM` de YouTube. Els segons que surten d'aquí ja són segons del vídeo del canal: no
s'ha de casar res, a diferència dels dotze episodis que es van haver de correlacionar pel so.

## Com es fa servir

A Kaggle, amb GPU (T4). Conjunt d'entrada: `josepabloucr/baba-ali-episodi-1-franges`, amb la
carpeta `arab/` (una franja per segon) i `temps.json` (quin segon és cada fitxer). Surt
`/kaggle/working/linies.json`.

Les franges es treuen del vídeo així (la franja es MESURA per a cada pujada: la del Baba Ali
«1-2» porta barres negres i el text cau a baix de la IMATGE, no del fotograma):

    ffmpeg -ss 35 -to 1341 -i baba-ali-01-02.mp4 \
           -vf "crop=1920:150:0:845,format=gray,fps=1" arab/%05d.png
"""

# %%
#: El de 3.000 milions cap de sobres a la T4 i llegeix l'àrab prou bé; el de 7.000 només hi cap
#: a 4 bits i triga el doble, i aquí hi ha 1.306 imatges.
MODEL = "Qwen/Qwen2.5-VL-3B-Instruct"
#: 0 = totes. Posa-hi 40 per a una passada de prova abans de gastar-hi mitja hora de GPU.
QUANTES = 0
#: Com s'assemblen dues lectures per considerar-les el mateix subtítol. Dues lectures del
#: mateix subtítol no surten mai lletra per lletra iguals.
S_ASSEMBLEN = 0.75

# %%
import subprocess
import sys

subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-U",
                "transformers>=4.51", "accelerate", "qwen-vl-utils"], check=False)

# %%
import glob
import json
import os
import re
from collections import Counter

DADES = None
for arrel, carpetes, _ in os.walk("/kaggle/input"):
    if "arab" in carpetes:
        DADES = arrel
        break
if DADES is None:
    raise SystemExit("no trobo la carpeta «arab» sota /kaggle/input: "
                     + str(glob.glob("/kaggle/input/*")))
print("dades:", DADES)

franges = sorted(f for f in os.listdir(os.path.join(DADES, "arab")) if f.endswith(".png"))
rellotge = json.load(open(os.path.join(DADES, "temps.json"), encoding="utf-8"))
segons = rellotge["segons"]
print(f"{len(franges)} franges, una per segon, del {rellotge['de_segon']} al {rellotge['fins_segon']}")


def nomes_arab(t):
    """Les lletres àrabs i prou: el model hi afegeix cometes, punts i de tant en tant una
    explicació en anglès, i res d'això és el subtítol."""
    return re.sub(r"\s+", " ", "".join(c for c in (t or "")
                                       if "؀" <= c <= "ۿ" or c == " ")).strip()


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


def s_assemblen(a, b):
    if not a or not b:
        return False
    return 1 - distancia(a, b) / max(len(a), len(b)) >= S_ASSEMBLEN


# %%
import torch
from PIL import Image
from transformers import AutoProcessor

try:
    from transformers import Qwen2_5_VLForConditionalGeneration as Cap
except Exception:
    from transformers import Qwen2VLForConditionalGeneration as Cap

proc = AutoProcessor.from_pretrained(MODEL)
model = Cap.from_pretrained(MODEL, torch_dtype=torch.float16, device_map="auto").eval()

PREGUNTA = ("This image is a strip cut from the bottom of a Moroccan TV frame. It may contain "
            "one line of ARABIC subtitle. Copy the Arabic text exactly, letter by letter. "
            "Write ONLY the Arabic: no translation, no explanation, no quotes. If there is no "
            "readable Arabic subtitle, write a single dash: -")


def llegeix(im):
    msg = [{"role": "user", "content": [{"type": "image"}, {"type": "text", "text": PREGUNTA}]}]
    text = proc.apply_chat_template(msg, add_generation_prompt=True, tokenize=False)
    ent = proc(text=[text], images=[im], return_tensors="pt", padding=True).to(model.device)
    with torch.no_grad():
        ids = model.generate(**ent, max_new_tokens=96, do_sample=False)
    return proc.batch_decode(ids[:, ent["input_ids"].size(1):], skip_special_tokens=True)[0].strip()


# %%
quines = franges if not QUANTES else franges[:QUANTES]
lectures = []
for i, nom in enumerate(quines):
    im = Image.open(os.path.join(DADES, "arab", nom)).convert("RGB")
    try:
        dit = nomes_arab(llegeix(im))
    except Exception as e:
        print(f"  {nom}: {type(e).__name__}: {str(e)[:120]}", flush=True)
        dit = ""
    lectures.append({"fitxer": nom, "segon": segons[nom], "diu": dit})
    if i % 50 == 0:
        print(f"  {i}/{len(quines)}  {segons[nom]}s  {dit[:60]}", flush=True)

json.dump(lectures, open("/kaggle/working/lectures.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("llegides", len(lectures), "franges")

# %%
# Ajuntar els fotogrames que diuen el mateix. Això és el que fa de rellotge.
linies = []
grup = []
for L in lectures:
    if not L["diu"]:
        if grup:
            linies.append(grup)
            grup = []
        continue
    if grup and s_assemblen(grup[-1]["diu"], L["diu"]) and L["segon"] - grup[-1]["segon"] <= 2:
        grup.append(L)
    else:
        if grup:
            linies.append(grup)
        grup = [L]
if grup:
    linies.append(grup)

fora = []
for g in linies:
    comptes = Counter(x["diu"] for x in g)
    diu, quants = comptes.most_common(1)[0]
    fora.append({
        "t": g[0]["segon"],
        #: L'últim fotograma on es veia, més un: la franja és d'un instant i el subtítol encara
        #: hi era durant aquell segon.
        "fi": g[-1]["segon"] + 1,
        "ar": diu,
        #: De quantes lectures surt, i quantes hi estaven d'acord. Una línia d'un sol fotograma
        #: no té cap confirmació; una de quatre amb quatre iguals, sí.
        "lectures": len(g),
        "dacord": quants,
    })

json.dump(fora, open("/kaggle/working/linies.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

print(f"\nlínies: {len(fora)}")
if fora:
    dur = [x["fi"] - x["t"] for x in fora]
    soles = sum(1 for x in fora if x["lectures"] == 1)
    unanimes = sum(1 for x in fora if x["lectures"] > 1 and x["dacord"] == x["lectures"])
    print(f"  durada: mediana {sorted(dur)[len(dur)//2]} s")
    print(f"  d'un sol fotograma (sense cap confirmació): {soles}")
    print(f"  amb totes les lectures iguals: {unanimes}")
    print(f"  text a la pantalla: {sum(dur)}s de {rellotge['fins_segon']-rellotge['de_segon']}s "
          f"({100*sum(dur)/(rellotge['fins_segon']-rellotge['de_segon']):.0f} %)")
    print("\n  les deu primeres:")
    for x in fora[:10]:
        print(f"    {x['t']:>5}s -> {x['fi']:>5}s  ({x['dacord']}/{x['lectures']})  {x['ar'][:60]}")
