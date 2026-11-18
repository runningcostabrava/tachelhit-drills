# -*- coding: utf-8 -*-
"""Auditoria independent de l'ASR dels talls de la SNRT (#601): diu si l'àudio i el text són el MATEIX CONTINGUT.

  gemini  20 talls de capítols VALIDATS (talls/intervals.json, durada bona), de >= 3 capítols, a l'atzar (llavor 1114).
          Gemini ESCOLTA el tall (àudio inline) i diu la llengua, què diu, el català i l'àrab. Es compara el seu català amb
          el català de l'àrab llegit per la fàbrica i amb el del tifinag pel nostre NLLB (chrF) i s'apunta el cost.
  full    un HTML autònom amb ~10 talls de <= 6 s (àudio en base64) i el tifinag + àrab + català de la fàbrica, perquè una
          persona marqui «concorda / no concorda / no ho sé». És un fitxer per a ella: no es publica.

Només biblioteca estàndard (corre a l'ECS). La clau de Gemini es llegeix de /root/.env (variable GEMINI_API_KEY) i no s'imprimeix
ni es desa enlloc. Límit de cost: 0,30 EUR per execució; el guió s'atura abans de passar-lo.
"""
import argparse
import base64
import collections
import html
import json
import os
import random
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import transcriptor_bucle as tb  # noqa: E402

LLAVOR = 1114
MODEL = "gemini-2.5-flash"
URL = "https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent"
PREU_ENTRADA_AUDIO_USD = 1.00 / 1e6      # USD per fitxa d'entrada d'àudio (gemini-2.5-flash)
PREU_ENTRADA_TEXT_USD = 0.30 / 1e6
PREU_SORTIDA_USD = 2.50 / 1e6
USD_A_EUR = 0.95
COST_MAX_EUR = 0.30
MAX_FITXES_SORTIDA = 500
DURADA_MIN, DURADA_MAX = 2.0, 6.0
CONF_MIN = 0.9
PROMPT = ("Aquest tall d'àudio és d'una entrevista de la televisió marroquina en llengua amaziga (tamazight). "
          "Escolta'l i respon NOMÉS amb un JSON amb aquestes claus: "
          '"llengua" (la que sents de debò: "amazic", "dàrija", "àrab", "francès", "altra" o "no hi ha veu"), '
          '"transcripcio" (què diu, en lletres llatines, com puguis), "catala" (la traducció al català), '
          '"arab" (la traducció a l\'àrab), "segur" (0 a 1, com de segur estàs que has entès el tall).')


# ------------------------------------------------------------------ chrF (Popović, n = 1..6, beta = 2), sense dependències
def _ngrams(t, n):
    t = t.replace(" ", "")
    return collections.Counter(t[i:i + n] for i in range(len(t) - n + 1))


def chrf(hip, ref, nmax=6, beta=2.0):
    """chrF en 0..1 (sobre caràcters sense espais). 0 si algun dels dos és buit."""
    hip, ref = (hip or "").lower(), (ref or "").lower()
    if not hip.replace(" ", "") or not ref.replace(" ", ""):
        return 0.0
    ps, rs = [], []
    for n in range(1, nmax + 1):
        h, r = _ngrams(hip, n), _ngrams(ref, n)
        if not h or not r:
            continue
        comu = sum((h & r).values())
        ps.append(comu / sum(h.values()))
        rs.append(comu / sum(r.values()))
    if not ps:
        return 0.0
    p, r = sum(ps) / len(ps), sum(rs) / len(rs)
    return 0.0 if p + r == 0 else (1 + beta ** 2) * p * r / (beta ** 2 * p + r)


# ------------------------------------------------------------------ selecció de talls validats
def candidats(arrel, durada=(DURADA_MIN, DURADA_MAX), conf=CONF_MIN):
    """[(fila, ruta del wav)] de les files aptes (porta §5 + wav validat per intervals.json) amb durada i confiança d'auditoria."""
    caps = tb.llegeix_capitols(arrel)
    aptes, _ = tb.selecciona(caps)
    out = []
    for slug, files in aptes.items():
        for r in files:
            if durada[0] <= r["durada"] <= durada[1] and (r.get("tifinag_conf") or 0) >= conf:
                out.append((r, os.path.join(caps[slug]["carpeta"], r["tall"])))
    return out


