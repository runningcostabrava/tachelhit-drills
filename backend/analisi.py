"""Desmuntar una oració: què hi passa, i quina unitat del curs l'explica (#341).

El propietari, sobre les històries: *«crec que per aquestes històries hauríem de tenir un anàlisi
gramàtic semblant al que fem en gramàtica, per cada oració.»*

La diferència amb la nota del curs (`grammar.write_notes`) no és d'estil sinó d'ancoratge. Allà
la nota respon «què mostra aquesta frase **d'aquesta unitat**», i per tant penja d'una parella
(frase, unitat). Una línia d'un conte no pertany a cap unitat: la pregunta s'ha de girar del
revés —«què passa en aquesta frase, i **quines unitats** l'expliquen»— i la resposta penja de la
frase sola.

Tres regles que no es toquen:

1. **Només sobre frases escrites.** Una línia que ningú no ha transcrit no es pot analitzar: la
   màquina escriuria una anàlisi convincent d'una frase que s'ha inventat ella, que és el
   mecanisme que ja ens ha mentit (#335: dinou de trenta transcripcions no volien dir res).
2. **El text del parlant no es toca.** L'anàlisi és un afegit, mai una correcció.
3. **Es diu que l'ha escrita una màquina.** Com les notes del curs, i pel mateix motiu.

I una comprovació que no és decorativa: el tros que l'anàlisi cita ha de ser **dins la frase**,
lletra per lletra. Una anàlisi que cita una paraula que no hi és està parlant d'una altra frase.
"""
from __future__ import annotations

import json
import re
from typing import Dict, List, Optional

import grammar

#: Les unitats que l'anàlisi pot citar. Si en diu una que no hi és, se'n va.
UNITATS = {u["slug"]: u["title"] for u in grammar.UNITS}

#: Un tros citat entre cometes dins l'anàlisi.
_CITAT = re.compile(r"«([^»]{1,30})»")


def _nomes_lletres(s: Optional[str]) -> str:
    return re.sub(r"[^\wⴰ-⵿]+", "", (s or "").lower())


def prompt(frases: List[dict]) -> str:
    """El que se li demana a la màquina, per a una tanda de frases."""
    llista = "\n".join(f"- id {f['id']}: «{f['shi']}» — {f['ca']}" for f in frases)
    unitats = "\n".join(f"  {s}: {t}" for s, t in UNITATS.items())
    return (
        "Ensenyes amazic (tamazight de l'Atles central) a catalanoparlants que comencen. Et dono "
        "frases d'un conte, amb el que volen dir.\n\n"
        "Per a cada frase, desmunta-la: quina mena de frase és, quin verb hi ha i en quina forma, "
        "i què hi fan els pronoms i les partícules. De 30 a 55 paraules, en català planer, com ho "
        "diria un mestre al costat de la frase.\n"
        "- anomena els trossos TAL COM ESTAN ESCRITS a la frase, entre cometes «»;\n"
        "- el tros que citis ha de ser DINS la frase, lletra per lletra. Si no hi és, no el citis;\n"
        "- res de mots de gramàtic ni de fonetista: ni «clític», ni «morfema», ni «inacomplert», "
        "ni «desinència», ni «fonema». Digues-ho a la manera planera;\n"
        "- si no en saps prou per dir-ne res de cert, posa l'anàlisi a \"\" i prou. Val més "
        "deixar-ho en blanc que inventar-s'ho.\n\n"
        "I digues quines UNITATS del curs expliquen aquesta frase (de zero a tres), amb el seu "
        f"identificador exacte d'aquesta llista:\n{unitats}\n\n"
        f"FRASES\n{llista}\n\n"
        'Respon NOMÉS amb un JSON: {"<id>": {"analisi": "<text>", "unitats": ["<slug>", …]}}.'
    )


def _quina_frase(clau, val, frases: List[dict], per_id: Dict[str, dict], n: int):
    """A quina frase respon aquesta entrada de la resposta.

    **La clau que torna el model no és de fiar.** Se li demana `{"<id>": …}` i torna `{"id 1": …}`,
    copiant el format de la llista que se li ha passat («- id 1: «…»»). Buscar `"1"` no trobava
    res i es llençava tot: 268 anàlisis de 281, i semblava que el model no en sabés.

    Per ordre: el número que hi hagi dins la clau; si no, el text de la frase, que el model sol
    repetir; i si no, l'ordre, que els models sí que respecten.
    """
    m = re.search(r"\d+", str(clau))
    if m and m.group(0) in per_id:
        return per_id[m.group(0)]
    per_text = {f["shi"]: f for f in frases}
    if isinstance(clau, str) and clau.strip() in per_text:
        return per_text[clau.strip()]
    if isinstance(val, dict):
        seva = (val.get("frase") or val.get("shi") or "").strip()
        if seva in per_text:
            return per_text[seva]
    return frases[n] if n < len(frases) else None


