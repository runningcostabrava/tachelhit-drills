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
import re
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
    "ig": "si (condicional)",      #: el model escriu la ġ sense punt la meitat de les vegades
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
    # Sortides del recompte de la llista de Tamazight For All (14-11-2026): paraules de
    # funció freqüents que no hi eren, i que el diccionari glossava com si fossin mots plens
    # —i, pitjor, marcades com a lectura SEGURA. `ġir` («només») sortia «Run, Caper, Hurry».
    "ġir": "només, solament",
    "ġar": "només, solament",
    "akkw": "tot, tots, completament",
    "waḫḫa": "tot i que, encara que — o, tot sol: d'acord, va bé",
    "mad": "què, el que, qui",
    "man": "quin, quina",
    "nnit": "mateix (reforça el que s'ha dit)",
    # `nniġ` és de dues menes i totes dues són corrents: la conjunció «o», i «vaig dir» del
    # verb `ini`. No es pot triar sense el context, i per això es diuen totes dues.
    "nniġ": "o, o bé — o bé: vaig dir (ini)",
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
SEGURES = ("diccionari", "partícula", "forma gramatical", "preposició amb pronom")

#: Quina mena de paraula ha de ser l'arrel perquè la regla valgui. Treure un afix de persona
#: d'una cosa que no és cap verb és com explicar «Barcelona» dient que «bar» és un local:
#: la peça existeix al diccionari i la lectura és falsa igualment.
MENA_DE_LA_REGLA = {"verb": "verb", "annexió": "nom", "plural": "nom", "plural i annexió": "nom"}


def _particula_al_davant(mot: str) -> List[Tuple[str, str]]:
    """Els talls <partícula> + <resta> possibles, el de la resta més llarga primer.

    L'ASR enganxa la partícula a la paraula que ve darrere, i les formes perdudes més
    freqüents de la llista de Tamazight For All són justament això —no vocabulari rar:

        ma + tigan   «què són»       n + tmaziġt  «de l'amazic»    s + udġar  «al lloc»
        da + ttinin  «(que) diuen»   is + awal    «que parla?»     n + twinst «de la frase»

    El partidor general no les toca perquè demana tres lletres per tros, i té raó en
    general: deixar partir per qualsevol lletra dona mentides. Les partícules, però, són una
    llista tancada i escrita a mà, i partir per una d'aquelles no és endevinar.

    **Només pel davant.** Tallar una lletra pel darrere i dir-ne clític converteix `musaġ`
    en «tisoreta» i `igddiġ` en «gos» —la trampa que la reixa de mena va néixer per aturar—,
    i a més la persona del verb ja la treu `_sense_verb`. La resta més llarga va primera
    perquè és la que porta el significat: provant abans les partícules de dues lletres,
    `sudġar` sortia `sudġ + ar` («conduir un animal») en comptes de `s + udġar`.
    """
    fora = []
    for n in (1, 2):
        if len(mot) <= n:
            continue
        cap, resta = mot[:n], mot[n:]
        if not clau_de_particula(cap):
            continue
        #: Una resta de menys de tres lletres casa amb qualsevol entrada del diccionari, i
        #: per això el guard vell no deixava partir mai `das`, `dak`, `dag`: però aquests
        #: eren els mots sense glossa més freqüents del corpus (16, 6, 7 aparicions) i es
        #: parteixen bé perquè la resta és a la taula escrita a mà (`d`+`as` «i + li»). La
        #: resta curta val només si és a la taula; les llargues, com abans.
        if len(resta) < MIN_ARREL and not clau_de_particula(resta):
            continue
        fora.append((cap, resta))
    fora.sort(key=lambda x: -len(x[1]))
    return fora


