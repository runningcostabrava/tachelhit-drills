# -*- coding: utf-8 -*-
"""El comú de la fàbrica de Tamazight TV (docs/recerca/tamazight-tv-fabrica-especificacio.md).

Arrel de dades `TD_TV` (al PC `C:\\Users\\josep\\Veus-tachelhit\\_escoltats\\tamazight_tv\\`, a l'ECS
`/root/tamazight_tv/`); un capítol és `TD_TV/<slug>/` amb `video.mp4` (720p amb so) i, si cal per al tifinag,
`video_1080.mp4`. Tot el que produeixen les etapes queda dins la carpeta del capítol (rutes relatives), llevat
d'una línia a `TD_TV/_informes/AAAA-MM-DD.md`. `estat.json` porta, per etapa, `inici`, `fi`, `comptes`, `versio`
i `error`. Les claus vénen de l'entorn: `.env` del backend al PC, `~/.env` o `.env` de la fàbrica a l'ECS.

Claus: DASHSCOPE_API_KEY + DASHSCOPE_BASE_URL (Model Studio: visió qwen3-vl-plus, text qwen3.8-max i qwen4-max),
DEEPSEEK_API_KEY (segon traductor), opcionals TD_SPACE_NLLB i TD_CATALEG (catàleg de producció per a la varietat).
"""
import io
import json
import os
import re
import subprocess
import sys
import time
import unicodedata
from collections import Counter

AQUI = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(AQUI)))
PY = sys.executable
VERSIO = "fabrica-2026-11-17"

#: Geometria dels subtítols de Tamazight TV en píxels d'un fotograma de 1280x720 (§4): tifinag y 588–608, àrab
#: y 615–650, dues línies centrades, blanc amb vora fosca. Per a una altra alçada es multiplica per alt/720.
BANDA_720 = (576, 660)     # la franja que es desa un cop per segon (les dues línies)
TIFINAG_720 = (580, 614)   # la línia del tifinag dins el fotograma (crop=1280:34:0:580)
ARAB_720 = (612, 656)      # la línia de l'àrab dins el fotograma (crop=1280:44:0:612)


def aplica_geometria(g):
    """Una sèrie amb una altra disposició de les línies (p. ex. l'àrab a dalt i el tifinag a sota, #601): canvia les tres franges d'aquest procés.
    g = {"BANDA_720": (y0, y1), "TIFINAG_720": (y0, y1), "ARAB_720": (y0, y1)}. Les etapes 02 i 05 la carreguen de `geometria.json` del capítol."""
    global BANDA_720, TIFINAG_720, ARAB_720
    BANDA_720, TIFINAG_720, ARAB_720 = tuple(g["BANDA_720"]), tuple(g["TIFINAG_720"]), tuple(g["ARAB_720"])


def geometria_de_linies(tif_720, arab_720):
    """De les y (escala 720p) del cos del tifinag i de la línia d'àrab a les tres franges: el retall del tifinag comença 8 px per sobre del cos i fa 34 px
    (com a la geometria per defecte, 588 → 580–614), el de l'àrab 3 px per sobre i 4 per sota, i la franja guardada les cobreix totes dues amb 4 px de marge."""
    t0 = int(round(tif_720[0])) - 8
    tif = (t0, t0 + 34)
    ara = (int(round(arab_720[0])) - 3, int(round(arab_720[1])) + 4)
    banda = (min(tif[0], ara[0]) - 4, max(tif[1], ara[1]) + 4)
    return {"BANDA_720": banda, "TIFINAG_720": tif, "ARAB_720": ara}


def desa_geometria(carpeta, g):
    with io.open(os.path.join(carpeta, "geometria.json"), "w", encoding="utf-8") as f:
        json.dump({k: list(v) for k, v in g.items()}, f)


def carrega_geometria(carpeta):
    """Si el capítol té `geometria.json` (disposició no estàndard), l'aplica. Torna True si n'hi havia."""
    p = os.path.join(carpeta, "geometria.json")
    if not os.path.exists(p):
        return False
    with io.open(p, encoding="utf-8") as f:
        aplica_geometria(json.load(f))
    return True


S_ASSEMBLEN = 0.75         # dues lectures del mateix subtítol no surten mai lletra per lletra iguals
MARGE_TALL = 0.25          # segons a cada banda del tall de so (§4, 03)


def td_tv():
    arrel = os.environ.get("TD_TV")
    if arrel:
        return arrel
    if os.name == "nt":
        return r"C:\Users\josep\Veus-tachelhit\_escoltats\tamazight_tv"
    return os.path.expanduser("~/tamazight_tv")


