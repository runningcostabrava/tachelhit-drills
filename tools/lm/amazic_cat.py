# -*- coding: utf-8 -*-
"""El diccionari amazic–català d'amazic.cat (Múrcia & Zenia, PEN Català), la referència que en
Pablo ha demanat de fer servir, com a quarta font independent per validar glosses, i en català.

Com funciona el web: `?post_type=encyclopedia&s=<forma>` torna els lemes CATALANS que contenen la
forma amaziga dins l'entrada; cada lema (`/dictionary/<lema>/`) porta els equivalents amazics en
tifinag i llatí amb etiquetes de varietat (QBYL, MZƔ, CW…) i d'àmbit (anat, ling…). Per a una
forma nostra es busca, es baixen els lemes i es queda cada lema on la forma apareix com a paraula
sencera en llatí. Tot es desa en una memòria cau (una petició per segon i mig, un cop per forma).
Ús: validació; el contingut és del diccionari.

ÚS:  amazic_cat.py <formes.txt (una per línia)> <memòria cau (carpeta)> <sortida.jsonl>
     com a mòdul: cerca(forma, cau) → [{"lema": …, "context": …, "url": …}]
"""
import hashlib
import io
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (tachelhit-drills; validacio de glosses; una peticio cada 1,5 s)"}
_ultim = [0.0]


def baixa(url, cau):
    os.makedirs(cau, exist_ok=True)
    f = os.path.join(cau, hashlib.md5(url.encode()).hexdigest() + ".html")
    if os.path.exists(f):
        return io.open(f, encoding="utf-8", errors="replace").read()
    espera = 1.5 - (time.time() - _ultim[0])
    if espera > 0:
        time.sleep(espera)
    _ultim[0] = time.time()
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
            h = r.read().decode("utf-8", errors="replace")
    except Exception as e:
        h = f"<!-- error {type(e).__name__} -->"
    io.open(f, "w", encoding="utf-8").write(h)
    return h


def text_de_lentrada(html):
    m = re.search(r"<article.*?</article>", html, flags=re.S)
    a = m.group(0) if m else html
    t = re.sub(r"<(script|style).*?</\1>", "", a, flags=re.S)
    t = re.sub(r"<br\s*/?>", "\n", t)
    t = re.sub(r"</(p|div|li|h\d|tr)>", "\n", t)
    t = re.sub(r"<[^>]+>", "", t)
    t = t.replace("&ograve;", "ò").replace("&agrave;", "à").replace("&eacute;", "é").replace("&egrave;", "è")
    t = re.sub(r"[ \t]+", " ", t)
    return re.sub(r"\n\s*\n+", "\n", t).strip()


#: el nostre lector escriu l'alfabet del MMS (ġ ḫ š ε); amazic.cat escriu ɣ x c ɛ
A_AMAZIC_CAT = (("ġ", "ɣ"), ("ḫ", "x"), ("š", "c"), ("ε", "ɛ"), ("ʷ", "ʷ"))


def forma_cat(f):
    for a, b in A_AMAZIC_CAT:
        f = f.replace(a, b)
    return f


def cerca(forma, cau):
    forma = forma_cat(forma.strip().lower())
    url = "https://www.amazic.cat/?post_type=encyclopedia&s=" + urllib.parse.quote(forma)
    h = baixa(url, cau)
    lemes = sorted(set(re.findall(r'href="(https://www\.amazic\.cat/dictionary/[^"#?]+)"', h)))
    fora = []
    patro = re.compile(r"(?<![a-zɣɛḍṭẓṣṛḥčğʷ])" + re.escape(forma) + r"(?![a-zɣɛḍṭẓṣṛḥčğʷ])")
    for u in lemes[:12]:
        t = text_de_lentrada(baixa(u, cau))
        lema = u.rstrip("/").rsplit("/", 1)[-1]
        #: el cos de l'entrada: les línies que duen tifinag (la resta és navegació i peu)
        cos = "\n".join(l for l in t.split("Imprimir")[0].split("\n") if re.search(r"[ⴰ-⵿]", l) and len(l) > 12)
        for tros in re.split(r"\s(?:ǁ|♦)\s", cos):
            if patro.search(tros):
                fora.append({"lema": urllib.parse.unquote(lema), "context": " ".join(tros.split())[:300], "url": u})
    return fora


if __name__ == "__main__":
    formes = [l.strip() for l in io.open(sys.argv[1], encoding="utf-8") if l.strip()]
    cau, fora = sys.argv[2], sys.argv[3]
    fets = set()
    if os.path.exists(fora):
        fets = {json.loads(l)["forma"] for l in io.open(fora, encoding="utf-8")}
    n = 0
    with io.open(fora, "a", encoding="utf-8") as g:
        for f in formes:
            if f in fets:
                continue
            r = cerca(f, cau)
            g.write(json.dumps({"forma": f, "lemes": r}, ensure_ascii=False) + "\n")
            g.flush()
            n += 1
            print(f"{f:16} {len(r)} lemes: {', '.join(sorted({x['lema'] for x in r}))[:80]}", flush=True)
    print("fet:", n, "formes noves")
