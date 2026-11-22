# -*- coding: utf-8 -*-
"""Llegeix veredictes.jsonl (dos auditors per frase) i, si hi és, veredictes_tercer.jsonl (el tercer,
només per a les obertes), i aplica la regla del 31-10: només l'acord entra.
- dos auditors TRIA amb el mateix text (igual un cop normalitzat, o chrF ≥ 0,9: només puntuació i
  majúscules) → confirmada; etiqueta traduit-per-maquina → traduit-per-auditors;
- dos auditors FORA → traduccio-descartada (s'afegeix l'etiqueta, el text es queda);
- la resta es queda com a proposta.
Amb el tercer, «dos» vol dir dos de tres. Escriu canvis.json (per a aplica.py) i resum.md.
ÚS: resum.py [<carpeta de dades>]"""
import collections, io, json, os, re, sys

AQUI = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else r"C:\Users\josep\Veus-tachelhit\_escoltats\traduccions\auditors"
pend = {x["id"]: x for x in json.load(io.open(os.path.join(AQUI, "pendents.json"), encoding="utf-8"))}
per = collections.defaultdict(dict)
for nom in ("veredictes.jsonl", "veredictes_tercer.jsonl"):
    p = os.path.join(AQUI, nom)
    if os.path.exists(p):
        for l in io.open(p, encoding="utf-8"):
            if l.strip():
                v = json.loads(l)
                per[v["id"]][v["auditor"]] = v
AUDITORS = ["qwen", "deepseek", "qwen4"]
amb_tercer = any("qwen4" in per[i] for i in per)


def norm(s):
    s = (s or "").lower().replace("[?]", "")
    s = re.sub(r"[^\w\s]", " ", s)
    return " ".join(s.split())


def ngrams(s, n):
    return collections.Counter(s[i:i + n] for i in range(len(s) - n + 1))


def chrf(a, b, N=6, beta=2.0):
    a, b = norm(a), norm(b)
    if not a or not b:
        return 0.0
    P = R = 0.0
    k = 0
    for n in range(1, N + 1):
        h, r = ngrams(a, n), ngrams(b, n)
        if not h or not r:
            continue
        c = sum((h & r).values())
        P += c / sum(h.values())
        R += c / sum(r.values())
        k += 1
    if not k:
        return 0.0
    P, R = P / k, R / k
    return 0.0 if P + R == 0 else (1 + beta ** 2) * P * R / (beta ** 2 * P + R)


def mateix(a, b):
    return norm(a) == norm(b) or chrf(a, b) >= 0.9


canvis, caixes, exemples = [], collections.Counter(), collections.defaultdict(list)
parells = collections.Counter()
amazic = lambda x: x.get("text_tachelhit_latin") or x.get("text_tachelhit") or x.get("text_arabic") or ""
for i, x in pend.items():
    vs = per.get(i, {})
    q, d = vs.get("qwen"), vs.get("deepseek")
    if not q or not d:
        caixes["sense els dos veredictes"] += 1
        continue
    parells[(q["mena"], d["mena"])] += 1
    tries = [(a, vs[a]["text"]) for a in AUDITORS if a in vs and vs[a]["mena"] == "tria"]
    fores = [a for a in AUDITORS if a in vs and vs[a]["mena"] == "fora"]
    acord = None
    for k in range(len(tries)):
        for m in range(k + 1, len(tries)):
            if mateix(tries[k][1], tries[m][1]):
                acord = (tries[k][0], tries[m][0], tries[k][1] if norm(tries[k][1]) == norm(tries[m][1]) else tries[m][1])
                break
        if acord:
            break
    if acord:
        text = acord[2]
        pel_tercer = "qwen4" in acord[:2]
        igual = norm(text) == norm(x["text_catalan"])
        caixes[("confirmada (igual que la màquina)" if igual else "confirmada (retocada igual per dos)") + (" · pel tercer" if pel_tercer else "")] += 1
        canvis.append({"id": i, "text_catalan": text, "tag": x["tag"].replace("traduit-per-maquina", "traduit-per-auditors"),
                       "abans": x["text_catalan"], "mena": "confirmada", "igual_que_maquina": igual, "auditors": list(acord[:2])})
        if not igual:
            exemples["retocada"].append((i, amazic(x), x["text_catalan"], text, "+".join(acord[:2])))
    elif len(fores) >= 2:
        caixes["descartada per dos" + (" · pel tercer" if "qwen4" in fores else "")] += 1
        nou_tag = x["tag"] if "traduccio-descartada" in x["tag"] else x["tag"].replace("traduit-per-maquina", "traduccio-descartada, traduit-per-maquina")
        canvis.append({"id": i, "tag": nou_tag, "abans": x["text_catalan"], "mena": "descartada", "auditors": fores})
        exemples["fora"].append((i, amazic(x), x["text_catalan"]))
    elif len(tries) >= 2:
        s = chrf(tries[0][1], tries[1][1])
        caixes[f"TRIA diferents sense cap parell igual (chrF {'≥0,7' if s >= 0.7 else '<0,7'})"] += 1
        exemples["diferents"].append((i, amazic(x), x["text_catalan"], tries[0][1], tries[1][1], round(s, 2)))
    else:
        caixes["sense acord (queda com a proposta)"] += 1

