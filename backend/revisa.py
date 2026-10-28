"""Les piles de revisió: cinc preguntes, i els botons que les resolen (#454).

Per què això i no una graella. Fins ara, per revisar, calia obrir `/drills`, prémer una
etiqueta i llegir una llista de 4.800 files decidint què fer amb cadascuna. **Això no es fa.**
Una pila de cinc-centes frases «per revisar» no la mira ningú, i les que més mal fan es queden
allà any rere any.

Les cinc etiquetes que l'anàlisi va posar no són cinc graus de la mateixa cosa: són **cinc
preguntes diferents**, i cadascuna té una resposta de dues o tres opcions. Aquí se'n serveix
una cada vegada, amb les seves opcions i res més.

Dues decisions que fan que això funcioni:

· **Marcar com a fet és treure l'etiqueta.** No hi ha cap taula nova ni cap estat a mantenir:
  la pila s'encongeix sola i el compte de l'etiqueta **és** la barra de progrés. I desfer una
  decisió és tornar a posar l'etiqueta.
· **«No ho sé» és una resposta.** Treu la frase de la pila d'avui sense tocar-ne res. És la
  regla de tot el projecte: el que no se sap no s'inventa.

El servidor no decideix mai res: aplica el que ha dit una persona. Les operacions que fa
—corregir, esborrar, enllaçar com a variant— ja existien totes; això només les posa darrere
d'un botó.
"""
from __future__ import annotations

import json
import re
import unicodedata
from typing import Dict, List, Optional

#: Les piles, en l'ordre en què val la pena fer-les: primer la que fa més mal.
#:
#: `dos-catalans` va primera perquè és l'única on no hi ha interpretació possible: la mateixa
#: frase té dos significats i **un dels dos és fals**, de manera que ara mateix l'app n'ensenya
#: un de mentida a qui estudia.
PILES: Dict[str, Dict] = {
    "dos-catalans": {
        "titol": "La mateixa frase amb dos significats",
        "pregunta": "Un dels dos és fals. Quin és el bo?",
        "parella": True,
        "opcions": [
            {"id": "tria", "diu": "aquest significat és el bo"},
            {"id": "dues", "diu": "són dues frases diferents"},
            {"id": "no-ho-se", "diu": "no ho sé"},
        ],
    },
    "potser-tallada": {
        "titol": "Sembla una frase tallada",
        "pregunta": "L'amazic diu tot el que diu el català?",
        "parella": True,
        "opcions": [
            {"id": "esborra", "diu": "esborra la curta"},
            {"id": "dues", "diu": "són diferents, deixa-les"},
            {"id": "no-ho-se", "diu": "no ho sé"},
        ],
    },
    "dos-amazics": {
        "titol": "Dues maneres de dir el mateix",
        "pregunta": "Són la mateixa paraula, una altra paraula, o una està malament?",
        "parella": True,
        "opcions": [
            {"id": "so", "diu": "la mateixa paraula, escrita d'una altra manera"},
            {"id": "paraula", "diu": "una altra manera de dir-ho"},
            {"id": "esborra", "diu": "una és un tros de l'altra"},
            {"id": "no-ho-se", "diu": "no ho sé"},
        ],
    },
    "arab-dins": {
        "titol": "Lletres àrabs dins del text amazic",
        "pregunta": "És una citació a posta o un camp enganxat malament?",
        "parella": False,
        "opcions": [
            {"id": "deixa", "diu": "és a posta"},
            {"id": "no-ho-se", "diu": "no ho sé"},
        ],
    },
    "per-escriure": {
        "titol": "Té veu i significat, i ningú no ha escrit l'amazic",
        "pregunta": "Dels esborranys de màquina, n'hi ha cap de bo?",
        "parella": False,
        "opcions": [
            {"id": "tria", "diu": "aquest esborrany és bo"},
            {"id": "no-ho-se", "diu": "cap dels dos"},
        ],
    },
}

TIFINAG = re.compile(r"[ⴰ-⵿]")


def esborranys_de(d) -> List[Dict]:
    """Els esborranys d'una frase, ordenats pel que més acord té amb els altres.

    Qui decideix ha de veure **quants** models ho han llegit i **si coincideixen**: una lectura
    sola és una endevinalla; tres que diuen el mateix és una altra cosa. Si la frase no en porta
    cap de nou, es fa servir el `text_tachelhit_suggested` de sempre, perquè la pantalla segueixi
    funcionant amb el que ja hi ha a la biblioteca.
    """
    fora = []
    cru = (getattr(d, "esborranys", "") or "").strip()
    if cru:
        try:
            carregats = json.loads(cru)
            if isinstance(carregats, list):
                for e in carregats:
                    if isinstance(e, dict) and (e.get("text") or "").strip():
                        fora.append({"text": e["text"].strip(),
                                     "model": (e.get("model") or "").strip() or None,
                                     "acord": e.get("acord")})
        except Exception:
            pass                       # un JSON trencat no ha de tombar la pantalla
    if not fora:
        vell = (getattr(d, "text_tachelhit_suggested", "") or "").strip()
        if vell:
            fora.append({"text": vell, "model": None, "acord": None})
    fora.sort(key=lambda e: -(e.get("acord") or 0))
    return fora


def etiquetes(d) -> List[str]:
    return [t.strip() for t in (getattr(d, "tag", "") or "").split(",") if t.strip()]


def te_pila(d, pila: str) -> bool:
    return pila in etiquetes(d)


