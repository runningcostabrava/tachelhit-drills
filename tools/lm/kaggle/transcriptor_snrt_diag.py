# Diagnòstic del transcriptor SNRT (#601): el CER de l'adaptador actual contra el tifinag de la fàbrica surt ~0,86 als capítols
# de Tadfi n Tskla (contra 0,15 a Common Voice). Abans d'entrenar, mirar per què. Tres sospites, totes mesurables:
#   1. el tall i el text són de línies diferents (desfasament en files): CER del tall i contra el text de la fila i+d, d = -3..3;
#   2. el tall està desplaçat en el temps (rellotge del tifinag): finestra de l'àudio continu (tall anterior + tall + tall següent)
#      desplaçada δ segons, contra el text de la fila i;
#   3. el parlant no parla amazic estàndard (darija, francès) o el model no hi arriba: mostra de hipòtesi contra referència.
# Només lectura: no entrena res. Sortida: diag.json i un fitxer de mostra a ull.
import os, subprocess, sys
os.environ["CUDA_VISIBLE_DEVICES"] = "0"
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-U", "transformers>=4.44", "librosa", "soundfile", "accelerate"], check=False)
import collections, json, random, re, unicodedata
import numpy as np, torch, librosa

MOSTRA_PER_CAPITOL = 100
DESPLAÇAMENTS = [-2.0, -1.0, -0.5, 0.0, 0.5, 1.0, 2.0]
SR = 16000


def de_kaggle(nom):
    for arrel, _, fitxers in os.walk("/kaggle/input"):
        if nom in fitxers:
            return os.path.join(arrel, nom)
    return None


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


ROWS = de_kaggle("rows.json")
ADAPT = de_kaggle("adaptador_shi_zouhir_b.pt")
D_S = os.path.dirname(ROWS)
rows = json.load(open(ROWS, encoding="utf-8"))
for r in rows:
    r["k"] = int(r["id"].rsplit("_", 1)[1])
per_cap = collections.defaultdict(dict)
for r in rows:
    per_cap[r["slug"]][r["k"]] = r

from transformers import AutoModelForCTC, AutoProcessor
BASE, LLENGUA = "facebook/mms-1b-all", "shi"
proc = AutoProcessor.from_pretrained(BASE)
proc.tokenizer.set_target_lang(LLENGUA)
model = AutoModelForCTC.from_pretrained(BASE, ignore_mismatched_sizes=True)
model.load_adapter(LLENGUA)
model.load_state_dict(torch.load(ADAPT, map_location="cpu"), strict=False)
dev = "cuda" if torch.cuda.is_available() else "cpu"
model.to(dev).eval()
cau = {}


def ona(r):
    if r["id"] not in cau:
        w, _ = librosa.load(os.path.join(D_S, r["fitxer"]), sr=SR, mono=True)
        cau[r["id"]] = w
    return cau[r["id"]]


def transcriu(w):
    w = w[: 20 * SR]
    if len(w) < SR // 4:
        return ""
    ent = proc(w, sampling_rate=SR, return_tensors="pt").to(dev)
    with torch.no_grad():
        return rica(proc.batch_decode(model(**ent).logits.argmax(-1))[0])


def cer(ref, hyp):
    return distancia(ref, hyp) / max(1, len(ref))


sortida = {"capitols": {}, "mostra": []}
rnd = random.Random(1114)
for slug, d in sorted(per_cap.items()):
    ks = sorted(d)
    triats = rnd.sample(ks, min(MOSTRA_PER_CAPITOL, len(ks)))
    hip = {k: transcriu(ona(d[k])) for k in triats}
    res = {"split": d[ks[0]]["split"], "n": len(triats), "files_aptes": len(ks)}
    # 1. desfasament en files
    for dk in range(-3, 4):
        par = [(rica(d[k + dk]["tifinag"]), hip[k]) for k in triats if (k + dk) in d]
        res[f"fila{dk:+d}"] = (sum(distancia(a, b) for a, b in par) / max(1, sum(len(a) for a, _ in par)), len(par))
    # 2. desplaçament temporal dins l'àudio continu (només on les tres files són consecutives)
    for dl in DESPLAÇAMENTS:
        par = []
        for k in triats:
            if (k - 1) in d and (k + 1) in d:
                a, b, c = ona(d[k - 1]), ona(d[k]), ona(d[k + 1])
                cont = np.concatenate([a, b, c])
                ini = len(a) + int(dl * SR)
                if ini < 0 or ini + len(b) > len(cont):
                    continue
                par.append((rica(d[k]["tifinag"]), transcriu(cont[ini: ini + len(b)])))
        res[f"temps{dl:+.1f}"] = (sum(distancia(a, b) for a, b in par) / max(1, sum(len(a) for a, _ in par)), len(par))
    sortida["capitols"][slug] = res
    print(slug[:8], json.dumps(res), flush=True)
    for k in triats[:5]:
        sortida["mostra"].append({"slug": slug, "id": d[k]["id"], "ref": rica(d[k]["tifinag"]), "hip": hip[k], "cer": cer(rica(d[k]["tifinag"]), hip[k])})
    cau.clear()
json.dump(sortida, open("/kaggle/working/diag.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("fet")
