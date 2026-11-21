# -*- coding: utf-8 -*-
"""Auditoria del coneixement del professor (sortida de `coneixement_darija.py`): per a cada ítem,
un segon model, independent del que l'ha extret, rep la frase `on` amb ±2 rètols del vtt de
context i l'ítem, i diu si el professor diu exactament això.

  · extret per DeepSeek  → audita qwen3.8-max (Model Studio)
  · extret per Qwen      → audita deepseek-chat

Veredictes: TRIA (ho diu exactament), FORA (no ho diu o ho diu diferent), NO-HO-SE. Una línia per
ítem a `coneixement_auditat.jsonl` (clau video:idx; reprèn si ja n'hi ha), amb el model auditor, el
que ha dit i les fitxes gastades. Després, `coneixement_darija_confirmat.md` només amb els TRIA, en la
mateixa forma que `coneixement_darija.md`.

Les sortides de màquina són candidats, no glosses: un TRIA vol dir que dos models independents
llegeixen el mateix al transcrit automàtic, no que el professor tingui raó ni que l'ASR de YouTube
l'hagi sentit bé.

ÚS: audita_coneixement.py <coneixement_darija.jsonl> --vtt <carpeta> --fora <coneixement_auditat.jsonl>
        [--fils N] [--limit N] [--md <coneixement_darija_confirmat.md>]
Claus: `TFA_ENV` (DASHSCOPE_*) i `DEEPSEEK_ENV` (DEEPSEEK_API_KEY), com a `mina_transcrits.py`.
"""
import collections
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
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv      # noqa: E402
load_dotenv(os.environ.get("TFA_ENV") or os.path.join(ARREL, "backend", ".env"), override=True)
if os.environ.get("DEEPSEEK_ENV"):
    load_dotenv(os.environ["DEEPSEEK_ENV"], override=False)
from coneixement_darija import cues     # noqa: E402

MODELS = {"deepseek": ("deepseek-chat", "https://api.deepseek.com/v1", "DEEPSEEK_API_KEY"),
          "qwen": ("qwen3.8-max", None, "DASHSCOPE_API_KEY")}
#: qui audita què: l'altre
AUDITOR_DE = {"deepseek-chat": "qwen", "qwen3.8-max": "deepseek"}

SISTEMA = """Ets un auditor independent. T'arriba un tros de la transcripció automàtica de YouTube (en àrab
marroquí, dàrija, lletres àrabs) d'una classe en vídeo sobre la llengua amaziga, i un ÍTEM que un altre
model n'ha extret: una paraula, expressió, afix o regla de l'amazic i el significat o la funció que,
segons l'ítem, el professor li dóna.

La teva feina és decidir si el professor DIU EXACTAMENT AIXÒ en aquest tros. Respon amb UNA sola línia:
- «TRIA» si la forma amaziga (lletres àrabs) és al tros i el significat o la funció que l'ítem li dóna és
  el que el professor en diu (en dàrija o en àrab).
- «FORA» si el professor no ho diu, o ho diu diferent: el significat és un altre, la forma no surt al tros,
  l'ítem barreja dues paraules, o la "paraula amaziga" és en realitat un mot del dàrija o de l'àrab
  que el professor no presenta com a amazic.
- «NO-HO-SE» si el tros no permet decidir (transcripció trencada, el significat es diu fora del tros).

Després del veredicte pots afegir, separat per un espai, un motiu en català de 15 paraules com a molt.
La forma en lletres llatines no es pot comprovar al transcrit (és àrab): no la jutgis, llevat que
contradigui clarament la forma àrab. No diguis TRIA per cortesia: si dubtes, NO-HO-SE."""