def tria(cands, n=20, min_capitols=3, llavor=LLAVOR):
    """n talls a l'atzar (llavor 1114) repartits entre almenys min_capitols capítols; error si no hi ha prou capítols."""
    per = collections.defaultdict(list)
    for c in cands:
        per[c[0]["slug"]].append(c)
    if len(per) < min_capitols:
        raise ValueError(f"calen {min_capitols} capítols validats i només n'hi ha {len(per)}")
    rnd = random.Random(llavor)
    slugs = sorted(per)
    rnd.shuffle(slugs)
    triats = []
    for s in slugs:
        per[s].sort(key=lambda c: c[0]["id"])
        rnd.shuffle(per[s])
    i = 0
    while len(triats) < n and any(per[s] for s in slugs):      # rotatiu: cap capítol no domina
        s = slugs[i % len(slugs)]
        if per[s]:
            triats.append(per[s].pop())
        i += 1
    return triats


# ------------------------------------------------------------------ Gemini
def clau_gemini(env="/root/.env"):
    for l in open(env, encoding="utf-8"):
        if l.startswith("GEMINI_API_KEY="):
            return l.split("=", 1)[1].strip().strip('"').strip("'")
    raise RuntimeError("no hi ha GEMINI_API_KEY a " + env)


def cos_peticio(wav_bytes):
    return {"contents": [{"parts": [{"text": PROMPT},
                                    {"inline_data": {"mime_type": "audio/wav", "data": base64.b64encode(wav_bytes).decode()}}]}],
            "generationConfig": {"temperature": 0, "maxOutputTokens": MAX_FITXES_SORTIDA, "responseMimeType": "application/json",
                                 "thinkingConfig": {"thinkingBudget": 0}}}


def cost_eur(usage):
    """Cost d'una crida a partir de usageMetadata (tota l'entrada es compta a preu d'àudio: cota alta)."""
    ent = usage.get("promptTokenCount", 0)
    sor = usage.get("candidatesTokenCount", 0) + usage.get("thoughtsTokenCount", 0)
    return (ent * PREU_ENTRADA_AUDIO_USD + sor * PREU_SORTIDA_USD) * USD_A_EUR


def crida(wav_bytes, clau, post=None):
    """Una crida; torna (resposta JSON de Gemini o None, usage). `post` es pot substituir a les proves."""
    cos = json.dumps(cos_peticio(wav_bytes)).encode()
    if post is None:
        req = urllib.request.Request(URL % MODEL, data=cos, headers={"Content-Type": "application/json", "x-goog-api-key": clau})
        with urllib.request.urlopen(req, timeout=120) as r:
            resp = json.load(r)
    else:
        resp = post(cos)
    usage = resp.get("usageMetadata", {})
    try:
        text = resp["candidates"][0]["content"]["parts"][0]["text"]
        return json.loads(text), usage
    except (KeyError, IndexError, ValueError):
        return None, usage


def audita(triats, clau, post=None, cost_max=COST_MAX_EUR):
    """-> (resultats, cost total EUR). S'atura abans de passar el límit (estima la crida següent amb la mitjana de les fetes)."""
    res, cost = [], 0.0
    for r, wav in triats:
        mitjana = cost / len(res) if res else 0.002
        if cost + mitjana > cost_max:
            res.append({"id": r["id"], "aturat": "límit de cost"})
            break
        resp, usage = crida(open(wav, "rb").read(), clau, post)
        c = cost_eur(usage)
        cost += c
        cat_ar = r.get("catala") or r.get("catala_a") or ""
        res.append({"id": r["id"], "slug": r["slug"], "durada": r["durada"], "tifinag": r["tifinag"], "arab_fabrica": r.get("arab"),
                    "catala_arab_fabrica": cat_ar, "catala_de_tifinag": r.get("catala_de_tifinag", ""),
                    "gemini": resp, "cost_eur": round(c, 5), "fitxes": usage,
                    "chrf_gemini_vs_arab": round(chrf((resp or {}).get("catala", ""), cat_ar), 3) if cat_ar else None,
                    "chrf_gemini_vs_tifinag": round(chrf((resp or {}).get("catala", ""), r.get("catala_de_tifinag", "")), 3) if r.get("catala_de_tifinag") else None,
                    "chrf_tifinag_vs_arab": round(chrf(r.get("catala_de_tifinag", ""), cat_ar), 3) if cat_ar and r.get("catala_de_tifinag") else None})
    return res, cost


