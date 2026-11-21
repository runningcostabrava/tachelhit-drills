"""transcriu.py — de les etiquetes dels grups al text del conte.

El vermell s'acumula lletra a lletra dins de cada pàgina, així que cada "línia vermella"
(tram) conté tot el que s'ha llegit fins aleshores a la pàgina; el text sencer és al tram
final de la pàgina (el que glifs.py ha segmentat). Per a cada fila de text de la pàgina:
  - tifinag: etiqueta de cada glif, en ordre, amb espais entre paraules;
    MARCA (signes petits) es resol per posició: a dalt = cometa ("), a baix = coma o punt;
    ⵏ amb forma de barra + punt = "!".
  - de/a: el primer tram de la pàgina on la fila ja té vermell / el primer on la fila
    és sencera (x1 final). Així les files repetides en centenars de fotogrames queden fusionades.
Desa transcripcio.json i conte.txt (tifinag + llatí amb el transliterador del projecte).

Ús: python -X utf8 transcriu.py
"""
import json
import os
import sys

os.environ.setdefault("LEXICON_WARMUP", "0")
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, r"C:\Users\josep\app2\tachelhit-drills.worktrees\mirar\backend")
try:
    from transliteration import to_forms
except Exception as e:  # pragma: no cover
    print("avís: no carrego el transliterador:", e)
    to_forms = None

PUNT_SENSE_ESPAI_ABANS = set(',.:?!')


def llati(t):
    if to_forms is None:
        return ""
    try:
        return to_forms(t)["clean_latin"]
    except Exception as e:
        return f"<error {e}>"


def resol_marca(g):
    """Signe petit: cometa si és a la meitat de dalt de la fila; a baix, punt si és baixet, coma si no."""
    fy0, fy1 = g["fila_caixa"][1], g["fila_caixa"][3]
    y0 = g["caixa_fotograma"][1]
    rel = (y0 - fy0) / max(1, fy1 - fy0)
    if rel < 0.35:
        return "\u2033"  # mitja cometa (es fusionen després)
    return "." if g["h_rel"] < 0.30 else ","


def text_fila(gs, etiq):
    gs = sorted(gs, key=lambda g: g["posicio"])
    peces = []  # (paraula, text)
    for g in gs:
        e = etiq[f"g{g['grup']:02d}"]["glif"]
        if e == "MARCA":
            t = resol_marca(g)
            # un puntet enmig d'una paraula (glifs de la mateixa paraula a banda i banda) és brossa del JPEG
            mateixa = [h for h in gs if h["paraula"] == g["paraula"]]
            if t == "." and any(h["posicio"] < g["posicio"] for h in mateixa) and any(h["posicio"] > g["posicio"] for h in mateixa):
                continue
        elif e == "ⵏ" and g.get("forma_excl"):
            t = "!"
        else:
            t = e
        if t == "":
            continue
        peces.append((g["paraula"], t))
    # ajunta per paraules
    paraules = []
    for p, t in peces:
        if paraules and paraules[-1][0] == p:
            paraules[-1][1] += t
        else:
            paraules.append([p, t])
    s = " ".join(t for _, t in paraules)
    # mitges cometes consecutives -> una cometa; una de sola també és una cometa
    while "\u2033\u2033" in s:
        s = s.replace("\u2033\u2033", "\u2033")
    s = s.replace(" \u2033 ", " \u2033").replace("\u2033", '"')
    # neteja tipogràfica: cap espai abans de , . : ? ! ni després de cometa d'obertura
    for c in PUNT_SENSE_ESPAI_ABANS:
        s = s.replace(" " + c, c)
    s = s.replace('" ', '"') if s.count('"') == 1 and s.strip().startswith('"') else s
    # cometa d'obertura enganxada a la lletra (g42, g56...) + la mitja cometa solta: una sola cometa
    while '""' in s:
        s = s.replace('""', '"')
    # espai després de , ? ! : . quan segueix una lletra
    import re
    s = re.sub(r'([,?!:.])(?=[ⴰ-⵿])', r' ', s)
    return s.strip()


def mateixa_fila(a, b):
    return abs(a[1] - b[1]) <= 4 and abs(a[3] - b[3]) <= 4 and abs(a[0] - b[0]) <= 6


def main():
    L = json.load(open(os.path.join(AQUI, "linies.json"), encoding="utf-8"))
    G = json.load(open(os.path.join(AQUI, "glifs.json"), encoding="utf-8"))
    etiq = json.load(open(os.path.join(AQUI, "etiquetes.json"), encoding="utf-8"))
    per_tram = {}
    for s in L:
        per_tram[s["id"]] = s
    pagines = {}
    for s in L:
        pagines.setdefault(s["pagina"], []).append(s)
    files = {}
    for g in G:
        files.setdefault((g["linia"], g["fila"]), []).append(g)

    sortida = []
    for (tram, fi), gs in sorted(files.items()):
        s = per_tram[tram]
        fila = gs[0]["fila_caixa"]
        trams_pag = pagines[s["pagina"]]
        de, a = None, None
        for t in trams_pag:
            for f in t["files"]:
                if mateixa_fila(f, fila):
                    if de is None:
                        de = t["de"]
                    if f[2] >= fila[2] - 3 and a is None:
                        a = t["de"]
        if de is None:
            de = s["de"]
        if a is None:
            a = s["a"]
        tif = text_fila(gs, etiq)
        sortida.append({
            "pagina": s["pagina"], "fila": fi, "de": de, "a": a,
            "fotograma": s["fotograma"], "tram_final": tram, "caixa": fila,
            "n_glifs": len(gs), "tifinag": tif, "llati": llati(tif),
            "dubtes": sorted({etiq[f"g{g['grup']:02d}"]["glif"] for g in gs if not etiq[f"g{g['grup']:02d}"].get("segur", True)}),
        })
    sortida.sort(key=lambda r: (r["pagina"], r["caixa"][1]))
    with open(os.path.join(AQUI, "transcripcio.json"), "w", encoding="utf-8") as f:
        json.dump(sortida, f, ensure_ascii=False, indent=1)

    # conte.txt: text en ordre, una pàgina per bloc; files idèntiques consecutives, una sola vegada
    linies_txt, vist = [], None
    pag_ant = None
    for r in sortida:
        if r["pagina"] != pag_ant:
            if pag_ant is not None:
                linies_txt.append("")
            linies_txt.append(f"# pàgina {r['pagina']}  ({r['de']:.1f} s, fotograma {r['fotograma']})")
            pag_ant = r["pagina"]
        if r["tifinag"] == vist:
            continue
        vist = r["tifinag"]
        linies_txt.append(f"[{r['de']:6.1f}-{r['a']:6.1f}] {r['tifinag']}")
        linies_txt.append(f"{'':16} {r['llati']}")
    with open(os.path.join(AQUI, "conte.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(linies_txt) + "\n")
    n_pag = len({r["pagina"] for r in sortida})
    n_gl = sum(r["n_glifs"] for r in sortida)
    print(f"{n_pag} pàgines, {len(sortida)} files, {n_gl} glifs -> transcripcio.json, conte.txt")


if __name__ == "__main__":
    main()
