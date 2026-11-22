# Observació del cercle virtuós (#601, tools/lm/cercle_virtuos.py). RECERCA privada: no es publica res i no entrena res.
# Amb el model M_r (adaptador_inici.pt: MMS `shi` + l'adaptador de la ronda) fa, sobre TOTS els talls diana dels capítols llegits:
#   (a) concordança so<->text (rang+marge i esquelet consonàntic, tools/snrt/concordanca.py) -> concordanca.json
#   (b) alineació forçada CTC sobre la finestra anterior+tall+següent -> alineacio.json (al_ini/al_fi absoluts, en segons del vídeo)
# Mateixa lògica que concordanca_snrt.py i alineacio_forcada_snrt.py (ja provats), units perquè el model es carregui un sol cop.
# Sortida: /kaggle/working/{concordanca,concordanca_resum,alineacio,cercle_obs}.json; cercle_obs.json porta RUN_ID perquè el cercle
# comprovi que no recull una sortida vella.
RUN_ID = ""
import os, subprocess, sys
os.environ["CUDA_VISIBLE_DEVICES"] = "0"
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-U", "transformers>=4.44", "librosa", "soundfile"], check=False)
import collections, json, re, statistics, time, unicodedata
import numpy as np, torch, librosa


def de_kaggle(nom):
    for arrel, _, fitxers in os.walk("/kaggle/input"):
        if nom in fitxers:
            return os.path.join(arrel, nom)
    return None


MOD = de_kaggle("concordanca.py")
ROWS = de_kaggle("rows.json")
ADAPT = de_kaggle("adaptador_inici.pt")
assert MOD and ROWS and ADAPT, (MOD, ROWS, ADAPT)
sys.path.insert(0, os.path.dirname(MOD))
import concordanca as cc
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
print("adaptador", ADAPT, flush=True)
dev = "cuda" if torch.cuda.is_available() else "cpu"
model.to(dev).eval()
VOC = proc.tokenizer.get_vocab()
BLANK = proc.tokenizer.pad_token_id


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


def transcriu_curt(w):
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


def concordanca(files):
    per_cap = collections.defaultdict(list)
    for r in files:
        if r["alvo"] and rica(r["tifinag"]):
            per_cap[r["slug"]].append(r)
    sortida, resum = {}, {}
    for slug, rs in per_cap.items():
        rs.sort(key=lambda r: r["id"])
        hips = []
        for r in rs:
            w, _ = librosa.load(os.path.join(D, "audio", slug, r["id"] + ".flac"), sr=SR, mono=True)
            hips.append(transcriu_curt(w[:14 * SR]))
        textos = [rica(r["tifinag"]) for r in rs]
        cers, altes = [], 0
        for i, r in enumerate(rs):
            p = cc.puntua(hips[i], textos[i], cc.controls_de(i, textos))
            p["alta"] = cc.alta_certesa(p)
            p["hip"], p["text"] = hips[i], textos[i]
            sortida[r["id"]] = p
            cers.append(p["cer"])
            altes += p["alta"]
        resum[slug] = {"talls": len(rs), "alta": altes, "cer_mediana": round(statistics.median(cers), 3), "far": cc.far(hips, textos)}
        print("concordança", slug[:10], resum[slug], flush=True)
    return sortida, resum


def alinea_un(slug, rs, n, r):
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
        txt = rica(m["tifinag"])
        if tok and txt:
            tok.append(VOC.get("|"))
        ini = len(tok)
        tok.extend(x for x in (token_de(c) for c in txt) if x is not None)
        tros[m["id"]] = (ini, len(tok))
    e = {"id": r["id"], "slug": slug, "origen": origen, "finestra_s": round(len(buf) / SR, 1)}
    c0, c1 = tros[r["id"]]
    if c1 - c0 < 3 or len(tok) < 3:
        e["error"] = "text massa curt"
        return e
    try:
        lp = logprobs(buf)
        path = viterbi(lp, tok)
    except Exception as ex:   # noqa: BLE001
        e["error"] = str(ex)[:120]
        torch.cuda.empty_cache()
        return e
    if path is None:
        e["error"] = "text més llarg que l'àudio"
        return e
    et = (path - 1) // 2   # índex d'etiqueta (només on path és senar)
    senar = (path % 2) == 1
    fr = np.where(senar & (et >= c0) & (et < c1))[0]
    if not len(fr):
        e["error"] = "sense fotogrames"
        return e
    dt = 0.02
    al_ini, al_fi = origen + fr[0] * dt, origen + (fr[-1] + 1) * dt
    sub_ini, sub_fi = r["a"] + 0.25, r["b"] - 0.25
    sc = float(np.mean([lp[t, tok[et[t]]] for t in fr]))
    e.update({"sub_ini": sub_ini, "sub_fi": sub_fi, "al_ini": round(float(al_ini), 2), "al_fi": round(float(al_fi), 2),
              "desp_ini": round(float(al_ini - sub_ini), 2), "desp_fi": round(float(al_fi - sub_fi), 2), "score": round(sc, 3)})
    return e


def alineacio(files):
    per = collections.defaultdict(dict)
    for r in files:
        per[r["slug"]][r["n"]] = r
    sortida = []
    for slug, rs in per.items():
        for n, r in sorted(rs.items()):
            if r["alvo"]:
                sortida.append(alinea_un(slug, rs, n, r))
        print("alineació", slug[:10], len(sortida), flush=True)
    return sortida


t0 = time.time()
files = json.load(open(ROWS, encoding="utf-8"))
print("files", len(files), "diana", sum(r["alvo"] for r in files), flush=True)
conc, resum = concordanca(files)
json.dump(conc, open("/kaggle/working/concordanca.json", "w", encoding="utf-8"), ensure_ascii=False)
json.dump(resum, open("/kaggle/working/concordanca_resum.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("concordança feta en %.0f s" % (time.time() - t0), flush=True)
ali = alineacio(files)
json.dump(ali, open("/kaggle/working/alineacio.json", "w", encoding="utf-8"), ensure_ascii=False)
json.dump({"run_id": RUN_ID, "adaptador": os.path.basename(ADAPT), "talls": len(conc), "alineats": sum(1 for e in ali if "al_ini" in e),
           "errors": dict(collections.Counter(e["error"] for e in ali if "error" in e)), "segons": round(time.time() - t0)},
          open("/kaggle/working/cercle_obs.json", "w"))
print("FI", len(ali), "en %.0f s" % (time.time() - t0))