def resum(res):
    fets = [x for x in res if x.get("gemini")]
    llengues = collections.Counter((x["gemini"].get("llengua") or "?").lower() for x in fets)
    mit = lambda k: (sum(x[k] for x in fets if x.get(k) is not None) / max(1, sum(1 for x in fets if x.get(k) is not None)))
    return {"n": len(fets), "sense_resposta": sum(1 for x in res if not x.get("gemini") and not x.get("aturat")),
            "llengues": dict(llengues), "capitols": len({x["slug"] for x in fets}),
            "chrf_gemini_vs_arab": round(mit("chrf_gemini_vs_arab"), 3), "chrf_gemini_vs_tifinag": round(mit("chrf_gemini_vs_tifinag"), 3),
            "chrf_tifinag_vs_arab": round(mit("chrf_tifinag_vs_arab"), 3),
            "cost_eur": round(sum(x.get("cost_eur", 0) for x in res), 4)}


# ------------------------------------------------------------------ full per a una persona
def full_html(talls):
    """HTML autònom. talls: [{id, wav (bytes), tifinag, arab, catala}]. Les marques es baixen com a JSON (sense servidor)."""
    blocs = []
    for i, t in enumerate(talls, 1):
        b64 = base64.b64encode(t["wav"]).decode()
        nom = html.escape(t["id"])
        blocs.append(
            f'<section data-id="{nom}"><h2>{i}</h2><audio controls preload="none" src="data:audio/wav;base64,{b64}"></audio>'
            f'<p class="tif" lang="zgh">{html.escape(t["tifinag"])}</p><p class="ar" dir="rtl" lang="ar">{html.escape(t.get("arab") or "")}</p>'
            f'<p class="ca">{html.escape(t.get("catala") or "")}</p>'
            f'<label><input type="radio" name="r{i}" value="concorda"> concorda</label> '
            f'<label><input type="radio" name="r{i}" value="no concorda"> no concorda</label> '
            f'<label><input type="radio" name="r{i}" value="no ho sé"> no ho sé</label></section>')
    return ('<!doctype html><html lang="ca"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>Talls de la SNRT: concorda el text?</title><style>body{font-family:system-ui;max-width:42rem;margin:1rem auto;padding:0 1rem}'
            'section{border:1px solid #8884;border-radius:8px;padding:.6rem 1rem;margin:1rem 0}.tif{font-size:1.4rem}.ar{font-size:1.2rem}'
            'audio{width:100%}</style></head><body><h1>Escolta cada tall i marca si el text és el que se sent</h1>'
            '<p>Cada tall dura menys de 6 s. El tifinag, l\'àrab i el català són els que ha llegit la màquina. Marca «concorda» '
            'si diu el mateix que sents, «no concorda» si diu una altra cosa, o «no ho sé». Al final, baixa les marques i envia-les.</p>'
            + "".join(blocs) +
            '<button id="b">Baixa les marques</button><script>document.getElementById("b").onclick=function(){var o={};'
            'document.querySelectorAll("section").forEach(function(s){var c=s.querySelector("input:checked");o[s.dataset.id]=c?c.value:null});'
            'var a=document.createElement("a");a.href=URL.createObjectURL(new Blob([JSON.stringify(o,null,1)],{type:"application/json"}));'
            'a.download="marques.json";a.click()}</script></body></html>')


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ordre", choices=["gemini", "full"])
    ap.add_argument("--arrel", default="/root/tamazight_tv")
    ap.add_argument("--sortida", default="/root/transcriptor")
    ap.add_argument("--n", type=int, default=None)
    a = ap.parse_args(argv)
    c = candidats(a.arrel)
    if a.ordre == "gemini":
        triats = tria(c, n=a.n or 20)
        res, cost = audita(triats, clau_gemini())
        json.dump({"resultats": res, "resum": resum(res)}, open(os.path.join(a.sortida, "auditoria_gemini.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        print(json.dumps(resum(res), ensure_ascii=False, indent=1))
    else:
        triats = tria(c, n=a.n or 10)
        talls = [{"id": r["id"], "wav": open(w, "rb").read(), "tifinag": r["tifinag"], "arab": r.get("arab"),
                  "catala": r.get("catala") or r.get("catala_a") or ""} for r, w in triats]
        open(os.path.join(a.sortida, "full_pablo.html"), "w", encoding="utf-8").write(full_html(talls))
        print(f"full amb {len(talls)} talls de {len({r['slug'] for r, _ in triats})} capítols")


if __name__ == "__main__":
    main()
