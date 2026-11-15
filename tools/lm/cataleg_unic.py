# -*- coding: utf-8 -*-
"""Un sol catàleg del canal Tamazight For All: vídeos + shorts + directes, amb la llengua parlada
estimada i la mena de peça. Punt 1 del programa del 15-11.

Llengua parlada, pel transcrit automàtic de YouTube (que reconeix l'àrab però no l'amazic):
  dàrija   ≥ 40 paraules per minut de subtítol automàtic   → el transcrit és text real (explicacions)
  amazic   < 15 paraules per minut (i ≥ 60 s)             → la màquina no hi entén res: veu amaziga
  mixta    entre 15 i 40, o peces curtes                   → a mirar
Mena, pel títol (àrab/anglès) i la pestanya d'origen: classe, conte, cançó, directe, opinió/altres.

ÚS: cataleg_unic.py <cataleg_canal_complet.jsonl> <cataleg_extra.jsonl> <sortida.jsonl> <resum.md> [carpeta de vtt automàtics]
"""
import collections
import io
import json
import re
import sys

CLASSE = ("تعلم", "تعليم", "درس", "قواعد", "نحو", "اللسانيات", "مصطلح", "مفردات", "كلمات", "learn", "lesson",
          "ستمازيغت", "تمرين", "معجم", "الأفعال", "الضمائر", "الصفات", "الجمع", "أبجدية", "تيفيناغ")
CONTE = ("حكاية", "قصة", "أسطورة", "خرافة", "tale", "story", "ⵜⴰⵏⴼⵓⵙⵜ", "traveller")
CANCO = ("أغنية", "نشيد", "song", "ⵜⴰⵎⴰⵣⵉⵔⵜ ⵏ ⵉⵙⵓⴼⴰ", "موسيقى")


def mena_de(titol, origen):
    t = (titol or "").lower()
    if any(k in t for k in CANCO):
        return "cançó"
    if any(k in t for k in CONTE):
        return "conte"
    if any(k in t for k in CLASSE):
        return "classe"
    if origen == "directe":
        return "directe"
    return "opinió/altres"


#: La densitat enganya dues vegades: els directes tenen subtítol automàtic només d'un tros, i
#: l'ASR de YouTube davant de l'amazic escriu brossa que compta com a paraules. El senyal bo és
#: la proporció de mots de funció del dàrija/àrab dins del transcrit: la parla en dàrija en té
#: molts; la brossa que surt de l'amazic, pocs.
FUNCIO_AR = set("في من على هذا هذه اللي ديال كاين كاينة واش باش غادي هو هي كان كانت ما لا و أو او لكن ولكن يعني بحال حتى "
                "إلى الى عن مع ذلك تلك هاد هادي داك ديك شنو علاش كيفاش فين منين بزاف شوية راه را هنا تمة عندي عندك عندو "
                "انا أنا انت أنت احنا حنا نحن هما هوما كل شي شيء واحد جوج تلاتة الأمازيغية الأمازيغ اللغة الكلمة".split())
TASHKIL = re.compile(r"[ؐ-ًؚ-ٰٟۖ-ۭـ]")


def proporcio_funcio(cami_vtt):
    """(mots, proporció de mots de funció) del transcrit automàtic, o (0, None) si no hi és."""
    import os
    if not cami_vtt or not os.path.exists(cami_vtt):
        return 0, None
    vist, mots = set(), []
    for l in io.open(cami_vtt, encoding="utf-8", errors="replace"):
        l = re.sub(r"<[^>]+>", "", l).strip()
        if not l or "-->" in l or l.startswith(("WEBVTT", "Kind:", "Language:")) or l in vist:
            continue
        vist.add(l)
        mots.extend(TASHKIL.sub("", w) for w in re.findall(r"[؀-ۿ]+", l))
    if not mots:
        return 0, None
    return len(mots), sum(1 for w in mots if w in FUNCIO_AR or w.lstrip("و") in FUNCIO_AR) / len(mots)