def carrega_env():
    """Les claus: TD_ENV; si no, el .env del backend del repositori (o del clon principal si som en un worktree),
    el de la fàbrica, ~/.env, el del directori actual. `override=True`: la màquina pot dur variables velles."""
    try:
        from dotenv import load_dotenv
    except ImportError:  # pragma: no cover
        return
    candidats = [os.environ.get("TD_ENV"), os.path.join(REPO, "backend", ".env")]
    pare = os.path.dirname(REPO)
    if pare.endswith(".worktrees"):
        candidats.append(os.path.join(os.path.dirname(pare), os.path.basename(pare)[:-len(".worktrees")], "backend", ".env"))
    candidats += [os.path.join(AQUI, ".env"), os.path.expanduser("~/.env"), os.path.join(os.getcwd(), ".env")]
    for p in candidats:
        if p and os.path.exists(p):
            load_dotenv(p, override=True)
            return


def slug_de(carpeta):
    return estat_llegeix(carpeta).get("slug") or os.path.basename(os.path.abspath(carpeta).rstrip("\\/"))


def video_de(carpeta, alt=None):
    """El vídeo del capítol: video.mp4 (o video_1080.mp4 si alt == 1080), o l'únic .mp4 de la carpeta."""
    if alt == 1080:
        p = os.path.join(carpeta, "video_1080.mp4")
        return p if os.path.exists(p) else None
    est = estat_llegeix(carpeta)
    cands = ([est["video"]] if est.get("video") else []) + ["video.mp4"]
    cands += sorted(f for f in os.listdir(carpeta) if f.lower().endswith((".mp4", ".mkv", ".webm")) and f != "video_1080.mp4")
    for c in cands:
        p = os.path.join(carpeta, c)
        if os.path.exists(p):
            return p
    return None


def mida_video(video):
    """(amplada, alçada, durada en segons) amb ffprobe."""
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height,duration",
                          "-of", "json", video], capture_output=True, text=True, check=True).stdout
    s = json.loads(out)["streams"][0]
    dur = s.get("duration")
    if not dur:
        out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", video],
                             capture_output=True, text=True, check=True).stdout
        dur = json.loads(out)["format"]["duration"]
    return int(s["width"]), int(s["height"]), float(dur)


def escala(alt):
    return alt / 720.0


def caixa(parell_720, alt, ample):
    y0, y1 = parell_720
    return (0, round(y0 * escala(alt)), ample, round(y1 * escala(alt)))


# ---------- estat.json ----------
def estat_llegeix(carpeta):
    p = os.path.join(carpeta, "estat.json")
    if os.path.exists(p):
        with io.open(p, encoding="utf-8") as f:
            return json.load(f)
    return {}


def _desa(carpeta, est):
    tmp = os.path.join(carpeta, "estat.json.tmp")
    with io.open(tmp, "w", encoding="utf-8") as f:
        json.dump(est, f, ensure_ascii=False, indent=1)
    os.replace(tmp, os.path.join(carpeta, "estat.json"))


def estat_desa(carpeta, **camps):
    est = estat_llegeix(carpeta)
    est.update(camps)
    _desa(carpeta, est)
    return est


def ara():
    return time.strftime("%Y-%m-%d %H:%M:%S")


def etapa_inici(carpeta, etapa):
    est = estat_llegeix(carpeta)
    d = est.setdefault(etapa, {})
    d.update({"inici": ara(), "fi": None, "versio": VERSIO, "error": None})
    d.setdefault("comptes", {})
    _desa(carpeta, est)


def etapa_fi(carpeta, etapa, comptes=None, error=None):
    est = estat_llegeix(carpeta)
    d = est.setdefault(etapa, {})
    d["fi"] = ara()
    d["error"] = error
    if comptes:
        d.setdefault("comptes", {}).update(comptes)
    _desa(carpeta, est)
    return d


def etapa_feta(carpeta, etapa):
    d = estat_llegeix(carpeta).get(etapa, {})
    return bool(d.get("fi")) and not d.get("error")


