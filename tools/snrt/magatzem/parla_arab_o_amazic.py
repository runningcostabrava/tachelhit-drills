"""De quina llengua es el so: de l'arab o de l'amazic?

Les 22 son el mateix programa (Tadfi n Tskla, una entrevista per episodi) i l'acord va de 41,7%
a 0,4%. El que canvia es el convidat. I a un episodi dolent l'orella sona a arab:

    arab     السلام عليكم، أشكركم على هذه الاستضافة
    tifinag  azul fllawn, tanmmirt...        (salutacio amaziga)
    oida     asulḫawmw usn uaa gimnara       ~ as-salamu alaykum

Si el convidat parla arab, el subtitol arab es la transcripcio i el tifinag una TRADUCCIO, i
llavors l'acord baix es correcte per sempre: d'aquells episodis no se'n pot aprendre so amazic,
per bo que es torni el model.

Es mesura sense saber res del convidat. Les dues comparacions es fan amb la MATEIXA regla
(esquelet de consonants + distancia d'edicio), una contra el tifinag i l'altra contra l'arab
passat a consonants llatines. La que guanya diu quina llengua s'esta sentint.
"""
import io, json, os, sys, glob, unicodedata
sys.path.insert(0, r"E:/tamazight/_magatzem")
from tria_el_millor_text import esquelet, lev  # noqa: E402

#: arab -> consonant llatina, nomes el que te un so clar; es treuen vocals i diacritics
AR = {"ا": "", "أ": "", "إ": "", "آ": "", "ء": "", "ئ": "", "ؤ": "", "ى": "", "ب": "b",
      "ت": "t", "ث": "t", "ج": "j", "ح": "ḥ", "خ": "ḫ", "د": "d", "ذ": "d", "ر": "r",
      "ز": "z", "س": "s", "ش": "š", "ص": "ṣ", "ض": "ḍ", "ط": "ṭ", "ظ": "ẓ", "ع": "ε",
      "غ": "ġ", "ف": "f", "ق": "q", "ك": "k", "ل": "l", "م": "m", "ن": "n", "ه": "h",
      "و": "w", "ي": "y", "ة": "t", "ـ": ""}


def esquelet_arab(t):
    fora = []
    for c in unicodedata.normalize("NFC", t or ""):
        if c in AR:
            fora.append(AR[c])
        elif c.isalpha():
            fora.append("")
    return "".join(fora)


def taxa(a, b):
    return lev(a, b) / max(len(a), len(b)) if a and b else 1.0


def main():
    sentit = {}
    for l in io.open(r"E:/tamazight/_sentit/sortida_26/sentit.jsonl", encoding="utf-8"):
        if l.strip():
            x = json.loads(l)
            sentit[x["id"]] = (x.get("sentit") or "").strip()

    out = []
    for p in sorted(glob.glob(r"E:/tamazight/_magatzem/rellegit_bo/*.json")):
        slug = os.path.splitext(os.path.basename(p))[0]
        llegit = json.load(io.open(p, encoding="utf-8"))["llegit"]
        if len(llegit) < 100:
            continue
        arab = {}
        for i, l in enumerate(io.open(f"E:/tamazight/_visor/{slug}/subtitols.jsonl", encoding="utf-8")):
            if l.strip():
                x = json.loads(l)
                arab[str(x.get("k", i))] = (x.get("arab") or "").strip()
        ct = ca = n = 0
        for k, ull in llegit.items():
            eo = esquelet(sentit.get(f"{slug}:{k}", ""))
            et, ea = esquelet(ull), esquelet_arab(arab.get(k, ""))
            if not eo or not et or not ea:
                continue
            n += 1
            ct += taxa(et, eo) <= .35
            ca += taxa(ea, eo) <= .35
        if n < 50:
            continue
        titol = json.load(io.open(f"E:/tamazight/_visor/{slug}/estat.json", encoding="utf-8"))["titol"]
        out.append((ct / n, ca / n, n, titol.replace("TADFI N TSKLA - ", "")))

    out.sort(reverse=True)
    print(f"{'convidat':<28}{'~tifinag':>10}{'~arab':>8}{'replicas':>10}  que se sent")
    for ct, ca, n, t in out:
        quin = "amazic" if ct > 2 * ca and ct > .05 else ("ARAB" if ca > ct else "cap de les dues")
        print(f"{t[:26]:<28}{100*ct:9.1f}%{100*ca:7.1f}%{n:10d}  {quin}")
    tot_t = sum(o[0] * o[2] for o in out) / sum(o[2] for o in out)
    tot_a = sum(o[1] * o[2] for o in out) / sum(o[2] for o in out)
    print(f"\nen conjunt: s'assembla al tifinag {100*tot_t:.1f}% i a l'arab {100*tot_a:.1f}%")


if __name__ == "__main__":
    main()
