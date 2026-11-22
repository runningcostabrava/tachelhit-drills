# -*- coding: utf-8 -*-
"""Porta d'alineació so <-> text (#601). Els intervals de les rèpliques són de 1 s (el rellotge mira un fotograma per
segon) i el subtítol no surt exactament quan es parla: un tall pot portar més so que text (o menys). En Pablo ho va
sentir el 18-11 (addenda 3 de transcriptor/INFORME.md): de 10 talls, 1 concordava del tot.

Aquesta porta NO sap on comença cada paraula (això demana un model acústic: forced alignment, pas 2 del pla); només
descarta els talls on el SO i el TEXT no poden ser el mateix contingut per raons mesurables sense model:
  ritme   els caràcters de tifinag per segon del subtítol s'allunyen de la mediana del capítol (el parlant té un ritme)
  buit    el tall comença o acaba amb silenci llarg més enllà del marge (text a pantalla mentre no es parla)
  curt    massa poc text o massa poc so per jutjar el ritme
Cada tall surt «ok» o «dubtosa» amb els motius. Només «ok» entra al transcriptor. Mai no modifica ni esborra res.

  python -X utf8 porta_alineacio.py <carpeta_del_capitol>      escriu talls/alineacio.json i imprimeix el resum
"""
import json
import os
import statistics
import sys
import wave

import numpy as np

RITME_MIN, RITME_MAX = 0.70, 1.40      # cps / mediana del capítol
BUIT_MAX = 0.70                        # s de silenci seguit al principi o al final del tall (el marge ja en fa 0,25)
CHARS_MIN, SO_MIN = 4, 1.0
DB_SOROLL = 30                         # el llindar de veu és el màxim del tall - 30 dB
MARGE = 0.25


def lletres_tifinag(t):
    return sum(1 for c in (t or "") if "\u2d30" <= c <= "\u2d7f")


def energia_db(cami):
    with wave.open(cami) as w:
        a = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(float) / 32768
    n = len(a) // 320                                   # trams de 20 ms a 16 kHz
    if n == 0:
        return np.zeros(0)
    return 20 * np.log10(np.sqrt((a[:n * 320].reshape(n, 320) ** 2).mean(1)) + 1e-9)


def silenci_seguit(v, des_del_final=False):
    """Segons de silenci seguit al principi (o al final) del vector de veu (booleans per tram de 20 ms)."""
    s = v[::-1] if des_del_final else v
    k = 0
    while k < len(s) and not s[k]:
        k += 1
    return k * 0.02


def mesura_tall(fila, cami_wav):
    """cps del subtítol, so total i silencis a les vores, d'un tall."""
    d = max(float(fila["t_fi"]) - float(fila["t_ini"]), 0.1)
    db = energia_db(cami_wav)
    if len(db) == 0:
        return {"cps": 0.0, "chars": 0, "so": 0.0, "buit_ini": 0.0, "buit_fi": 0.0}
    v = db > db.max() - DB_SOROLL
    ch = lletres_tifinag(fila.get("tifinag"))
    return {"cps": ch / d, "chars": ch, "so": len(db) * 0.02, "buit_ini": silenci_seguit(v), "buit_fi": silenci_seguit(v, True)}


def veredicte(m, cps_mediana):
    """m: mesura_tall; cps_mediana: ritme típic del capítol. -> (veredicte, [motius])"""
    motius = []
    if m["chars"] < CHARS_MIN or m["so"] < SO_MIN:
        motius.append("curt")
    elif cps_mediana > 0:
        r = m["cps"] / cps_mediana
        if not RITME_MIN <= r <= RITME_MAX:
            motius.append("ritme %.2f" % r)
    if m["buit_ini"] > BUIT_MAX or m["buit_fi"] > BUIT_MAX:
        motius.append("buit")
    return ("dubtosa" if motius else "ok"), motius


def porta_capitol(carpeta, files):
    """files: rèpliques del capítol (subtitols.jsonl). -> {id: {v, cps, ratio, motius}}"""
    mes = {}
    for f in files:
        if f.get("credits") or not f.get("tall"):
            continue
        cami = os.path.join(carpeta, f["tall"])
        if os.path.exists(cami):
            mes[f["id"]] = mesura_tall(f, cami)
    ritmes = [m["cps"] for m in mes.values() if m["chars"] >= CHARS_MIN and m["so"] >= SO_MIN]
    med = statistics.median(ritmes) if ritmes else 0.0
    out = {}
    for i, m in mes.items():
        v, mot = veredicte(m, med)
        out[i] = {"v": v, "cps": round(m["cps"], 2), "ratio": round(m["cps"] / med, 2) if med else None, "motius": mot}
    return out, med


def main_carpeta(carpeta, files):
    out, med = porta_capitol(carpeta, files)
    json.dump({"cps_mediana": round(med, 2), "talls": out}, open(os.path.join(carpeta, "talls", "alineacio.json"), "w", encoding="utf-8"), ensure_ascii=False)
    ok = sum(1 for x in out.values() if x["v"] == "ok")
    print(os.path.basename(carpeta)[:12], "talls %d · ok %d (%.0f %%) · cps mediana %.1f" % (len(out), ok, 100 * ok / max(len(out), 1), med))


def main():
    carpeta = os.path.abspath(sys.argv[1])
    main_carpeta(carpeta, [json.loads(l) for l in open(os.path.join(carpeta, "subtitols.jsonl"), encoding="utf-8") if l.strip()])


if __name__ == "__main__":
    main()
