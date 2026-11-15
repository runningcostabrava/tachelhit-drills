# -*- coding: utf-8 -*-
"""Minar els transcrits automàtics dels vídeos en DÀRIJA del canal: el professor explica paraules
i regles de l'amazic en àrab marroquí, i el transcrit de YouTube, en aquests vídeos, és text de
debò (≥ 40 paraules per minut; en els vídeos parlats en amazic és brossa).

Per a cada vídeo, el model llegeix el transcrit sencer i en treu, en JSON, cada paraula o
expressió amaziga que el professor ESMENTA I EXPLICA: tal com surt al transcrit (lletres àrabs),
la forma llatina si el professor la lletreja o es pot deduir amb seguretat, el significat que
ell en dóna (en àrab, tal com ho diu, i en català), i la frase del transcrit on ho diu, perquè
es pugui comprovar. El que el professor no explica, no s'inventa.

Això és «autoglossa» a escala: la font és el parlant mateix. Material de tercers: instrument de
validació; res no entra a la biblioteca.

ÚS: mina_transcrits.py <carpeta de vtt> <cataleg.jsonl> <sortida.jsonl> [quants]
"""
import glob
import io
import json
import os
import re
import sys

ARREL = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ARREL, "backend"))
os.chdir(os.path.join(ARREL, "backend"))
from dotenv import load_dotenv      # noqa: E402
load_dotenv(os.environ.get("TFA_ENV") or os.path.join(ARREL, "backend", ".env"))
import deepseek_client as DS        # noqa: E402

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


if __name__ == "__main__":
    carpeta, cataleg, fora = sys.argv[1], sys.argv[2], sys.argv[3]
    quants = int(sys.argv[4]) if len(sys.argv) > 4 else 9999
    titols = {}
    for l in io.open(cataleg, encoding="utf-8"):
        d = json.loads(l)
        titols[d["id"]] = d.get("titol") or ""
    fets = set()
    if os.path.exists(fora):
        for l in io.open(fora, encoding="utf-8"):
            fets.add(json.loads(l)["video"])
    n = 0
    with io.open(fora, "a", encoding="utf-8") as g:
        for cami in sorted(glob.glob(os.path.join(carpeta, "*.vtt"))):
            vid = os.path.basename(cami).split(".")[0]
            if vid in fets:
                continue
            text = text_del_vtt(cami)
            if len(text.split()) < 60:
                continue
            q = f"TÍTOL DEL VÍDEO: {titols.get(vid, '')}\n\nTRANSCRIPCIÓ:\n{text[:14000]}"
            try:
                r = DS.deepseek_generate(SYS, [{"role": "user", "text": q}], max_output_tokens=4000,
                                         temperature=0.0, timeout=180)
                m = re.search(r"\[.*\]", r or "", flags=re.S)
                items = json.loads(m.group(0)) if m else []
            except Exception as e:
                items, r = [], f"(error {type(e).__name__}: {str(e)[:80]})"
            g.write(json.dumps({"video": vid, "titol": titols.get(vid, ""), "paraules_transcrit": len(text.split()),
                                "items": items, "cru": None if items else (r or "")[:300]}, ensure_ascii=False) + "\n")
            g.flush()
            n += 1
            print(f"{vid} {len(text.split()):5} mots → {len(items):3} ítems  {titols.get(vid, '')[:50]}", flush=True)
            if n >= quants:
                break
    print("fet:", n, "vídeos nous")
