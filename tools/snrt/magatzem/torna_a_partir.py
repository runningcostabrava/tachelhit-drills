"""Tornar a posar els espais a la sortida de l'orella, sense tornar a entrenar.

En Pablo: «sovint veig que no sap distingir els espais entre paraules». Mesurat
(`quant_error_es_espai.py`), te rao i costa car:

  * **l'11-28 % del nostre error son nomes els espais** (el mateix CER amb els espais trets dels
    dos costats baixa de 0,1714 a 0,1278 al tfa-226, de 0,1440 a 0,1040 al cv-zgh);
  * el **WER es 3-4 vegades el CER**: una frontera mal posada espatlla dues paraules senceres;
  * **l'orella diu menys paraules que l'ull el 70 % de les vegades**: enganxa, no parteix.

Aixo no demana un model nou: demana **tornar a partir** el que ja diu. Una paraula enganxada es
parteix amb Viterbi sobre un lexic amb frequencies -- es tria la particio que maximitza la suma
de log P(paraula) --, i **nomes es toquen les paraules que el lexic no coneix**: si l'orella ha
dit una paraula que existeix, no s'hi toca.

**D'on surt el lexic i per que importa.** Si el lexic sortis de les mateixes frases amb que es
mesura, el resultat seria trampa. Per aixo es fa de dues maneres i es diuen les dues:

  * `biblioteca`: les 6.628 frases amazigues de l'aplicacio (gent, no maquina);
  * `snrt`: nomes el tifinag cremat als videos del SNRT, que es un corpus **separat** de les
    quatre proves amb veritat humana.

    torna_a_partir.py [biblioteca|snrt|totes]
"""
import json
import io
import math
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, r"E:/tamazight/_magatzem")

def _taula_tifinag():
    """La taula de lletres d'`acord_26.py`, llegida sense executar-lo.

    Importar-lo l'executa sencer -- llegeix `sys.argv` i es pot aturar -- i aqui nomes cal el
    mapa de lletres."""
    t = io.open(r"E:/tamazight/_magatzem/acord_26.py", encoding="utf-8").read()
    i = t.index("TIF = {")
    j = t.index("}", i) + 1
    d = {}
    exec(t[i:j], {}, d)
    return d["TIF"]


TIF = _taula_tifinag()

MAG = Path(r"E:/tamazight/_magatzem")
BIBLIO = Path(r"E:/tamazight/_entrenament/manifest_v3.jsonl")
SORTIDA = MAG / "ronda/sortida/snrt_B_sortides.json"
D_ON = sys.argv[1] if len(sys.argv) > 1 else "totes"
MIN_TROS = 2          #: cap tros d'una consonant: partiria tot
MAX_PARAULA = 14      #: mes llarg que aixo ja no es una paraula


def lev(a, b):
    if not a or not b:
        return max(len(a), len(b))
    ant = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        act = [i]
        for j, cb in enumerate(b, 1):
            act.append(min(ant[j] + 1, act[j - 1] + 1, ant[j - 1] + (ca != cb)))
        ant = act
    return ant[-1]


def rica(t):
    t = unicodedata.normalize("NFC", (t or "").lower())
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", t, flags=re.UNICODE)).strip()


def del_tifinag(t):
    fora = []
    for c in (t or ""):
        if c in TIF:
            fora.append(TIF[c])
        elif unicodedata.name(c, "").startswith("TIFINAGH"):
            fora.append("")          #: glif que no sabem llegir: fora, no inventem
        else:
            fora.append(c)
    return "".join(fora)


# ------------------------------------------------------------------ el lèxic
vocab = Counter()
if D_ON in ("biblioteca", "totes"):
    for l in io.open(BIBLIO, encoding="utf-8"):
        if l.strip():
            vocab.update(rica(json.loads(l).get("text")).split())
nb = len(vocab)
if D_ON in ("snrt", "totes"):
    for l in io.open(MAG / "text_triat.jsonl", encoding="utf-8"):
        if l.strip():
            vocab.update(rica(del_tifinag(json.loads(l).get("tifinag"))).split())
total = sum(vocab.values())
print(f"lèxic «{D_ON}»: {len(vocab)} formes ({nb} de la biblioteca), {total} aparicions")

cost = {w: -math.log(n / total) for w, n in vocab.items()}
PENA = -math.log(0.5 / total)      #: una forma desconeguda costa mes que la mes rara coneguda


def parteix(p):
    """Viterbi: la partició que costa menys. Torna la paraula sencera si no hi guanya res."""
    if p in cost or len(p) < 2 * MIN_TROS:
        return [p]
    n = len(p)
    millor = [0.0] + [math.inf] * n
    d = [0] * (n + 1)
    for i in range(1, n + 1):
        for j in range(max(0, i - MAX_PARAULA), i - MIN_TROS + 1):
            tros = p[j:i]
            c = millor[j] + cost.get(tros, PENA + .7 * len(tros))
            if c < millor[i]:
                millor[i] = c
                d[i] = j
    #: la paraula sencera, com a candidata: nomes es parteix si surt a compte de debo
    sencera = cost.get(p, PENA + .7 * len(p))
    if millor[n] >= sencera - 1e-9:
        return [p]
    fora, i = [], n
    while i > 0:
        fora.append(p[d[i]:i])
        i = d[i]
    return fora[::-1]


# ------------------------------------------------------------------ la mesura
per = defaultdict(lambda: {"ea": 0, "eb": 0, "n": 0, "wa": 0, "wb": 0, "nw": 0, "part": 0,
                           "toc": 0})
exemples = []
for x in json.load(io.open(SORTIDA, encoding="utf-8")):
    if (x.get("model") or "").startswith("abans"):
        continue
    o, d = rica(x.get("or")), rica(x.get("dit"))
    if not o:
        continue
    nou = []
    canviat = False
    for p in d.split():
        trossos = parteix(p)
        if len(trossos) > 1:
            canviat = True
        nou += trossos
    nou = " ".join(nou)
    s = per[x["prova"]]
    s["ea"] += lev(o, d)
    s["eb"] += lev(o, nou)
    s["n"] += len(o)
    s["wa"] += lev(o.split(), d.split())
    s["wb"] += lev(o.split(), nou.split())
    s["nw"] += len(o.split())
    if canviat:
        s["toc"] += 1
        if len(exemples) < 6 and lev(o, nou) < lev(o, d):
            exemples.append((d[:48], nou[:52], o[:48]))

print(f"\n{'prova':<16}{'talls':>7}{'tocats':>8}{'CER abans':>11}{'CER després':>12}"
      f"{'   │':>4}{'WER abans':>11}{'WER després':>12}")
for prova, s in sorted(per.items()):
    ca, cb = s["ea"] / max(1, s["n"]), s["eb"] / max(1, s["n"])
    wa, wb = s["wa"] / max(1, s["nw"]), s["wb"] / max(1, s["nw"])
    fa = "millor" if cb < ca else ("pitjor" if cb > ca else "igual")
    print(f"{prova:<16}{s['nw']:>7}{s['toc']:>8}{ca:>11.4f}{cb:>12.4f}"
          f"{'   │':>4}{wa:>11.4f}{wb:>12.4f}  {fa}")

print("\nexemples (abans → després → el que deia la persona):")
for a, b, o in exemples:
    print(f"   {a}\n   → {b}\n   = {o}\n")
