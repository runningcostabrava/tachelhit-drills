"""L'abecedari: cada lletra, com sona, i on es pot sentir dins la nostra biblioteca (#368).

El capítol es diu «Sons i escriptura» i de l'escriptura no en deia res: pintava tifinag a cada
targeta i donava per fet que qui mirava ja sabia què estava mirant. Això és l'altra meitat.

Tres coses, i cap no s'inventa res:

1. **Què és el tifinag** —d'on ve, que el neotifinag és el que l'IRCAM va fixar el 2003, que té
   una lletra per so i que es llegeix d'esquerra a dreta—, escrit aquí i no demanat a cap model.
2. **Cada lletra amb les paraules de casa que la porten**, i amb el tall de la gravació on es
   diu. No hi ha cap fitxer de so nou: una paraula és un drill i dos temps (vegeu `word_audio`),
   i la veu és sempre d'algú (#288). Una lletra que encara no sona **ho diu**, que és el que
   converteix el forat en una petició concreta: no «ens falten gravacions» sinó «ens falta algú
   que digui una paraula amb ṣ» (#302).
3. **Les parelles que es distingeixen per una sola lletra** —ⵖ/ⵅ, ⵜ/ⵟ, ⴷ/ⴹ, ⵙ/ⵚ, ⵣ/ⵥ, ⵔ/ⵕ, ⴽ/ⵇ—
   buscades a la biblioteca, no escrites a mà: són les que de debò ensenyen a sentir la
   diferència, i les que fan possible l'exercici de «quina de les dues sona».

Com es mira si una paraula porta una lletra: pels seus **fonemes**
(`transliteration.phonemes`), no per les lletres escrites. «rix» i «riɣ» són la mateixa paraula
escrita per dues mans (#364) i «sh», «ch» i «c» són totes la ⵛ: comparar lletra a lletra faria
desaparèixer la meitat de les gravacions que tenim.
"""
from __future__ import annotations

import time
import threading
from typing import Dict, List, Optional, Tuple

import transliteration

#: Què és aquesta escriptura, dit abans de les lletres. Del compendi d'amazic.cat (§ 1,
#: Fonologia i grafemàtica) i de la regla de la casa (#339).
QUE_ES: Dict = {
    "titol": "Què és el tifinag",
    "cos": [
        "El tifinag és l'escriptura pròpia de l'amazic. Ve de l'alfabet dels líbics, que fa més "
        "de dos mil anys ja s'escrivia al nord d'Àfrica, i els tuaregs no l'han deixat d'escriure "
        "mai. El que fem servir aquí és el **neotifinag**, la forma que l'Institut Reial de la "
        "Cultura Amaziga (IRCAM) va fixar el 2003 i que és la que s'ensenya a les escoles del "
        "Marroc.",

        "No és l'àrab ni el llatí disfressats: té **una lletra per so** i es llegeix **d'esquerra "
        "a dreta**, com el català. Si saps quin so fa cada lletra, ja el pots llegir.",

        "A l'app veuràs cada frase escrita de dues maneres, i és **el mateix idioma**: el llatí "
        "amb els seus punts i ganxos és el que escriuen els nostres parlants, i el tifinag és "
        "l'escriptura oficial de la llengua. Per això el tifinag va sempre al davant i el llatí "
        "a sota.",

        "Les lletres que el català no té són poques i es poden aprendre una per una: la ⵖ i la "
        "ⵅ (la r francesa i la j castellana), la ⵄ i la ⵃ (fetes a la gola), les emfàtiques ⴹ ⵟ "
        "ⵚ ⵥ ⵕ (dites amb la llengua més enrere) i la marca ⵯ, que arrodoneix els llavis.",
    ],
}

