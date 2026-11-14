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

## El que el model entrega, i el que es calcula aquí

Al model se li demana **només el que demana judici**:

  interlineal   una paraula catalana (o «?») PER CADA TOKEN, en ordre. Si la llista no fa la
                llargada dels tokens, la resposta sencera es rebutja. No pot ometre.
  tema          un grup nominal que digui de què va el tros, o «?».
  cita          d'entre els tokens que el codi li assenyala (els que segueixen un verb de
                dir), el que el parlant ANOMENA, marcat a la interlineal com «token» sense
                traduir. O null.
  frase         el català de corregut, si el vol. Va A PART i passa el filtre.

I el que és una consulta a les taules que ja tenim, **no se li pregunta: es calcula**. La
primera mesura (14-11, 40 trossos) ho va ensenyar: `polaritat` omplert 8 de 40 quan `ur` surt
104 vegades al corpus i la taula el glossa bé sempre; `mena` 11 de 40; `qui_hi_surt` 9 de 40,
i tres de les set podes del filtre eren persones que es llegeixen del prefix (`n-` = nosaltres,
`-ḫ` = jo). Demanar-ho al model i castigar-lo per no saber-ho enllaçar era el pitjor dels dos
mons. Tot el que el model VA omplir era cert (tema 13/13, mena 11/11, polaritat 8/8, qui 9/9);
el problema era que n'omplia un terç.

## El suport, comprovat contra la interlineal

La primera versió demanava al model un camp `soste` (paraula → tokens) a part. L'auditor va
demostrar dos forats: el filtre només mirava que l'índex fos dins de rang —apuntant tot al
token 0, la frase falsa del #17 («el meu pare») passava neta— i `MIN_PLENA = 4` deixava lliure
tot el contingut de tres lletres («gos», «pou», «nen»). I el cost: de set podes, sis van treure
coses CERTES que el model tenia escrites a la seva pròpia interlineal, i cap no va caçar una
invenció. El model sap posar la paraula a la casella i no sap tornar a dir en quina casella
l'ha posada.

Per això el suport es comprova **contra la interlineal**: una paraula plena del `tema` o de la
`frase` val si surt en alguna casella de la interlineal, o si és ella mateixa un token del tros
(«imikk» citat: el filtre vell el podava per «sense token» quan ÉS un token). `soste` queda com
a ajut opcional per quan la paraula catalana no casa literalment amb la casella.

## El que això NO fa

