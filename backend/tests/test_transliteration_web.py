"""La taula del web ha de ser la mateixa que la de casa (#339).

El web en té una còpia perquè la pantalla transliterà cada frase que pinta, i fer-ho al servidor
costa 247 µs per frase —un segon sencer per a les 4.221 de la llista de drills— i deixaria l'app
sense els dos alfabets quan no hi ha connexió.

El perill d'una còpia és que divergeixi. Aquesta prova torna a generar-la i la compara amb el
fitxer que hi ha: si algú afegeix una lletra al Python i no torna a generar, la CI es posa
vermella **abans** que ningú llegeixi una paraula amb una lletra de menys. Ja ha passat: la ġ i
la γ gregues que faltaven al mapa feien que «aɣrum» (pa) es veiés ⴰⵔⵓⵎ, que és una altra paraula.
"""
import subprocess
import sys
from pathlib import Path

ARREL = Path(__file__).resolve().parent.parent


def test_the_web_s_table_is_the_same_one():
    generador = ARREL / "tools" / "genera_tifinag.py"
    fitxer = ARREL.parent / "frontend" / "src" / "utils" / "tifinag.data.ts"
    assert fitxer.exists(), "falta frontend/src/utils/tifinag.data.ts: torna-la a generar"

    fet = subprocess.run([sys.executable, str(generador), "--mira"],
                         capture_output=True, text=True, encoding="utf-8", cwd=str(ARREL))
    assert fet.returncode == 0, fet.stderr

    ara = fitxer.read_text(encoding="utf-8").replace("\r\n", "\n")
    toca = fet.stdout.replace("\r\n", "\n")
    assert ara.strip() == toca.strip(), (
        "la taula del web no és la del backend. Torna-la a generar:\n"
        "    python tools/genera_tifinag.py"
    )
