"""La sèrie Baba Ali: quin vídeo del canal és cada episodi nostre, i el text per llegir-lo.

QUÈ TENIM. 3.621 frases de tretze episodis (del 2 al 15; l'1 i el 14 no hi són). Cada frase
porta l'àrab llegit de la pantalla amb OCR, una traducció catalana feta per màquina, el tall
de so i, al títol, el segon on surt («Baba Ali · episodi 15 · 29:16»). El vídeo no és nostre:
és de la SNRT, publicat al canal del Baba Ali a YouTube, i per això el visor l'encasta des
d'allà en comptes de servir-ne cap còpia.

COM SE SAP QUE EL VÍDEO ÉS AQUELL. Les marques de temps les va escriure qui va fer els talls, i
no casen amb la pujada: cada pujada comença amb uns dos minuts de resum i de rètols, i a més
algunes porten dos o tres episodis seguits. El desplaçament de cada episodi s'ha mesurat
CORRELACIONANT l'envolvent del so dels nostres talls contra la banda sonora de la pujada: el
tall que tenim desat és un tros exacte d'aquell so, i trobar-lo és un càlcul, no una
endevinalla. Un tall sol pot encertar per casualitat dins de mitja hora de conversa; aquí es
demana que molts donin el mateix desplaçament i que la segona pujada candidata quedi clarament
per sota. `data/baba_ali_pujades.json` guarda, per a cada episodi, el vídeo, el desplaçament i
amb quantes proves s'ha dit. Els episodis que no han casat surten al visor igualment, però
sense vídeo i dient-ho.

I QUAN LA PUJADA ÉS MUDA. Dues pujades (les dels episodis 7 i 9) venen de YouTube amb el so
esborrat: −91 dB de cap a cap, el silenci digital, segurament per una reclamació de la música.
Allà la correlació del so no és possible mai. S'han casat per la IMATGE: el subtítol àrab va
cremat a la franja de baix, i el moment en què un subtítol deixa lloc al següent és exactament
el que són les nostres marques; es mira quant canvia la franja de fotograma a fotograma i es
correlaciona igual. Com que l'episodi gairebé omple la pujada, només hi ha uns 40 s de
desplaçaments possibles, i el bo en casa el doble que el millor de tots els altres. La prova
que ho tanca és llegir fotogrames del segon que el desplaçament prediu i veure que la pantalla
hi diu la nostra línia, paraula per paraula. Per això `proves` diu de quina mena és (`com`).

EL TEMPS. `t` és el segon de la nostra marca. El segon del vídeo és `t + desplaçament`.

EL QUE LA MÀQUINA HI SENT (#535). A cada línia hi ha, a més, l'amazic que un model d'ASR va
sentir al tall de veu (`am`, de `text_tachelhit_suggested`). No és text de ningú: el model
enganxa els mots i s'inventa lletres, i per això va a part i es diu d'on surt. Les línies on
dues lectures coincideixen lletra per lletra van marcades (`am_acord`): 50 de les 2.727 que
s'han llegit dues vegades. Que s'ASSEMBLIN no es marca, perquè no vol dir res —els dos models
són de la mateixa família i a 2.331 parelles passen del 0,8 de semblança—; veg. `hi_ha_acord`.

EL TEXT. Les esmenes d'aquí NO toquen la biblioteca (ADR 0003: el text del parlant no es
reescriu d'ofici). S'apliquen quan es serveix la línia, i la resposta ho diu amb `esmenat`.
Són dues menes:

  · el nom del mercader. L'OCR va llegir «بلقاسم» (Belkacem) les 42 vegades que surt, i la
    pantalla escriu «أبي القاسم» (Abu-l-Qàssim). Comprovat contra la imatge l'11-11-2026 amb
    l'episodi 5 baixat del canal. No es veia llegint el text, perquè Belkacem és un nom
    marroquí corrent: la imatge és l'única que ho diu.
  · les fórmules islàmiques. La màquina les convertia en advocacions marianes cada vegada que
    en trobava una («ما شاء الله» → «Mare de Déu»). La regla mira l'àrab i esmena el començament
    del català, que així torna a valer si algun dia es tradueix de nou.
"""
import json
import os
import re
from typing import Callable, Optional

from sqlalchemy.orm import Session

AQUI = os.path.dirname(os.path.abspath(__file__))
PUJADES_JSON = os.path.join(AQUI, "data", "baba_ali_pujades.json")

#: «Baba Ali · episodi 15 · 29:16» -> 1756 segons
MARCA = re.compile(r"(?:(\d{1,2}):)?(\d{1,3}):(\d{2})\s*$")

#: una línia no s'aguanta a la pantalla més d'això, encara que la següent sigui lluny
MAX_DURADA = 6.0
MIN_DURADA = 0.8

#: Canvis que valen a tota la sèrie, a la línia que siguin.
CANVIS = [
    {"camp": "ar", "era": "بلقاسم", "ara": "أبي القاسم"},
    {"camp": "ca", "era": "Belkassem", "ara": "Abu-l-Qàssim"},
    {"camp": "ca", "era": "Belkacem", "ara": "Abu-l-Qàssim"},
]

