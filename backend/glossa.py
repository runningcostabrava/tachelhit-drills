"""El paraula per paraula d'una frase amaziga (#361).

Fins ara aquest pas vivia en un guió del bloc de notes d'una sessió. Les seves regles —i són
regles guanyades a pols— no eren a cap fitxer del repositori, no hi havia cap prova que les
comprovés, i tornar-lo a passar demanava la meva màquina. Les altres passes de la casa (les
anàlisis, l'escoltar, l'alineament, el tros de la frase) ja no són així.

Les regles, amb el seu perquè:

1. **Es glossa el que està escrit.** Els parlants escriuen com volen —`gh` per ɣ, `kh` per x, `3`
   per ɛ, majúscules per a les emfàtiques— i la paraula tal com la frase l'escriu és la **clau**
   que fa servir tot el que ve després: el so d'una paraula (#271), el tros de la frase catalana
   (#356), la cerca. Si aquí s'escriu d'una altra manera, allò no la troba. Per això la paraula
   que es desa surt de **la frase**, no del model.
2. **El significat és el de la paraula, no el del lloc que ocupa.** La primera passada casava
   posicions i en sortien coses com «am = va»: la paraula amaziga i la catalana no ocupen el
   mateix lloc, i de vegades no n'hi ha ni el mateix nombre.
3. **Una partícula porta una etiqueta curta** («ad» = partícula de futur, «ur» = no) i un verb amb
   el pronom enganxat es glossa sencer («nnayas» = li va dir). Partir-ho seria ensenyar una
   gramàtica que la llengua no fa.
4. **Mai la paraula amaziga com el seu propi significat**, i mai un significat buit: si no se'n
   sap prou, hi va «?». Dir «no ho sabem» és una resposta; fer veure que sí, no.
5. **El tifinag el posa el transliterador de la casa**, no el model. És el mateix codi que pinta
   les frases a la pantalla, i així les dues cares d'una paraula no se separen mai.
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional

import transliteration

#: Paraules per frase. Per sobre d'això la frase no és una frase: és un paràgraf sencer mal tallat,
#: i glossar-lo paraula per paraula no ajuda ningú.
MAX_PARAULES = 14

#: Frases per crida, i tokens de sortida. Una glossa és curta, però val més quedar lluny del
#: sostre que descobrir-lo perdent una tanda sencera (#357).
PER_CRIDA = 15
MAX_TOKENS = 3000

#: Quan s'ha demanat i no n'ha sortit res de cert. No és el mateix que no haver-ho demanat.
NO_HO_SABEM = "?"

_PARAULA = re.compile(r"[^\W\d_]+", re.UNICODE)


def paraules_de(text: Optional[str]) -> List[str]:
    """Les paraules de la frase, tal com la frase les escriu i en el seu ordre."""
    return [w for w in re.split(r"\s+", (text or "").strip()) if _PARAULA.search(w)]


def _plana(s: str) -> str:
    """Igual per comparar: sense majúscules ni la puntuació dels extrems."""
    return (s or "").strip().strip(".,;:!?¿¡«»\"'()[]…-").lower()


def prompt(frases: List[dict]) -> str:
    """El que se li demana a la màquina, per a una tanda de frases."""
    llista = "\n".join(
        f"- id {f['id']}: «{f['shi']}» | la frase vol dir: «{f['ca']}»" for f in frases)
    return (
        "Gloss each sentence of Central Atlas Tamazight below WORD BY WORD for someone learning it "
        "through Catalan. For each word, as it is written and in its order, say what THAT WORD "
        "means by itself — never the piece of the Catalan translation that happens to fall in the "
        "same position.\n"
        "- a grammatical word gets a short Catalan label: «ad» = partícula de futur, «ur» = no, "
        "«is» = partícula de pregunta, «n» = de, «da/ar» = marca d'acció habitual, «ay/ayd» = "
        "el que;\n"
        "- a word with a pronoun glued to it is glossed whole: «ghori» = tinc / a mi, «nnayas» = "
        "li va dir, «-i» = em;\n"
        "- NEVER repeat the Tamazight word as its own meaning, and never leave a meaning empty;\n"
        "- use the sentence's meaning only to choose between senses; when you truly cannot tell, "
        f'give «{NO_HO_SABEM}».\n'
        "The speakers spell freely (gh = ɣ, kh = x, 3 = ɛ, capital letters for emphatics): gloss "
        "what is written, and copy each word exactly as the sentence writes it.\n\n"
        f"SENTENCES\n{llista}\n\n"
        'Answer ONLY with a JSON object {"<id>": [["<word as written>", "<meaning in Catalan>"], …]}.'
    )


def _casa(val, mots: List[str]) -> List[tuple]:
    """Casar el que torna el model amb les paraules DE LA FRASE.

    Es busca la paraula del model entre les que encara no s'han fet servir, endavant primer. Si no
    hi és i el model n'ha tornat tantes com n'hi ha, es pren la del lloc; si no, es llença el
    parell: glossar una paraula que la frase no diu seria posar un significat a una paraula que el
    parlant no ha dit mai.
    """
    if not isinstance(val, list):
        return []
    fetes = set()
    fora = []
    mateix_nombre = len(val) == len(mots)
    for k, parell in enumerate(val):
        if isinstance(parell, (list, tuple)) and len(parell) >= 2:
            mot, ca = str(parell[0] or ""), str(parell[1] or "")
        elif isinstance(parell, dict):
            mot, ca = str(parell.get("shi") or ""), str(parell.get("ca") or "")
        else:
            continue
        clau = _plana(mot)
        quin = None
        for j, m in enumerate(mots):
            if j not in fetes and _plana(m) == clau and clau:
                quin = j
                break
        if quin is None and mateix_nombre and k not in fetes:
            quin = k
        if quin is None:
            continue
        fetes.add(quin)
        fora.append((mots[quin], ca, quin))
    fora.sort(key=lambda x: x[2])
    return [(m, ca) for m, ca, _ in fora]


def neteja(resposta: dict, frases: List[dict]) -> Dict[int, List[dict]]:
    """El paraula per paraula que s'aguanta, amb el tifinag posat per la casa."""
    per_id = {str(f["id"]): f for f in frases}
    fora: Dict[int, List[dict]] = {}
    for n, (clau, val) in enumerate((resposta or {}).items()):
        m = re.search(r"\d+", str(clau))
        f = per_id.get(m.group(0)) if m else None
        if f is None:
            f = frases[n] if n < len(frases) else None
        if f is None:
            continue
        mots = paraules_de(f["shi"])
        glosses = []
        for mot, ca in _casa(val, mots):
            ca = (ca or "").strip()
            if not ca or _plana(ca) == _plana(mot):
                ca = NO_HO_SABEM          # ha dit la paraula mateixa, o no ha dit res
            try:
                tif = transliteration.to_forms(mot).get("tifinagh") or None
            except Exception:
                tif = None
            glosses.append({"shi": mot, "tif": tif, "ca": ca})
        if glosses:
            fora[int(f["id"])] = glosses
    return fora


