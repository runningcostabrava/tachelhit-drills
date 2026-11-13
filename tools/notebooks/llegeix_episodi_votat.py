# %%
"""L'àrab cremat d'un episodi sencer, llegit tres vegades per segon i votat (#493).

Els episodis 2-15 del Baba Ali tenen 3.621 línies a la biblioteca. L'1 i el 14 no en tenen cap,
i del 16 al 30 tampoc. Aquest guió fa el camí sencer per a un episodi: de la franja del subtítol
a una llista de línies amb el seu segon.

## La decisió que ja estava presa, i que vaig tornar a equivocar

Decidir on comença i on acaba cada subtítol **comptant píxels no funciona**. Ja està escrit a
`llegir_imatges_qwen.py`: dues passades i dues respostes impossibles (351 subtítols en 52
minuts, i després 2.647). El 13-11-2026 ho vaig tornar a provar amb l'episodi 1 i van sortir 25
i després 17, quan l'episodi 2 en té 210. Amb un llindar de blanc, un cel clar compta tant com
una lletra.

**Qui pot dir si dos fotogrames diuen el mateix és qui els llegeix.** Es llegeix un fotograma
per segon i després s'ajunten els que diuen el mateix: el rellotge surt sol i no hi ha cap
llindar triat a ull.

## TRES retalls NO serveixen. Un en va prou, i és el mateix de sempre.

Aquest quadern sap llegir tants retalls per fotograma com en tingui, i es va fer perquè es
creia que votant entre tres sortiria una lectura millor. **És fals, i el número que ho deia
era una confusió.** Tornant a comptar el 13-11-2026 sobre les mateixes 15 línies de
l'episodi 1, amb la mateixa normalització i els mateixos errors desats a `retalls.json`:

| lectura | error per lletra |
|---|---|
| `alt` — franja fixa de 200 px | **0,100** |
| `just` — retallat a les files amb tinta | 0,186 |
| `just2x` — el mateix, ampliat | 0,138 |
| votant entre els tres | 0,167 |
| el sostre: si sabessis quin triar cada cop | 0,029 |

Votar és **pitjor** que fer servir només la franja alta, i el 0,039 que hi havia apuntat com
a resultat de la votació era, de fet, el sostre (0,029): el que sortiria si un oracle triés
el bon retall cada vegada. Un oracle no el tenim. I les dues lectures que es creia que
coincidien a 12 línies de 15 coincideixen a 9, i quan coincideixen no sempre tenen raó.

Per què falla: els tres retalls no s'equivoquen de manera independent. Surten de la mateixa
imatge, i quan el fotograma és dolent, els tres s'equivoquen alhora i sovint igual; la
majoria confirma l'error en comptes de delatar-lo.

**Conseqüència pràctica:** per a un episodi nou, es treu UNA franja per segon amb
`tools/baba_ali/franges.py` i s'escriu `"menes": ["alt"]` al `temps.json`. Costa un terç de
GPU i llegeix millor. Els episodis 1 i 14 es van llegir amb els tres retalls i la votació; el
seu text és pitjor del que hauria estat, i tornar-los a passar amb un sol retall és feina
pendent.

El que sí que val és l'altra votació, la de sota: el mateix subtítol llegit en segons
diferents. Aquelles lectures sí que són independents, perquè són imatges diferents.

## I una cosa que surt de franc

Un subtítol que dura quatre segons es llegeix quatre vegades (dotze, amb els tres retalls), i
cada lectura és independent. La línia es queda amb la que més es repeteix i desa quantes hi
estaven d'acord, que és el número que diu de quina et pots refiar.

## El rellotge val per a YouTube

Per a l'episodi 1, el fitxer del disc (`baba-ali-01-02.mp4`, 3.118 s) ÉS la pujada
`ihwiZk1WmJM` de YouTube. Els segons que surten d'aquí ja són segons del vídeo del canal: no
s'ha de casar res, a diferència dels dotze episodis que es van haver de correlacionar pel so.

## Com es fa servir

A Kaggle, amb GPU (T4). Conjunt d'entrada amb la carpeta `arab/` (tres imatges per segon:
`00001_alt.png`, `00001_just.png`, `00001_just2x.png`) i `temps.json`. Les treu
`tools/baba_ali/franges.py`. Surt `/kaggle/working/linies.json`.
"""

# %%
#: El de 3.000 milions cap de sobres a la T4 i llegeix l'àrab prou bé; el de 7.000 només hi cap
#: a 4 bits i triga el doble, i aquí hi ha gairebé 4.000 imatges.
MODEL = "Qwen/Qwen2.5-VL-3B-Instruct"
#: 0 = totes. Posa-hi 60 per a una passada de prova abans de gastar-hi una hora i mitja de GPU.
QUANTES = 0
#: Com s'assemblen dues lectures per considerar-les la mateixa. Dues lectures del mateix
#: subtítol no surten mai lletra per lletra iguals.
S_ASSEMBLEN = 0.75
#: I quant han de coincidir dos RETALLS del mateix fotograma per donar-los per bons. Més estret
#: que l'anterior a posta: aquí miren exactament la mateixa imatge.
RETALLS_DACORD = 0.90

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

rellotge = json.load(open(os.path.join(DADES, "temps.json"), encoding="utf-8"))
segons = rellotge["segons"]
MENES = rellotge.get("menes") or ["alt"]
fitxers = sorted(f for f in os.listdir(os.path.join(DADES, "arab")) if f.endswith(".png"))
print(f"{len(fitxers)} imatges · {len(segons)} segons · {len(MENES)} retalls per segon")


