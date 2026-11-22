"""Casar cada episodi del visor amb el seu video de YouTube.

En Pablo vol veure els episodis **des del mobil quan no es a casa**. Avui el visor demana el
fitxer al disc de qui mira (es la condicio del permis: aqui no es serveix cap video), i aixo
nomes funciona a l'ordinador on son els fitxers.

La sortida no es pujar res: **els episodis son al canal public de la SNRT a YouTube** -- d'alla
els baixem nosaltres -- i el visor **ja sap encastar-hi el reproductor** quan l'episodi porta
`video_youtube`. Amb els nostres subtitols a sobre, la pantalla completa i els salts. Zero
pujades, zero emmagatzematge, i el video el serveix qui ja el servia.

Aixo nomes CASA i escriu un fitxer; no toca produccio. La carrega la fa en Pablo amb
`tools/snrt/puja_al_visor_privat.py`.

Com es casa, per ordre de seguretat:
  1. pel numero d'episodi, quan el slug el porta (`baba_ali_08` -> «Episode 8» / «الحلقة 8»);
  2. pel nom del convidat, que es el titol del capitol a `varietats.json`;
  3. per durada, si el visor en sap la durada i nomes hi ha un video del canal que hi casi.

Surt `pont_youtube.json` i diu quins queden sense casar.
"""
import io
import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

MAG = Path(r"E:/tamazight/_magatzem")
LLISTA = Path(r"C:/Users/josep/Veus-tachelhit/_escoltats/tamazight_tv_videos.txt")
EPISODIS = MAG / "episodis_del_visor.json"      #: desat d'una crida a /snrt-privat/


def net(t):
    t = unicodedata.normalize("NFD", (t or "").upper())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.sub(r"[^A-Z0-9 ]+", " ", t).strip()


videos = []
for l in io.open(LLISTA, encoding="utf-8", errors="replace"):
    p = l.rstrip("\n").split("|")
    if len(p) < 4:
        continue
    try:
        d = int(p[1])
    except ValueError:
        d = 0
    videos.append({"id": p[0], "durada": d, "titol": "|".join(p[3:])})
print(f"{len(videos)} vídeos al canal")

if not EPISODIS.exists():
    raise SystemExit(f"falta {EPISODIS}: desa-hi la resposta de /snrt-privat/ quan el servidor hi sigui")
eps = json.load(io.open(EPISODIS, encoding="utf-8"))
eps = eps.get("episodis", eps)
print(f"{len(eps)} episodis al visor\n")

per_durada = defaultdict(list)
for v in videos:
    per_durada[v["durada"]].append(v)

pont, sense = {}, []
for e in eps:
    slug, titol, dur = e["slug"], e.get("titol") or "", e.get("durada")
    trobat = None

    #: 1. pel numero, quan el slug el porta
    m = re.match(r"^(baba_ali)_(\d+)$", slug)
    if m:
        n = int(m.group(2))
        cands = [v for v in videos
                 if ("BABA ALI" in v["titol"].upper() or "بابا علي" in v["titol"])
                 and v["durada"] >= 300
                 and (re.search(rf"Episode\s*0*{n}\b", v["titol"], re.I)
                      or re.search(rf"الحلقة\s*0*{n}\b", v["titol"]))]
        if len(cands) == 1:
            trobat = cands[0]

    #: 2. pel nom del convidat
    if not trobat and titol:
        nom = net(titol)
        nom = re.sub(r"^TADFI N TSKLA ", "", nom).strip()
        if len(nom) >= 6:
            cands = [v for v in videos if nom in net(v["titol"])]
            if len(cands) == 1:
                trobat = cands[0]
            elif len(cands) > 1 and dur:
                prop = [v for v in cands if abs(v["durada"] - float(dur)) <= 30]
                if len(prop) == 1:
                    trobat = prop[0]

    #: 3. per durada, nomes si es inequivoc
    if not trobat and dur:
        cands = [v for v in videos if abs(v["durada"] - float(dur)) <= 5 and v["durada"] >= 300]
        if len(cands) == 1:
            trobat = cands[0]

    if trobat:
        pont[slug] = {"youtube": trobat["id"], "titol_youtube": trobat["titol"][:70],
                      "durada_visor": dur, "durada_youtube": trobat["durada"]}
    else:
        sense.append((slug, titol[:40], dur))

json.dump(pont, io.open(MAG / "pont_youtube.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print(f"casats: {len(pont)} de {len(eps)}")
for slug, d in list(pont.items())[:8]:
    dif = (d["durada_youtube"] - (d["durada_visor"] or 0)) if d["durada_visor"] else None
    print(f"   {slug:<22}{d['youtube']}  ({'%+ds' % dif if dif is not None else '?'})"
          f"  {d['titol_youtube'][:40]}")
print(f"\nsense casar: {len(sense)}")
for s in sense[:10]:
    print(f"   {s[0]:<22}{(s[1] or '')[:34]:<36}{('%.0f min' % (s[2]/60)) if s[2] else '?'}")
print("\nescrit pont_youtube.json")