def neteja(resposta: dict, frases: List[dict]) -> Dict[int, dict]:
    """Quedar-se només amb el que s'aguanta.

    Es llença: l'anàlisi que cita un tros que no és a la frase (parla d'una altra frase), la que
    fa servir mots de gramàtic (ningú no l'entén), i les unitats inventades.
    """
    per_id = {str(f["id"]): f for f in frases}
    fora: Dict[int, dict] = {}
    for n, (clau, val) in enumerate((resposta or {}).items()):
        if not isinstance(val, dict):
            continue
        f = _quina_frase(clau, val, frases, per_id, n)
        if not f:
            continue
        text = (val.get("analisi") or "").strip()
        if not text:
            continue
        if any(j in text.lower() for j in grammar.NOTE_JARGON):
            continue
        dins = _nomes_lletres(f["shi"])
        citats = [c for c in _CITAT.findall(text) if _nomes_lletres(c)]
        if any(_nomes_lletres(c) not in dins for c in citats):
            continue
        unitats = [u for u in (val.get("unitats") or []) if u in UNITATS][:3]
        fora[int(f["id"])] = {"analisi": text, "unitats": unitats}
    return fora


def desa(db, quines: Dict[int, dict]) -> int:
    """Guardar-les, substituint el que hi hagués per a aquella frase."""
    from models import SentenceAnalysis
    fets = 0
    for drill_id, val in quines.items():
        fila = db.get(SentenceAnalysis, drill_id)
        if fila is None:
            fila = SentenceAnalysis(drill_id=drill_id)
            db.add(fila)
        fila.body = val["analisi"]
        fila.units = ",".join(val["unitats"])
        fets += 1
    db.commit()
    return fets


def per_a(db, drill_ids: List[int]) -> Dict[str, dict]:
    """Les anàlisis que ja tenim d'aquestes frases, per servir-les amb la història."""
    if not drill_ids:
        return {}
    from models import SentenceAnalysis
    files = db.query(SentenceAnalysis).filter(SentenceAnalysis.drill_id.in_(drill_ids)).all()
    return {str(f.drill_id): {"analisi": f.body,
                              "unitats": [u for u in (f.units or "").split(",") if u],
                              "titols": [UNITATS.get(u, u) for u in (f.units or "").split(",") if u]}
            for f in files}


def escriu(frases: List[dict]) -> Dict[int, dict]:
    """Una crida: desmuntar aquesta tanda de frases."""
    from gemini_client import gemini_generate
    cru = gemini_generate(
        "Ets un mestre d'amazic que desmunta una frase perquè qui aprèn vegi com està feta.",
        [{"role": "user", "text": prompt(frases)}],
        max_output_tokens=3000, temperature=0.2, timeout=240)
    return neteja(resposta_json(cru), frases)


def frases_de(db, drill_ids: List[int], refer: bool = False) -> List[dict]:
    """Les línies que es poden analitzar: les que algú ha escrit de debò.

    Les altres no hi són a posta. Una línia sense text amazic no es pot desmuntar —no hi ha res
    a desmuntar— i demanar-ho igualment faria que la màquina se la inventés primer i l'analitzés
    després, que és la pitjor de les dues coses que podríem fer.
    """
    from models import Drill as DrillModel, SentenceAnalysis
    if not drill_ids:
        return []
    fetes = set() if refer else {
        r[0] for r in db.query(SentenceAnalysis.drill_id)
        .filter(SentenceAnalysis.drill_id.in_(drill_ids)).all()}
    fora = []
    for d in db.query(DrillModel).filter(DrillModel.id.in_(drill_ids)).all():
        shi = (d.text_tachelhit or "").strip()
        if not shi or d.id in fetes:
            continue
        fora.append({"id": d.id, "shi": shi, "ca": (d.text_catalan or "").strip()})
    return fora


def resposta_json(cru: str) -> dict:
    """El JSON que torna el model, encara que l'emboliqui amb tanques de codi."""
    net = (cru or "").strip()
    if net.startswith("```"):
        net = re.sub(r"^```[a-z]*\n?|\n?```$", "", net)
    try:
        d = json.loads(net)
    except Exception:
        m = re.search(r"\{.*\}", net, re.S)
        if not m:
            return {}
        try:
            d = json.loads(m.group(0))
        except Exception:
            return {}
    return d if isinstance(d, dict) else {}