def nomes_arab(t):
    """Les lletres àrabs i prou: el model hi afegeix cometes, punts i de tant en tant una
    explicació en anglès, i res d'això és el subtítol."""
    return re.sub(r"\s+", " ", "".join(c for c in (t or "")
                                       if "؀" <= c <= "ۿ" or c == " ")).strip()


def plana(t):
    """Per comparar: sense vocals curtes i amb les lletres que s'escriuen de dues maneres
    portades a una de sola."""
    t = re.sub(r"[ً-ْٰـ]", "", t or "")
    for a, b in (("أ", "ا"), ("إ", "ا"), ("آ", "ا"), ("ئ", "ي"), ("ى", "ي"), ("ة", "ه")):
        t = t.replace(a, b)
    return t.replace(" ", "")


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


def semblança(a, b):
    a, b = plana(a), plana(b)
    if not a or not b:
        return 0.0
    return 1 - distancia(a, b) / max(len(a), len(b))

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
            "one or two lines of ARABIC subtitle. Copy the Arabic text exactly, letter by "
            "letter. Write ONLY the Arabic: no translation, no explanation, no quotes. If "
            "there is no readable Arabic subtitle, write a single dash: -")


def llegeix(im):
    msg = [{"role": "user", "content": [{"type": "image"}, {"type": "text", "text": PREGUNTA}]}]
    text = proc.apply_chat_template(msg, add_generation_prompt=True, tokenize=False)
    ent = proc(text=[text], images=[im], return_tensors="pt", padding=True).to(model.device)
    with torch.no_grad():
        ids = model.generate(**ent, max_new_tokens=128, do_sample=False)
    return proc.batch_decode(ids[:, ent["input_ids"].size(1):], skip_special_tokens=True)[0].strip()

# %%
# --- 1. llegir cada retall de cada segon
claus = sorted(segons)
if QUANTES:
    claus = claus[:QUANTES]
lectures = []
for i, clau in enumerate(claus):
    diu = {}
    for mena in MENES:
        nom = f"{clau}_{mena}.png" if len(MENES) > 1 else f"{clau}.png"
        cami = os.path.join(DADES, "arab", nom)
        if not os.path.exists(cami):
            continue
        try:
            diu[mena] = nomes_arab(llegeix(Image.open(cami).convert("RGB")))
        except Exception as e:
            print(f"  {nom}: {type(e).__name__}: {str(e)[:100]}", flush=True)
            diu[mena] = ""

    # --- 2. votar entre els retalls: el que dos diuen igual
    #     Mesurat sobre 15 línies: 0,100 d'error amb la franja alta sola, 0,039 votant.
    #     Si cap parella no coincideix, es queda la franja alta, que és la que menys erra sola.
    triat, acord = None, 0
    noms = [m for m in MENES if diu.get(m)]
    for a in range(len(noms)):
        for b in range(a + 1, len(noms)):
            if semblança(diu[noms[a]], diu[noms[b]]) >= RETALLS_DACORD:
                triat, acord = noms[a], 2
                break
        if triat:
            break
    if triat is None:
        triat = MENES[0] if diu.get(MENES[0]) else (noms[0] if noms else None)
        acord = 1 if triat else 0

    lectures.append({"clau": clau, "segon": segons[clau], "diu": diu.get(triat, ""),
                     "retall": triat, "retalls_dacord": acord, "tots": diu})
    if i % 50 == 0:
        print(f"  {i}/{len(claus)}  {segons[clau]}s  [{triat}] {diu.get(triat,'')[:55]}",
              flush=True)

json.dump(lectures, open("/kaggle/working/lectures.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("llegits", len(lectures), "segons")

# %%
# --- 3. ajuntar els segons que diuen el mateix. Això és el que fa de rellotge.
linies, grup = [], []
for L in lectures:
    if not L["diu"]:
        if grup:
            linies.append(grup)
            grup = []
        continue
    if grup and semblança(grup[-1]["diu"], L["diu"]) >= S_ASSEMBLEN \
            and L["segon"] - grup[-1]["segon"] <= 2:
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
        "lectures": len(g),
        "dacord": quants,
        #: A quants dels segons d'aquesta línia hi havia dos retalls que deien el mateix.
        "retalls_dacord": sum(1 for x in g if x["retalls_dacord"] >= 2),
    })

json.dump(fora, open("/kaggle/working/linies.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

print(f"\nlínies: {len(fora)}")
if fora:
    dur = [x["fi"] - x["t"] for x in fora]
    finestra = rellotge["fins_segon"] - rellotge["de_segon"]
    print(f"  durada mediana: {sorted(dur)[len(dur)//2]} s")
    print(f"  d'un sol fotograma (sense cap confirmació): "
          f"{sum(1 for x in fora if x['lectures'] == 1)}")
    print(f"  amb totes les lectures iguals: "
          f"{sum(1 for x in fora if x['lectures'] > 1 and x['dacord'] == x['lectures'])}")
    print(f"  amb dos retalls d'acord a tots els seus segons: "
          f"{sum(1 for x in fora if x['retalls_dacord'] == x['lectures'])}")
    print(f"  text a la pantalla: {sum(dur)}s de {finestra}s "
          f"({100*sum(dur)/max(finestra,1):.0f} %)")
    print("\n  les deu primeres:")
    for x in fora[:10]:
        print(f"    {x['t']:>5}s → {x['fi']:>5}s  ({x['dacord']}/{x['lectures']}, "
              f"{x['retalls_dacord']} amb dos retalls)  {x['ar'][:55]}")