def glossa(mot: str, al_diccionari: Callable[[str], List[str]],
           es_verb: Optional[Callable[[str], bool]] = None,
           es_nom: Optional[Callable[[str], bool]] = None,
           partir: bool = True) -> Optional[Tuple[str, str]]:
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

    #: 1. la forma tal com sona, i la partícula si també ho és
    sig = al_diccionari(mot)
    clau = clau_de_particula(mot)
    if clau:
        #: Dues o tres lletres casen amb qualsevol cosa, i el diccionari en té entrades: `ig`
        #: («si» condicional) sortia glossat «Pistachio» amb tota la seguretat del món, i
        #: `dad` (partícula verbal) sortia «pare». Quan totes dues lectures existeixen es
        #: donen totes dues, la de la gramàtica primera, i la parella NO és una lectura
        #: segura: qui la llegeixi ha de triar amb el context.
        diu, mena = _TAULA[clau], _MENA_TAULA[clau]
        if sig:
            return f"{diu} — o bé: {', '.join(sig[:2])}", f"{mena} o diccionari"
        if " — o bé: " in diu:
            #: la taula mateixa diu dues lectures (`inna`: «va dir» o «mare»); cap no és segura
            return diu, f"{mena} o diccionari"
        return diu, mena
    if sig:
        return ", ".join(sig[:4]), "diccionari"

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
            return f"{', '.join(sig[:4])} ({forma})", com

    #: 5. l'últim recurs: una partícula enganxada al davant d'una paraula que sí que se sap.
    #: `partir=False` a la crida de dins perquè no es parteixi un tros ja partit: dos talls
    #: seguits deixen una arrel de dues lletres i tornem a ser on no volíem.
    if partir:
        for cap, resta in _particula_al_davant(mot):
            diu = glossa(resta, al_diccionari, es_verb, es_nom, partir=False)
            if diu:
                return (f"{_TAULA[clau_de_particula(cap)]} + {diu[0]}",
                        "partícula enganxada")
    return None


# --------------------------------------------------------------------------------------
# El pont amb el lèxic del projecte
# --------------------------------------------------------------------------------------

