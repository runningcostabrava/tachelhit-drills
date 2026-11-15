# -*- coding: utf-8 -*-
"""El creuament de fonts, en codi: per a cada forma amaziga, què en diu cada font independent, i
si dues o més coincideixen en el significat. Punt 2 del programa del 15-11.

Fonts (totes de fora de la nostra canonada):
  · inducció amb subtítols humans en anglès i en àrab (Dice per rètol)
  · el glossari i els cursos del web de l'autor (tamazightforall.com)
  · les explicacions del professor en dàrija (minades amb la frase on ho diu)
  · amazic.cat (lemes catalans on surt la forma)
  · ⵡⵉⴽⵉⵎⴰⵡⴰⵍ (traduccions en/fr/ar, lliure)
i el que diem nosaltres (`glossa()`), que no compta com a font.

El judici d'acord entre llengües (anglès, àrab, francès, català) el fa el model, amb el material
de cada font davant i l'ordre de no inventar: torna si ≥ 2 fonts coincideixen, la glossa catalana
que en surt i quines fonts la sostenen. El resultat és un candidat a `LEXIC_VALIDAT` amb la
procedència escrita; mai una glossa sola.

ÚS: creuament.py --induccio_en <md> --induccio_ar <md> --web <web_vs_lexic.md> --darija <mina_tot.jsonl>
      --amazic_cat <consultes.jsonl> --wikimawal <wikimawal.json> --fora <sortida sense extensió> [--quants N]
"""
import collections
import io
import json
import os
import re
import sys

ARREL = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ARREL, "backend"))
os.chdir(os.path.join(ARREL, "backend"))
os.environ["LEXICON_WARMUP"] = "0"
from dotenv import load_dotenv      # noqa: E402
load_dotenv(os.environ.get("TFA_ENV") or os.path.join(ARREL, "backend", ".env"))
import deepseek_client as DS        # noqa: E402
import lexicon                      # noqa: E402
import morfologia                   # noqa: E402

SYS = """Ets un lexicògraf. Per a UNA forma amaziga et dono el que en diuen fonts independents, cada una
en la seva llengua (anglès, àrab, francès, català), i el que en diu el nostre lèxic. Has de dir si
DUES O MÉS fonts externes coincideixen en un mateix significat (el mateix concepte, encara que la
paraula sigui d'una altra llengua o un sinònim), i quin és aquest significat en català, curt.
No inventis res: si les fonts no coincideixen o només n'hi ha una, digues-ho. Torna NOMÉS un JSON:
{"acord": true|false, "glossa_ca": "…" o "", "fonts_que_coincideixen": ["…"], "nostre_lexic": "coincideix"|"contradiu"|"no en té"|"no es pot dir", "nota": "≤ 15 paraules"}"""


def arg(nom, defecte=None):
    a = sys.argv
    return a[a.index(nom) + 1] if nom in a else defecte


def llegeix_md_induccio(cami, etiqueta):
    fora = collections.defaultdict(list)
    if not cami or not os.path.exists(cami):
        return fora
    for l in io.open(cami, encoding="utf-8"):
        m = re.match(r"\| \*\*(confirmat|nou|contradiu|nom propi)\*\* \| (\d+) \| `([^`]+)` \| ([^|]*) \|", l)
        if m:
            fora[m.group(3).lower()].append(f"{etiqueta} ({m.group(2)} rètols): {m.group(4).strip()}")
    return fora


