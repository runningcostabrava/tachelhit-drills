# -*- coding: utf-8 -*-
"""Transcripcions PROVISIONALS dels contes de Tamazight For All, per a l'H4 (afinar el lector amb
veu d'aquest canal quan no hi ha transcripció humana). Lingüista de camp: s'escriu el que el
millor lector sent, es guarda només el que dues lectures i el lèxic avalen, i es mesura després
contra els 226 versos amb veritat, que NO entren aquí (els 8 vídeos de la veritat queden fora).

Entrada: les transcripcions del kernel `tfa-58-transcriu` (paraules amb temps, lectura `greedy` i
`lexic_bi`) i els wav de 16 kHz dels 58 vídeos. Sortida: `corpus_tfa.json` [{fitxer, lletra,
video, de, a, acord, en_lexic}] + `audio/*.wav`, en el format de `afina_mms_lletres_riques.py`.

Filtres (cada un es compta):
  · enunciat: paraules consecutives de `lexic_bi` amb buits < 0,6 s, 1–14 s, ≥ 3 paraules
  · acord: ≥ 60 % de les paraules de `lexic_bi` també les diu `greedy` al mateix tram (±0,3 s)
  · lèxic: ≥ 70 % de les paraules són al lèxic (unigrams_shi.txt)

ÚS: pseudo_tfa.py <transcripcions/> <wavs/> <unigrams_shi.txt> <sortida/> [ids a excloure, separats per comes]
"""
import glob
import io
import json
import os
import subprocess
import sys

VERITAT = {"4Y4FcUHUeU4", "8DfuBnaijUg", "9TdhtZkmUTo", "TJFWJ5FKQg8", "lDbAAcdoVgQ", "o21uxEQoczE",
           "oFVo66DStDc", "tR-hRjd9O-k", "X7_kAT8_J64"}


def enunciats(paraules, buit=0.6, maxim=14.0):
    grups, cur = [], []
    for w in paraules:
        if cur and (w["start"] - cur[-1]["end"] > buit or w["end"] - cur[0]["start"] > maxim):
            grups.append(cur)
            cur = []
        cur.append(w)
    if cur:
        grups.append(cur)
    return grups


def acord(grup, greedy):
    de, a = grup[0]["start"] - 0.3, grup[-1]["end"] + 0.3
    g = {w["text"] for w in greedy if w["start"] >= de and w["end"] <= a}
    if not grup:
        return 0.0
    return sum(1 for w in grup if w["text"] in g) / len(grup)


if __name__ == "__main__":
    carpeta, wavs, uni_cami, fora = sys.argv[1:5]
    exclou = set(VERITAT) | set((sys.argv[5] if len(sys.argv) > 5 else "").split(",")) - {""}
    LLINDAR_ACORD = float(os.environ.get("ACORD", "0.6"))
    TALLA = os.environ.get("TALLA", "1") == "1"        # TALLA=0: només comptar, sense ffmpeg
    lexic = set(l.strip() for l in io.open(uni_cami, encoding="utf-8") if l.strip())
    os.makedirs(os.path.join(fora, "audio"), exist_ok=True)
    comptes = {"videos": 0, "enunciats": 0, "curts": 0, "sense_acord": 0, "fora_lexic": 0, "bons": 0, "segons": 0.0}
    files = []
    for f in sorted(glob.glob(os.path.join(carpeta, "*.json"))):
        d = json.load(io.open(f, encoding="utf-8"))
        vid = d["video"]
        if vid in exclou or not d.get("lexic_bi"):
            continue
        wav = os.path.join(wavs, vid + ".wav")
        if not os.path.exists(wav):
            continue
        comptes["videos"] += 1
        for k, grup in enumerate(enunciats(d["lexic_bi"])):
            comptes["enunciats"] += 1
            dur = grup[-1]["end"] - grup[0]["start"]
            if len(grup) < 3 or dur < 1.0:
                comptes["curts"] += 1
                continue
            ac = acord(grup, d["greedy"])
            if ac < LLINDAR_ACORD:
                comptes["sense_acord"] += 1
                continue
            en_lex = sum(1 for w in grup if w["text"] in lexic) / len(grup)
            if en_lex < 0.7:
                comptes["fora_lexic"] += 1
                continue
            nom = f"{vid}_{k:04d}.wav"
            de, a = max(0.0, grup[0]["start"] - 0.15), grup[-1]["end"] + 0.15
            if TALLA:
                subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-ss", f"{de:.2f}", "-to", f"{a:.2f}", "-i", wav,
                                "-ac", "1", "-ar", "16000", "-y", os.path.join(fora, "audio", nom)], check=True)
            files.append({"fitxer": nom, "lletra": " ".join(w["text"] for w in grup), "video": vid,
                          "de": round(de, 2), "a": round(a, 2), "acord": round(ac, 2), "en_lexic": round(en_lex, 2),
                          "font": "Tamazight For All, transcripció provisional (feix + lèxic), 15-11-2026"})
            comptes["bons"] += 1
            comptes["segons"] += a - de
    json.dump(files, io.open(os.path.join(fora, "corpus_tfa.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    comptes["minuts"] = round(comptes.pop("segons") / 60, 1)
    print(json.dumps(comptes, ensure_ascii=False))
