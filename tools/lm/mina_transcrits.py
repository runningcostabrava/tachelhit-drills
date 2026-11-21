# -*- coding: utf-8 -*-
"""Minar els transcrits automàtics dels vídeos en DÀRIJA del canal: el professor explica paraules
i regles de l'amazic en àrab marroquí, i el transcrit de YouTube, en aquests vídeos, és text de
debò (≥ 20 paraules per minut i ≥ 20 % de mots de funció del dàrija, segons `cataleg_unic.py`;
en els vídeos parlats en amazic és brossa).

Per a cada vídeo, el model llegeix el transcrit sencer i en treu, en JSON, cada paraula o
expressió amaziga que el professor ESMENTA I EXPLICA: tal com surt al transcrit (lletres àrabs),
la forma llatina si el professor la lletreja o es pot deduir amb seguretat, el significat que
ell en dóna (en àrab, tal com ho diu, i en català), i la frase del transcrit on ho diu, perquè
es pugui comprovar. El que el professor no explica, no s'inventa.

Això és «autoglossa» a escala: la font és el parlant mateix. Material de tercers: instrument de
validació; res no entra a la biblioteca.

Models: DeepSeek (`deepseek-chat`, t = 0) per defecte; si DeepSeek torna un error de quota
(402/429), el vídeo passa a `qwen3.8-max` de Model Studio amb el MATEIX prompt. Cada línia de
sortida diu quin model l'ha minada (`model`) i quantes fitxes ha costat (`fitxes`), perquè
l'auditoria (`audita_coneixement.py`) pugui triar l'altre model.

ÚS: mina_transcrits.py <carpeta de vtt> <cataleg.jsonl> <sortida.jsonl> [quants]
        [--nomes ids.json]          només aquests vídeos (llista JSON d'ids)
        [--ja mina_a.jsonl …]       vídeos ja minats en altres fitxers: no es repeteixen
        [--fils N]                  vídeos en paral·lel (per defecte 1)
        [--model deepseek|qwen]     model de partida (per defecte deepseek)
Claus: `TFA_ENV` (el .env del backend, amb DASHSCOPE_*) i `DEEPSEEK_ENV` (un .env amb
DEEPSEEK_API_KEY), si no són al .env de l'arrel del backend.
"""
import glob
import io
import json
import os
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import requests

ARREL = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ARREL, "backend"))
os.chdir(os.path.join(ARREL, "backend"))
from dotenv import load_dotenv      # noqa: E402
load_dotenv(os.environ.get("TFA_ENV") or os.path.join(ARREL, "backend", ".env"), override=True)
if os.environ.get("DEEPSEEK_ENV"):
    load_dotenv(os.environ["DEEPSEEK_ENV"], override=False)

SYS = """Ets un lingüista que llegeix la transcripció automàtica (en àrab marroquí, dàrija) d'una classe
en vídeo sobre la llengua amaziga (tamazight). El professor parla en dàrija i hi esmenta paraules,
expressions i regles de l'amazic. La transcripció és automàtica: té errors, i les paraules amazigues
hi surten escrites amb lletres àrabs tal com la màquina les ha sentit.

Treu-ne NOMÉS el que el professor explica explícitament: una paraula o expressió amaziga i el
significat o la funció que ell en dóna. Res que no sigui al text. Per a cada una torna un objecte:
  "amazic_ar": la paraula tal com surt al transcrit (lletres àrabs)
  "amazic_llati": la forma en lletres llatines segons la convenció IRCAM (a b c d ḍ e f g gʷ ɣ h ḥ i j k kʷ l m n q r ṛ s ṣ t ṭ u w x y z ẓ ɛ), NOMÉS si el professor la lletreja o la forma és inequívoca; si no, ""
  "significat_ar": el significat o funció en àrab, amb les paraules del professor
  "significat_ca": el mateix en català, curt
  "mena": "paraula" | "expressió" | "regla" | "afix"
  "on": la frase del transcrit (≤ 25 paraules) on ho diu
Torna una llista JSON i res més. Si no hi ha res, torna []."""

MODELS = {"deepseek": ("deepseek-chat", "https://api.deepseek.com/v1", "DEEPSEEK_API_KEY"),
          "qwen": ("qwen3.8-max", None, "DASHSCOPE_API_KEY")}
#: Els errors que volen dir «aquest proveïdor no et servirà ara», no «aquest vídeo és dolent».
QUOTA = ("402", "429", "quota", "credits", "rate limit", "insufficient", "resource_exhausted")


def crida(nom, user, timeout=180):
    """Una crida de xat (API d'OpenAI) al model `nom`; torna (text, fitxes_in, fitxes_out).
    Reintenta els errors de servidor; aixeca RuntimeError amb el codi si no se'n surt."""
    model, base, clau = MODELS[nom]
    base = base or os.environ["DASHSCOPE_BASE_URL"].rstrip("/")
    key = os.environ[clau].strip()
    body = {"model": model, "messages": [{"role": "system", "content": SYS}, {"role": "user", "content": user}],
            "max_tokens": 4000, "temperature": 0}
    if model.startswith("qwen"):
        body["enable_thinking"] = False
    err = ""
    for intent in range(4):
        try:
            r = requests.post(base + "/chat/completions", headers={"Authorization": "Bearer " + key}, json=body, timeout=timeout)
        except Exception as e:
            err = f"{type(e).__name__}: {str(e)[:80]}"
            time.sleep(3 + 5 * intent)
            continue
        if r.status_code == 200:
            d = r.json()
            u = d.get("usage") or {}
            return ((d["choices"][0]["message"].get("content") or "").strip(), u.get("prompt_tokens", 0), u.get("completion_tokens", 0))
        err = f"{r.status_code} {r.text[:120]}"
        if r.status_code in (500, 502, 503) or (r.status_code == 429 and intent < 2):
            time.sleep(5 + 10 * intent)
            continue
        break
    raise RuntimeError(err)


