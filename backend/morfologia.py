# -*- coding: utf-8 -*-
"""Trobar al diccionari una paraula que hi és escrita d'una altra manera.

El diccionari guarda la forma de citació: `asif` «riu», `argaz` «home», `tamaziġt`. El que
surt de la boca d'algú gairebé mai no és aquesta forma. Comptant les 3.393 paraules que el
model va sentir als catorze vídeos de la llista de Tamazight For All (13-11-2026), només
1.250 —el 37 %— eren al diccionari tal com sonaven. I el que faltava no era vocabulari rar:

    da (60)  ur (46)  ma (24)  ad (18)  is (17)  ar (15)      partícules
    tga (26) iga (14) ttinin (20) tgi (13) igat (8)           el verb «ser» i el verb «dir»
    tmaziġt (23)  wasif (9)  waḍu (7)  ugafa (5)  imaziġn (13) estat d'annexió i plurals

És a dir: la gramàtica. Aquest mòdul la desfà per poder consultar el diccionari.

## La regla que ho manté honest

**Una forma derivada només val si el diccionari la coneix.** Es proposen candidates amb
regles conegudes i es pregunta al lèxic; la que no hi és, es llença. Així una regla mal
aplicada no inventa cap significat: simplement no troba res. I cada troballa diu COM s'hi ha
arribat (`annexió`, `plural`, `verb`, `partícula`), perquè qui la llegeixi —persona o
màquina— pugui desconfiar-ne.

## Les tres menes

**Annexió** (estat d'annexió). Després d'una preposició o d'un verb, el nom canvia de
principi: `asif` → `wasif`, `argaz` → `urgaz`, `agafa` → `ugafa`, `tamaziġt` → `tmaziġt`.
Són quatre canvis i es desfan.

**Plural.** `amaziġ` → `imaziġn`, `taguri` → `tguriwin`, `tamddukalt` → `timddukalin`. Les
regles es componen amb les d'annexió, que és com `tguriwin` arriba a `taguri`.

**Verb.** La persona va al voltant de l'arrel: `n-ssn` «sabem», `sawal-ḫ` «parlo»,
`t-gi-t` «ets», `lla-n` «són», i el `tt-` de l'habitual (`tt-inin` «diuen»). Es treuen els
afixos i es busca l'arrel. Aquí es demana que l'arrel faci **tres lletres o més**: amb dues,
qualsevol cosa casa per casualitat.

**Partícules.** Aquestes no vindran mai del lèxic: `lexicon._STOP` les esborra a posta
perquè embrutaven les cerques, i un diccionari de mots plens tampoc no les porta. Són una
classe tancada —es poden comptar— i van escrites aquí a mà, amb la gramàtica al davant. És
l'única part d'aquest fitxer que no surt d'una consulta, i per això va separada i marcada.

Prové del compendi d'amazic.cat i de la gramàtica d'El Mountassir que ja és al projecte.
"""
from typing import Callable, List, Optional, Tuple