#: ----------------------------------------------------------------------------------------
#: LES FORMES QUE AGUANTEN LA FRASE, I QUE EL DICCIONARI SERVEIX MALAMENT
#: ----------------------------------------------------------------------------------------
#: D'on surt aquesta taula. Una auditoria de la llista de Tamazight For All (14-11-2026) va
#: mesurar que **171 de les 220 aparicions del verb «ser» arriben al traductor absents o
#: convertides en un nom**: `tga` sortia «Juniper» 40 vegades, `illa` «Obligation, Case» 23,
#: `tlla` «action de pleurer» 22. Això explica per què les traduccions són «a mitges»: els
#: noms hi arriben i el verb no, i el model s'ha d'inventar qui fa què.
#:
#: Per què una taula a mà i no una regla. El diccionari CONEIX aquestes paraules: `mac` hi
#: consta «cependant, mais». El que passa és que les altres grafies de la mateixa paraula
#: (`maša`, `macc`, `mašš`) cauen damunt d'homògrafs —«Seek, Search», «Only»— i la lectura
#: bona perd. Contra un homògraf no hi ha tria automàtica que valgui: cal dir-ho.
#:
#: Cada forma ve d'una font escrita, no d'una endevinalla:
#:   · els paradigmes de `g` (condició) i `ili` (existència/lloc), de `iri` (voler) i les
#:     preposicions: manual de tamazight del Peace Corps Marroc (2007), que és de la
#:     varietat d'aquests vídeos. Hi consta també que els adjectius manllevats de l'àrab
#:     EXIGEIXEN `g` («iga muhim» = «és important»), i la negació amb `ur` canviant la `a`
#:     en `i`: `ur illi`, `ur tlli`, `ur llin`, `ur llint`.
#:   · `macc` com a conjunció: entrada `macc-micc-maccann`, pos=conj., del diccionari
#:     d'Oulhaj que ja tenim al lèxic, i `mac` = «cependant, mais».
#:   · `digs`/`gis`: el manual els fa servir en text corrent («is digs bit...» = «que hi ha
#:     lavabo a dins?»).
FORMES_GRAMATICALS = {
    # El verb g: «ser» de condició i descripció, I TAMBÉ «fer». El conferenciant el fa servir
    # amb tots dos sentits («ma t-iga?» = «què és?»; «ig» = fa), o sigui que cap lectura no
    # pot dir només «és». Per què no hi ha `ga`: al corpus surt `ga tawins` en una lectura i
    # `tga tawins` en l'altra del mateix tall — no és un lexema, és l'ASR menjant-se la
    # primera lletra, i això es tracta al normalitzador, no al diccionari.
    "giġ": "sóc, faig", "giḫ": "sóc, faig", "gix": "sóc, faig",
    "tgit": "ets, fas",
    #: `tgi` és sobretot el negatiu darrere d'`ur` («ur tgi ġar iwaliwn» = «no són només
    #: paraules»), i també «ets»: dues lectures, totes dues corrents.
    "tgi": "no és, no fa (darrere d'ur) — o bé: ets",
    "iga": "és, fa (ell)",
    #: tercera persona femenina i segona persona es confonen en algunes varietats
    "tga": "és, fa (ella) — o bé: ets, fas",
    "nga": "som, fem", "ng": "som, fem",
    "tgam": "sou, feu", "gan": "són, fan", "gant": "són, fan (elles)",
    "igan": "que és, que fa; que són",
    # El verb ili: ser, existir, haver-hi. Sense `lan`: és `llan` amb una sola ela, feina
    # del normalitzador.
    "illa": "hi ha, és (ell)", "tlla": "hi ha, és (ella)",
    #: en tamazight de l'Atles `lla` és també la marca de progressiu («està fent»), i aquest
    #: home parla estàndard de l'Atles: les dues lectures són corrents
    "lla": "hi ha, és — o bé: marca de progressiu (està …-nt)",
    "llan": "hi ha, són", "llant": "hi ha, són (elles)", "nlla": "som, hi som",
    "illan": "que hi ha, que són",
    "lliġ": "era, hi era", "lliḫ": "era, hi era",
    # les mateixes, en negatiu darrere d'`ur` (la `a` es torna `i`)
    "illi": "no hi ha, no és", "tlli": "no hi ha, no és",
    "llin": "no hi ha, no són", "llint": "no hi ha, no són (elles)",
    # voler: iri, que porta forma de passat amb sentit de present
    "riġ": "vull", "riḫ": "vull", "trit": "vols",
    "ira": "vol", "tra": "vol (ella)",
    "nra": "volem", "tram": "voleu", "tramt": "voleu (vosaltres)",
    # «però», la peça que porta l'estructura lògica de la frase
    #: l'ASR escriu `maša` i `mašša`, que amb la `š→c` són `maca` i `macca`: hi han de ser
    #: totes, perquè la primera versió d'aquesta taula només duia `macc` i de 93 aparicions
    #: de «però» en trobava 1.
    "macc": "però", "mac": "però", "maca": "però", "macca": "però",
    "maccan": "però", "maccann": "però",
    "micc": "però, a fi que",
    # preposicions i el pronom enganxat que el manual fa servir en text corrent
    "sg": "de, des de", "zg": "de, des de",
    "gis": "dins d'allò, hi", "digs": "dins d'allò, hi",
    "gisn": "dins d'ells, hi", "gisnt": "dins d'elles, hi",
    "dat": "davant de", "agnsu": "dins",
    # dues lectures corrents totes dues, i no es pot triar sense context
    "inna": "va dir (ini) — o bé: mare",
    "dad": "partícula verbal (da+d) — o bé: aquest",
    "dadd": "partícula verbal (da+d) — o bé: aquest",
}

#: La taula està escrita amb l'ortografia del compendi (`acku`, `max`), i el model d'ASR
#: escriu `ašku`, `maḫ`: el seu adaptador es va afinar amb `c→š` i `x→ḫ`. El lèxic ja
#: normalitza aquestes parelles, però la NOSTRA taula no ho feia, i `ašku` —la quarta
#: paraula més freqüent de la llista, 52 aparicions— no hi casava: en comptes de «perquè»
#: rebia «Because, because of, Since» del diccionari, marcat com a lectura SEGURA quan era
#: sort. Es prova la forma tal com ve i les variants d'ortografia.
#: I la labialitzada: la taula escriu `akkw` («tot») i l'ASR escriu `akku`. Contra la veritat
#: humana dels contes narrats (14-11), `akku` sortia glossat «perroquet» i «lloro» —dues
#: vegades, dues glosses diferents, totes dues falses— perquè no casava amb la taula i caia al
#: diccionari.
_ORTOGRAFIA = (("š", "c"), ("c", "š"), ("ḫ", "x"), ("x", "ḫ"), ("kku", "kkw"), ("kkw", "kku"),
               ("gu", "gw"), ("gw", "gu"))