def llengua_de(d, vtt=None):
    dur = d.get("durada") or 0
    if not dur:
        return "?"
    if dur < 60:
        return "curta"
    n, pf = proporcio_funcio(vtt)
    if pf is None:
        return "sense transcrit"
    wpm = n / (dur / 60)
    d["mots_auto"], d["pf_auto"], d["wpm_auto"] = n, round(pf, 3), round(wpm, 1)
    #: calibrat amb controls (15-11): contes en amazic 3–14 mots i pf ≤ 0,11; classes de
    #: lingüística en amazic 1–3 mots/min; Stamazight (dàrija) 120 mots/min i pf 0,30–0,37;
    #: directes «bالدارجة» 60 mots/min i pf 0,23–0,25 (hi diuen molt d'amazic).
    if wpm >= 20 and pf >= 0.20:
        return "dàrija"
    if wpm < 10 or pf < 0.15:
        return "amazic"
    return "mixta"


if __name__ == "__main__":
    base, extra, fora, resum = sys.argv[1:5]
    vtts = sys.argv[5] if len(sys.argv) > 5 else None
    import os
    peces = {}
    for cami, origen in ((base, "vídeo"), (extra, None)):
        for l in io.open(cami, encoding="utf-8"):
            d = json.loads(l)
            d["id"] = d["id"].split("\t")[0].strip()      # el catàleg dels extres duia la línia sencera com a id
            o = origen or ("directe" if (d.get("durada") or 0) >= 1500 or "live_chat" in (d.get("humans") or []) else "short")
            d["origen"] = o
            vtt = os.path.join(vtts, d["id"] + ".ar-orig.vtt") if vtts else None
            d["llengua"] = llengua_de(d, vtt)
            d["mena"] = mena_de(d.get("titol"), o)
            d["pm_auto"] = round((d.get("auto_quantes") or 0) / max(1, (d.get("durada") or 0) / 60), 1)
            d["humans_text"] = [h for h in (d.get("humans") or []) if h != "live_chat"]
            peces[d["id"]] = d
    with io.open(fora, "w", encoding="utf-8") as g:
        for d in peces.values():
            g.write(json.dumps(d, ensure_ascii=False) + "\n")
    tot = len(peces)
    hores = lambda xs: round(sum(x.get("durada") or 0 for x in xs) / 3600, 1)
    linies = [f"# Catàleg únic del canal Tamazight For All ({tot} peces, {hores(peces.values())} h) — 15-11-2026\n"]
    for camp in ("origen", "llengua", "mena"):
        c = collections.Counter(d[camp] for d in peces.values())
        linies.append(f"\n## Per {camp}\n\n| {camp} | peces | hores | amb subtítols humans (text) |\n|---|---|---|---|")
        for k, n in c.most_common():
            xs = [d for d in peces.values() if d[camp] == k]
            linies.append(f"| {k} | {n} | {hores(xs)} | {sum(1 for d in xs if d['humans_text'])} |")
    LL = ("amazic", "dàrija", "mixta", "curta", "sense transcrit", "?")
    linies.append("\n## Llengua × mena (peces)\n\n| mena \\ llengua | " + " | ".join(LL) + " |\n|---|---|---|---|---|---|---|")
    for m in ("classe", "conte", "cançó", "directe", "opinió/altres"):
        fila = [str(sum(1 for d in peces.values() if d["mena"] == m and d["llengua"] == ll)) for ll in LL]
        linies.append(f"| {m} | " + " | ".join(fila) + " |")
    am = [d for d in peces.values() if d["llengua"] == "amazic"]
    linies.append(f"\n**Veu amaziga neta (per a H4):** {len(am)} peces, {hores(am)} h; d'aquestes, {sum(1 for d in am if d['humans_text'])} "
                  f"amb subtítols humans ({hores([d for d in am if d['humans_text']])} h).")
    io.open(resum, "w", encoding="utf-8").write("\n".join(linies) + "\n")
    print("\n".join(linies))
