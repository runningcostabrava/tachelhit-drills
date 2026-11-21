"""El so que escolta l'orella es el de la replica que li toca?

A deu episodis l'orella treu text que no casa ni amb el tifinag ni amb l'arab. Aixo es el que
passaria si el tall d'audio no contingues el moment de la replica: el model sentiria el final
d'una frase i el principi de la seguent, i trauria una cosa que no casa amb res.

El desplaçament per INDEX ja esta descartat (d de -3 a +3, i d=0 guanya pertot). Pero un
desfasament en TEMPS no: l'ull llegeix el vídeo que tinc jo i l'orella va escoltar els talls que
la fabrica va fer del SEU baixat. Si els dos fitxers no comencen al mateix punt (un tros
d'anuncis, una careta mes llarga), les mateixes marques de temps donen moments diferents.

Es busca sense tocar cap video: per a cada replica es mira quina linia de TOT l'episodi
s'assembla mes al que s'ha sentit, i es mira la distribucio de la diferencia de temps. Si no hi
ha desfasament, els encerts s'amunteguen a 0 s. Si n'hi ha, s'amunteguen al desfasament.
"""
import io, json, os, sys, glob, statistics
sys.path.insert(0, r"E:/tamazight/_magatzem")
from tria_el_millor_text import esquelet, lev  # noqa: E402

CASOS = ["hmssyuzoyqzywbaj", "oeeljuwkqlqtebzr", "nknrztnktbvaxnrs", "agnkrfivlpeuwzme",
         "bueyrhjvjyaleocf"]
MOSTRA = 70

sentit = {}
for l in io.open(r"E:/tamazight/_sentit/sortida_26/sentit.jsonl", encoding="utf-8"):
    if l.strip():
        x = json.loads(l)
        sentit[x["id"]] = (x.get("sentit") or "").strip()

for pref in CASOS:
    p = next((q for q in glob.glob(r"E:/tamazight/_magatzem/rellegit_bo/*.json")
              if os.path.basename(q).startswith(pref)), None)
    if not p:
        continue
    slug = os.path.splitext(os.path.basename(p))[0]
    llegit = json.load(io.open(p, encoding="utf-8"))["llegit"]
    temps = {}
    for i, l in enumerate(io.open(f"E:/tamazight/_visor/{slug}/subtitols.jsonl", encoding="utf-8")):
        if l.strip():
            x = json.loads(l)
            temps[str(x.get("k", i))] = x.get("t_ini")
    claus = [k for k in llegit if esquelet(llegit[k]) and esquelet(sentit.get(f"{slug}:{k}", ""))]
    cands = [(k, esquelet(llegit[k])) for k in claus]
    pas = max(1, len(claus) // MOSTRA)
    dt, di, encerts = [], [], 0
    for k in claus[::pas]:
        eo = esquelet(sentit[f"{slug}:{k}"])
        millor, taxa_millor = None, 1.0
        for k2, e2 in cands:
            t = lev(e2, eo) / max(len(e2), len(eo))
            if t < taxa_millor:
                taxa_millor, millor = t, k2
        if millor is None or taxa_millor > .35:
            continue
        encerts += 1
        di.append(int(millor) - int(k))
        if temps.get(millor) is not None and temps.get(k) is not None:
            dt.append(float(temps[millor]) - float(temps[k]))
    titol = json.load(io.open(f"E:/tamazight/_visor/{slug}/estat.json", encoding="utf-8"))["titol"]
    print(f"\n=== {titol.replace('TADFI N TSKLA - ', '')[:30]}  ({len(claus)} replicas)")
    print(f"mostra {len(claus[::pas])}, hi troba parella {encerts}")
    if di:
        zero = sum(1 for d in di if d == 0)
        print(f"la parella es la MATEIXA linia {zero} de {len(di)} vegades")
        if len(di) > zero:
            altres = [d for d in di if d]
            print(f"quan no, el salt en linies: mediana {statistics.median(altres):+.0f}, "
                  f"de {min(altres):+d} a {max(altres):+d}")
            at = [d for d in dt if abs(d) > .01]
            if at:
                print(f"i en segons: mediana {statistics.median(at):+.1f} s, "
                      f"de {min(at):+.0f} a {max(at):+.0f}")