def frases_de(db, drill_ids: List[int], refer: bool = False) -> List[dict]:
    """Les línies que es poden glossar: escrites, amb significat, i d'una llargada de frase."""
    from models import Drill as DrillModel
    if not drill_ids:
        return []
    import tram
    fora = []
    for d in db.query(DrillModel).filter(DrillModel.id.in_(drill_ids)).all():
        shi, ca = (d.text_tachelhit or "").strip(), (d.text_catalan or "").strip()
        if not shi or not ca:
            continue
        if not refer and tram.glosses_de(d.glosses):
            continue
        mots = paraules_de(shi)
        if not mots or len(mots) > MAX_PARAULES:
            continue
        fora.append({"id": d.id, "shi": shi, "ca": ca})
    return fora


def desa(db, quines: Dict[int, List[dict]]) -> int:
    """Desar el paraula per paraula, sense tocar res més de la línia."""
    import json
    from models import Drill as DrillModel
    fets = 0
    for drill_id, glosses in quines.items():
        d = db.get(DrillModel, drill_id)
        if d is None:
            continue
        d.glosses = json.dumps(glosses, ensure_ascii=False)
        fets += 1
    db.commit()
    return fets


def escriu(frases: List[dict]) -> Dict[int, List[dict]]:
    """Demanar-ho, de quinze en quinze."""
    import analisi
    from gemini_client import gemini_generate
    fora: Dict[int, List[dict]] = {}
    for i in range(0, len(frases), PER_CRIDA):
        tanda = frases[i:i + PER_CRIDA]
        cru = gemini_generate(
            "Ets un mestre d'amazic que glossa una frase paraula per paraula per a qui comença.",
            [{"role": "user", "text": prompt(tanda)}],
            max_output_tokens=MAX_TOKENS, temperature=0.1, timeout=240)
        fora.update(neteja(analisi.resposta_json(cru), tanda))
    return fora