#: Les dues taules escrites a mà, en un sol lloc per consultar-les. La mena es guarda a part
#: perquè la glossa pugui dir la veritat: `iga` no és cap partícula, és una forma del verb
#: «ser», i dir-ne «partícula» seria mentir sobre com s'hi ha arribat.
_TAULA = dict(PARTICULES)
_TAULA.update(FORMES_GRAMATICALS)
_MENA_TAULA = {k: "partícula" for k in PARTICULES}
_MENA_TAULA.update({k: "forma gramatical" for k in FORMES_GRAMATICALS})


def clau_de_particula(mot: str) -> Optional[str]:
    """La clau amb què `mot` surt a les taules a mà, o None. Prova l'ortografia de l'ASR."""
    if mot in _TAULA:
        return mot
    for a, b in _ORTOGRAFIA:
        if a in mot:
            altra = mot.replace(a, b)
            if altra in _TAULA:
                return altra
    return None


#: Prefixos de persona del verb. Un nom no en porta mai cap.
_PERSONA_A_LEXEMPLE = ("t", "te", "n", "i", "y", "tt")


def _lexemple_el_conjuga(entrada: dict) -> bool:
    """L'exemple de l'entrada duu el seu propi mot amb un prefix de persona?

    El `pos` del diccionari s'equivoca, i de manera sistemàtica: quan l'anglès té un nom i un
    verb amb la mateixa forma, hi va el nom. `sawal` («parlar») hi consta `pos: "n."` amb la
    glossa «Tick», i `shuṛṛu` («bramar») hi consta «Bray» —però l'exemple de la MATEIXA
    entrada diu `ar ishuṛṛu uɣwyul`, «el ruc brama». El prefix de persona és la prova: un nom
    no en porta.

    Això importa perquè la reixa de mena del #599 llegeix `pos`, i per tant hereta els seus
    errors: `sawalḫ` («parlo») no es resolia i acabava mal partit com `s + awalḫ`.

    Afecta 128 entrades de les 16.072 sense «v.» al pos. Poques, però netes: jutjant-ne
    quinze a l'atzar el 14-11-2026, catorze eren verbs i la quinzena un participi d'arrel
    verbal. Es demana la vora de paraula sencera, perquè buscar el mot a dins de l'exemple
    casava `kra tidrekt` amb la partícula `ra` i donava 709 falsos positius.
    """
    cap = (entrada.get("tashlhit") or "").strip().lower()
    exemple = (entrada.get("example") or "").lower()
    if len(cap) < 3 or " " in cap or not exemple:
        return False
    return any(re.search(r"\b" + re.escape(p + cap) + r"\b", exemple)
               for p in _PERSONA_A_LEXEMPLE)


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
        if _lexemple_el_conjuga(e):
            menes.add("verb")
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

        #: L'anglès es queda amb DUES places, no tres. Tenim dos diccionaris independents i
        #: cap dels dos no guanya sempre: `awal` és «Chat, Deal, Term» en anglès i «parole,
        #: langage» en francès (el francès té raó); `illan` és «Real, True, Actual» en anglès
        #: i «millet» en francès (l'anglès té raó). Amb l'anglès ocupant les tres places i
        #: `glossa` quedant-se'n tres, el francès NO arribava mai al model que escriu el
        #: català, i això passava en 937 aparicions de la llista —el 41 % de les que tenen
        #: glossa. Dues lectures independents valen més que tres del mateix lloc: quan
        #: coincideixen («tutlayt» = Language, langue) és un senyal fort, i quan no, qui
        #: munta la frase pot triar amb el context en comptes de rebre'n una a l'atzar.
        for e in (r.get("dictionary") or []):
            for en in (e.get("english") or [])[:2]:
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
