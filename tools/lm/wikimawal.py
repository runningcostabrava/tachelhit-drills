# -*- coding: utf-8 -*-
"""ⵡⵉⴽⵉⵎⴰⵡⴰⵍ, el Viccionari en amazic estàndard (zgh.wiktionary.org; ~1.000 entrades, CC BY-SA 4.0):
la primera font LLIURE que tenim. Es llegeix del bolcat oficial (pages-articles.xml.bz2) i se'n
treu, per entrada: el lema en tifinag, el lema en llatí (amb el nostre transliterador), la
categoria gramatical si la plantilla la diu, les definicions (en amazic, línies «#») i les
traduccions per llengua (plantilles {{t|xx|…}} i afins), amb la llicència i l'atribució.

ÚS: wikimawal.py <pages-articles.xml.bz2> <sortida.json>
"""
import bz2
import io
import json
import os
import re
import sys
import xml.etree.ElementTree as ET

ARREL = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ARREL, "backend"))
os.environ["LEXICON_WARMUP"] = "0"
import transliteration as T   # noqa: E402

NS = "{http://www.mediawiki.org/xml/export-0.11/}"
LLENGUES = {"ar": "ar", "fr": "fr", "en": "en", "es": "es", "ca": "ca", "ber": "ber", "shi": "shi", "kab": "kab", "rif": "rif", "tzm": "tzm"}


def llati(tif):
    try:
        return (T.to_forms(tif) or {}).get("clean_latin") or ""
    except Exception:
        return ""


def neteja(w):
    w = re.sub(r"\{\{[^{}]*\}\}", "", w)
    w = re.sub(r"\[\[([^\]|]*\|)?([^\]]*)\]\]", r"\2", w)
    w = re.sub(r"'{2,}", "", w)
    return " ".join(w.split())


def entrada(titol, text):
    tr = {}
    #: la plantilla de traducció del Viccionari zgh és {{ⵜⴰⵙⵓⵖⵍⵜ|en|language}} (4.779 cops al bolcat)
    for m in re.finditer(r"\{\{(?:ⵜⴰⵙⵓⵖⵍⵜ|t\+?|t-|trad|l)\|([a-z-]+)\|([^|}]+)", text):
        ll, cos = m.group(1), m.group(2).strip()
        if ll in LLENGUES and cos:
            tr.setdefault(ll, [])
            for mot in re.split(r"[,;،/]", cos):
                mot = mot.strip()
                if mot and mot not in tr[ll]:
                    tr[ll].append(mot)
    #: la morfologia que el Viccionari dóna: {{ⵉⵙⵎ|ⴰⵎⵢⵉⵡⵏ=sg|ⴰⵎⴰⴳⵓⵜ=pl|ⴰⴷⴷⴰⴷ ⴰⵎⴰⵔⵓⵣ=annexió|…}} i {{ⴰⵥⵓⵕ|1=…}}
    morf = {}
    m = re.search(r"\{\{(ⵉⵙⵎ|ⴰⵎⵢⴰⴳ|ⴰⵔⴱⵉⴱ)\s*\n?((?:\|[^{}]*\n?)+?)\}\}", text)
    if m:
        morf["plantilla"] = m.group(1)
        for camp in re.finditer(r"\|\s*([^=|\n]+?)\s*=\s*([^|\n]*)", m.group(2)):
            k, v = camp.group(1).strip(), camp.group(2).strip().replace("{{PAGENAME}}", titol)
            if v:
                morf[k] = v
    arrel = re.search(r"\{\{ⴰⵥⵓⵕ\s*((?:\|\d=[^|}\n]*\s*)+)\}\}", text)
    if arrel:
        morf["arrel"] = "".join(x for x in re.findall(r"\|\d=([^|}\n]*)", arrel.group(1)) if x.strip())
    #: traduccions escrites com «* àrab: ...» o «* français : ...» dins d'una secció de traduccions
    for m in re.finditer(r"^\*\s*\{\{([a-z-]+)\}\}\s*:\s*(.+)$", text, flags=re.M):
        ll, resta = m.group(1), neteja(m.group(2))
        if ll in LLENGUES and resta:
            tr.setdefault(ll, [])
            for x in re.split(r"[,;]", resta):
                x = x.strip()
                if x and x not in tr[ll]:
                    tr[ll].append(x)
    defs = [neteja(l[1:]) for l in text.split("\n") if l.startswith("#") and not l.startswith(("#:", "#*"))]
    #: la categoria: la secció {{ⵟ|ⵉⵙⵎ}} (nom), {{ⵟ|ⴰⵎⵢⴰⴳ}} (verb), {{ⵟ|ⴰⵔⴱⵉⴱ}} (adjectiu)…
    CATS = {"ⵉⵙⵎ": "nom", "ⴰⵎⵢⴰⴳ": "verb", "ⴰⵔⴱⵉⴱ": "adjectiu", "ⴰⵎⵔⵏⵓ": "adverbi", "ⴰⵎⵇⵇⵉⵎ": "pronom",
            "ⵜⴰⵏⵣⵖⵜ": "preposició", "ⵜⴰⵙⵖⵓⵏⵜ": "conjunció", "ⵜⴰⵎⴰⵜⴰⵔⵜ": "partícula", "ⵉⵙⵎ ⵏ ⵉⵎⴰⵏ": "nom propi"}
    cat = None
    m = re.search(r"==+\s*\{\{ⵟ\|([^|}]+)(?:\|zgh)?\}\}\s*==+", text)
    if m:
        cat = CATS.get(m.group(1).strip(), m.group(1).strip())
    return {"tifinag": titol, "llati": llati(titol), "categoria": cat, "definicions": defs[:6], "traduccions": tr, "morfologia": morf}


if __name__ == "__main__":
    bolcat, fora = sys.argv[1], sys.argv[2]
    entrades, n_pag = [], 0
    with bz2.open(bolcat, "rb") as fh:
        for ev, el in ET.iterparse(fh, events=("end",)):
            if el.tag != NS + "page":
                continue
            ns = el.find(NS + "ns").text
            titol = el.find(NS + "title").text or ""
            if ns == "0" and re.search(r"[ⴰ-⵿]", titol):
                rev = el.find(NS + "revision")
                text = (rev.find(NS + "text").text or "") if rev is not None else ""
                if not text.lower().startswith("#redirect") and "#ⴰⵙⵡⴰⵍⴰ" not in text[:40]:
                    entrades.append(entrada(titol, text))
                    n_pag += 1
            el.clear()
    amb_tr = sum(1 for e in entrades if e["traduccions"])
    per_ll = {}
    for e in entrades:
        for ll in e["traduccions"]:
            per_ll[ll] = per_ll.get(ll, 0) + 1
    out = {"_font": "ⵡⵉⴽⵉⵎⴰⵡⴰⵍ — Wiktionary en amazic estàndard (zgh.wiktionary.org), bolcat pages-articles; "
                    "text sota CC BY-SA 4.0 (atribució: els col·laboradors del Viccionari zgh). Llegit el 15-11-2026.",
           "entrades": entrades}
    json.dump(out, io.open(fora, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{n_pag} entrades en tifinag · {amb_tr} amb traduccions · per llengua {per_ll} · "
          f"amb definicions {sum(1 for e in entrades if e['definicions'])}")
    for e in entrades[:5]:
        print("  ", json.dumps(e, ensure_ascii=False)[:220])