#: Partícules, pronoms i preposicions: classe tancada, escrita a mà. Mai una endevinalla:
#: si una forma no és clara, no hi és. El valor és el que vol dir en català.
PARTICULES = {
    # marques de temps i d'aspecte
    "da": "partícula d'acció habitual",
    "ar": "partícula d'acció en curs",
    "ad": "partícula de futur o d'intenció",
    "rad": "partícula de futur",
    "ra": "partícula de futur",
    # negació i interrogació
    "ur": "no (negació)",
    "uhu": "no",
    "ula": "ni, tampoc; també",
    "is": "partícula de pregunta (sí o no)",
    "ma": "què, qui",
    "max": "per què",
    "maḫ": "per què",
    "maniġ": "on",
    "mani": "on",
    "manwa": "quin",
    "manta": "quina",
    "mnnaw": "quants",
    "mamnk": "com",
    "mamnkd": "com",
    # pronoms independents
    "nkki": "jo",
    "nkkin": "jo",
    "kiyi": "tu (masculí)",
    "kiyyi": "tu (masculí)",
    "kmmi": "tu (femení)",
    "ntta": "ell",
    "nttat": "ella",
    "nkkni": "nosaltres",
    "nkknti": "nosaltres (femení)",
    "kunni": "vosaltres",
    "kunnti": "vosaltres (femení)",
    "nutni": "ells",
    "nutnti": "elles",
    # possessius (van enganxats al nom)
    "nnu": "meu",
    "inu": "meu",
    "nnk": "teu (masculí)",
    "nnm": "teu (femení)",
    "nns": "seu",
    "nnġ": "nostre",
    "nnḫ": "nostre",
    "nnun": "vostre",
    "nnunt": "vostre (femení)",
    "nnsn": "llur",
    "nnsnt": "llur (femení)",
    # preposicions
    "ġ": "a, dins",
    "g": "a, dins",
    "n": "de",
    "s": "amb, cap a",
    "d": "i, amb",
    "dar": "a casa de, en poder de",
    "ġur": "a casa de, en poder de",
    "zund": "com",
    "f": "sobre, per",
    "ddaw": "sota",
    "ingr": "entre",
    "ar_prep": "fins a",
    "bla": "sense",
    # conjuncions
    "acku": "perquè",
    "aškud": "perquè",
    "imma": "pel que fa a",
    "walaynni": "però",
    "walaynnit": "però",
    "iġ": "si (condicional)",
    "mk": "quan, com",
    "lliġ": "quan",
    "nna": "que (relatiu)",
    "lli": "que (relatiu)",
    # demostratius i determinants
    "ġayad": "això",
    "ġayan": "allò",
    "ġwad": "aquest",
    "ġwan": "aquell",
    "ann": "aquell",
    "anna": "aquell",
    "ad_dem": "aquest",
    "yaḍ": "altre",
    "yaḍnin": "altre, altres",
    "aḍnin": "altre, altres",
    "kullu": "tot",
    "kraygat": "cada",
    "kra": "alguna cosa, una mica",
    "yan": "un",
    "yat": "una",
    "win": "el de",
    "tin": "la de",
    "wi": "els de",
    "ti": "les de",
    "wis": "partícula d'ordinal (masculí)",
    "tis": "partícula d'ordinal (femení)",
    # clítics de complement
    "yyi": "em",
    "iyi": "em",
    "ak": "et (masculí)",
    "am": "et (femení)",
    "as": "li",
    "aġ": "ens",
    "aḫ": "ens",
    "awn": "us",
    "asn": "els",
    "asnt": "els (femení)",
    "tn": "els",
    "tnt": "les",
    "tt": "la",
    # adverbis molt corrents
    "ġilad": "ara",
    "daġ": "també, altre cop",
    "daḫ": "també, altre cop",
    "ġik": "així",
    "imikk": "una mica",
    "bahra": "molt",
    "atig": "molt",
}

#: Les preposicions que porten el pronom enganxat: `dar`+`s` = «en poder d'ell» = «ell té».
PREPOSICIONS_AMB_CLITIC = ("dar", "ġur", "ġ", "s", "f", "ddaw", "ingr", "zund")
#: Els pronoms que s'hi enganxen, i què volen dir en aquesta posició. Van dels més llargs als
#: més curts, perquè `darnsn` no es talli a `dar`+`n`.
CLITICS = {
    "nsnt": "elles", "nsn": "ells", "unt": "vosaltres (femení)", "un": "vosaltres",
    "nġ": "nosaltres", "nḫ": "nosaltres", "snt": "elles", "sn": "ells",
    "i": "mi", "k": "tu (masculí)", "m": "tu (femení)", "s": "ell/ella",
    "ġ": "nosaltres", "ḫ": "nosaltres",
}

#: Afixos de persona del verb. Prefix i sufix es treuen alhora o per separat. La `a-` no hi
#: és: la partícula `ad` del futur va solta, i posant-la aquí `ahta` es llegia «hta, deixar».
_PREFIX_VERB = ("tt", "t", "i", "y", "n")
_SUFIX_VERB = ("nt", "at", "ġ", "ḫ", "g", "t", "n", "m")
#: Una arrel més curta que això casa amb qualsevol cosa i no prova res.
MIN_ARREL = 3


def _sense_annexio(mot: str) -> List[str]:
    """Les formes lliures possibles d'un nom en estat d'annexió."""
    fora = []
    if mot.startswith("w") and len(mot) > 2:
        fora.append(mot[1:])            # w+asif  → asif
    if mot.startswith("u") and len(mot) > 2:
        fora.append("a" + mot[1:])      # urgaz   → argaz
        fora.append("a" + mot)          # ugafa   → augafa (rar, però existeix)
        fora.append(mot[1:])            # u+X     → X
    if mot.startswith("y") and len(mot) > 2:
        fora.append(mot[1:])            # yifis   → ifis
        fora.append("i" + mot[1:])
    if mot.startswith("t") and len(mot) > 2 and mot[1] not in "aeiou":
        fora.append("ta" + mot[1:])     # tmaziġt → tamaziġt
        fora.append("ti" + mot[1:])
    return fora


