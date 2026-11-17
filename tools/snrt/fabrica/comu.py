# -*- coding: utf-8 -*-
"""El comú de la fàbrica de la SNRT: la carpeta d'un vídeo, l'estat, les claus i les distàncies.

Una carpeta per vídeo. Hi ha d'haver el `.mp4` (el que diu `estat.json["video"]`, o `video.mp4`, o l'únic
`.mp4` de la carpeta). Tot el que produeixen les etapes queda dins la carpeta, amb rutes relatives, i
`estat.json` porta els comptes de cada etapa. Res és de Windows: les rutes són relatives a la carpeta i
les claus vénen de l'entorn (`.env` del backend al PC, `.env` de la carpeta de la fàbrica a l'ECS).

Claus que llegeix: DASHSCOPE_API_KEY + DASHSCOPE_BASE_URL (Model Studio: visió qwen3-vl-plus i
qwen3.8-max), DEEPSEEK_API_KEY (segon traductor de l'àrab), i opcionalment TD_SPACE_NLLB (el Space del
traductor amazic) i TD_CATALEG (el catàleg de producció per a l'estimació de varietat).
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

#: Geometria dels subtítols de Tamazight TV, en píxels d'un fotograma de 1280x720 (mesurada a «Illy» i a
#: l'entrevista «Tadfi n Tskla»: dues línies centrades, blanc amb vora fosca, tifinag a dalt i àrab a sota).
#: Per a una altra alçada es multiplica per alt/720.
BANDA_720 = (576, 660)     # la franja que es desa un cop per segon (les dues línies)
TIFINAG_720 = (580, 614)   # la línia del tifinag dins el fotograma
ARAB_720 = (612, 656)      # la línia de l'àrab dins el fotograma
S_ASSEMBLEN = 0.75         # dues lectures del mateix subtítol no surten mai lletra per lletra iguals


def carrega_env():
    """Les claus: TD_ENV si està definit; si no, el .env del backend del repositori, el de la fàbrica, el
    del directori actual. `override=True` perquè la màquina pot dur variables de sistema velles."""
    try:
        from dotenv import load_dotenv
    except ImportError:  # pragma: no cover
        return
    candidats = [os.environ.get("TD_ENV"), os.path.join(REPO, "backend", ".env"), os.path.join(AQUI, ".env"),
                 os.path.join(os.getcwd(), ".env")]
    # en un worktree de git (app2/tachelhit-drills.worktrees/<nom>/) el .env és al clon principal del costat
    pare = os.path.dirname(REPO)
    if pare.endswith(".worktrees"):
        candidats.append(os.path.join(os.path.dirname(pare), os.path.basename(pare)[:-len(".worktrees")], "backend", ".env"))
    for p in candidats:
        if p and os.path.exists(p):
            load_dotenv(p, override=True)
            return


def video_de(carpeta):
    est = estat_llegeix(carpeta)
    cands = [est.get("video")] if est.get("video") else []
    cands += ["video.mp4"] + sorted(f for f in os.listdir(carpeta) if f.lower().endswith((".mp4", ".mkv", ".webm")))
    for c in cands:
        p = os.path.join(carpeta, c)
        if c and os.path.exists(p):
            return p
    sys.exit(f"no trobo cap vídeo a {carpeta}")


def mida_video(video):
    """(amplada, alçada, durada en segons) amb ffprobe."""
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height,duration",
                          "-of", "json", video], capture_output=True, text=True, check=True).stdout
    s = json.loads(out)["streams"][0]
    return int(s["width"]), int(s["height"]), float(s.get("duration") or 0)


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


def estat_desa(carpeta, etapa=None, **camps):
    est = estat_llegeix(carpeta)
    if etapa:
        d = est.setdefault(etapa, {})
        d.update(camps)
        d["actualitzat"] = time.strftime("%Y-%m-%d %H:%M:%S")
    else:
        est.update(camps)
    tmp = os.path.join(carpeta, "estat.json.tmp")
    with io.open(tmp, "w", encoding="utf-8") as f:
        json.dump(est, f, ensure_ascii=False, indent=1)
    os.replace(tmp, os.path.join(carpeta, "estat.json"))
    return est


def etapa_feta(carpeta, etapa):
    return bool(estat_llegeix(carpeta).get(etapa, {}).get("fet"))


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


# ---------- text ----------
DIACRITICS = re.compile("[ً-ٰٟـ]")


def nomes_arab(t):
    """Les lletres àrabs i prou, sense vocals curtes ni tatwil: el model les posa un segon sí i un segon no."""
    t = DIACRITICS.sub("", t or "")
    return re.sub(r"\s+", " ", "".join(c for c in t if "؀" <= c <= "ۿ" or c == " ")).strip()


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


# ---------- Model Studio (OpenAI-compatible) ----------
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
