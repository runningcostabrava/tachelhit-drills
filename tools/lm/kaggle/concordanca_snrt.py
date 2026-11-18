# Concordància so <-> text de Tamazight TV (#601). RECERCA privada: no es publica res. Sense entrenar res: només escolta.
# El model acústic que ja tenim (MMS `shi` + adaptador H4b, el del Space) transcriu cada tall; es compara amb el tifinag que va
# llegir l'OCR dels píxels. Si s'assemblen més que una vintena de textos d'altres talls del capítol (esquelet consonàntic,
# vegeu tools/snrt/concordanca.py), els dos canals independents diuen el mateix: veu clara + text bo, sense parlant natiu.
# Sortida: concordanca.json (per tall: hipòtesi, cer, rang, marge, alta) i concordanca_resum.json (per capítol: % d'alta certesa,
# CER mediana = claredat de la veu; FAR = falsa acceptació amb parells barrejats).
import os, subprocess, sys
os.environ["CUDA_VISIBLE_DEVICES"] = "0"
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-U", "transformers>=4.44", "librosa", "soundfile"], check=False)
import collections, json, re, statistics, unicodedata
import numpy as np, torch, librosa


def de_kaggle(nom):
    for arrel, _, fitxers in os.walk("/kaggle/input"):
        if nom in fitxers:
            return os.path.join(arrel, nom)
    return None


MOD = de_kaggle("concordanca.py")
ROWS = de_kaggle("rows.json")
ADAPT = de_kaggle("adaptador_shi_zouhir_b.pt")
assert MOD and ROWS and ADAPT, (MOD, ROWS, ADAPT)
sys.path.insert(0, os.path.dirname(MOD))
import concordanca as cc

TIF_RIC = {"ⴰ": "a", "ⴱ": "b", "ⴳ": "g", "ⴷ": "d", "ⴹ": "ḍ", "ⴻ": "e", "ⴼ": "f", "ⴽ": "k", "ⵀ": "h", "ⵃ": "ḥ", "ⵄ": "ε",
           "ⵅ": "ḫ", "ⵇ": "q", "ⵉ": "i", "ⵊ": "j", "ⵍ": "l", "ⵎ": "m", "ⵏ": "n", "ⵓ": "u", "ⵔ": "r", "ⵕ": "r", "ⵖ": "ġ",
           "ⵙ": "s", "ⵚ": "ṣ", "ⵛ": "š", "ⵜ": "t", "ⵟ": "ṭ", "ⵡ": "w", "ⵢ": "y", "ⵣ": "z", "ⵥ": "ẓ", "ⵯ": "w"}
LLATI_RIC = {"ɣ": "ġ", "γ": "ġ", "ɛ": "ε", "ṛ": "r", "c": "š", "x": "ḫ", "χ": "ḫ", "ž": "j", "ǧ": "j", "ʷ": "w", "v": "f", "p": "b", "o": "u"}


def rica(t):
    t = unicodedata.normalize("NFC", (t or "")).strip().lower()
    t = "".join(TIF_RIC.get(c, c) for c in t)
    t = "".join(LLATI_RIC.get(c, c) for c in t)
    t = re.sub(r"[^a-zġεḥḍṭṣẓḫš ]+", "", t)
    return re.sub(r" +", " ", t).strip()


from transformers import AutoModelForCTC, AutoProcessor
BASE, LLENGUA, SR = "facebook/mms-1b-all", "shi", 16000
proc = AutoProcessor.from_pretrained(BASE)
proc.tokenizer.set_target_lang(LLENGUA)
model = AutoModelForCTC.from_pretrained(BASE, ignore_mismatched_sizes=True)
model.load_adapter(LLENGUA)
assert not model.load_state_dict(torch.load(ADAPT, map_location="cpu"), strict=False).unexpected_keys
dev = "cuda" if torch.cuda.is_available() else "cpu"
model.to(dev).eval()

D = os.path.dirname(ROWS)
files = [r for r in json.load(open(ROWS, encoding="utf-8")) if rica(r["tifinag"]) and os.path.exists(os.path.join(D, r["fitxer"]))]
per_cap = collections.defaultdict(list)
for r in files:
    per_cap[r["slug"]].append(r)
print("talls", len(files), "capítols", len(per_cap), flush=True)

sortida, resum, far_tot = {}, {}, []
for slug, rs in per_cap.items():
    rs.sort(key=lambda r: r["id"])
    hips = []
    for r in rs:
        w, _ = librosa.load(os.path.join(D, r["fitxer"]), sr=SR, mono=True)
        ent = proc(w[:14 * SR], sampling_rate=SR, return_tensors="pt").to(dev)
        with torch.no_grad():
            ids = model(**ent).logits.argmax(-1)
        hips.append(rica(proc.batch_decode(ids)[0]))
    textos = [rica(r["tifinag"]) for r in rs]
    cers, altes = [], 0
    for i, r in enumerate(rs):
        p = cc.puntua(hips[i], textos[i], cc.controls_de(i, textos))
        p["alta"] = cc.alta_certesa(p)
        p["hip"], p["text"], p["split"] = hips[i], textos[i], r["split"]
        sortida[r["id"]] = p
        cers.append(p["cer"])
        altes += p["alta"]
    f = cc.far(hips, textos)
    resum[slug] = {"talls": len(rs), "alta": altes, "alta_pct": round(100 * altes / len(rs), 1), "cer_mediana": round(statistics.median(cers), 3), "far": f}
    print(slug[:12], resum[slug], flush=True)
json.dump(sortida, open("/kaggle/working/concordanca.json", "w", encoding="utf-8"), ensure_ascii=False)
json.dump(resum, open("/kaggle/working/concordanca_resum.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
