# -*- coding: utf-8 -*-
"""Llegeix veredictes.jsonl (dos auditors per frase) i aplica la regla del 31-10: només l'acord entra.
- tots dos TRIA amb el mateix text (igual un cop normalitzat, o chrF ≥ 0,9: només puntuació/majúscules)
  → confirmada (text del Qwen si són iguals; si difereixen per puntuació, el del DeepSeek, que és el que
  va més sec); etiqueta traduit-per-maquina → traduit-per-auditors;
- tots dos FORA → traduccio-descartada (s'afegeix l'etiqueta, el text es queda);
- la resta es queda com a proposta.
Escriu canvis.json (per a aplica.py) i resum.md."""
import collections, io, json, os, re, sys

AQUI = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else r"C:\Users\josep\Veus-tachelhit\_escoltats\traduccions\auditors"  # carpeta de dades, fora del repositori
pend = {x["id"]: x for x in json.load(io.open(os.path.join(AQUI, "pendents.json"), encoding="utf-8"))}
per = collections.defaultdict(dict)
for l in io.open(os.path.join(AQUI, "veredictes.jsonl"), encoding="utf-8"):
    if l.strip():
        v = json.loads(l)
        per[v["id"]][v["auditor"]] = v


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


canvis, caixes, exemples = [], collections.Counter(), collections.defaultdict(list)
parells = collections.Counter()
for i, x in pend.items():
    q, d = per.get(i, {}).get("qwen"), per.get(i, {}).get("deepseek")
    if not q or not d:
        caixes["sense els dos veredictes"] += 1
        continue
    parells[(q["mena"], d["mena"])] += 1
    nou_tag = None
    if q["mena"] == d["mena"] == "tria":
        s = chrf(q["text"], d["text"])
        iguals = norm(q["text"]) == norm(d["text"])
        if iguals or s >= 0.9:
            text = q["text"] if iguals else d["text"]
            mateix_que_maquina = norm(text) == norm(x["text_catalan"])
            caixes["confirmada (igual que la màquina)" if mateix_que_maquina else "confirmada (retocada igual pels dos)"] += 1
            nou_tag = x["tag"].replace("traduit-per-maquina", "traduit-per-auditors")
            canvis.append({"id": i, "text_catalan": text, "tag": nou_tag, "abans": x["text_catalan"], "mena": "confirmada",
                           "igual_que_maquina": mateix_que_maquina})
            if not mateix_que_maquina:
                exemples["retocada"].append((i, x.get("text_tachelhit_latin") or x["text_tachelhit"], x["text_catalan"], text))
        else:
            caixes[f"tots dos TRIA però diferents (chrF {'≥0,7' if s >= 0.7 else '<0,7'})"] += 1
            exemples["diferents"].append((i, x.get("text_tachelhit_latin") or x["text_tachelhit"], x["text_catalan"], q["text"], d["text"], round(s, 2)))
    elif q["mena"] == d["mena"] == "fora":
        caixes["descartada pels dos"] += 1
        nou_tag = x["tag"] if "traduccio-descartada" in x["tag"] else x["tag"].replace("traduit-per-maquina", "traduccio-descartada, traduit-per-maquina")
        canvis.append({"id": i, "tag": nou_tag, "abans": x["text_catalan"], "mena": "descartada"})
        exemples["fora"].append((i, x.get("text_tachelhit_latin") or x["text_tachelhit"], x["text_catalan"]))
    else:
        caixes["sense acord (queda com a proposta)"] += 1

json.dump(canvis, io.open(os.path.join(AQUI, "canvis.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
fitxes = collections.Counter()
temps = collections.defaultdict(list)
errors = collections.Counter()
for i in per:
    for a, v in per[i].items():
        fitxes[a + " entrada"] += v.get("in", 0)
        fitxes[a + " sortida"] += v.get("out", 0)
        temps[a].append(v["s"])
        if v.get("error"):
            errors[a] += 1
menes = collections.Counter((v["auditor"], v["mena"]) for i in per for v in per[i].values())

L = ["# Parella d'auditors Qwen + DeepSeek sobre les traduccions «traduit-per-maquina» (16-11-2026)", "",
     f"Frases: {len(pend)} (MTNRA {sum(1 for x in pend.values() if 'mtnra' in x['tag'])}, Common Voice {sum(1 for x in pend.values() if 'common-voice' in x['tag'])}). "
     "Auditors: `qwen3.8-max` (Model Studio, sense raonament) i `deepseek-chat` (API directa), temperatura 0, el mateix encàrrec, "
     "amb el diccionari de l'IRCAM, el Viccionari i les taules de conjugació de cada paraula (`lexicon.grounding_lines`). "
     "Regla del 31-10: només l'acord entra.", "",
     "## Veredictes per auditor", "", "| auditor | TRIA | FORA | NO-HO-SE | altre/buit | errors d'API | latència mediana |", "|---|---|---|---|---|---|---|"]
for a in ("qwen", "deepseek"):
    t = sorted(temps[a])
    L.append(f"| {a} | {menes[(a, 'tria')]} | {menes[(a, 'fora')]} | {menes[(a, 'no-ho-se')]} | {menes[(a, 'altre')] + menes[(a, 'buit')]} | {errors[a]} | {t[len(t) // 2] if t else 0:.1f} s |")
L += ["", "## Parelles de veredictes (qwen, deepseek)", ""]
for (a, b), n in parells.most_common():
    L.append(f"- {a} / {b}: {n}")
L += ["", "## Resultat", ""]
for k, n in caixes.most_common():
    L.append(f"- {k}: **{n}**")
L += ["", f"Canvis preparats a `canvis.json`: {sum(1 for c in canvis if c['mena'] == 'confirmada')} confirmades, "
      f"{sum(1 for c in canvis if c['mena'] == 'descartada')} descartades. Fitxes: {dict(fitxes)}.", ""]
for nom, titol in (("retocada", "Confirmades amb el mateix retoc pels dos (mostra)"), ("fora", "Descartades pels dos (mostra)"), ("diferents", "Tots dos TRIA però amb text diferent (mostra, no entren)")):
    L += [f"## {titol}", ""]
    for e in exemples[nom][:12]:
        if nom == "diferents":
            L.append(f"- #{e[0]} `{e[1][:60]}` · màquina: «{e[2][:80]}» · qwen: «{e[3][:80]}» · deepseek: «{e[4][:80]}» (chrF {e[5]})")
        elif nom == "retocada":
            L.append(f"- #{e[0]} `{e[1][:60]}` · màquina: «{e[2][:90]}» → «{e[3][:90]}»")
        else:
            L.append(f"- #{e[0]} `{e[1][:60]}` · màquina: «{e[2][:100]}»")
    L.append("")
io.open(os.path.join(AQUI, "resum.md"), "w", encoding="utf-8").write("\n".join(L))
print("\n".join(L[:40]))