def prompt(x, context):
    it = [f"forma amaziga (transcrit): {x.get('amazic_ar')}"]
    if x.get("amazic_llati"):
        it.append(f"forma llatina proposada: {x['amazic_llati']}")
    it.append(f"significat/funció segons l'ítem (àrab): {x.get('significat_ar')}")
    it.append(f"significat/funció segons l'ítem (català): {x.get('significat_ca')}")
    it.append(f"mena: {x.get('mena')}")
    return ("TROS DEL TRANSCRIT (uns 15 segons abans i després del moment on el model diu que ho diu):\n" + context +
            "\n\nFRASE ON L'ÍTEM DIU QUE HO DIU:\n" + (x.get("on") or "") +
            "\n\nÍTEM:\n" + "\n".join("- " + l for l in it) +
            "\n\nLa teva resposta (TRIA / FORA / NO-HO-SE, i el motiu):")


#: Context al voltant del rètol on ho diu, en segons. Els rètols automàtics de YouTube són rodants
#: (cada línia surt sola i després enganxada a la següent) i duren ~3 s: ±2 rètols serien ±3 s de
#: paraula, massa poc per sentir el significat. ±15 s són uns 4-5 rètols reals per banda.
FINESTRA = 15.0


def context_de(x, rets):
    """El tros del vtt al voltant del rètol que conté la frase `on`, sense les repeticions dels
    rètols rodants (un rètol contingut al següent es deixa caure)."""
    if not rets or x.get("de") is None:
        return x.get("on") or ""
    tros = [(de, a, t) for de, a, t in rets if de >= x["de"] - FINESTRA and de <= (x.get("a") or x["de"]) + FINESTRA]
    if not tros:
        return x.get("on") or ""
    nets = [t for k, (_, _, t) in enumerate(tros) if k + 1 >= len(tros) or t not in tros[k + 1][2]]
    return "\n".join(nets)


def crida(nom, user, timeout=120):
    model, base, clau = MODELS[nom]
    base = base or os.environ["DASHSCOPE_BASE_URL"].rstrip("/")
    key = os.environ[clau].strip()
    body = {"model": model, "messages": [{"role": "system", "content": SISTEMA}, {"role": "user", "content": user}],
            "max_tokens": 200, "temperature": 0}
    if model.startswith("qwen"):
        body["enable_thinking"] = False
    t0, err = time.time(), ""
    for intent in range(4):
        try:
            r = requests.post(base + "/chat/completions", headers={"Authorization": "Bearer " + key}, json=body, timeout=timeout)
            if r.status_code == 200:
                d = r.json()
                u = d.get("usage") or {}
                return {"dit": (d["choices"][0]["message"].get("content") or "").strip(), "s": round(time.time() - t0, 2),
                        "in": u.get("prompt_tokens", 0), "out": u.get("completion_tokens", 0)}
            err = f"{r.status_code} {r.text[:120]}"
            if r.status_code in (429, 500, 502, 503):
                time.sleep(5 + 10 * intent)
                continue
            break
        except Exception as e:
            err = f"{type(e).__name__}: {str(e)[:100]}"
            time.sleep(3 + 5 * intent)
    return {"dit": "", "s": round(time.time() - t0, 2), "error": err}


def veredicte(dit):
    l = next((l.strip(" -*`\"«»") for l in dit.splitlines() if l.strip()), "")
    u = l.upper().replace("É", "E").replace("È", "E")
    if u.startswith("TRIA"):
        return "tria"
    if u.startswith("FORA"):
        return "fora"
    if u.startswith("NO-HO-SE") or u.startswith("NO HO SE"):
        return "no-ho-se"
    return "altre" if l else "buit"


