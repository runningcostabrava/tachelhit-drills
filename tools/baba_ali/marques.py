"""Les nostres marques de temps dels episodis que no han casat (7 i 9), per casar-les per IMATGE.

Les pujades d'aquests dos episodis venen MUDES de YouTube (-91 dB, silenci absolut), segurament
per una reclamacio de la musica. Per tant la correlacio del so no hi serveix mai. El que si que
hi ha a la imatge son els subtitols arabs cremats a la franja de baix: no cal llegir-los per
casar l'episodi, nomes cal saber QUAN n'hi ha. Aixo dona dos senyals de presencia -- el nostre
(una linia dura de la seva marca fins a la seguent, com fa el visor) i el del video (hi ha
lletres clares a la franja o no) -- i es correlacionen igual que vam fer amb el so.

Aqui nomes es treu la llista de marques; mesurar el video va a l'altre guio.
"""
import io
import json
import os
import re
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
#: el cau local de la biblioteca; es pot canviar amb TD_BIBLIOTECA
BIB = os.environ.get("TD_BIBLIOTECA",
                     r"C:\Users\josep\Veus-tachelhit\_subtitols\_biblioteca.json")

#: «Baba Ali · episodi 15 · 29:16» -> 1756 segons
MARCA = re.compile(r"(?:(\d{1,2}):)?(\d{1,3}):(\d{2})\s*$")
EPISODI = re.compile(r"episodi\s+(\d{1,2})")

MAX_DURADA = 6.0
MIN_DURADA = 0.8


def segons_de(titol):
    m = MARCA.search((titol or "").strip())
    if not m:
        return None
    h, mi, s = m.group(1), m.group(2), m.group(3)
    return int(h or 0) * 3600 + int(mi) * 60 + int(s)


def carrega():
    """episodi -> [(segon, arab, catala)], ordenat pel segon i sense repeticions."""
    drills = json.load(io.open(BIB, encoding="utf-8"))
    per_ep = {}
    for d in drills:
        titol = d.get("source_title") or ""
        if "baba" not in titol.lower() and "baba" not in (d.get("tag") or "").lower():
            continue
        me = EPISODI.search(titol.lower())
        s = segons_de(titol)
        if not me or s is None:
            continue
        per_ep.setdefault(int(me.group(1)), []).append(
            (s, (d.get("text_arabic") or "").strip(), (d.get("text_catalan") or "").strip()))
    for ep, files in per_ep.items():
        vistes, netes = set(), []
        for s, ar, ca in sorted(files, key=lambda f: f[0]):
            if (s, ar) in vistes:
                continue
            vistes.add((s, ar))
            netes.append((s, ar, ca))
        per_ep[ep] = netes
    return per_ep


def trams(files):
    """[(inici, fi)] tal com el visor els pinta: fins a la seguent, maxim 6 s, minim 0,8."""
    fora = []
    for i, (s, _ar, _ca) in enumerate(files):
        seg = files[i + 1][0] if i + 1 < len(files) else s + MAX_DURADA
        fi = min(seg, s + MAX_DURADA)
        fora.append((float(s), max(fi, s + MIN_DURADA)))
    return fora


if __name__ == "__main__":
    per_ep = carrega()
    vol = [int(a) for a in sys.argv[1:]] or sorted(per_ep)
    for ep in vol:
        files = per_ep.get(ep) or []
        if not files:
            print(f"episodi {ep}: cap linia")
            continue
        t = trams(files)
        cobert = sum(f - i for i, f in t)
        print(f"episodi {ep}: {len(files)} linies, de {files[0][0]}s a {files[-1][0]}s "
              f"({files[-1][0]/60:.1f} min), {cobert:.0f}s amb subtitol "
              f"({100*cobert/max(1, files[-1][0]-files[0][0]):.0f}% del tram)")
        if ep in vol[:2]:
            for s, ar, ca in files[:4]:
                print(f"    {s//60:02d}:{s%60:02d}  {ar[:38]}  |  {ca[:34]}")
    json.dump({str(ep): [[s, ar, ca] for s, ar, ca in f] for ep, f in per_ep.items()},
              io.open(os.path.join(AQUI, "marques.json"), "w", encoding="utf-8"),
              ensure_ascii=False)
    print(f"\ndesat a {os.path.join(AQUI, 'marques.json')}")
