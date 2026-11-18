# Diagnòstic d'alineació forçada (#601, 18-11-2026). RECERCA privada: no es publica res i no entrena res.
# Pregunta: els talls de la SNRT tenen els límits ben posats? Per a cada tall «diana» es munta una finestra amb el tall
# anterior, ell i el següent (posats al seu temps absolut), s'alinea el text dels tres JUNTS amb el model acústic que ja tenim
# (MMS `shi` + adaptador H4b, CTC Viterbi forçat) i es mira on cau realment el text de la diana: desplaçament respecte als límits
# del subtítol. Després es torna a tallar l'àudio pel lloc on el model sent el text i es retranscriu, per comparar el CER
# d'esquelet abans i després (si baixa molt, el problema eren els límits; si no, és el model o els subtítols).
# Sortida: /kaggle/working/alineacio.json
import os, subprocess, sys
os.environ["CUDA_VISIBLE_DEVICES"] = "0"
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-U", "transformers>=4.44", "librosa", "soundfile"], check=False)
import collections, json, re, unicodedata
import numpy as np, torch, librosa


def de_kaggle(nom):
    for arrel, _, fitxers in os.walk("/kaggle/input"):
        if nom in fitxers:
            return os.path.join(arrel, nom)
    return None


ROWS = de_kaggle("rows.json")
ADAPT = de_kaggle("adaptador_shi_zouhir_b.pt")
assert ROWS and ADAPT, (ROWS, ADAPT)
D = os.path.dirname(ROWS)

TIF_RIC = {"ⴰ": "a", "ⴱ": "b", "ⴳ": "g", "ⴷ": "d", "ⴹ": "ḍ", "ⴻ": "e", "ⴼ": "f", "ⴽ": "k", "ⵀ": "h", "ⵃ": "ḥ", "ⵄ": "ε",
           "ⵅ": "ḫ", "ⵇ": "q", "ⵉ": "i", "ⵊ": "j", "ⵍ": "l", "ⵎ": "m", "ⵏ": "n", "ⵓ": "u", "ⵔ": "r", "ⵕ": "r", "ⵖ": "ġ",
           "ⵙ": "s", "ⵚ": "ṣ", "ⵛ": "š", "ⵜ": "t", "ⵟ": "ṭ", "ⵡ": "w", "ⵢ": "y", "ⵣ": "z", "ⵥ": "ẓ", "ⵯ": "w"}
LLATI_RIC = {"ɣ": "ġ", "γ": "ġ", "ɛ": "ε", "ṛ": "r", "c": "š", "x": "ḫ", "χ": "ḫ", "ž": "j", "ǧ": "j", "ʷ": "w", "v": "f", "p": "b", "o": "u"}
RIC_TOKEN = {"ġ": ["ɣ", "ġ"], "ε": ["ɛ", "ε"], "š": ["c", "š"], "ḫ": ["x", "ḫ"]}


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
VOC = proc.tokenizer.get_vocab()
BLANK = proc.tokenizer.pad_token_id
print("vocab", len(VOC), "blank", BLANK, "mostra", list(VOC)[:40], flush=True)


def token_de(c):
    if c == " ":
        return VOC.get("|")
    for cand in RIC_TOKEN.get(c, [c]):
        if cand in VOC:
            return VOC[cand]
    return None


def logprobs(w):
    ent = proc(w, sampling_rate=SR, return_tensors="pt").to(dev)
    with torch.no_grad():
        lg = model(**ent).logits[0].float()
    return torch.log_softmax(lg, -1).cpu().numpy()


def transcriu(w):
    if len(w) < SR // 2:
        return ""
    ent = proc(w, sampling_rate=SR, return_tensors="pt").to(dev)
    with torch.no_grad():
        ids = model(**ent).logits.argmax(-1)
    return rica(proc.batch_decode(ids)[0])


