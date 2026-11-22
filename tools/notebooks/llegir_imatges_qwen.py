"""Llegir lletra d'una imatge amb el Qwen: l'àrab cremat i el tifinag

Dues preguntes amb la mateixa eina, i totes dues són de les que avui paguem o no sabem fer.

**L'àrab.** El vídeo d'en Baba Ali (52 minuts de taixelhit del Souss parlat de veritat) porta
l'àrab cremat a sota, i l'àrab diu el que l'autor va escriure que deia cada frase: una tercera
font de significat, independent de nosaltres. Fins ara el llegia el Gemini, que cobra i que s'ha
quedat sense crèdit dues vegades aquest mes. El Tesseract, de franc, en treu dos de cada tres.

**El tifinag.** Aquest és el forat de debò: no el sap llegir ningú. El Gemini torna símbols que
s'hi assemblen i el Tesseract no el porta. Avui l'única manera de treure text d'un vídeo amazic
és que una persona bategi trenta-i-escaig signes a mà per cada família de vídeos.

## Per què s'envia un fotograma per segon i no «un per subtítol»

Perquè decidir on comença i on acaba cada subtítol comptant píxels no funciona. Dues passades i
dues respostes impossibles: 351 subtítols en 52 minuts (i comprovat: els segments llargs
portaven text diferent al principi i al final) i després 2.647. Mesurant-ho amb el Tesseract com
a veritat, el millor llindar encerta 43 de 58 — perquè el Tesseract només llegeix dos de cada
tres subtítols, i la meitat dels «són diferents» és ell llegint malament el mateix.

Qui sí que pot dir si dos fotogrames diuen el mateix és **qui els llegeix**. O sigui que es
llegeix un fotograma per segon i després s'ajunten els que diuen el mateix: el rellotge surt
sol, i no hi ha cap llindar triat a ull.

## I com es mesura el tifinag sense text d'or

Dels 25 fotogrames en tenim el que l'ASR va *sentir* de l'àudio al mateix moment. No és or: és
una segona màquina. Però són dues vies independents —una mira, l'altra escolta— i quan
coincideixen, la coincidència val més que qualsevol de les dues per separat. Aquí no es mesura
encert: es mesura **acord**.

I la trampa que ja ens ha costat quatre mesures falses aquest mes: el model escriu en llatí i la
referència és en tifinag. Comparar-les tal qual dona un error del 100% encara que ho hagi
llegit perfectament. Aquí es plega tot a la mateixa forma abans de comparar.
"""

# %%
#: El de 3.000 milions cap de sobres a la T4 i va de pressa; el de 7.000 només hi cap a 4 bits.
#: El PRIMER llegeix tot l'àrab; els altres només el tifinag i una mostra, per comparar-los
#: sense gastar-hi una hora de GPU cadascun.
MODELS = [
    ("Qwen/Qwen2.5-VL-3B-Instruct", False),
    ("Qwen/Qwen2.5-VL-7B-Instruct", True),    # a 4 bits
]
#: Quants fotogrames àrabs llegeix el primer model. Amb 0 els llegeix tots.
QUANTS_ARAB = 0
#: I quants en llegeixen els altres, només per poder-los comparar.
MOSTRA = 60

# %%
import subprocess
import sys

subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-U",
                "transformers>=4.51", "accelerate", "qwen-vl-utils", "bitsandbytes"], check=False)
import transformers
print("transformers", transformers.__version__)

# %%
import glob
import json
import os
import unicodedata

TIF_A_LLATI = {
    "ⴰ": "a", "ⴱ": "b", "ⴳ": "g", "ⴷ": "d", "ⴹ": "d", "ⴻ": "e", "ⴼ": "f", "ⴽ": "k",
    "ⵀ": "h", "ⵃ": "h", "ⵄ": "a", "ⵅ": "x", "ⵇ": "q", "ⵉ": "i", "ⵊ": "j", "ⵍ": "l",
    "ⵎ": "m", "ⵏ": "n", "ⵓ": "u", "ⵔ": "r", "ⵕ": "r", "ⵖ": "g", "ⵙ": "s", "ⵚ": "s",
    "ⵛ": "c", "ⵜ": "t", "ⵟ": "t", "ⵡ": "w", "ⵢ": "y", "ⵣ": "z", "ⵥ": "z", "ⵯ": "w",
}
PLEGA = {"ɣ": "g", "ɛ": "a", "ḥ": "h", "ḍ": "d", "ṭ": "t", "ẓ": "z", "ṣ": "s", "ṛ": "r",
         "š": "c", "ž": "j", "ǧ": "j", "č": "c", "e": "", "'": "", "’": ""}


