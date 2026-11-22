"""El tros de la frase catalana que respon a cada paraula amaziga (#356).

La glossa diu **què vol dir** una paraula, i ho diu amb la forma de diccionari: «confien». La
frase catalana, en canvi, diu «confiança». La pantalla que segueix la veu (#340) encén el català
casant la glossa amb les paraules de la frase, i per això només encenia el **41%** de les
paraules glossades: la resta de la línia es quedava apagada, no perquè no sabéssim què vol dir
sinó perquè ho teníem escrit d'una altra manera.

Són dues feines i per això són dos camps. `ca` **no es toca** —és el que la lliçó ensenya— i s'hi
afegeix `ca_tram`: el tros **exacte** de la frase catalana, copiat lletra per lletra, o res quan
el català no en diu cap tros (una partícula de futur, una interjecció).

Afluixar la comparació no serveix: «confien» comparteix prefix amb «confirmar» i amb «confitura»,
i «interjecció» no s'ha d'encendre enlloc. Una paraula encesa que no toca ensenya una
correspondència falsa, i qui aprèn es creu el que la pantalla li encén. Per això el tros que diu
la màquina es comprova **dins la frase**, i si no hi és, fora —la mateixa regla que les anàlisis
de les oracions (#341).
"""
from __future__ import annotations

import json
import re
from typing import Dict, List, Optional, Tuple

#: Paraules per crida. Una frase pot portar-ne dotze, i la resposta és curta (un tros per paraula),
#: però val més quedar lluny del sostre que descobrir-lo perdent una tanda (#357).
PER_CRIDA = 10

MAX_TOKENS = 2500


def _plana(s: str) -> str:
    """Igual per comparar: sense accents de més ni majúscules ni puntuació als extrems."""
    return (s or "").strip().strip(".,;:!?¿¡«»\"'()[]…-").lower()


def dins(frase: str, tros: str) -> Optional[str]:
    """El tros tal com la frase l'escriu, o res si la frase no el diu.

    Es busca sense tenir en compte majúscules, perquè el model escriu «Matí» allà on la frase diu
    «matí», però el que es desa és **el tall de la frase**, no el que ha escrit el model: així el
    que s'encén a la pantalla és sempre text de la frase.
    """
    f, t = frase or "", (tros or "").strip()
    if not f or not t:
        return None
    i = f.lower().find(t.lower())
    if i < 0:
        t2 = _plana(t)
        if not t2:
            return None
        i = f.lower().find(t2)
        if i < 0:
            return None
        return f[i:i + len(t2)]
    return f[i:i + len(t)]


def glosses_de(cru: Optional[str]) -> List[dict]:
    """El paraula per paraula que ja porta la línia, o una llista buida."""
    try:
        got = json.loads((cru or "").strip() or "[]")
    except Exception:
        return []
    return [g for g in got if isinstance(g, dict)] if isinstance(got, list) else []


def li_falta(cru: Optional[str]) -> bool:
    """Hi ha glossa i encara no hi ha cap tros: val la pena demanar-ho."""
    gl = glosses_de(cru)
    return bool(gl) and not any((g.get("ca_tram") or "").strip() for g in gl)


def prompt(frases: List[dict]) -> str:
    """El que se li demana a la màquina, per a una tanda de frases."""
    trossos = []
    for f in frases:
        mots = ", ".join(f"«{g.get('shi')}»" for g in f["glosses"] if (g.get("shi") or "").strip())
        trossos.append(f"- id {f['id']}\n  amazic: «{f['shi']}»\n  català: «{f['ca']}»\n  paraules: {mots}")
    llista = "\n".join(trossos)
    return (
        "Tens frases en amazic (tamazight de l'Atles central) amb la seva traducció al català, i la "
        "llista de les paraules amazigues de cada frase.\n\n"
        "Per a cada paraula amaziga, digues QUIN TROS DE LA FRASE CATALANA li respon. Regles:\n"
        "- el tros ha de ser COPIAT LLETRA PER LLETRA de la frase catalana que et dono, tal com hi "
        "està escrit. No el posis en infinitiu, no el canviïs de nombre ni de persona, no "
        "l'escriguis d'una altra manera;\n"
        "- pot ser una paraula o unes quantes de seguides («no he fet», «a la vora»);\n"
        "- si el català no diu res per a aquella paraula —una partícula que el català no té, una "
        "interjecció, un pronom que ja va dins el verb— posa-hi \"\" i prou. Deixar-ho en blanc és "
        "la resposta bona, no una fallada;\n"
        "- no facis servir dues vegades el mateix tros per a dues paraules, si no és que la frase "
        "catalana el diu dues vegades.\n\n"
        f"FRASES\n{llista}\n\n"
        'Respon NOMÉS amb un JSON: {"<id>": [["<paraula amaziga>", "<tros català>"], …]}.'
    )