#: Regles: mira QUÈ DIU L'ÀRAB i esmena el començament del català.
REGLES = [
    {"arab_conte": ["ما شاء الله"], "catala_comenca": ["Mare de Déu", "Mare meva"],
     "ara": "Maixal·lah"},
    {"arab_conte": ["يا لطيف", "يالطيف"], "catala_comenca": ["Mare de Déu", "Mare meva"],
     "ara": "Valga'm Déu"},
]

FONT = {
    "obra": "Baba Ali (sèrie de la SNRT)",
    "canal": "https://www.youtube.com/channel/UC5hZVXdX1xLIpILdNlq0BSw",
    "text": "àrab llegit de la pantalla amb OCR; el català és de màquina i no l'ha revisat ningú",
}

_pujades_cau: Optional[dict] = None


def _taula() -> dict:
    global _pujades_cau
    if _pujades_cau is None:
        try:
            with open(PUJADES_JSON, encoding="utf-8") as f:
                _pujades_cau = json.load(f)
        except (OSError, ValueError):
            _pujades_cau = {}
    return _pujades_cau


def pujades() -> dict:
    """La taula d'episodi -> vídeo i desplaçament, tal com es va mesurar."""
    return _taula().get("episodis", {})


def sense_video() -> dict:
    """Per què d'un episodi no en sabem el vídeo: el canal no el té, o la pujada és muda.

    Dir-ho val més que deixar-ho en blanc: qui ho miri demà sabrà si val la pena tornar-hi."""
    return _taula().get("sense_video", {})


def com_s_ha_mesurat() -> dict:
    return _taula().get("mesura", {})


def slug(playlist: Optional[str]) -> str:
    """«Baba Ali · episodi 15» -> «episodi-15». El que fa d'identificador a la URL."""
    net = (playlist or "sense-episodi").replace("Baba Ali · ", "").strip()
    return re.sub(r"\s+", "-", net)


def segon_de(titol: Optional[str]) -> Optional[float]:
    m = MARCA.search((titol or "").strip())
    if not m:
        return None
    h, mi, s = m.group(1), m.group(2), m.group(3)
    return int(h or 0) * 3600 + int(mi) * 60 + int(s)


def esmena(ca: str, ar: str) -> tuple:
    """El text tal com es mostra, i si s'hi ha tocat res. La biblioteca no es canvia."""
    ca0, ar0 = ca, ar
    for c in CANVIS:
        if c["camp"] == "ar" and c["era"] in ar:
            ar = ar.replace(c["era"], c["ara"])
        elif c["camp"] == "ca" and c["era"] in ca:
            ca = ca.replace(c["era"], c["ara"])
    for r in REGLES:
        if not any(a in ar for a in r["arab_conte"]):
            continue
        for inici in r["catala_comenca"]:
            if ca.startswith(inici):
                ca = r["ara"] + ca[len(inici):]
                break
    return ca, ar, (ca != ca0 or ar != ar0)


def _files(db: Session, amb_veu: bool = False):
    """Les frases del Baba Ali, només les columnes que el visor fa servir.

    Render dona 512 MB: demanar les files senceres de 3.621 frases (amb glosses i tot) omple la
    memòria sense cap motiu. `amb_veu` hi suma el que la màquina sent a la veu, que només fa
    falta quan es mira UN episodi, no per comptar-los tots."""
    from models import Drill as DrillModel
    cols = [DrillModel.id, DrillModel.source_playlist, DrillModel.source_title,
            DrillModel.text_catalan, DrillModel.text_arabic, DrillModel.audio_url]
    if amb_veu:
        cols += [DrillModel.text_tachelhit_suggested, DrillModel.esborranys]
    return db.query(*cols).filter(DrillModel.tag.ilike("%baba-ali%")).all()


#: per comparar dues lectures: el que compta és què s'hi sent, no on talla els mots
NOMES_LLETRES = re.compile(r"[^0-9a-zà-ɏɐ-ʯⴰ-⵿]")


def _mateixa_lectura(a: str, b: str) -> bool:
    """Dues lectures diuen el mateix si, tret dels espais i els signes, són iguals.

    No es plega cap lletra: ɣ, ɛ, ḥ i les emfàtiques són el que distingeix una paraula d'una
    altra, i plegar-les faria passar per acord el que no ho és."""
    return NOMES_LLETRES.sub("", a.lower()) == NOMES_LLETRES.sub("", b.lower()) != ""


def lectures(esborranys: Optional[str]) -> list:
    """Les lectures de màquina desades a `esborranys`: [{"text", "model"}], sense repetides."""
    try:
        fora = json.loads(esborranys or "[]")
    except (TypeError, ValueError):
        return []
    if not isinstance(fora, list):
        return []
    netes, vistos = [], set()
    for e in fora:
        if not isinstance(e, dict):
            continue
        text = (e.get("text") or "").strip()
        model = (e.get("model") or "").strip()
        if not text or model in vistos:
            continue
        vistos.add(model)
        netes.append({"text": text, "model": model})
    return netes