No comprova que la paraula catalana sigui la bona: això només ho pot dir una persona. Comprova
que cada cosa dita tingui un lloc d'on sortir. Una interlineal pot ser falsa; no pot ser
inventada del no-res. Mesurat (14-11, v2, jutjat a cegues, acord del jutge 20/20): la frase
filtrada passa de 15 falsos de 40 a 2, i perd 5 bones pel camí.
"""
import json
import re
from typing import Callable, Dict, List, Optional, Tuple

MENES = ("afirmació", "pregunta", "ordre", "citació", "?")
POLARITATS = ("afirmatiu", "negatiu", "restrictiu", "?")
PERSONES = ("jo", "tu", "ell/ella", "nosaltres", "vosaltres", "ells/elles")

#: Les paraules del català que no cal sostenir en cap token: articles, preposicions, còpula,
#: pronoms, connectors. Curada el 14-11 després que «gos, pou, nen, nom, sud» passessin sense
#: token per ser de tres lletres: ara la llargada no eximeix res, només aquesta llista.
_BUIDES = {
    "el", "la", "els", "les", "un", "una", "uns", "unes", "de", "del", "dels", "a", "al",
    "als", "en", "amb", "per", "que", "què", "i", "o", "no", "ni", "és", "són", "era",
    "eren", "ser", "hi", "ha", "han", "hem", "has", "he", "som", "sou", "ets", "s", "l", "d",
    "es", "se", "ho", "li", "lo", "em", "et", "ens", "us", "me", "te", "aquest", "aquesta",
    "aquests", "aquestes", "això", "allò", "com", "si", "més", "molt", "tot", "tots", "tota",
    "totes", "ja", "també", "però", "perquè", "quan", "on", "qui", "sí", "mateix", "mateixa",
    "cap", "res", "alguna", "algun", "alguns", "algunes", "cada", "quin", "quina", "quins",
    "quines", "seu", "seva", "seus", "seves", "meu", "meva", "teu", "teva", "nostre",
    "nostra", "nostres", "vostre", "vostra", "ell", "ella", "ells", "elles", "jo", "tu",
    "nosaltres", "vosaltres", "aquí", "allà", "ara", "després", "abans", "entre", "sobre",
    "sense", "fins", "des", "cap", "contra", "doncs", "així", "tan", "tant", "poc", "poca",
    "pot", "poden", "va", "van", "vaig", "fer", "fa", "fan", "diu", "diuen", "dir",
}
#: Les partícules i formes que donen la polaritat i la mena, en l'ortografia de l'ASR.
_NEGACIO = {"ur", "wr", "uhu"}
_RESTRICCIO = {"ġir", "ġar", "ɣir", "ɣar", "xir", "xar"}
_PREGUNTA_SI_NO = {"is", "iz"}
_PREGUNTA = {"ma", "maḫ", "max", "mad", "man", "manik", "mamnk", "mamnkd", "matta", "mani",
             "maniġ", "manta", "manwa", "mit", "maf"}
#: Formes del verb «dir» (ini) tal com surten de l'ASR: darrere d'una, el token següent és un
#: candidat a citació. `nniġ` és també «o»: ambigua, però com a candidat no fa mal.
_VERBS_DE_DIR = {"ini", "inna", "innas", "tnna", "nnan", "nniġ", "nniḫ", "ttini", "ittini",
                 "tttini", "ttinin", "ittinin", "dattinin", "daittini", "danttini", "nttini",
                 "qqarn", "iqqar", "tqqar", "qqar", "ismnns", "ism"}
#: Pronoms independents → persona. De la taula de partícules.
_PRONOMS = {"nkki": "jo", "nkkin": "jo", "nk": "jo", "kiyi": "tu", "kiyyi": "tu", "kmmi": "tu",
            "ntta": "ell/ella", "nttat": "ell/ella", "nkkni": "nosaltres", "nkknti": "nosaltres",
            "nkkwni": "nosaltres", "kunni": "vosaltres", "kunnti": "vosaltres",
            "nutni": "ells/elles", "nutnti": "ells/elles"}
#: Les persones que el verb duu escrites. Només es llegeixen si `es_verb` confirma que
#: l'arrel és un verb, perquè una `-n` final també és el plural d'un nom.
_PERSONA_VERB = (
    (re.compile(r"^n(?!n)\w{2,}$"), "nosaltres"),      # n-ssn «sabem», n-sawal «parlem»
    (re.compile(r"^\w{2,}(ḫ|ġ)$"), "jo"),              # sawal-ḫ «parlo», ri-ġ «vull»
    (re.compile(r"^t\w{2,}t$"), "tu"),                 # t-gi-t «ets», t-ri-t «vols»
    (re.compile(r"^\w{3,}n$"), "ells/elles"),          # ttini-n «diuen», lla-n «són»
)


def tokens(tros: str) -> List[str]:
    return (tros or "").split()


def _net(w: str) -> str:
    return w.lower().strip("«»\"'.,;:!?()")


def _paraules_plenes(text: str) -> List[str]:
    return [m for m in (x.lower() for x in re.findall(r"[^\W\d_]+", text or ""))
            if len(m) >= 2 and m not in _BUIDES]


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


def _cobertes(inter: List[str], toks: List[str], soste: dict) -> set:
    """Les paraules que tenen on sortir: les de les caselles de la interlineal, els tokens
    mateixos (una cita és un token), i les que `soste` lliga a un token vàlid."""
    fora = set()
    for cel in inter:
        fora.update(x.lower() for x in re.findall(r"[^\W\d_]+", cel))
    fora.update(_net(t) for t in toks)
    #: `soste` només ajuda quan apunta a una casella que el model HA OMPLERT: serveix per
    #: lligar «amazigues» a la casella «amazic». Apuntat a una casella buida no sosté res —
    #: apuntant tot al token 0 amb la interlineal tota a «?», la frase falsa del #17 passava.
    for clau, v in soste.items():
        if any(inter[i] != "?" for i in _indexos_valids(v, len(toks))):
            fora.update(x.lower() for x in re.findall(r"[^\W\d_]+", str(clau)))
    fora.discard("")
    return fora


def _sostingut(text: str, cobertes: set) -> Tuple[bool, List[str]]:
    orfes = [p for p in _paraules_plenes(text) if p not in cobertes]
    return (not orfes), orfes


def candidats_a_cita(toks: List[str]) -> List[int]:
    """Els índexs dels tokens que segueixen un verb de dir: el codi els assenyala, el model tria."""
    fora = []
    for i, t in enumerate(toks[:-1]):
        if _net(t) in _VERBS_DE_DIR:
            fora.append(i + 1)
    return fora


def polaritat(toks: List[str]) -> str:
    nets = {_net(t) for t in toks}
    if nets & _RESTRICCIO:
        return "restrictiu"
    if nets & _NEGACIO or any(_net(t).startswith("ur") and len(t) <= 3 for t in toks):
        return "negatiu"
    return "afirmatiu"


def mena(toks: List[str]) -> str:
    nets = [_net(t) for t in toks]
    if nets and nets[0] in _PREGUNTA_SI_NO:
        return "pregunta"
    if any(t in _PREGUNTA for t in nets[:3]):
        return "pregunta"
    if any(t in _VERBS_DE_DIR for t in nets):
        return "citació"
    return "afirmació"


def qui_hi_surt(toks: List[str], es_verb: Optional[Callable[[str], bool]] = None) -> List[str]:
    """Les persones que un pronom o un afix del verb sostenen. Sense `es_verb`, només pronoms
    i els afixos inequívocs (`-ḫ`/`-ġ` de primera persona)."""
    fora = []
    for t in toks:
        n = _net(t)
        if n in _PRONOMS:
            fora.append(_PRONOMS[n])
            continue
        for patro, persona in _PERSONA_VERB:
            if patro.match(n):
                arrel_verbal = es_verb(n) if es_verb else (persona == "jo")
                if arrel_verbal:
                    fora.append(persona)
                break
    vist, unics = set(), []
    for p in fora:
        if p not in vist:
            vist.add(p)
            unics.append(p)
    return unics


def comprova(resposta: str, tros: str,
             es_verb: Optional[Callable[[str], bool]] = None,
             es_gent: Optional[Callable[[str], bool]] = None) -> Tuple[Optional[dict], List[str]]:
    """(fets nets, motius de poda). Fets és None si la resposta no val com a conjunt.

    Es rebutja TOT només per dues raons: no és JSON, o la interlineal no fa la llargada dels
    tokens. La resta es poda element a element i es diu què s'ha podat.

    `es_verb(forma)` diu si una forma és verbal (per llegir-ne la persona); `es_gent(forma)`
    diu si un token designa gent (un gentilici, un pronom), que no pot ser una citació: al #9
    el model va prendre `imaziġn` («els amazics», subjecte de «diuen») per la paraula anomenada.
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
    cobertes = _cobertes(inter, toks, soste)

    tema = str((d.get("marc") or {}).get("tema") if isinstance(d.get("marc"), dict)
               else d.get("tema") or "?").strip() or "?"
    if tema != "?":
        ok, orfes = _sostingut(tema, cobertes)
        if not ok:
            motius.append(f"tema sense token: {', '.join(orfes)}")
            tema = "?"

    #: la cita: només d'entre els candidats que el codi assenyala, marcada a la interlineal
    #: com «token» sense traduir, i mai un token que designi gent
    cita = d.get("cita")
    cita = str(cita).strip() if cita else None
    if cita:
        c = _net(cita)
        idx = [i for i in candidats_a_cita(toks) if _net(toks[i]) == c]
        if not idx:
            motius.append(f"cita que no segueix cap verb de dir: {cita}")
            cita = None
        elif es_gent and es_gent(c):
            motius.append(f"cita que designa gent, no una paraula anomenada: {cita}")
            cita = None
        elif not any(_net(inter[i]) == c for i in idx):
            motius.append(f"cita no marcada a la interlineal com a «{c}»")
            cita = None
        else:
            cita = toks[idx[0]]

    frase = d.get("frase")
    frase = str(frase).strip() or None if frase is not None else None
    if frase:
        ok, orfes = _sostingut(frase, cobertes)
        if not ok:
            motius.append(f"frase amb paraules sense token: {', '.join(orfes)}")
            frase = None

    return {
        "interlineal": inter,
        "marc": {"tema": tema, "mena": mena(toks), "polaritat": polaritat(toks),
                 "qui_hi_surt": qui_hi_surt(toks, es_verb)},
        "cita": cita,
        "frase": frase,
    }, motius
