# -*- coding: utf-8 -*-
"""Induir glosses a partir del corpus paral·lel sorollós (ASR amazic ↔ subtítol humà anglès).

Mètode: per a cada token amazic prou freqüent, quins mots anglesos de contingut surten al mateix
rètol més del que l'atzar faria (Dice sobre rètols: 2·c(a,e) / (c(a) + c(e))). És el mateix
raonament que va confirmar `turft` = «ship» a mà, fet per a tots els tokens alhora. El que surt
NO és una glossa: és un candidat amb un número, que es compara amb el diccionari:
  · coincideix amb el diccionari → la glossa queda confirmada per un parlant (el subtitulador);
  · el diccionari no té el token → candidat nou (el lèxic del camp que faltava);
  · contradiu el diccionari → un dels dos és fals; a mirar.
Els subtítols humans tradueixen el sentit, no paraula per paraula, i l'ASR talla malament: el
senyal és feble i cal freqüència. Per això el mínim de rètols per token és 4.

ÚS: induccio.py <parells.jsonl> <sortida.md> [mínim de rètols=4] [en|ar]
"""
import collections
import io
import json
import re
import sys

STOP_EN = set("""the a an and or of to in on at for with from by is are was were be been being am i you he she it
we they me him her us them my your his its our their this that these those there here not no yes do does did
have has had will would can could shall should may might must as if then than so but what which who whom whose
when where why how all any some one two very just also too only even still about into out up down over under
again more most such own same other s t ll re ve d m don didn doesn isn aren wasn weren won can't let go get got
going come came said say says tell told like know knew think thought want wanted take took give gave make made
see saw look looked find found put keep let oh ah hey well now back off away ever never always""".split())


def mots(t):
    return [w for w in re.findall(r"[a-z']+", t.lower()) if len(w) > 2 and w not in STOP_EN]


#: Àrab: 16 vídeos només tenen subtítol àrab, i als 42 que en tenen dos l'àrab és la llengua
#: del subtitulador (més literal que l'anglès). Es treuen les vocals curtes i la xadda, i els
#: prefixos enganxats més corrents (ال، و، ف، ب، ل، ك), perquè «الملك» i «ملك» siguin el mateix.
STOP_AR = set("""في من على إلى الى عن مع هذا هذه ذلك تلك هو هي هم أنا انا أنت انت نحن ما لا لم لن لماذا كيف أين اين
متى من هل قد كان كانت يكون أن ان إن إذا اذا ثم و أو او بل لكن لكن حتى كل بعض غير قال قالت يقول له لها لهم لي لك
لنا ماذا الذي التي الذين شيء شيئا هنا هناك الآن الان يا أيها ايها نعم كلا ليس ليست عند عندما بعد قبل بين فوق تحت
أمام امام وراء خلف حول دون منذ كذلك أيضا ايضا جدا فقط إنه انه إنها انها أنه انه هكذا ذا تم""".split())
TASHKIL = re.compile(r"[ؐ-ًؚ-ٰٟۖ-ۭـ]")


def arabitza(w):
    w = TASHKIL.sub("", w)
    for a, b in (("أ", "ا"), ("إ", "ا"), ("آ", "ا"), ("ى", "ي"), ("ة", "ه")):
        w = w.replace(a, b)
    for pref in ("وال", "فال", "بال", "كال", "لل", "ال", "و", "ف", "ب", "ل"):
        if w.startswith(pref) and len(w) - len(pref) >= 3:
            w = w[len(pref):]
            break
    return w


def mots_ar(t):
    fora = []
    for w in re.findall(r"[؀-ۿ]+", t or ""):
        n = arabitza(w)
        if len(n) >= 3 and n not in STOP_AR and TASHKIL.sub("", w) not in STOP_AR:
            fora.append(n)
    return fora


if __name__ == "__main__":
    parells = [json.loads(l) for l in io.open(sys.argv[1], encoding="utf-8") if l.strip()]
    minim = int(sys.argv[3]) if len(sys.argv) > 3 else 4
    llengua = sys.argv[4] if len(sys.argv) > 4 else "en"
    c_am, c_en, c_junts = collections.Counter(), collections.Counter(), collections.Counter()
    for p in parells:
        if not p.get(llengua):
            continue
        am = set(w.lower() for w in p["asr"].split() if len(w) >= 3)
        en = set(mots(p["en"])) if llengua == "en" else set(mots_ar(p["ar"]))
        c_am.update(am)
        c_en.update(en)
        for a in am:
            for e in en:
                c_junts[(a, e)] += 1
    files = []
    for a, na in c_am.items():
        if na < minim:
            continue
        cands = []
        for (x, e), nj in c_junts.items():
            if x != a or nj < 2:
                continue
            dice = 2 * nj / (na + c_en[e])
            cands.append((dice, nj, e))
        cands.sort(reverse=True)
        if cands and cands[0][0] >= 0.25:
            files.append((na, a, cands[:3]))
    files.sort(key=lambda x: -x[0])
    with io.open(sys.argv[2], "w", encoding="utf-8") as g:
        nom_ll = "anglès" if llengua == "en" else "àrab"
        g.write(f"# Glosses induïdes del corpus paral·lel ({len(parells)} rètols, mínim {minim} rètols per token, {nom_ll})\n\n")
        g.write(f"Candidats, no glosses: Dice ≥ 0,25 entre el token de l'ASR i un mot {nom_ll} del mateix rètol.\n\n")
        g.write(f"| rètols | token ASR | candidats ({nom_ll}) (Dice, rètols junts) |\n|---|---|---|\n")
        for na, a, cands in files:
            g.write(f"| {na} | `{a}` | " + "; ".join(f"**{e}** ({d:.2f}, {nj})" for d, nj, e in cands) + " |\n")
    print(f"{len(files)} tokens amb candidat → {sys.argv[2]}")
    for na, a, cands in files[:25]:
        print(f"  {na:4} {a:14} " + "; ".join(f"{e} ({d:.2f},{nj})" for d, nj, e in cands))
