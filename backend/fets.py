# -*- coding: utf-8 -*-
"""Comprovar en codi el que el model entrega d'un tros: que tot el que diu s'aguanti en un token.

## Per què no una frase

El 14-11-2026 un auditor va jutjar a mà 40 trossos de la llista de Tamazight For All amb
català: 9 bons, 16 a mitges, 15 falsos. I quan es va servir el verb «ser» que faltava, els
falsos van caure a 8 però els bons es van quedar a 9: el model no va entendre més, va deixar
de mentir. Dels 8 falsos que quedaven, dos eren del model mateix i ensenyen el forat:

  · al #9 tenia `islman` = «peix» glossat bé dues vegades i va escriure «les paraules
    amazigues són poques»: UNA FRASE POT OMETRE UN TOKEN sense que es vegi;
  · al #19 tenia la glossa correcta («lligat») i va escriure «és diferent de»: UNA FRASE POT
    ESCRIURE UNA RELACIÓ, i les relacions són on viuen les inversions.

Aquest mòdul treu els dos permisos. El model entrega quatre coses, i cap no és una frase que
pugui passar sola:

  interlineal   una paraula catalana (o «?») PER CADA TOKEN, en ordre. Si la llista no fa la
                llargada dels tokens, la resposta sencera es rebutja. No pot ometre.
  marc          el tros DESCRIT, no traduït: `tema` (un grup nominal), `mena`, `polaritat`,
                `qui_hi_surt`. Cap camp admet una relació; per això cap no es pot invertir.
  cita          la paraula amaziga que el parlant anomena («da ttinin X»), copiada d'un token
                i SENSE traduir. És el producte més valuós d'una classe de lingüística.
  frase         el català de corregut, si el vol. Va A PART i passa el mateix filtre.

I la peça que ho fa estructural: `soste` lliga cada paraula plena del `tema` i de la `frase`
als tokens d'on surt. **El que no té token, es treu abans de desar-se.** Si la frase perd
paraules, la frase cau; el `tema` cau a «?»; la `cita` que no és cap token cau a null.

## El que això NO fa

No comprova que la paraula catalana sigui la bona: això només ho pot dir una persona (o el
diccionari, i ja sabem que menteix una de cada tres). Comprova que cada cosa dita tingui un
lloc d'on sortir. Una interlineal pot ser falsa; no pot ser inventada del no-res.
"""
import json
import re
from typing import Dict, List, Optional, Tuple

MENES = ("afirmació", "pregunta", "ordre", "citació", "?")
POLARITATS = ("afirmatiu", "negatiu", "restrictiu", "?")
PERSONES = ("jo", "tu", "ell/ella", "nosaltres", "vosaltres", "ells/elles")
#: Les paraules del català que no cal sostenir en cap token: articles, preposicions, còpula…
_BUIDES = {
    "el", "la", "els", "les", "un", "una", "uns", "unes", "de", "del", "dels", "a", "al",
    "als", "en", "amb", "per", "que", "què", "i", "o", "no", "és", "són", "era", "eren",
    "hi", "ha", "hem", "has", "he", "som", "sou", "ets", "s", "l", "d", "es", "se", "ho",
    "li", "lo", "em", "et", "ens", "us", "me", "te", "aquest", "aquesta", "això", "allò",
    "com", "si", "més", "molt", "tot", "tots", "tota", "totes", "ja", "també", "però",
    "perquè", "quan", "on", "qui", "sí", "mateix", "mateixa", "cap", "res", "alguna", "algun",
}
#: Fins a tres lletres tot és funció o terminació; de quatre en amunt, és contingut.
MIN_PLENA = 4


def tokens(tros: str) -> List[str]:
    return (tros or "").split()


def _paraules_plenes(text: str) -> List[str]:
    fora = []
    for m in re.findall(r"[^\W\d_]+", (text or "").lower()):
        if len(m) >= MIN_PLENA and m not in _BUIDES:
            fora.append(m)
    return fora


