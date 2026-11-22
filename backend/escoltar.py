"""Escoltar i triar: un exercici d'entendre, no de llegir (#333).

Tot el que teníem entrena a **llegir** amazic. Res no entrenava a **entendre'l quan algú el
diu**, que és el que al final serveix per parlar amb algú.

Sona un tall, no es veu el text, i l'estudiant tria entre quatre significats. Després sí que es
veu la frase i d'on surt.

**Funciona sense transcripció**, i això és el que el fa possible avui: només calen veu i
significat. Les 644 línies que tenen veu i cap paraula amaziga escrita (#320) —el corpus TutlAit,
les històries del canal— no serveixen per llegir i serveixen **exactament** per a això.

---

El pas que fa o desfà l'exercici és **triar les tres opcions dolentes**. Tres traduccions a
l'atzar fan que s'encerti pel descart: si la bona té nou paraules i les altres tres en tenen
dues, no cal haver entès res. Per això una opció dolenta ha de ser:

1. **de la mateixa llargada** (banda de ±40% de paraules),
2. **del mateix tema**, quan el sabem, i
3. **prou diferent de la bona** — perquè si la frase diu «vine aquí» i una opció diu «acosta't»,
   totes dues són certes i l'exercici és injust. Es mesura amb les paraules de contingut que
   comparteixen, i si en comparteixen massa, fora.

I **la tria queda escrita**: cada opció dolenta torna per què es va triar (la banda de llargada,
el tema, i quant s'assembla a la bona), de manera que es pot revisar com tot a la casa.
"""
from __future__ import annotations

import random
import re
from typing import Dict, List, Optional

#: Paraules que no diuen res del significat, i que per tant no compten per decidir si dues
#: traduccions volen dir el mateix.
BUIDES = {
    "el", "la", "els", "les", "un", "una", "uns", "unes", "de", "del", "dels", "d", "a", "al",
    "als", "en", "amb", "per", "però", "que", "què", "i", "o", "no", "es", "se", "em", "et",
    "ens", "li", "ho", "hi", "és", "era", "ser", "estar", "ha", "has", "he", "hem", "han",
    "va", "vas", "van", "el·la", "ell", "ella", "jo", "tu", "nosaltres", "vosaltres", "ells",
    "meu", "teu", "seu", "meva", "teva", "seva", "aquest", "aquesta", "aquell", "aquella",
    "molt", "més", "ja", "com", "quan", "on", "si", "sí",
}

_PARAULA = re.compile(r"[\wàèéíòóúïüç·']+", re.I)

#: Per sobre d'això, dues traduccions diuen prou el mateix perquè totes dues puguin ser certes.
#: La mesura és de paraules de contingut compartides sobre el total (Jaccard).
MASSA_IGUALS = 0.34

#: La llargada ha de ser propera: ±40% de paraules, i mai menys de dues de diferència.
BANDA = 0.40


def mots(text: Optional[str]) -> set:
    return {w.lower() for w in _PARAULA.findall(text or "")} - BUIDES


def s_assemblen(a: str, b: str) -> float:
    ma, mb = mots(a), mots(b)
    if not ma or not mb:
        return 0.0
    return round(len(ma & mb) / len(ma | mb), 3)


def temes(d) -> set:
    return {t.strip() for t in (getattr(d, "topics", None) or "").split(",") if t.strip()}


def _llargada_ok(bona: str, altra: str) -> bool:
    na, nb = len((bona or "").split()), len((altra or "").split())
    if not na or not nb:
        return False
    return abs(na - nb) <= max(2, round(na * BANDA))