def net(t):
    """Les dues bandes a la mateixa forma. Sense això, `ⵜⴰⵣⵣⵍⴰ` i `tazzla` donen un 100%."""
    t = unicodedata.normalize("NFC", (t or "")).strip().lower()
    t = "".join(TIF_A_LLATI.get(c, c) for c in t)
    for mult, un in (("gh", "g"), ("kh", "x"), ("ch", "c"), ("sh", "c"), ("ou", "u")):
        t = t.replace(mult, un)
    t = "".join(PLEGA.get(c, c) for c in t)
    return "".join(c for c in t if c.isalnum())


def nomes_arab(t):
    return "".join(c for c in (t or "") if "؀" <= c <= "ۿ")


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
    """Dues lectures del mateix subtítol no surten mai lletra per lletra iguals."""
    if not a or not b:
        return False
    return 1 - distancia(a, b) / max(len(a), len(b)) >= 0.75


# Les dades, d'on sigui que Kaggle les hagi muntat: el nom de la carpeta ha canviat un cop i la
# passada va caure sencera per això.
DADES = None
for arrel, carpetes, _ in os.walk("/kaggle/input"):
    if "arab" in carpetes and "conte" in carpetes:
        DADES = arrel
        break
if DADES is None:
    raise SystemExit("no trobo la carpeta de les imatges sota /kaggle/input: "
                     + str(glob.glob("/kaggle/input/**", recursive=True)[:40]))
print("dades:", DADES)

arabs = sorted(f for f in os.listdir(os.path.join(DADES, "arab")) if f.endswith(".png"))
contes = sorted(f for f in os.listdir(os.path.join(DADES, "conte")) if f.endswith(".png"))
veritat = json.load(open(os.path.join(DADES, "conte_veritat.json"), encoding="utf-8"))
print("fotogrames àrabs (un per segon): %d · fotogrames de tifinag: %d" % (len(arabs), len(contes)))

# %%
import torch
from PIL import Image
from transformers import AutoProcessor

try:
    from transformers import Qwen2_5_VLForConditionalGeneration as Cap
except Exception:
    from transformers import Qwen2VLForConditionalGeneration as Cap


def carrega(model_id, quatre_bits):
    proc = AutoProcessor.from_pretrained(model_id)
    args = {"device_map": "auto"}
    if quatre_bits:
        from transformers import BitsAndBytesConfig
        args["quantization_config"] = BitsAndBytesConfig(
            load_in_4bit=True, bnb_4bit_compute_dtype=torch.float16, bnb_4bit_quant_type="nf4")
    else:
        args["torch_dtype"] = torch.float16
    return proc, Cap.from_pretrained(model_id, **args).eval()


def llegeix(proc, model, im, pregunta):
    msg = [{"role": "user", "content": [{"type": "image"}, {"type": "text", "text": pregunta}]}]
    text = proc.apply_chat_template(msg, add_generation_prompt=True, tokenize=False)
    ent = proc(text=[text], images=[im], return_tensors="pt", padding=True).to(model.device)
    with torch.no_grad():
        ids = model.generate(**ent, max_new_tokens=128, do_sample=False)
    return proc.batch_decode(ids[:, ent["input_ids"].size(1):],
                             skip_special_tokens=True)[0].strip()


PREGUNTA_TIF = ("This image shows a subtitle written in the TIFINAGH alphabet (Berber, Unicode "
                "U+2D30..U+2D7F), burned into a video frame. Copy the Tifinagh characters "
                "exactly as you see them, sign by sign. Write ONLY those characters: no "
                "translation, no transliteration, no explanation. If you see no Tifinagh text, "
                "write NOTHING.")
PREGUNTA_ARAB = ("This image is one line of ARABIC subtitle from a Moroccan film, in black on "
                 "white. Copy the Arabic text exactly, letter by letter. Write ONLY the Arabic: "
                 "no translation, no explanation, no quotes. If there is no readable Arabic, "
                 "write a single dash: -")

