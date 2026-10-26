"""Escriure la taula del transliterador per al web, treta de la de debò.

Per què el web en té una còpia: la pantalla ha d'ensenyar **sempre els dos alfabets, amb el
tifinag al lloc de més importància** (#339), i això vol dir transliterar cada frase que es pinta.
Fer-ho al servidor costa 247 µs per frase —un segon sencer per a les 4.221 de la llista de
drills, a cada petició— i a més deixaria l'app sense els dos alfabets quan no hi ha connexió,
que en una app de mòbil no és un detall.

Per què es genera i no s'escriu a mà: **dues taules escrites a mà divergeixen.** El que hi ha a
`backend/transliteration.py` és la font; això n'escriu la còpia, i una prova
(`tests/test_transliteration.py`) torna a generar-la i falla si el fitxer del web no hi és igual.
Si algú afegeix una lletra al Python i no torna a generar, la CI es posa vermella.

    python tools/genera_tifinag.py          escriu el fitxer
    python tools/genera_tifinag.py --mira   el torna per la sortida, sense tocar res
"""
import json
import sys
from pathlib import Path

ARREL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ARREL))

import transliteration as T  # noqa: E402

DEST = ARREL.parent / "frontend" / "src" / "utils" / "tifinag.data.ts"


def text() -> str:
    def json_ordenat(d):
        return json.dumps({k: d[k] for k in sorted(d)}, ensure_ascii=False, indent=2)

    return (
        "// GENERAT per backend/tools/genera_tifinag.py — NO s'edita a mà.\n"
        "//\n"
        "// La taula de debò és backend/transliteration.py. Si hi afegeixes una lletra, torna a\n"
        "// generar aquest fitxer: hi ha una prova que ho comprova i la CI es posa vermella si no\n"
        "// coincideixen. Dues taules escrites a mà divergeixen, i quan divergeixen el que llegeix\n"
        "// qui aprèn deixa de ser el que diu qui parla.\n"
        "\n/** Com s'escriu cada so, en tot el que la gent escriu -> el so. */\n"
        f"export const ENTRADA: Record<string, string> = {json_ordenat(T._INPUT)};\n"
        "\n/** El so -> la seva lletra tifinag. */\n"
        f"export const TIFINAG: Record<string, string> = {json_ordenat(T._TIFINAGH)};\n"
        "\n/** El so -> com s'escriu en llatí acadèmic. */\n"
        f"export const LLATI: Record<string, string> = {json_ordenat(T._CLEAN)};\n"
    )


def main():
    t = text()
    if "--mira" in sys.argv:
        # A la consola de Windows s'hi escriu en cru i en UTF-8: amb `print` hi peta, perquè la
        # cp1252 d'aquesta màquina no sap escriure ni una ɛ ni una lletra tifinag.
        sys.stdout.buffer.write(t.encode("utf-8"))
        return
    DEST.write_text(t, encoding="utf-8")
    print(f"escrit {DEST} ({len(t)} caràcters)")


if __name__ == "__main__":
    main()
