# -*- coding: utf-8 -*-
"""Els ítems confirmats del professor (TRIA de l'auditoria) contra el glossari de 59 termes
lingüístics del web de l'autor (`backend/data/lexic_validat_web_tfa.json`): la mateixa persona,
dos canals (el que escriu al web i el que diu a classe).

Un ítem casa amb un terme del glossari si la forma llatina coincideix (sense diacrítics ni ʷ), o si
el significat àrab de l'ítem conté el terme àrab del glossari, o si el significat català de l'ítem
i el del glossari comparteixen una paraula de ≥ 5 lletres. Per a cada parella: coincideix (la forma
i el significat casen), contradiu (mateixa forma, significat diferent / mateix significat, forma
diferent) o res. Tot per llegir a mà: el glossari és terminologia de l'IRCAM i el professor a
classe usa sovint el terme àrab o una forma col·loquial.

ÚS: confirmats_vs_web.py <mina_confirmats.jsonl> <lexic_validat_web_tfa.json> <sortida.md>
"""
import io
import json
import re
import sys
import unicodedata

STOP = set("de la el les els un una que és són amb per al del dels en i o no si lletra forma paraula nom".split())


def pla(s):
    s = unicodedata.normalize("NFKD", (s or "").lower().replace("ʷ", ""))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z ]", "", s.replace("ɣ", "gh").replace("ɛ", "e")).strip()


def mots(s):
    return {w for w in re.findall(r"[a-zà-ÿ·]+", (s or "").lower()) if len(w) >= 5 and w not in STOP}


if __name__ == "__main__":
    mina, gloss, fora = sys.argv[1], sys.argv[2], sys.argv[3]
    termes = json.load(io.open(gloss, encoding="utf-8"))["termes"]
    items = []
    for l in io.open(mina, encoding="utf-8"):
        d = json.loads(l)
        for it in d["items"]:
            it["video"] = d["video"]
            items.append(it)
    files = []
    termes_tocats = set()
    for it in items:
        lat = pla(it.get("amazic_llati"))
        sig_ar = it.get("significat_ar") or ""
        sig_ca = mots(it.get("significat_ca"))
        for t, g in termes.items():
            forma = lat and lat == pla(t)
            ar = g.get("ar") and any(part.strip() and part.strip() in sig_ar for part in re.split(r"[/(),]", g["ar"]) if len(part.strip()) >= 4)
            ca = bool(sig_ca & mots(g.get("ca")))
            if not (forma or ar or ca):
                continue
            if forma and (ar or ca):
                caixa = "coincideix"
            elif forma:
                caixa = "contradiu (forma igual, significat diferent)"
            else:
                caixa = "exemple del terme (categoria), no el terme"
            termes_tocats.add(t)
            files.append((caixa, t, g.get("ca"), it.get("amazic_llati") or "—", it.get("amazic_ar"), (it.get("significat_ca") or "")[:70], it["video"]))
    ordre = {"coincideix": 0, "contradiu (forma igual, significat diferent)": 1, "exemple del terme (categoria), no el terme": 2}
    files.sort(key=lambda x: (ordre[x[0]], x[1]))
    import collections
    c = collections.Counter(x[0] for x in files)
    with io.open(fora, "w", encoding="utf-8") as g:
        g.write(f"# El professor a classe (ítems confirmats) contra el glossari del seu web\n\n{len(items)} ítems confirmats · "
                f"{len(termes)} termes del glossari · {len(termes_tocats)} termes tocats per algun ítem\n\nCaixes: {dict(c)}\n\n"
                "La major part de les classes són lèxic corrent (animals, cos, casa) i el glossari és metallenguatge: que es toquin pocs "
                "termes és el que s'espera. «Mateix significat, forma diferent» vol dir sovint que a classe el professor diu el terme en "
                "àrab i al web en amazic.\n\n| caixa | terme del web | significat (web) | forma llatina (classe) | forma àrab (classe) | el professor diu | vídeo |\n|---|---|---|---|---|---|---|\n")
        for x in files:
            g.write("| " + " | ".join(str(v).replace("|", "/") for v in x) + " |\n")
        g.write("\n## Termes del glossari que cap ítem confirmat no toca\n\n")
        g.write(", ".join(f"`{t}` ({g2.get('ca')})" for t, g2 in termes.items() if t not in termes_tocats) + "\n")
    print(f"{len(items)} ítems · {len(termes)} termes · tocats {len(termes_tocats)} · {dict(c)}")
    for x in files[:40]:
        print("  " + " | ".join(str(v)[:40] for v in x[:6]))