if __name__ == "__main__":
    fonts = collections.defaultdict(list)
    for forma, xs in llegeix_md_induccio(arg("--induccio_en"), "subtítols humans en anglès").items():
        fonts[forma] += xs
    for forma, xs in llegeix_md_induccio(arg("--induccio_ar"), "subtítols humans en àrab").items():
        fonts[forma] += xs
    web = arg("--web")
    if web and os.path.exists(web):
        for l in io.open(web, encoding="utf-8"):
            m = re.match(r"\| (coincideix|contradiu|no la tenim) \| ([^|]*) \| ([^|]*) \| ([^|]*) \| ([^|]*) \| ([^|]*) \|", l)
            if m and m.group(4).strip():
                fonts[m.group(4).strip().lower()].append(f"web de l'autor ({m.group(2).strip()}): {m.group(5).strip()} {m.group(6).strip()}".strip())
    dar = arg("--darija")
    if dar and os.path.exists(dar):
        for l in io.open(dar, encoding="utf-8"):
            d = json.loads(l)
            for it in d.get("items") or []:
                lat = re.sub(r"[^a-zɣɛḍṭẓṣṛḥġḫšεʷ' -]", "", (it.get("amazic_llati") or "").lower()).strip()
                if lat and " " not in lat and len(lat) >= 3:
                    fonts[lat].append(f"professor en dàrija ({d['video']}): {it.get('significat_ca')}")
    ac = arg("--amazic_cat")
    if ac and os.path.exists(ac):
        for l in io.open(ac, encoding="utf-8"):
            d = json.loads(l)
            if d.get("lemes"):
                fonts[d["forma"].lower()].append("amazic.cat (lemes catalans): " + ", ".join(sorted({x["lema"] for x in d["lemes"]}))[:120])
    wm = arg("--wikimawal")
    if wm and os.path.exists(wm):
        for e in json.load(io.open(wm, encoding="utf-8")).get("entrades") or []:
            tr = e.get("traduccions") or {}
            if e.get("llati") and (tr.get("en") or tr.get("fr")):
                fonts[e["llati"].lower()].append("Viccionari zgh: " + "; ".join((tr.get("en") or [])[:2] + (tr.get("fr") or [])[:2] + (tr.get("ar") or [])[:1]))
    #: només les formes amb ≥ 2 fonts externes de MENA diferent
    def mena(x):
        #: els subtítols humans en anglès i en àrab els va escriure la mateixa persona: una sola font
        m = x.split(" (")[0].split(":")[0]
        return "subtítols humans" if m.startswith("subtítols humans") else m
    cands = {f: xs for f, xs in fonts.items() if len({mena(x) for x in xs}) >= 2 and re.fullmatch(r"[a-zɣɛḍṭẓṣṛḥġḫšεʷ'-]{3,}", f)}
    print(f"{len(fonts)} formes amb alguna font · {len(cands)} amb ≥ 2 fonts de mena diferent")
    lexicon.load()
    sig, ev, en = morfologia.amb_lexicon(lexicon)
    fora = arg("--fora")
    quants = int(arg("--quants", "99999"))
    fets = set()
    if os.path.exists(fora + ".jsonl"):
        fets = {json.loads(l)["forma"] for l in io.open(fora + ".jsonl", encoding="utf-8")}
    n = 0
    with io.open(fora + ".jsonl", "a", encoding="utf-8") as g:
        for forma in sorted(cands, key=lambda f: -len(cands[f])):
            if forma in fets:
                continue
            g_ = morfologia.glossa(forma, sig, ev, en)
            q = f"FORMA: {forma}\n\nFONTS EXTERNES:\n" + "\n".join(f"- {x}" for x in cands[forma][:12]) + \
                f"\n\nEL NOSTRE LÈXIC DIU: {g_[0] + ' [' + g_[1] + ']' if g_ else '(res)'}"
            try:
                r = DS.deepseek_generate(SYS, [{"role": "user", "text": q}], max_output_tokens=300, temperature=0.0, timeout=90)
                m = re.search(r"\{.*\}", r or "", flags=re.S)
                j = json.loads(m.group(0)) if m else {}
            except Exception as e:
                j = {"error": f"{type(e).__name__}: {str(e)[:60]}"}
            j.update({"forma": forma, "fonts": cands[forma][:12], "nostre": (g_[0][:80] + f" [{g_[1]}]") if g_ else ""})
            g.write(json.dumps(j, ensure_ascii=False) + "\n")
            g.flush()
            n += 1
            print(f"{forma:14} acord={j.get('acord')} {str(j.get('glossa_ca'))[:30]:30} lèxic={j.get('nostre_lexic')}", flush=True)
            if n >= quants:
                break
    #: la taula
    files = [json.loads(l) for l in io.open(fora + ".jsonl", encoding="utf-8")]
    c = collections.Counter((bool(x.get("acord")), x.get("nostre_lexic")) for x in files)
    with io.open(fora + ".md", "w", encoding="utf-8") as g:
        g.write(f"# Creuament de fonts ({len(files)} formes amb ≥ 2 fonts externes)\n\nRecompte (acord, el nostre lèxic): {dict(c)}\n\n")
        g.write("| acord | forma | glossa (ca) | fonts que coincideixen | el nostre lèxic | nota |\n|---|---|---|---|---|---|\n")
        for x in sorted(files, key=lambda x: (not x.get("acord"), x.get("nostre_lexic") != "contradiu")):
            g.write(f"| {'✓' if x.get('acord') else ''} | `{x['forma']}` | {x.get('glossa_ca','')} | {', '.join(x.get('fonts_que_coincideixen') or [])[:80]} | {x.get('nostre_lexic','')}: {x.get('nostre','')[:50]} | {x.get('nota','')} |\n")
    print("fet:", n, "formes noves ·", dict(c))