#: Les lletres, en l'ordre de l'IRCAM. `com` és com sona, dit per a algú que parla català;
#: `altres` és com els nostres parlants l'escriuen també, perquè qui busca «gh» trobi la ⵖ.
LLETRES: List[Dict] = [
    {"tif": "ⴰ", "lat": "a", "com": "com la a del català.", "mena": "vocal"},
    {"tif": "ⴱ", "lat": "b", "com": "com la b de «barca»."},
    {"tif": "ⴳ", "lat": "g", "com": "sempre com la g de «gat», també davant de e i de i."},
    {"tif": "ⴳⵯ", "lat": "gʷ", "com": "una g dita amb els llavis arrodonits, com si diguessis «gu» de cop.",
     "altres": ["gw"], "mena": "labialitzada"},
    {"tif": "ⴷ", "lat": "d", "com": "com la d de «dit»."},
    {"tif": "ⴹ", "lat": "ḍ", "com": "una d emfàtica: la mateixa d amb la llengua més enrere i la boca més oberta.",
     "mena": "emfatica"},
    # El so de la ⴻ és la vocal neutra, que el mòdul de transliteració escriu «ə»: la lletra i
    # el fonema no es diuen igual, i és l'única del llistat on passa.
    {"tif": "ⴻ", "lat": "e", "so": "ə", "com": "la vocal neutra, molt breu. Molts no l'escriuen mai.",
     "mena": "vocal"},
    {"tif": "ⴼ", "lat": "f", "com": "com la f de «foc»."},
    {"tif": "ⴽ", "lat": "k", "com": "com la c de «casa», també davant de e i de i."},
    {"tif": "ⴽⵯ", "lat": "kʷ", "com": "una k amb els llavis arrodonits.", "altres": ["kw"], "mena": "labialitzada"},
    {"tif": "ⵀ", "lat": "h", "com": "una h aspirada, com la h anglesa de «house»."},
    {"tif": "ⵃ", "lat": "ḥ", "com": "una h més fonda, feta amb la gola ben estreta.", "altres": ["7"], "mena": "gola"},
    {"tif": "ⵄ", "lat": "ɛ", "com": "feta ben avall a la gola, estrenyent-la. És l'ayn de l'àrab.",
     "altres": ["3", "ε"], "mena": "gola"},
    {"tif": "ⵅ", "lat": "x", "com": "com la j castellana de «jota», o la ch alemanya de «Bach».",
     "altres": ["kh", "5"]},
    {"tif": "ⵇ", "lat": "q", "com": "una k feta més enrere, amb la part del darrere de la llengua.",
     "altres": ["9"]},
    {"tif": "ⵉ", "lat": "i", "com": "com la i del català.", "mena": "vocal"},
    {"tif": "ⵊ", "lat": "j", "com": "com la j catalana de «jove».", "altres": ["ž", "dj"]},
    {"tif": "ⵍ", "lat": "l", "com": "com la l de «lluna», però sense palatalitzar."},
    {"tif": "ⵎ", "lat": "m", "com": "com la m de «mà»."},
    {"tif": "ⵏ", "lat": "n", "com": "com la n de «nas»."},
    {"tif": "ⵓ", "lat": "u", "com": "com la u del català.", "mena": "vocal"},
    {"tif": "ⵔ", "lat": "r", "com": "una r breu, com la r de «mira»."},
    {"tif": "ⵕ", "lat": "ṛ", "com": "una r emfàtica: la mateixa r amb la llengua més enrere.", "mena": "emfatica"},
    {"tif": "ⵖ", "lat": "ɣ", "com": "la r francesa de «Paris». És la mateixa posició que la ⵅ, "
                                     "però amb veu. Molts l'escriuen «gh», i al recull de Beni "
                                     "Mellal s'escriu «x» (#364).",
     "altres": ["gh", "ġ", "8", "γ"]},
    {"tif": "ⵙ", "lat": "s", "com": "com la s de «sol»."},
    {"tif": "ⵚ", "lat": "ṣ", "com": "una s emfàtica, dita amb la llengua més enrere.", "mena": "emfatica"},
    {"tif": "ⵛ", "lat": "š", "com": "com la x de «caixa».", "altres": ["c", "sh", "ch"]},
    {"tif": "ⵜ", "lat": "t", "com": "com la t de «tot»."},
    {"tif": "ⵟ", "lat": "ṭ", "com": "una t emfàtica.", "mena": "emfatica"},
    {"tif": "ⵡ", "lat": "w", "com": "com la w anglesa de «water»."},
    {"tif": "ⵢ", "lat": "y", "com": "com la i de «iaia»."},
    {"tif": "ⵣ", "lat": "z", "com": "com la z de «zero»."},
    {"tif": "ⵥ", "lat": "ẓ", "com": "una z emfàtica.", "mena": "emfatica"},
]

