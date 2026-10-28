"""Exercicis que ensenyen el punt de la unitat, fets amb les frases de la biblioteca (#428).

Les preguntes que ja hi havia a una lliçó comproven que **reconeixes** una frase —«com es diu
X?», «escolta i tria el significat»—, i això no és el que la unitat ensenya. A «possessius» el
que s'ha d'aprendre és que la casa d'ell no es diu com la casa teva; a «estat d'annexió», que
`argaz` es torna `urgaz` darrere d'una preposició.

Per això cada unitat diu **quina és la seva peça**, i l'exercici la tapa o la pregunta. La peça
va escrita a mà, unitat per unitat, i no endevinada: una peça mal triada ensenya una cosa falsa,
que és pitjor que no tenir exercici.

Tres regles que fan que un exercici valgui:

· **Només frases que algú ha dit.** La resposta és el que va dir qui la va dir, i no una forma
  que hàgim construït nosaltres.
· **Una sola peça a la frase.** Si el patró hi casa dues vegades, tapar-ne una és ambigu: qui
  respon no pot saber quina li demanes. Aquella frase no serveix i es deixa.
· **Es compara pel SO.** Qui escriu `gh` on la resposta diu `ɣ` ha encertat: són la mateixa
  lletra escrita per dues mans (#364), i dir-li que no seria ensenyar-li una falsedat.

I la regla de sempre: si una unitat no té prou frases per a un exercici honest, **no se'n fa cap
i es diu**, com ja fem amb les seccions buides del Mètode.
"""
from __future__ import annotations

import random
import re
from typing import Dict, List, Optional

import practice
import transliteration

#: La peça de cada unitat: què es tapa, com es diu a la pantalla i què es pregunta.
#:
#: Els patrons surten de mirar com ho escriu la biblioteca, no d'un manual: els possessius hi
#: són amb guionet (`tarbat-ns`) i sense (`tarbat nun`), i amb la x de Beni Mellal (`-nnx`) tant
#: com amb la ɣ. Un patró que només conegués la forma del llibre deixaria fora mitja biblioteca.
PECES: Dict[str, Dict] = {
    "possessius": {
        "nom": "el possessiu",
        "pregunta": "De qui és? Escriu el tros que falta.",
        "ajuda": "«meu» és -inu / -nu, «teu» -nnk (a un home) i -nnm (a una dona), «seu» -nns / -ns.",
        "patro": re.compile(
            r"(?:(?<=\s)|(?<=-)|(?<=‑))"
            r"(inu|innu|nnu|nu|nnk|nnek|nnm|nnem|nns|nnes|ns|nnɣ|nnx|nnaɣ|nnax|nnun|nun|nnsn|nsn|winu|winsh|wins)"
            r"(?=\s|$|[.,!?¿;:])", re.I),
    },
    "negacio": {
        "nom": "la negació",
        "pregunta": "Com es diu que NO? Escriu el tros que falta.",
        "ajuda": "La negació va davant del verb: «ur», i de vegades amb un «ša» al final.",
        "patro": re.compile(r"(?:(?<=^)|(?<=\s))(ur|urd|uhu)(?=\s|$|[.,!?¿;:])", re.I),
    },
    "preposicions": {
        "nom": "la preposició",
        "pregunta": "Quina preposició hi va? Tria-la.",
        "ajuda": "«g/ɣ» és a dins, «s» cap a o amb, «f» damunt, «zg» des de, «dar/ɣur» a casa de o tenir.",
        "patro": re.compile(
            r"(?:(?<=^)|(?<=\s))(g|ɣ|gh|x|s|f|zg|zɣ|dar|ɣur|ghur|xur|ɣer|ger)(?=\s)", re.I),
    },
}

#: L'estat d'annexió es queda fora a posta.
#:
#: La seva peça són les primeres lletres del nom —«argaz» es torna «urgaz», «tamɣart» es torna
#: «tmɣart»—, i això no es pot trobar amb un patró: darrere d'una preposició, un nom que COMENÇA
#: per t- («taffiwin», «tirra») s'hi veu igual que un que ha perdut la a-, i el patró en faria un
#: exercici que ensenya una cosa falsa. Caldrà la forma lliure del nom per poder-ho preguntar:
#: aleshores l'exercici és «com comença darrere de la preposició?» amb les dues formes al davant.