json.dump(canvis, io.open(os.path.join(AQUI, "canvis.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
fitxes, temps, errors = collections.Counter(), collections.defaultdict(list), collections.Counter()
for i in per:
    for a, v in per[i].items():
        fitxes[a + " entrada"] += v.get("in", 0)
        fitxes[a + " sortida"] += v.get("out", 0)
        temps[a].append(v["s"])
        if v.get("error"):
            errors[a] += 1
menes = collections.Counter((v["auditor"], v["mena"]) for i in per for v in per[i].values())

L = [f"# Auditors de màquina sobre «traduit-per-maquina» ({os.path.basename(AQUI)}, 16-11-2026)", "",
     f"Frases: {len(pend)}. Auditors: `qwen3.8-max` i `deepseek-chat` (tots dos sobre totes), " + ("i `qwen4-max` raonant com a tercer sobre les obertes (un TRIA i l'altre NO-HO-SE, o dos TRIA diferents). " if amb_tercer else "") +
     "Temperatura 0, el mateix encàrrec. Regla del 31-10: només l'acord de dos entra.", "",
     "## Veredictes per auditor", "", "| auditor | frases | TRIA | FORA | NO-HO-SE | altre/buit | errors d'API | latència mediana |", "|---|---|---|---|---|---|---|---|"]
for a in AUDITORS:
    t = sorted(temps[a])
    if not t:
        continue
    L.append(f"| {a} | {len(t)} | {menes[(a, 'tria')]} | {menes[(a, 'fora')]} | {menes[(a, 'no-ho-se')]} | {menes[(a, 'altre')] + menes[(a, 'buit')]} | {errors[a]} | {t[len(t) // 2]:.1f} s |")
L += ["", "## Parelles de veredictes (qwen, deepseek)", ""]
for (a, b), n in parells.most_common():
    L.append(f"- {a} / {b}: {n}")
L += ["", "## Resultat", ""]
for k, n in caixes.most_common():
    L.append(f"- {k}: **{n}**")
L += ["", f"Canvis preparats a `canvis.json`: {sum(1 for c in canvis if c['mena'] == 'confirmada')} confirmades, "
      f"{sum(1 for c in canvis if c['mena'] == 'descartada')} descartades. Fitxes: {dict(fitxes)}.", ""]
for nom, titol in (("retocada", "Confirmades amb el mateix retoc per dos (mostra)"), ("fora", "Descartades per dos (mostra)"), ("diferents", "TRIA diferents sense cap parell igual (mostra, no entren)")):
    L += [f"## {titol}", ""]
    for e in exemples[nom][:12]:
        if nom == "diferents":
            L.append(f"- #{e[0]} `{e[1][:60]}` · màquina: «{e[2][:80]}» · a: «{e[3][:80]}» · b: «{e[4][:80]}» (chrF {e[5]})")
        elif nom == "retocada":
            L.append(f"- #{e[0]} `{e[1][:60]}` · màquina: «{e[2][:90]}» → «{e[3][:90]}» ({e[4]})")
        else:
            L.append(f"- #{e[0]} `{e[1][:60]}` · màquina: «{e[2][:100]}»")
    L.append("")
io.open(os.path.join(AQUI, "resum.md"), "w", encoding="utf-8").write("\n".join(L))
print("\n".join(L[:40]))