def text_del_vtt(cami):
    linies, vist = [], set()
    for l in io.open(cami, encoding="utf-8", errors="replace"):
        l = re.sub(r"<[^>]+>", "", l).strip()
        if not l or "-->" in l or l.startswith(("WEBVTT", "Kind:", "Language:")) or l.isdigit():
            continue
        if l not in vist:
            vist.add(l)
            linies.append(l)
    return " ".join(linies)


def trossos_de(text):
    """Els directes duren hores: es minen a trossos de ~12.000 caràcters, tallats per espai."""
    out, i = [], 0
    while i < len(text):
        j = min(len(text), i + 12000)
        if j < len(text):
            j = text.rfind(" ", i, j) or j
        out.append(text[i:j])
        i = j
    return out


def mina_video(vid, titol, text, model_inicial):
    """Torna la línia de sortida d'un vídeo: ítems, model que els ha tret i fitxes gastades."""
    items, r, nom = [], "", model_inicial
    fitxes = {"in": 0, "out": 0}
    trossos = trossos_de(text)
    for k, tros in enumerate(trossos):
        q = f"TÍTOL DEL VÍDEO: {titol}\n\nTRANSCRIPCIÓ (part {k + 1} de {len(trossos)}):\n{tros}"
        for _ in range(2):
            try:
                r, fi, fo = crida(nom, q)
                fitxes["in"] += fi
                fitxes["out"] += fo
                m = re.search(r"\[.*\]", r or "", flags=re.S)
                for it in (json.loads(m.group(0)) if m else []):
                    it["part"] = k + 1
                    items.append(it)
                break
            except Exception as e:
                r = f"(error {type(e).__name__}: {str(e)[:120]})"
                if nom == "deepseek" and any(s in str(e).lower() for s in QUOTA):
                    print(f"  {vid}: DeepSeek sense quota ({str(e)[:40]}), passo a qwen3.8-max", flush=True)
                    nom = "qwen"
                    continue
                break
    return {"video": vid, "titol": titol, "paraules_transcrit": len(text.split()), "items": items,
            "cru": None if items else (r or "")[:300], "model": MODELS[nom][0], "fitxes": fitxes}


if __name__ == "__main__":
    args = sys.argv[1:]
    def opcio(nom, quants=1):
        if nom not in args:
            return None
        i = args.index(nom)
        vals = args[i + 1:i + 1 + quants] if quants else []
        j = i + 1
        while quants == 0 and j < len(args) and not args[j].startswith("--"):
            vals.append(args[j]); j += 1
        del args[i:j if quants == 0 else i + 1 + quants]
        return vals
    nomes = opcio("--nomes")
    ja = opcio("--ja", 0) or []
    fils = int((opcio("--fils") or ["1"])[0])
    model_inicial = (opcio("--model") or ["deepseek"])[0]
    carpeta, cataleg, fora = args[0], args[1], args[2]
    quants = int(args[3]) if len(args) > 3 else 9999
    titols = {}
    for l in io.open(cataleg, encoding="utf-8"):
        d = json.loads(l)
        titols[d["id"]] = d.get("titol") or ""
    fets = set()
    for f in [fora] + ja:
        if os.path.exists(f):
            for l in io.open(f, encoding="utf-8"):
                fets.add(json.loads(l)["video"])
    volguts = set(json.load(io.open(nomes[0], encoding="utf-8"))) if nomes else None
    feines = []
    for cami in sorted(glob.glob(os.path.join(carpeta, "*.vtt"))):
        vid = os.path.basename(cami).split(".")[0]
        if vid in fets or (volguts is not None and vid not in volguts):
            continue
        text = text_del_vtt(cami)
        if len(text.split()) < 60:
            continue
        fets.add(vid)
        feines.append((vid, text))
        if len(feines) >= quants:
            break
    print(f"{len(feines)} vídeos a minar amb {model_inicial}, {fils} fils", flush=True)
    pany = threading.Lock()
    tot = {"in": 0, "out": 0}
    with io.open(fora, "a", encoding="utf-8") as g, ThreadPoolExecutor(max_workers=fils) as ex:
        def una(f):
            vid, text = f
            d = mina_video(vid, titols.get(vid, ""), text, model_inicial)
            with pany:
                g.write(json.dumps(d, ensure_ascii=False) + "\n")
                g.flush()
                tot["in"] += d["fitxes"]["in"]
                tot["out"] += d["fitxes"]["out"]
                print(f"{vid} {d['paraules_transcrit']:5} mots → {len(d['items']):3} ítems  {d['model']:13} {titols.get(vid, '')[:50]}", flush=True)
        list(ex.map(una, feines))
    print(f"fet: {len(feines)} vídeos nous · fitxes {tot['in']} dins / {tot['out']} fora")
