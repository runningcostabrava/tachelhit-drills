"""El compendi de gramàtica, anat a buscar en comptes de carregat (#374).

El compendi d'amazic.cat fa 549.650 caràcters —uns 137.000 tokens— i anava sencer al prompt de
sistema de **cada** pregunta, es preguntés el que es preguntés. Mesurat a `/ai/usage`: una sola
pregunta al copilot costava 0,065 € i 228.900 tokens d'entrada, seixanta vegades més que una
crida del `pipeline` (0,001 €). Una pregunta costava més del doble que tota la passa de glosses
que va escriure el paraula per paraula de 67 línies d'històries.

I hi havia una ironia pitjor que el preu: el copilot portava dos-cents mil tokens del llibre de
gramàtica i **cap frase de la biblioteca**. Quan li preguntaven una paraula, el que tenia a mà
era el llibre; i contestava amb el llibre, o se la inventava.

## Com es parteix

El compendi porta 310 seccions numerades («1.1.2 L'alfabet tifinag i la notació llatina») i set
capítols. Es parteix per aquelles seccions, que és com el llibre mateix s'ordena: així el tros
que es torna comença on comença una idea i no a mitja frase.

## Com es tria

Es compten les paraules de la pregunta dins de cada secció, i el títol pesa més que el cos —qui
busca «imperatiu» vol la secció que es diu «L'imperatiu», no les quinze que l'anomenen de
passada. No hi ha cap model pel mig: és comptar, i per això costa zero i dona sempre el mateix.

**Cada paraula pesa segons com de rara és.** Amb totes pesant igual, «les vocals» tornava el
capítol de les conjuncions: «les» surt a dues-centes seccions i s'emportava el compte, mentre
que «vocals» en tria quatre. Una llista de paraules buides escrita a mà sempre se'n deixa una;
comptar a quantes seccions surt cada paraula no se'n deixa cap.

Sempre s'hi afegeix **l'índex dels set capítols**, que val cent paraules i evita la resposta
pitjor de totes: que el model es pensi que el compendi no parla d'una cosa perquè el tros que li
ha tocat no en parla.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Dict, List, Optional, Tuple

#: Fins on pot arribar el tros que es torna. Amb 14.000 caràcters hi caben entre sis i deu
#: seccions, que és molt més del que una pregunta necessita i quatre ordres de magnitud menys
#: que el llibre sencer.
MAX_CARACTERS = 14000

_TALLS: Optional[List[Dict]] = None
_INDEX: Optional[str] = None
#: A quantes seccions surt cada paraula. D'aquí surt el pes: com més seccions, menys tria.
_ON: Optional[Dict[str, int]] = None

#: «1.1.2 L'alfabet tifinag…» — el número i el títol d'una secció, a principi de línia.
_CAP = re.compile(r"(?m)^\s*(\d+(?:\.\d+){0,3})\.?\s+(\S[^\n]{2,70})$")


def _plana(s: str) -> str:
    t = unicodedata.normalize("NFD", (s or "").lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    return t


def _mots(s: str) -> List[str]:
    return re.findall(r"[a-z0-9ɣɛḥḍṭṣẓšžʷ]{3,}", _plana(s))


def _pes(mot: str) -> float:
    """Com de rara és una paraula, i per tant quant tria.

    «les» surt a dues-centes seccions i no tria res; «imperatiu» en tria quatre i les tria
    totes. Això és el que fa que no calgui cap llista de paraules buides escrita a mà, que
    sempre se'n deixa alguna.
    """
    import math
    n = len(_TALLS or []) or 1
    return math.log(1 + n / (1 + (_ON or {}).get(mot, 0)))


def talls(text: str) -> List[Dict]:
    """El compendi partit per les seves seccions numerades."""
    global _TALLS
    if _TALLS is not None:
        return _TALLS
    caps = list(_CAP.finditer(text))
    fora: List[Dict] = []
    for i, m in enumerate(caps):
        fi = caps[i + 1].start() if i + 1 < len(caps) else len(text)
        cos = text[m.start():fi].strip()
        if len(cos) < 120:
            continue          # una capçalera repetida del peu de pàgina, no una secció
        fora.append({"num": m.group(1), "titol": m.group(2).strip(), "text": cos,
                     "mots_titol": set(_mots(m.group(2))), "mots": set(_mots(cos)),
                     "compte": _compte(_mots(cos))})
    _TALLS = fora
    global _ON
    _ON = {}
    for t in fora:
        for m in t["mots"]:
            _ON[m] = _ON.get(m, 0) + 1
    return fora


def _compte(mots: List[str]) -> Dict[str, int]:
    c: Dict[str, int] = {}
    for m in mots:
        c[m] = c.get(m, 0) + 1
    return c


def index(text: str) -> str:
    """Els capítols, perquè es vegi de què parla el llibre encara que no toqui aquest tros."""
    global _INDEX
    if _INDEX is None:
        caps = re.findall(r"(?m)^##\s+(.+)$", text)
        _INDEX = "El compendi té aquests capítols: " + "; ".join(c.strip() for c in caps) + "."
    return _INDEX


def per(pregunta: str, text: str, max_caracters: int = MAX_CARACTERS) -> Tuple[str, List[str]]:
    """El tros del compendi que fa al cas, i quines seccions s'hi han posat.

    Sense pregunta no es tria res i es torna només l'índex: val més dir de què parla el llibre
    que endevinar quin tros calia.
    """
    index_txt = index(text)
    q = set(_mots(pregunta))
    if not q:
        return index_txt, []

    talls(text)                      # perquè els pesos existeixin abans de fer-los servir
    puntuats = []
    for t in _TALLS or []:
        al_titol = sum(_pes(m) for m in q & t["mots_titol"])
        al_cos = sum(_pes(m) * min(3, t["compte"].get(m, 0)) for m in q if m in t["mots"])
        if not al_titol and not al_cos:
            continue
        # El títol pesa: qui busca «imperatiu» vol la secció que es diu així, no les quinze que
        # l'anomenen de passada. El cos es reparteix per la llargada perquè una secció de deu
        # pàgines no guanyi només per ser llarga.
        punts = al_titol * 6 + al_cos / max(1.0, len(t["compte"]) ** 0.5)
        puntuats.append((punts, t))

    puntuats.sort(key=lambda p: -p[0])
    trossos, noms, mida = [], [], 0
    for _punts, t in puntuats:
        if mida + len(t["text"]) > max_caracters:
            continue
        trossos.append(t["text"])
        noms.append("%s %s" % (t["num"], t["titol"]))
        mida += len(t["text"])
        if mida > max_caracters * 0.8:
            break
    if not trossos:
        return index_txt, []
    return index_txt + "\n\n" + "\n\n".join(trossos), noms


def oblida():
    """Per a les proves: torna a partir el text la pròxima vegada."""
    global _TALLS, _INDEX, _ON
    _TALLS = None
    _INDEX = None
    _ON = None