#: Els sons que s'assemblen i que una parella de paraules gairebé iguals ensenya a distingir.
PARELLES_SONS: List[Tuple[str, str]] = [
    ("ɣ", "x"), ("t", "ṭ"), ("d", "ḍ"), ("s", "ṣ"), ("z", "ẓ"), ("r", "ṛ"), ("k", "q"),
]

#: L'índex de paraules que es poden sentir, calculat un cop i guardat una estona: mirar els
#: fonemes de cada paraula de la biblioteca a cada visita seria treballar per no res.
_CAU: Dict[str, object] = {"quan": 0.0, "mots": None}
_CAU_SEGONS = 300
_pany = threading.Lock()


def _mots(db, refresca: bool = False) -> List[dict]:
    """Totes les paraules que tenen un tall on se les sent, amb els seus fonemes.

    Una paraula per clau: la que surt més amunt a `word_audio` —els nostres parlants primer, que
    és com `clips_for` les ordena— i no una fila per cada vegada que es diu.
    """
    ara = time.time()
    with _pany:
        if not refresca and _CAU["mots"] is not None and ara - float(_CAU["quan"]) < _CAU_SEGONS:
            return _CAU["mots"]  # type: ignore[return-value]
    from models import Drill as DrillModel, WordAudio

    files = (db.query(WordAudio, DrillModel)
             .join(DrillModel, DrillModel.id == WordAudio.drill_id)
             .filter(DrillModel.audio_url.isnot(None), DrillModel.audio_url != "")
             .order_by(WordAudio.source.asc(), WordAudio.id.asc()).all())
    vistos: Dict[str, dict] = {}
    for w, d in files:
        if w.key in vistos:
            continue
        fon = transliteration.phonemes(w.word)
        if not fon:
            continue
        vistos[w.key] = {
            "word": w.word, "key": w.key, "tif": transliteration.to_forms(w.word)["tifinagh"],
            "fonemes": fon, "drill_id": w.drill_id, "audio_url": (d.audio_url or "").strip(),
            "start": w.start_ms / 1000.0, "end": w.end_ms / 1000.0,
            "speaker": (w.speaker or getattr(d, "author", None) or None),
            "region": getattr(d, "region", None), "source": w.source or "library",
            "sentence": getattr(d, "text_tachelhit", None), "meaning": getattr(d, "text_catalan", None),
        }
    mots = list(vistos.values())
    with _pany:
        _CAU["mots"], _CAU["quan"] = mots, ara
    return mots


def so_de(lletra: Dict) -> str:
    """El fonema d'una lletra: el mateix que el llatí, tret de la ⴻ."""
    return str(lletra.get("so") or lletra["lat"])


def _posicio(fon: List[str], so: str) -> Optional[str]:
    """On sona la lletra dins la paraula: al començament, al mig o al final.

    Importa: la ⵖ no sona igual al començament que al final, i és justament el que explica el
    #364 de la x i la ɣ."""
    if so not in fon:
        return None
    i = fon.index(so)
    if i == 0:
        return "inici"
    return "final" if i == len(fon) - 1 else "mig"