def viterbi(lp, tok):
    """Alineació forçada CTC (numpy). lp: (T, V) log-probs; tok: llista d'ids. -> estat per fotograma o None si no hi cap."""
    T, L = lp.shape[0], len(tok)
    S = 2 * L + 1
    lab = np.full(S, BLANK, dtype=np.int64)
    lab[1::2] = tok
    if T < L:
        return None
    NEG = -1e30
    a = np.full(S, NEG)
    a[0] = lp[0, BLANK]
    if S > 1:
        a[1] = lp[0, lab[1]]
    bp = np.zeros((T, S), dtype=np.int8)
    salta = np.zeros(S, dtype=bool)
    salta[3::2] = lab[3::2] != lab[1:-2:2]   # es pot saltar el blanc entre dues etiquetes diferents
    for t in range(1, T):
        c0 = a
        c1 = np.concatenate(([NEG], a[:-1]))
        c2 = np.concatenate(([NEG, NEG], a[:-2]))
        c2 = np.where(salta, c2, NEG)
        st = np.stack([c0, c1, c2])
        arg = st.argmax(0)
        a = st[arg, np.arange(S)] + lp[t, lab]
        bp[t] = arg
    s = S - 1 if a[S - 1] >= a[S - 2] else S - 2
    path = np.zeros(T, dtype=np.int64)
    for t in range(T - 1, -1, -1):
        path[t] = s
        s -= int(bp[t, s])
    return path


files = json.load(open(ROWS, encoding="utf-8"))
per = collections.defaultdict(dict)
for r in files:
    per[r["slug"]][r["n"]] = r
sortida = []
for slug, rs in per.items():
    for n, r in sorted(rs.items()):
        if not r["target"]:
            continue
        membres = [rs[m] for m in (n - 1, n, n + 1) if m in rs]
        origen = min(m["a"] for m in membres)
        fi = max(m["b"] for m in membres)
        buf = np.zeros(int((fi - origen) * SR) + SR, dtype=np.float32)
        for m in membres:
            w, _ = librosa.load(os.path.join(D, "audio", slug, m["id"] + ".flac"), sr=SR, mono=True)
            i0 = int((m["a"] - origen) * SR)
            buf[i0:i0 + len(w)] = w[:len(buf) - i0]
        tok, tros = [], {}
        for m in membres:
            t0 = len(tok)
            txt = rica(m["tifinag"])
            if tok and txt:
                tok.append(VOC.get("|"))
            ini = len(tok)
            tok.extend(x for x in (token_de(c) for c in txt) if x is not None)
            tros[m["id"]] = (ini, len(tok))
        e = {"id": r["id"], "slug": slug, "text": rica(r["tifinag"]), "hip_vell": r["hip_vell"], "cer_vell": r["cer_vell"], "finestra_s": round(len(buf) / SR, 1)}
        c0, c1 = tros[r["id"]]
        if c1 - c0 < 3 or len(tok) < 3:
            e["error"] = "text massa curt"
            sortida.append(e)
            continue
        try:
            lp = logprobs(buf)
            path = viterbi(lp, tok)
        except Exception as ex:   # noqa: BLE001
            e["error"] = str(ex)[:120]
            sortida.append(e)
            continue
        if path is None:
            e["error"] = "text més llarg que l'àudio"
            sortida.append(e)
            continue
        et = (path - 1) // 2   # índex d'etiqueta (només on path és senar)
        senar = (path % 2) == 1
        fr = np.where(senar & (et >= c0) & (et < c1))[0]
        if not len(fr):
            e["error"] = "sense fotogrames"
            sortida.append(e)
            continue
        dt = 0.02
        al_ini, al_fi = origen + fr[0] * dt, origen + (fr[-1] + 1) * dt
        sub_ini, sub_fi = r["a"] + 0.25, r["b"] - 0.25
        sc = float(np.mean([lp[t, tok[et[t]]] for t in fr]))
        e.update({"sub_ini": sub_ini, "sub_fi": sub_fi, "al_ini": round(float(al_ini), 2), "al_fi": round(float(al_fi), 2),
                  "desp_ini": round(float(al_ini - sub_ini), 2), "desp_fi": round(float(al_fi - sub_fi), 2), "score": round(sc, 3)})
        i0 = max(0, int((al_ini - 0.3 - origen) * SR))
        i1 = min(len(buf), int((al_fi + 0.3 - origen) * SR))
        e["hip_nou"] = transcriu(buf[i0:i1])
        sortida.append(e)
    print(slug[:10], len(sortida), flush=True)
json.dump(sortida, open("/kaggle/working/alineacio.json", "w", encoding="utf-8"), ensure_ascii=False)
print("FI", len(sortida))