def hi_ha_acord(lectures_: list) -> bool:
    """Dues lectures de màquina diuen exactament el mateix.

    QUANT VAL AIXÒ, mesurat sobre les 2.727 línies del Baba Ali que tenen dues lectures (MMS
    afinat i MMS adaptador ric). Els dos models surten de la mateixa família, i per això
    s'assemblen gairebé sempre: 1.181 parelles passen del 0,9 de semblança i 2.331 del 0,8. O
    sigui que «s'assemblen» no diu res. Coincidir LLETRA PER LLETRA, en canvi, només passa a
    50 línies, i és el que es marca.

    Control, perquè la mesura no s'autoenganyi: aparellant lectures de línies DIFERENTS a
    l'atzar (3.000 parelles), cap no arriba a 0,7 i una de mil passa de 0,6. La semblança, per
    tant, sí que distingeix una línia d'una altra; el que no pot dir és si el que han sentit és
    el que s'hi diu. Això ho ha de dir una persona, i per això la lectura va a part del text."""
    if len(lectures_) < 2:
        return False
    primera = lectures_[0]["text"]
    return all(_mateixa_lectura(primera, l["text"]) for l in lectures_[1:])


def episodis(db: Session) -> list:
    """Els episodis que tenim, amb quantes línies i si en sabem el vídeo."""
    compte: dict = {}
    for f in _files(db):
        e = slug(f.source_playlist)
        c = compte.setdefault(e, {"episodi": e, "linies": 0, "amb_so": 0})
        c["linies"] += 1
        if f.audio_url:
            c["amb_so"] += 1
    fora = []
    for e, c in compte.items():
        p = pujades().get(e) or {}
        fora.append({**c,
                     "video": p.get("video"),
                     "desplacament": p.get("desplacament"),
                     "comprovat": p.get("proves"),
                     "titol_pujada": p.get("titol_pujada"),
                     "per_que_sense_video": None if p.get("video") else sense_video().get(e)})
    #: per número, que «episodi-10» no vagi davant de «episodi-2»
    fora.sort(key=lambda x: (int(m.group()) if (m := re.search(r"\d+", x["episodi"])) else 999))
    return fora


def linies(db: Session, episodi: str,
           normalitza: Optional[Callable[[str], str]] = None) -> Optional[dict]:
    """Un episodi per mirar: les línies en ordre, amb el text esmenat i el tall de so.

    Torna None si no en tenim cap línia, que és com el visor sap dir «aquest no el tenim»
    en comptes d'ensenyar una pantalla buida."""
    brutes = []
    for f in _files(db, amb_veu=True):
        if slug(f.source_playlist) != episodi:
            continue
        t = segon_de(f.source_title)
        if t is None:
            continue
        ca, ar, tocada = esmena((f.text_catalan or "").strip(), (f.text_arabic or "").strip())
        so = f.audio_url or None
        if so and normalitza:
            so = normalitza(so)
        llegides = lectures(f.esborranys)
        brutes.append({"id": f.id, "t": t, "ca": ca, "ar": ar, "so": so, "esmenat": tocada,
                       "am": (f.text_tachelhit_suggested or "").strip() or None,
                       "am_models": len(llegides),
                       "am_acord": hi_ha_acord(llegides)})
    if not brutes:
        return None
    brutes.sort(key=lambda x: (x["t"], x["id"]))

    #: Onze frases del Baba Ali estan duplicades a la biblioteca (mateix segon i mateix text,
    #: identificadors seguits). Al visor hi han de sortir un sol cop.
    #: Les onze porten, això sí, un tall de veu diferent i una lectura de màquina diferent: el
    #: subtítol es va aguantar a la pantalla mentre es deien dues coses. Aquí hi va la primera,
    #: perquè el que es pinta és el subtítol; les altres segueixen a la biblioteca i a /revisa,
    #: que és on es jutgen les lectures.
    vistes, netes = set(), []
    for x in brutes:
        clau = (x["t"], x["ca"], x["ar"])
        if clau in vistes:
            continue
        vistes.add(clau)
        netes.append(x)

    #: el final: quan comença la següent, i mai més de MAX_DURADA
    for a, b in zip(netes, netes[1:]):
        a["fi"] = round(max(min(b["t"] - 0.05, a["t"] + MAX_DURADA), a["t"] + MIN_DURADA), 2)
    netes[-1]["fi"] = round(netes[-1]["t"] + MAX_DURADA / 2, 2)

    p = pujades().get(episodi) or {}
    return {"episodi": episodi,
            "video": p.get("video"),
            "desplacament": p.get("desplacament"),
            "comprovat": p.get("proves"),
            "titol_pujada": p.get("titol_pujada"),
            "per_que_sense_video": None if p.get("video") else sense_video().get(episodi),
            "duplicades_tretes": len(brutes) - len(netes),
            "esmenades": sum(1 for x in netes if x["esmenat"]),
            "amb_veu_sentida": sum(1 for x in netes if x["am"]),
            "acords": sum(1 for x in netes if x["am_acord"]),
            "font": FONT,
            "linies": netes}