# %%
resultats = {}
for k_model, (model_id, quatre) in enumerate(MODELS):
    print("\n===", model_id, "(4 bits)" if quatre else "", flush=True)
    try:
        proc, model = carrega(model_id, quatre)
    except Exception as e:
        print("   no s'ha pogut carregar:", str(e)[:200], flush=True)
        resultats[model_id] = {"error": str(e)[:300]}
        continue

    # --- el tifinag, que es pot mesurar ---
    tif = {}
    suma_d = suma_n = acords = 0
    for nom in contes:
        ref = (veritat.get(nom) or {}).get("tif", "")
        try:
            dit = llegeix(proc, model, Image.open(os.path.join(DADES, "conte", nom)).convert("RGB"),
                          PREGUNTA_TIF)
        except Exception as e:
            dit = "(error: %s)" % str(e)[:60]
        r, h = net(ref), net(dit)
        if r:
            d = distancia(r, h)
            suma_d += d
            suma_n += len(r)
            if d / max(1, len(r)) <= 0.35:
                acords += 1
        tif[nom] = {"ref_asr": ref, "diu": dit,
                    "signes_tifinag": sum(1 for c in dit if "ⴰ" <= c <= "⵿")}
        print("   %-9s %s" % (nom, dit[:66]), flush=True)
    print("   >>> acord amb el que l'ASR va sentir: %d de %d   distància %.3f"
          % (acords, len(contes), suma_d / max(1, suma_n)), flush=True)

    # --- l'àrab. El primer model els llegeix tots; els altres, una mostra per comparar ---
    quins = arabs if k_model == 0 else arabs[::max(1, len(arabs) // MOSTRA)][:MOSTRA]
    if k_model == 0 and QUANTS_ARAB:
        quins = arabs[:QUANTS_ARAB]
    ar = {}
    amb = 0
    for k, nom in enumerate(quins, 1):
        try:
            dit = llegeix(proc, model, Image.open(os.path.join(DADES, "arab", nom)).convert("RGB"),
                          PREGUNTA_ARAB)
        except Exception as e:
            dit = ""
            print("   %s ha fallat: %s" % (nom, str(e)[:60]), flush=True)
        lletres = len(nomes_arab(dit))
        if lletres >= 6:
            amb += 1
        ar[nom] = dit
        if k <= 6 or k % 200 == 0:
            print("   %-10s %s" % (nom, dit[:66]), flush=True)
    print("   >>> fotogrames amb àrab llegible: %d de %d" % (amb, len(quins)), flush=True)

    resultats[model_id] = {"tifinag": tif, "acord_tifinag": acords,
                           "distancia_tifinag": round(suma_d / max(1, suma_n), 4),
                           "arab": ar, "arab_llegibles": amb, "arab_mirats": len(quins)}
    json.dump(resultats, open("/kaggle/working/lectura_imatges.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    del model, proc
    torch.cuda.empty_cache()

# %%
# El rellotge, que surt de la lectura i no de cap llindar: segons seguits que diuen el mateix
# són un subtítol. El nom del fitxer ja porta el segon del vídeo.
millor = max((k for k in resultats if resultats[k].get("arab_mirats", 0) > 500),
             key=lambda k: resultats[k]["arab_llegibles"], default=None)
if millor:
    llegits = []
    for nom, dit in sorted(resultats[millor]["arab"].items()):
        t = int(nom[1:-4])
        a = nomes_arab(dit)
        llegits.append((t, a, dit.strip()))
    escenes = []
    for t, a, cru in llegits:
        if len(a) < 6:
            continue
        if escenes and s_assemblen(escenes[-1]["clau"], a) and t - escenes[-1]["a"] <= 2:
            escenes[-1]["a"] = t
            if len(a) > len(escenes[-1]["clau"]):      # la lectura més llarga sol ser la més neta
                escenes[-1]["clau"], escenes[-1]["arab"] = a, cru
        else:
            escenes.append({"de": t, "a": t, "clau": a, "arab": cru})
    for e in escenes:
        e["dura"] = e["a"] - e["de"] + 1
        del e["clau"]
    json.dump(escenes, open("/kaggle/working/escenes_arab.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    dur = sum(e["dura"] for e in escenes)
    print("\n=== %d subtítols, %.1f min de lletra, %.1fs de mitjana (model: %s) ==="
          % (len(escenes), dur / 60, dur / max(1, len(escenes)), millor))
    for e in escenes[:10]:
        print("  %5ds  %2ds  %s" % (e["de"], e["dura"], e["arab"][:60]))
print("desat a /kaggle/working/")