def treu_etiqueta(d, pila: str) -> None:
    """Fet és fora de la pila. Això és tot el registre de progrés que hi ha, i és suficient."""
    queden = [t for t in etiquetes(d) if t != pila]
    d.tag = ", ".join(queden) if queden else None


def _pla(t: Optional[str]) -> str:
    t = unicodedata.normalize("NFC", (t or "").lower())
    return re.sub(r"\s+", " ", re.sub(r"[^\w\sⴰ-⵿]", " ", t)).strip()


def companya(db, drill, pila: str):
    """L'altra frase de la pregunta, quan la pregunta és un parell.

    A `dos-catalans` la companya és la que diu **el mateix amazic amb un altre significat**; a
    les altres dues, la que diu **el mateix significat amb un altre amazic**. Sense ella, la
    pregunta no es pot respondre: no es tria entre una cosa i res.
    """
    from models import Drill as DrillModel
    if not PILES.get(pila, {}).get("parella"):
        return None
    if pila == "dos-catalans":
        mateix = _pla(drill.text_tachelhit)
        if not mateix:
            return None
        for altre in db.query(DrillModel).filter(DrillModel.id != drill.id).all():
            if _pla(altre.text_tachelhit) == mateix and _pla(altre.text_catalan) != _pla(drill.text_catalan):
                return altre
        return None
    mateix = _pla(drill.text_catalan)
    if not mateix:
        return None
    for altre in db.query(DrillModel).filter(DrillModel.id != drill.id).all():
        if _pla(altre.text_catalan) == mateix and _pla(altre.text_tachelhit) != _pla(drill.text_tachelhit):
            return altre
    return None


def comptes(db) -> Dict[str, int]:
    """Quantes en queden a cada pila. Això és la barra de progrés."""
    from models import Drill as DrillModel
    fora = {k: 0 for k in PILES}
    for d in db.query(DrillModel).filter(DrillModel.tag.isnot(None)).all():
        for t in etiquetes(d):
            if t in fora:
                fora[t] += 1
    return fora


def seguent(db, pila: str, saltats: Optional[List[int]] = None):
    """La frase següent d'aquesta pila, saltant el que ja s'ha dit que no se sap avui."""
    from models import Drill as DrillModel
    saltats = set(saltats or [])
    for d in db.query(DrillModel).filter(DrillModel.tag.isnot(None)).order_by(DrillModel.id.asc()).all():
        if d.id in saltats or not te_pila(d, pila):
            continue
        return d
    return None


def decideix(db, pila: str, drill, altre, opcio: str, tria: Optional[int] = None,
             esborrany: Optional[str] = None) -> Dict:
    """Aplica el que ha dit una persona, i treu la frase de la pila.

    `no-ho-se` no toca res: només la treu d'avui. El que no se sap no s'escriu.
    """
    if opcio not in {o["id"] for o in PILES[pila]["opcions"]}:
        raise ValueError("opció desconeguda")

    fet = {"pila": pila, "drill": drill.id, "opcio": opcio, "canvis": []}

    if opcio == "no-ho-se":
        return fet                                  # ni es treu l'etiqueta: tornarà un altre dia

    if opcio == "dues" or opcio == "deixa":
        treu_etiqueta(drill, pila)
        if altre is not None:
            treu_etiqueta(altre, pila)
        fet["canvis"].append("s'han deixat com estaven")

    elif opcio == "tria":
        if pila == "per-escriure":
            # Un esborrany triat NO és el text del parlant: va a `*_suggested`, i allà el
            # confirma qui sàpiga la llengua. Aquesta pantalla no escriu text amazic de ningú.
            drill.text_tachelhit_suggested = (esborrany or "").strip() or None
            fet["canvis"].append("l'esborrany s'ha desat com a suggeriment")
            treu_etiqueta(drill, pila)
        else:
            bona = drill if tria == drill.id else altre
            dolenta = altre if tria == drill.id else drill
            if bona is None or dolenta is None:
                raise ValueError("falta la companya")
            dolenta.text_catalan = bona.text_catalan
            fet["canvis"].append("el significat de #%d passa a ser el de #%d" % (dolenta.id, bona.id))
            treu_etiqueta(drill, pila)
            if altre is not None:
                treu_etiqueta(altre, pila)

    elif opcio == "esborra":
        if altre is None:
            raise ValueError("falta la companya")
        curta, llarga = sorted([drill, altre], key=lambda d: len(d.text_tachelhit or ""))
        if (curta.audio_url or "").strip():
            # Una frase amb veu no s'esborra mai per ser curta: la gravació és d'algú.
            treu_etiqueta(drill, pila)
            treu_etiqueta(altre, pila)
            fet["canvis"].append("la curta té veu: no s'esborra, només surt de la pila")
        else:
            db.delete(curta)
            treu_etiqueta(llarga, pila)
            fet["canvis"].append("s'ha esborrat #%d" % curta.id)

    elif opcio in ("so", "paraula"):
        if altre is None:
            raise ValueError("falta la companya")
        # L'original és el que té veu; si cap, el més antic.
        original, variant = sorted([drill, altre],
                                   key=lambda d: (not (d.audio_url or "").strip(), d.id))
        variant.variant_of = original.id
        variant.variant_kind = opcio
        treu_etiqueta(drill, pila)
        treu_etiqueta(altre, pila)
        fet["canvis"].append("#%d queda com a variant «%s» de #%d" % (variant.id, opcio, original.id))

    return fet