def _sense_plural(mot: str) -> List[str]:
    """Els singulars possibles d'un plural."""
    fora = []
    if mot.startswith("i") and mot.endswith("n") and len(mot) > 3:
        fora.append("a" + mot[1:-1])    # imaziġn → amaziġ
        fora.append("a" + mot[1:-1] + "t")
        fora.append(mot[1:-1])
    if mot.startswith("i") and len(mot) > 3:
        fora.append("a" + mot[1:])      # iḍan → aḍan
    if mot.startswith("ti") and mot.endswith("in") and len(mot) > 4:
        fora.append("ta" + mot[2:-2] + "t")   # timddukalin → tamddukalt
        fora.append("ta" + mot[2:-2])
    if mot.endswith("win") and len(mot) > 4:
        fora.append(mot[:-3])           # tguriwin → tguri (i d'aquí, per annexió, taguri)
    if mot.endswith("tn") and len(mot) > 3:
        fora.append(mot[:-2])
    return fora


def _sense_verb(mot: str) -> List[str]:
    """Les arrels possibles d'una forma verbal, trets els afixos de persona."""
    fora = []
    caps = [""] + [p for p in _PREFIX_VERB if mot.startswith(p)]
    for cap in caps:
        tros = mot[len(cap):]
        cues = [""] + [s for s in _SUFIX_VERB if tros.endswith(s)]
        for cua in cues:
            arrel = tros[:len(tros) - len(cua)] if cua else tros
            if cap == "" and cua == "":
                continue
            if len(arrel) >= MIN_ARREL:
                fora.append(arrel)
                if arrel.startswith("tt"):     # habitual: tt-inin → inin
                    if len(arrel) - 2 >= MIN_ARREL:
                        fora.append(arrel[2:])
    return fora


def _preposicio_amb_clitic(mot: str) -> Optional[str]:
    """«dars» = dar + s: «en poder d'ell», o sigui «ell té»."""
    for prep in sorted(PREPOSICIONS_AMB_CLITIC, key=len, reverse=True):
        if not mot.startswith(prep) or len(mot) <= len(prep):
            continue
        resta = mot[len(prep):]
        if resta in CLITICS:
            return f"{PARTICULES[prep]} + {CLITICS[resta]}"
    return None


def candidates(mot: str) -> List[Tuple[str, str]]:
    """Les formes a provar al diccionari, amb el nom de la regla que les ha fetes.

    L'ordre importa poc —qui crida es queda la primera que el diccionari conegui— però les
    regles més segures van primer.
    """
    mot = (mot or "").strip().lower()
    fora: List[Tuple[str, str]] = []
    vist = set()

    def posa(f, com):
        f = f.strip()
        if f and f != mot and f not in vist and len(f) >= 2:
            vist.add(f)
            fora.append((f, com))

    for f in _sense_annexio(mot):
        posa(f, "annexió")
    for f in _sense_plural(mot):
        posa(f, "plural")
        #: un plural en annexió: tguriwin → tguri → taguri
        for g in _sense_annexio(f):
            posa(g, "plural i annexió")
    for f in _sense_verb(mot):
        posa(f, "verb")
    return fora


#: De quines maneres d'arribar-hi ens podem refiar. Les altres són una REGLA aplicada, i el
#: 13-11-2026 se'n van jutjar quaranta a mà: quinze bones, dotze defensables i **tretze
#: dolentes** —`taqafa` (l'àrab «cultura») llegit «Guess», `wid` «els de» llegit «cadena»,
#: `tla` i `tgi` (el verb ser) llegits «font» i «mena d'ahidús». Una de cada tres falla.
#: Per això qui les faci servir les ha de donar com el que són: una possibilitat.
SEGURES = ("diccionari", "partícula", "preposició amb pronom")

#: Quina mena de paraula ha de ser l'arrel perquè la regla valgui. Treure un afix de persona
#: d'una cosa que no és cap verb és com explicar «Barcelona» dient que «bar» és un local:
#: la peça existeix al diccionari i la lectura és falsa igualment.
MENA_DE_LA_REGLA = {"verb": "verb", "annexió": "nom", "plural": "nom", "plural i annexió": "nom"}