def _json_del_model(resposta: str) -> Optional[dict]:
    """El JSON de la resposta, tolerant les cometes de bloc i el text al voltant."""
    r = (resposta or "").strip()
    r = re.sub(r"^```(?:json)?\s*|\s*```$", "", r, flags=re.S)
    m = re.search(r"\{.*\}", r, flags=re.S)
    if not m:
        return None
    try:
        d = json.loads(m.group(0))
    except Exception:
        return None
    return d if isinstance(d, dict) else None


def _indexos_valids(v, n: int) -> List[int]:
    if isinstance(v, int):
        v = [v]
    if not isinstance(v, list):
        return []
    return sorted({i for i in v if isinstance(i, int) and 0 <= i < n})


def _cobertes(soste: dict, n: int) -> set:
    """Les paraules que `soste` lliga a algun token vàlid, clau per clau.

    Una clau pot tenir més d'una paraula («una mica» → token 4): a la primera passada sobre
    la mostra de 40 el filtre buscava «mica» com a clau sencera, no la trobava, i podava la
    frase per «paraula sense token». Era el filtre qui mentia.
    """
    fora = set()
    for clau, v in soste.items():
        if _indexos_valids(v, n):
            fora.update(re.findall(r"[^\W\d_]+", str(clau).lower()))
    return fora


def _sostingut(text: str, soste: dict, n: int) -> Tuple[bool, List[str]]:
    """Totes les paraules plenes de `text` tenen un token darrere? Torna les que no."""
    cobertes = _cobertes(soste, n)
    orfes = [p for p in _paraules_plenes(text) if p not in cobertes]
    return (not orfes), orfes


def comprova(resposta: str, tros: str) -> Tuple[Optional[dict], List[str]]:
    """(fets nets, motius de rebuig). Fets és None si la resposta no val com a conjunt.

    Es rebutja TOT només per dues raons: no és JSON, o la interlineal no fa la llargada dels
    tokens (si pot saltar-se'n un, el filtre no serveix). La resta es poda element a element
    i es diu què s'ha podat, perquè qui llegeixi el JSON sàpiga què hi havia.
    """
    toks = tokens(tros)
    n = len(toks)
    motius: List[str] = []
    d = _json_del_model(resposta)
    if d is None:
        return None, ["la resposta no és JSON"]

    inter = d.get("interlineal")
    if not isinstance(inter, list) or len(inter) != n:
        return None, [f"interlineal de {len(inter) if isinstance(inter, list) else '?'} "
                      f"elements per {n} tokens"]
    inter = [str(x).strip() or "?" for x in inter]

    soste = d.get("soste") if isinstance(d.get("soste"), dict) else {}
    soste = {str(k).lower(): v for k, v in soste.items()}

    marc_in = d.get("marc") if isinstance(d.get("marc"), dict) else {}
    tema = str(marc_in.get("tema") or "?").strip()
    if tema != "?":
        ok, orfes = _sostingut(tema, soste, n)
        if not ok:
            motius.append(f"tema sense token: {', '.join(orfes)}")
            tema = "?"
    mena = marc_in.get("mena") if marc_in.get("mena") in MENES else "?"
    pol = marc_in.get("polaritat") if marc_in.get("polaritat") in POLARITATS else "?"
    qui_in = marc_in.get("qui_hi_surt") or []
    qui = []
    if isinstance(qui_in, list):
        for p in qui_in:
            if p in PERSONES and _indexos_valids(soste.get(f"qui:{p}"), n):
                qui.append(p)
            elif p in PERSONES:
                motius.append(f"persona sense token: {p}")

    cita = d.get("cita")
    if cita is not None:
        cita = str(cita).strip()
        if cita and cita.lower() not in {t.lower() for t in toks}:
            motius.append(f"cita que no és cap token: {cita}")
            cita = None
        cita = cita or None

    frase = d.get("frase")
    if frase is not None:
        frase = str(frase).strip() or None
    if frase:
        ok, orfes = _sostingut(frase, soste, n)
        if not ok:
            motius.append(f"frase amb paraules sense token: {', '.join(orfes)}")
            frase = None

    return {
        "interlineal": inter,
        "marc": {"tema": tema, "mena": mena, "polaritat": pol, "qui_hi_surt": qui},
        "cita": cita,
        "frase": frase,
        "soste": {k: _indexos_valids(v, n) for k, v in soste.items()},
    }, motius