def _ordena(mots: List[dict]) -> List[dict]:
    """Primer les que diu algú amb nom, i de les seves, les paraules curtes.

    Una paraula dita per Halima, d'Aït Mraw, val més que la mateixa dita per ningú en particular;
    i una paraula curta ensenya la lletra millor que una de llarga, on es perd."""
    return sorted(mots, key=lambda m: (m["source"] != "library", not (m.get("speaker") or "").strip(),
                                       len(m["fonemes"])))


def exemples(db, so: str, limit: int = 6) -> List[dict]:
    """Les paraules de la biblioteca que porten aquest so i es poden sentir."""
    quines = [m for m in _mots(db) if so in m["fonemes"]]
    fora = []
    for m in _ordena(quines)[:max(1, limit)]:
        fora.append({**{k: v for k, v in m.items() if k != "fonemes"},
                     "posicio": _posicio(m["fonemes"], so)})
    return fora


def abecedari(db, exemples_per_lletra: int = 2) -> Dict:
    """Tot l'abecedari: cada lletra amb com sona, quantes paraules nostres la porten, i dues.

    La lletra que no sona enlloc hi surt igual i amb `sona: false`: amagar-la seria amagar la
    feina que falta."""
    mots = _mots(db)
    fora = []
    for l in LLETRES:
        so = so_de(l)
        seves = [m for m in mots if so in m["fonemes"]]
        tria = _ordena(seves)[:max(0, exemples_per_lletra)]
        fora.append({
            **l,
            "quantes": len(seves),
            "sona": bool(seves),
            "exemples": [{**{k: v for k, v in m.items() if k != "fonemes"},
                          "posicio": _posicio(m["fonemes"], so)} for m in tria],
        })
    muda = [l["lat"] for l in fora if not l["sona"]]
    return {"que_es": QUE_ES, "lletres": fora, "mudes": muda,
            "paraules": len(mots), "amb_so": sum(1 for l in fora if l["sona"]),
            "total": len(fora)}


def parelles(db, per_so: int = 4) -> List[Dict]:
    """Parelles de paraules que es distingeixen per una sola lletra, totes dues amb veu.

    Buscades a la biblioteca i no escrites a mà: una parella inventada ensenyaria a sentir una
    diferència entre dues paraules que ningú no ha dit mai. Dues paraules fan parella quan tenen
    els mateixos fonemes excepte un, i aquell és el de la parella de sons."""
    mots = _mots(db)
    per_llargada: Dict[int, List[dict]] = {}
    for m in mots:
        per_llargada.setdefault(len(m["fonemes"]), []).append(m)
    fora: List[Dict] = []
    for a, b in PARELLES_SONS:
        trobades: List[Dict] = []
        for quants, grup in per_llargada.items():
            if quants < 2:
                continue
            index: Dict[Tuple, dict] = {}
            for m in grup:
                fon = m["fonemes"]
                for i, so in enumerate(fon):
                    if so not in (a, b):
                        continue
                    # la paraula amb un forat allà on va el so de la parella
                    clau = (i, tuple(fon[:i]), tuple(fon[i + 1:]))
                    altre = index.get(clau)
                    if altre is None:
                        index[clau] = m
                        continue
                    if altre["fonemes"][i] == so or altre["key"] == m["key"]:
                        continue
                    amb_a = m if so == a else altre
                    amb_b = altre if so == a else m
                    trobades.append({"so_a": a, "so_b": b, "posicio": i,
                                     "a": {k: v for k, v in amb_a.items() if k != "fonemes"},
                                     "b": {k: v for k, v in amb_b.items() if k != "fonemes"}})
        # les curtes primer: són les que es distingeixen de debò per la lletra i no pel context
        trobades.sort(key=lambda p: len(p["a"]["word"]))
        fora.append({"so_a": a, "so_b": b,
                     "tif_a": transliteration.to_forms(a)["tifinagh"],
                     "tif_b": transliteration.to_forms(b)["tifinagh"],
                     "quantes": len(trobades), "parelles": trobades[:max(1, per_so)]})
    return fora