def opcions_dolentes(bona, candidates: List, quantes: int = 3, llavor: Optional[int] = None) -> List[dict]:
    """Tres significats que podrien ser el d'aquest tall, i no ho són.

    Es tria en tres rondes i es diu de quina ronda surt cada una, perquè la tria es pugui
    revisar: primer les del mateix tema i la mateixa llargada, després les de la mateixa
    llargada, i al final, si encara en falten, qualsevol que no vulgui dir el mateix. Si al final
    no n'hi ha prou, l'exercici es queda amb les que hagi trobat en comptes d'omplir-lo amb
    escombraries: **menys opcions és millor que una opció que no serveix**.
    """
    text_bo = (bona.text_catalan or "").strip()
    seus = temes(bona)
    rnd = random.Random(llavor if llavor is not None else bona.id)

    pot_ser = []
    for d in candidates:
        altre = (d.text_catalan or "").strip()
        if d.id == bona.id or not altre or altre.lower() == text_bo.lower():
            continue
        prop = s_assemblen(text_bo, altre)
        if prop > MASSA_IGUALS:
            continue          # podria ser certa també: fora
        pot_ser.append((d, altre, prop))

    rnd.shuffle(pot_ser)
    fora: List[dict] = []
    vistos = set()

    def agafa(filtre, perque):
        for d, altre, prop in pot_ser:
            if len(fora) >= quantes:
                return
            if d.id in vistos or altre.lower() in {o["text"].lower() for o in fora}:
                continue
            if not filtre(d, altre):
                continue
            vistos.add(d.id)
            fora.append({"text": altre, "drill_id": d.id, "perque": perque,
                         "s_assembla": prop, "paraules": len(altre.split())})

    agafa(lambda d, a: bool(seus & temes(d)) and _llargada_ok(text_bo, a), "mateix tema i llargada")
    agafa(lambda d, a: _llargada_ok(text_bo, a), "mateixa llargada")
    agafa(lambda d, a: True, "cap altra de millor")
    return fora


def es_bona_per_escoltar(d) -> bool:
    """Un tall serveix si es pot sentir i si sabem què vol dir. El text amazic és igual."""
    return bool((getattr(d, "audio_url", "") or "").strip()
                and (getattr(d, "text_catalan", "") or "").strip()
                and len((d.text_catalan or "").split()) >= 2)


def sessio(db, limit: int = 10, llavor: Optional[int] = None) -> List[dict]:
    """Una tanda de talls per escoltar, cada un amb les seves quatre opcions."""
    from models import Drill as DrillModel
    tots = [d for d in db.query(DrillModel).filter(
        DrillModel.audio_url.isnot(None), DrillModel.audio_url != "",
        DrillModel.text_catalan.isnot(None), DrillModel.text_catalan != "").all()
        if es_bona_per_escoltar(d)]
    if len(tots) < 4:
        return []
    rnd = random.Random(llavor)
    tria = rnd.sample(tots, min(max(1, limit), len(tots)))
    fora = []
    for d in tria:
        dolentes = opcions_dolentes(d, tots, llavor=llavor)
        if not dolentes:
            continue
        bona = {"text": (d.text_catalan or "").strip(), "drill_id": d.id, "bona": True}
        totes = [bona] + [{**o, "bona": False} for o in dolentes]
        rnd.shuffle(totes)
        fora.append({
            "drill_id": d.id,
            "audio_url": d.audio_url,
            "opcions": totes,
            # El que es veu NOMÉS després de triar: la frase, qui la diu i d'on surt.
            "despres": {
                "text_tachelhit": (d.text_tachelhit or "").strip() or None,
                "speaker": getattr(d, "speaker", None) or getattr(d, "author", None),
                "variety": getattr(d, "variety", None), "region": getattr(d, "region", None),
                "source_title": getattr(d, "source_title", None),
                "source_url": getattr(d, "source_url", None),
                "source_channel": getattr(d, "source_channel", None),
                "glosses": getattr(d, "glosses", None),
            },
        })
    return fora


def comptes(db) -> Dict[str, int]:
    """Quant material hi ha per a aquest exercici, i quant n'hi ha que no serveix per llegir."""
    from models import Drill as DrillModel
    tots = [d for d in db.query(DrillModel).filter(
        DrillModel.audio_url.isnot(None), DrillModel.audio_url != "").all()]
    bons = [d for d in tots if es_bona_per_escoltar(d)]
    return {"amb_veu": len(tots), "serveixen": len(bons),
            "sense_text_amazic": sum(1 for d in bons if not (d.text_tachelhit or "").strip())}