# ---------- jsonl ----------
def jsonl_llegeix(path):
    if not os.path.exists(path):
        return []
    with io.open(path, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def jsonl_escriu(path, files):
    tmp = path + ".tmp"
    with io.open(tmp, "w", encoding="utf-8") as f:
        for x in files:
            f.write(json.dumps(x, ensure_ascii=False) + "\n")
    os.replace(tmp, path)


def subtitols(carpeta):
    return jsonl_llegeix(os.path.join(carpeta, "subtitols.jsonl"))


def desa_subtitols(carpeta, files):
    jsonl_escriu(os.path.join(carpeta, "subtitols.jsonl"), files)


# ---------- text ----------
DIACRITICS = re.compile("[\u064b-\u065f\u0670\u0640]")


def nomes_arab(t):
    """Les lletres àrabs i prou, sense vocals curtes ni tatwil: el model les posa un segon sí i un segon no."""
    t = DIACRITICS.sub("", t or "")
    return re.sub(r"\s+", " ", "".join(c for c in t if "\u0600" <= c <= "\u06ff" or c == " ")).strip()


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


def s_assemblen(a, b, llindar=S_ASSEMBLEN):
    if not a or not b:
        return False
    return 1 - distancia(a, b) / max(len(a), len(b)) >= llindar


def chrf(hyp, ref, n=6, beta=2.0):
    """chrF (Popović 2015) sobre caràcters sense espais, n-grames 1..n, mitjana de P i R per ordre."""
    h = unicodedata.normalize("NFC", (hyp or "")).replace(" ", "").lower()
    r = unicodedata.normalize("NFC", (ref or "")).replace(" ", "").lower()
    if not h or not r:
        return 0.0
    ps, rs = [], []
    for k in range(1, n + 1):
        hg = Counter(h[i:i + k] for i in range(len(h) - k + 1))
        rg = Counter(r[i:i + k] for i in range(len(r) - k + 1))
        if not hg or not rg:
            continue
        com = sum((hg & rg).values())
        ps.append(com / max(1, sum(hg.values())))
        rs.append(com / max(1, sum(rg.values())))
    if not ps:
        return 0.0
    P, R = sum(ps) / len(ps), sum(rs) / len(rs)
    if P + R == 0:
        return 0.0
    return round((1 + beta ** 2) * P * R / (beta ** 2 * P + R), 4)


_NORM = [("ḍ", "d"), ("ṭ", "t"), ("ẓ", "z"), ("ṣ", "s"), ("ṛ", "r"), ("ḥ", "h"), ("gh", "ɣ"), ("γ", "ɣ"), ("ġ", "ɣ"),
         ("ch", "š"), ("sh", "š"), ("c", "š"), ("kh", "x"), ("3", "ɛ"), ("ε", "ɛ"), ("ʷ", ""), ("ⵯ", ""), ("e", ""),
         ("-", ""), ("'", ""), ("’", "")]


def normalitza(t):
    """§6.2: només per comparar ortografies; mai es guarda com a text."""
    t = unicodedata.normalize("NFC", (t or "")).lower()
    for a, b in _NORM:
        t = t.replace(a, b)
    return re.sub(r"(.)\1+", r"\1", t)


def translitera():
    """`to_forms` del backend (ⵜⵉⴼⵉⵏⴰⵖ → llatí net), o None si no és a mà."""
    sys.path.insert(0, os.path.join(REPO, "backend"))
    os.environ.setdefault("LEXICON_WARMUP", "0")
    try:
        from transliteration import to_forms
        return lambda t: to_forms(t)["clean_latin"]
    except Exception:
        return None


# ---------- xat (OpenAI-compatible: Model Studio i DeepSeek) ----------
def xat(model, messages, max_tokens=300, temperature=0.0, timeout=120, base=None, key=None, thinking=False, intents=4):
    """Una crida de xat amb reintents; torna (text, usage) o aixeca RuntimeError."""
    import requests
    key = key or os.environ.get("DASHSCOPE_API_KEY", "").strip()
    base = (base or os.environ.get("DASHSCOPE_BASE_URL", "")).rstrip("/")
    if not key or not base:
        raise RuntimeError("falten DASHSCOPE_API_KEY / DASHSCOPE_BASE_URL")
    body = {"model": model, "messages": messages, "max_tokens": max_tokens, "temperature": temperature}
    if model.startswith(("qwen3", "qwen4")):
        body["enable_thinking"] = thinking
    err = ""
    for intent in range(intents):
        try:
            r = requests.post(base + "/chat/completions", headers={"Authorization": "Bearer " + key}, json=body, timeout=timeout)
            if r.status_code == 200:
                d = r.json()
                return (d["choices"][0]["message"].get("content") or "").strip(), d.get("usage") or {}
            err = f"{r.status_code} {r.text[:120]}"
            if r.status_code not in (429, 500, 502, 503):
                break
        except Exception as e:  # xarxa
            err = str(e)[:120]
        time.sleep(4 + 8 * intent)
    raise RuntimeError(err)


def diu(log, *parts):
    s = " ".join(str(p) for p in parts)
    print(s, flush=True)
    if log is not None:
        log.write(s + "\n"); log.flush()


def obre_log(carpeta):
    return io.open(os.path.join(carpeta, "fabrica.log"), "a", encoding="utf-8")