def _per_paraula(val, glosses: List[dict]) -> List[Tuple[dict, str]]:
    """Casar el que torna el model amb les paraules de la glossa.

    Primer per la paraula amaziga tal com està escrita —que és el que se li ha demanat— i si no,
    per l'ordre. La clau que torna un model és una pista, no una clau (#353).
    """
    if not isinstance(val, list):
        return []
    per_mot: Dict[str, dict] = {}
    for g in glosses:
        clau = _plana(str(g.get("shi") or ""))
        if clau and clau not in per_mot:
            per_mot[clau] = g
    fora: List[Tuple[dict, str]] = []
    for n, parell in enumerate(val):
        if isinstance(parell, (list, tuple)) and len(parell) >= 2:
            mot, tros = str(parell[0] or ""), str(parell[1] or "")
        elif isinstance(parell, dict):
            mot, tros = str(parell.get("shi") or ""), str(parell.get("ca_tram") or parell.get("tram") or "")
        else:
            continue
        g = per_mot.get(_plana(mot)) or (glosses[n] if n < len(glosses) else None)
        if g is not None:
            fora.append((g, tros))
    return fora


def neteja(resposta: dict, frases: List[dict]) -> Dict[int, List[dict]]:
    """Les glosses d'aquestes frases amb el tros afegit, quan el tros s'aguanta.

    Es llença el tros que la frase catalana no diu: parla d'una altra frase. `ca` no es toca mai.
    """
    per_id = {str(f["id"]): f for f in frases}
    fora: Dict[int, List[dict]] = {}
    for n, (clau, val) in enumerate((resposta or {}).items()):
        m = re.search(r"\d+", str(clau))
        f = per_id.get(m.group(0)) if m else None
        if f is None:
            f = frases[n] if n < len(frases) else None
        if f is None:
            continue
        posats = 0
        noves = [dict(g) for g in f["glosses"]]
        quin = {id(g): nova for g, nova in zip(f["glosses"], noves)}
        for g, tros in _per_paraula(val, f["glosses"]):
            nova = quin.get(id(g))
            if nova is None:
                continue
            tal_com = dins(f["ca"], tros)
            if tal_com:
                nova["ca_tram"] = tal_com
                posats += 1
        if posats:
            fora[int(f["id"])] = noves
    return fora


def frases_de(db, drill_ids: List[int], refer: bool = False) -> List[dict]:
    """Les línies on això serveix: tenen paraula per paraula i tenen traducció catalana."""
    from models import Drill as DrillModel
    if not drill_ids:
        return []
    fora = []
    for d in db.query(DrillModel).filter(DrillModel.id.in_(drill_ids)).all():
        ca = (d.text_catalan or "").strip()
        gl = glosses_de(d.glosses)
        if not ca or not gl:
            continue
        if not refer and not li_falta(d.glosses):
            continue
        fora.append({"id": d.id, "shi": (d.text_tachelhit or "").strip(), "ca": ca, "glosses": gl})
    return fora


def desa(db, quines: Dict[int, List[dict]]) -> int:
    """Desar les glosses amb el tros, sense tocar res més de la línia."""
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
    """Demanar-ho, de deu en deu."""
    from gemini_client import gemini_generate
    fora: Dict[int, List[dict]] = {}
    for i in range(0, len(frases), PER_CRIDA):
        tanda = frases[i:i + PER_CRIDA]
        cru = gemini_generate(
            "Ets un traductor que assenyala, dins una frase catalana, el tros que respon a cada paraula amaziga.",
            [{"role": "user", "text": prompt(tanda)}],
            max_output_tokens=MAX_TOKENS, temperature=0.1, timeout=240)
        import analisi
        fora.update(neteja(analisi.resposta_json(cru), tanda))
    return fora


def compte(glosses: List[dict]) -> Tuple[int, int]:
    """Quantes paraules glossades hi ha i quantes tenen tros: la mesura del #356."""
    amb = sum(1 for g in glosses if (g.get("ca_tram") or "").strip())
    return len(glosses), amb