#: Com a mínim, perquè un exercici valgui la pena: quatre frases per poder-ne fer tres i que les
#: respostes falses surtin de la mateixa unitat.
MIN_FRASES = 4


def _net(t: Optional[str]) -> str:
    return " ".join((t or "").split())


def igual_de_so(a: str, b: str) -> bool:
    """Si dues respostes diuen el mateix, escrites com sigui.

    `gh`/`ɣ`, `c`/`š`, `3`/`ɛ`: la mateixa lletra per dues mans. La clau fonètica del projecte ja
    ho sap i és la que fan servir la cerca i el repàs."""
    return practice.sound_key(a or "") == practice.sound_key(b or "")


def _darrere_de(text: str, inici: int, quines) -> bool:
    """Si la paraula que hi ha just abans d'aquesta posició és una de les que es demanen."""
    abans = text[:inici].strip().split()
    return bool(abans) and abans[-1].strip("-‑").lower() in quines


def _una_peca(text: str, peca: Dict) -> Optional[re.Match]:
    """L'única peça de la unitat dins d'aquesta frase, o res.

    Dues peces a la mateixa frase no serveixen: tapar-ne una és demanar una cosa que qui respon
    no pot endevinar quina és."""
    quines = [m for m in peca["patro"].finditer(text)
              if "nomes_darrere" not in peca or _darrere_de(text, m.start(1), peca["nomes_darrere"])]
    return quines[0] if len(quines) == 1 else None


def _amb_el_buit(text: str, m: re.Match) -> str:
    """La frase amb la peça tapada, i el buit de la mida de la peça."""
    return text[:m.start(1)] + "·" * max(3, len(m.group(1))) + text[m.end(1):]


def fes(slug: str, frases: List, quants: int = 3) -> List[Dict]:
    """Els exercicis que aquesta unitat pot fer de debò amb les seves frases.

    `frases` són les files de la unitat (drills). Torna una llista buida quan no n'hi ha prou:
    val més cap exercici que un de dolent.
    """
    peca = PECES.get(slug)
    if not peca:
        return []
    bones = []
    for d in frases:
        text = _net(getattr(d, "text_tachelhit", None))
        ca = _net(getattr(d, "text_catalan", None))
        if not text or not ca or len(text.split()) < 2:
            continue
        m = _una_peca(text, peca)
        if m is None:
            continue
        bones.append((d, text, ca, m))
    if len(bones) < MIN_FRASES:
        return []

    # Les que es poden escoltar van davant: un exercici que a més sona ensenya dues coses.
    bones.sort(key=lambda t: (not (getattr(t[0], "audio_url", "") or "").strip(), len(t[1])))
    totes_les_formes = sorted({m.group(1).lower() for _, _, _, m in bones})

    fora: List[Dict] = []
    for d, text, ca, m in bones[:max(1, quants)]:
        resposta = m.group(1)
        rnd = random.Random(d.id)
        # Les falses són formes que la MATEIXA unitat fa servir de debò: inventar-ne una seria
        # ensenyar una forma que ningú no diu.
        altres = [f for f in totes_les_formes if not igual_de_so(f, resposta)]
        rnd.shuffle(altres)
        # Les opcions es pinten en minúscula: la frase pot començar amb majúscula i una llista
        # amb «Winu» i «nns» ja diu quina és la bona sense pensar-hi.
        opcions = [resposta.lower()] + altres[:3]
        rnd.shuffle(opcions)
        fora.append({
            "kind": "omple" if len(opcions) < 4 else "tria",
            "unit": slug,
            "drill_id": d.id,
            "pregunta": peca["pregunta"],
            "ajuda": peca["ajuda"],
            "que": peca["nom"],
            "shi": _amb_el_buit(text, m),
            "tif": transliteration.to_forms(_amb_el_buit(text, m))["tifinagh"],
            "ca": ca,
            "resposta": resposta,
            "opcions": opcions if len(opcions) >= 4 else [],
            "audio_url": (getattr(d, "audio_url", "") or "").strip() or None,
            "speaker": getattr(d, "speaker", None) or getattr(d, "author", None),
            "region": getattr(d, "region", None),
        })
    return fora


def corregeix(exercici: Dict, dit: str) -> bool:
    """Si la resposta val. Es compara pel so: `gh` i `ɣ` són la mateixa lletra."""
    return igual_de_so(dit, (exercici or {}).get("resposta") or "")