def escriu_md(items, veredictes, cami):
    per_video = collections.OrderedDict()
    for x in items:
        v = veredictes.get(f"{x['video']}:{x['idx']}")
        if v and v["veredicte"] == "tria":
            per_video.setdefault(x["video"], []).append(x)
    n = sum(len(xs) for xs in per_video.values())
    linies = ["# El que el professor explica en dàrija, confirmat per un segon model\n",
              f"Només els ítems on l'auditor independent (qwen3.8-max per als extrets per DeepSeek, i a l'inrevés) diu TRIA: "
              f"{n} ítems de {len(items)} auditats, {len(per_video)} vídeos. Cada línia: la forma al transcrit (lletres àrabs), la "
              "forma llatina si es pot deduir, el significat que el professor dóna, i l'enllaç al segon on ho diu. Dos models que "
              "llegeixen el mateix al transcrit automàtic: candidats amb procedència, no glosses. Material de tercers.\n"]
    for vid, xs in per_video.items():
        linies.append(f"\n## {xs[0].get('titol') or vid} — `{vid}` ({len(xs)} ítems)\n")
        for mena in ("regla", "afix", "expressió", "paraula"):
            ys = [x for x in xs if x.get("mena") == mena]
            if not ys:
                continue
            linies.append(f"\n**{mena}**\n")
            for x in ys:
                lat = f" *{x['amazic_llati']}*" if x.get("amazic_llati") else ""
                enll = f" [{int(x['de'])//60}:{int(x['de'])%60:02d}]({x['url']})" if x.get("url") else ""
                linies.append(f"- **{x.get('amazic_ar')}**{lat} — {x.get('significat_ca')}{enll}")
    io.open(cami, "w", encoding="utf-8").write("\n".join(linies) + "\n")
    return n, len(per_video)


if __name__ == "__main__":
    args = sys.argv[1:]
    def opcio(nom, defecte=None):
        if nom in args:
            i = args.index(nom)
            v = args[i + 1]
            del args[i:i + 2]
            return v
        return defecte
    vtt = opcio("--vtt")
    fora = opcio("--fora")
    fils = int(opcio("--fils", "3"))
    limit = int(opcio("--limit", "0"))
    md = opcio("--md")
    items = [json.loads(l) for l in io.open(args[0], encoding="utf-8")]
    if limit:
        items = items[:limit]
    fets = {}
    if os.path.exists(fora):
        for l in io.open(fora, encoding="utf-8"):
            if l.strip():
                v = json.loads(l)
                fets[v["clau"]] = v
    rets_cache = {}
    def rets_de(vid):
        if vid not in rets_cache:
            cami = os.path.join(vtt, vid + ".ar-orig.vtt")
            rets_cache[vid] = cues(cami) if os.path.exists(cami) else []
        return rets_cache[vid]
    feines = [x for x in items if f"{x['video']}:{x['idx']}" not in fets]
    print(f"{len(items)} ítems · {len(fets)} ja auditats · {len(feines)} pendents · {fils} fils", flush=True)
    pany = threading.Lock()
    tot = {"in": 0, "out": 0, "n": 0}
    t0 = time.time()
    with io.open(fora, "a", encoding="utf-8") as out, ThreadPoolExecutor(max_workers=fils) as ex:
        def una(x):
            nom = AUDITOR_DE.get(x.get("model") or "deepseek-chat", "qwen")
            r = crida(nom, prompt(x, context_de(x, rets_de(x["video"]))))
            v = {"clau": f"{x['video']}:{x['idx']}", "video": x["video"], "idx": x["idx"], "extret_per": x.get("model"),
                 "auditor": MODELS[nom][0], "veredicte": veredicte(r.get("dit", "")) if not r.get("error") else "error", **r}
            with pany:
                out.write(json.dumps(v, ensure_ascii=False) + "\n")
                out.flush()
                fets[v["clau"]] = v
                tot["in"] += r.get("in", 0); tot["out"] += r.get("out", 0); tot["n"] += 1
                if tot["n"] % 50 == 0:
                    c = collections.Counter(w["veredicte"] for w in fets.values())
                    print(f"  {tot['n']}/{len(feines)} · {dict(c)} · {int(time.time() - t0)} s", flush=True)
        list(ex.map(una, feines))
    c = collections.Counter(w["veredicte"] for w in fets.values())
    print(f"fet: {tot['n']} crides · fitxes {tot['in']} dins / {tot['out']} fora · veredictes {dict(c)}")
    if md:
        n, nv = escriu_md(items, fets, md)
        print(f"{n} ítems TRIA de {nv} vídeos → {md}")