def glossa(mot: str, al_diccionari: Callable[[str], List[str]],
           es_verb: Optional[Callable[[str], bool]] = None,
           es_nom: Optional[Callable[[str], bool]] = None) -> Optional[Tuple[str, str]]:
    """Què vol dir `mot`, i com s'hi ha arribat. None si no se'n pot dir res.

    `al_diccionari(forma)` ha de tornar els significats d'aquella forma exacta, o una llista
    buida. Res del que surt d'aquí no és una invenció: o la forma és al diccionari, o és a la
    taula de partícules escrita a mà.

    `es_verb` i `es_nom` diuen de quina mena és una forma. Sense ells, una regla s'acontenta
    que la seva arrel sigui al diccionari, i es treien afixos de persona a coses que no són
    cap verb: sobre les paraules dels catorze vídeos, donar-los-hi atura 71 formes com
    `musaġ` → «tisoreta (musa)», `igddiġ` → «gos», `nislman` → «peix».

    El que la reixa NO pot aturar és una regla ben aplicada que cau en una paraula
    equivocada: `inllan` (forma del verb ser) es llegeix «henna» perquè `anlla` és un nom de
    debò i el plural de `anlla` seria això mateix. Contra això no hi ha reixa; només hi ha
    dir-ho, i per això `glossa` torna sempre COM s'hi ha arribat.
    """
    mot = (mot or "").strip().lower()
    if not mot:
        return None

    def mena_va_be(forma, com):
        vol = MENA_DE_LA_REGLA.get(com)
        if vol == "verb" and es_verb is not None:
            return es_verb(forma)
        if vol == "nom" and es_nom is not None:
            return es_nom(forma)
        return True

    #: 1. la forma tal com sona
    sig = al_diccionari(mot)
    if sig:
        return ", ".join(sig[:3]), "diccionari"

    #: 2. partícula? Va abans de les regles: `da` no és cap verb desfigurat.
    if mot in PARTICULES:
        return PARTICULES[mot], "partícula"

    #: 3. preposició amb el pronom enganxat
    p = _preposicio_amb_clitic(mot)
    if p:
        return p, "preposició amb pronom"

    #: 4. les regles, i només val la que el diccionari confirmi amb la mena que toca.
    #: Una regla NO pot acabar en una partícula: les partícules no porten afixos de persona
    #: ni es posen en annexió, i deixar-ho passar donava `blan` = «sense (bla)».
    for forma, com in candidates(mot):
        if not mena_va_be(forma, com):
            continue
        sig = al_diccionari(forma)
        if sig:
            return f"{', '.join(sig[:3])} ({forma})", com
    return None


# --------------------------------------------------------------------------------------
# El pont amb el lèxic del projecte
# --------------------------------------------------------------------------------------

def _mena(registre: dict) -> set:
    """De quina mena és una paraula, segons el que en diuen les dues fonts."""
    menes = set()
    if registre.get("verb") or registre.get("conjugation"):
        menes.add("verb")
    for e in (registre.get("dictionary") or []):
        pos = (e.get("pos") or "").lower()
        if "v." in pos:
            menes.add("verb")
        if "n." in pos:
            menes.add("nom")
    for e in (registre.get("ircam") or []):
        gram = (e.get("grammar") or "").lower()
        if "verbe" in gram:
            menes.add("verb")
        if "nom" in gram:
            menes.add("nom")
    return menes


def amb_lexicon(lexicon):
    """(significats, és_verb, és_nom) per a `glossa`, llegint el lèxic del projecte.

    Mira les quatre butaques que `lexicon.lookup` torna —diccionari d'Oulhaj, IRCAM, formes
    conjugades i arrels verbals—, no només les dues primeres: el 13-11-2026 les conjugacions
    hi eren i no es miraven, i això sol eren 99 paraules de 3.393.
    """
    cau = {}

    def _mira(forma):
        if forma not in cau:
            r = lexicon.lookup(forma, max_words=1)
            cau[forma] = r[0] if r else {}
        return cau[forma]

    def significats(forma):
        r = _mira(forma)
        fora = []

        def posa(x):
            x = (x or "").strip()
            if x and x not in fora:
                fora.append(x)

        for e in (r.get("dictionary") or []):
            for en in (e.get("english") or [])[:3]:
                posa(en)
        for e in (r.get("ircam") or []):
            posa((e.get("french") or "").split(";")[0].strip()[:40])
        for c in (r.get("conjugation") or []):
            fr = (c.get("french") or "").split(";")[0].strip()
            if fr:
                posa(f"{fr} [{c.get('tense', '')}]".strip())
        v = r.get("verb")
        if v:
            posa((v.get("french") or "").split(";")[0].strip())
        return fora

    return (significats,
            lambda forma: "verb" in _mena(_mira(forma)),
            lambda forma: "nom" in _mena(_mira(forma)))
