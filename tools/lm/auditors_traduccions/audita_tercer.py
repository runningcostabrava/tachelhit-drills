# -*- coding: utf-8 -*-
"""Tercer auditor (qwen4-max, raonant) només per a les frases on els dos primers no van tancar:
dos veredictes diferents (TRIA/NO-HO-SE, FORA/NO-HO-SE, TRIA/FORA) o dos TRIA amb text diferent. Mateix encàrrec i mateixes fonts que
audita.py (o audita_arab.py si la carpeta és la de Baba Ali: ho detecta pel camp text_arabic sense
text_tachelhit). Escriu veredictes_tercer.jsonl a la carpeta de dades; resum.py el llegeix i aplica
«dos de tres amb el mateix text».
ÚS: audita_tercer.py [<carpeta de dades>]   (LIMIT=n per provar)"""
import collections, io, json, os, sys, threading, time
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import audita
from audita import TERCER, crida, veredicte

AQUI = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else r"C:\Users\josep\Veus-tachelhit\_escoltats\traduccions\auditors"


def norm(s):
    import re
    s = (s or "").lower().replace("[?]", "")
    return " ".join(re.sub(r"[^\w\s]", " ", s).split())


def main():
    pend = json.load(io.open(os.path.join(AQUI, "pendents.json"), encoding="utf-8"))
    per = collections.defaultdict(dict)
    for l in io.open(os.path.join(AQUI, "veredictes.jsonl"), encoding="utf-8"):
        if l.strip():
            v = json.loads(l)
            per[v["id"]][v["auditor"]] = v
    arab = bool(pend) and not pend[0].get("text_tachelhit") and pend[0].get("text_arabic")
    if arab:
        import audita_arab
        audita.SISTEMA = audita_arab.SISTEMA
        prompt = audita_arab.prompt
    else:
        import lexicon
        from transliteration import to_forms
        lexicon.load()
        for x in pend:
            f = to_forms(x["text_tachelhit"])
            x["llati"] = x.get("text_tachelhit_latin") or f.get("clean_latin") or ""
            x["fonts"] = lexicon.grounding_lines(x["text_tachelhit"]) or lexicon.grounding_lines(x["llati"])
        prompt = audita.prompt

    def oberta(i):
        q, d = per.get(i, {}).get("qwen"), per.get(i, {}).get("deepseek")
        if not q or not d:
            return False
        menes = {q["mena"], d["mena"]}
        if menes in ({"tria", "no-ho-se"}, {"fora", "no-ho-se"}, {"tria", "fora"}):
            return True
        return q["mena"] == d["mena"] == "tria" and norm(q["text"]) != norm(d["text"])

    pend = [x for x in pend if oberta(x["id"])]
    LIMIT = int(os.environ.get("LIMIT") or 0)
    if LIMIT:
        pend = pend[:LIMIT]
    sortida = os.path.join(AQUI, "prova_tercer.jsonl" if LIMIT else "veredictes_tercer.jsonl")
    fets = set()
    if os.path.exists(sortida):
        for l in io.open(sortida, encoding="utf-8"):
            if l.strip():
                fets.add(json.loads(l)["id"])
    (nom, _) = next(iter(TERCER.items()))
    feines = [x for x in pend if x["id"] not in fets]
    print("obertes", len(pend), "crides pendents", len(feines), "auditor", nom, flush=True)
    pany = threading.Lock()
    t0 = time.time()
    n = 0
    with io.open(sortida, "a", encoding="utf-8") as out, ThreadPoolExecutor(max_workers=4) as ex:
        def una(x):
            r = crida(nom, prompt(x))
            mena, text = veredicte(r["dit"])
            return {"id": x["id"], "auditor": nom, "mena": mena, "text": text, "cru": r["dit"][:600], "s": r["s"],
                    "in": r.get("in", 0), "out": r.get("out", 0), "error": r.get("error")}
        for v in ex.map(una, feines):
            with pany:
                out.write(json.dumps(v, ensure_ascii=False) + "\n")
                out.flush()
                n += 1
                if n % 50 == 0:
                    print(n, "de", len(feines), f"{time.time() - t0:.0f} s", flush=True)
    print("fet en", f"{time.time() - t0:.0f} s", flush=True)


if __name__ == "__main__":
    main()
