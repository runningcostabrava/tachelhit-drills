"""Llegir el tifinag cremat agrupant les formes (#439).

Les quatre coses que es comproven aquí són les quatre que van fallar de debò mentre es llegia
el conte del lleó i el ratolí, i cadascuna fallava en silenci: no petava res, simplement en
sortia un text una mica diferent del que hi ha escrit al vídeo. Per això tenen prova.
"""
import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest

ARREL = Path(__file__).resolve().parent.parent


def _carrega():
    fitxer = ARREL.parent / "tools" / "text_de_video" / "signes.py"
    assert fitxer.exists(), "falta tools/text_de_video/signes.py"
    spec = importlib.util.spec_from_file_location("signes_de_video", fitxer)
    modul = importlib.util.module_from_spec(spec)
    sys.modules["signes_de_video"] = modul
    spec.loader.exec_module(modul)
    return modul


signes = _carrega()


def test_els_dos_puntets_de_la_u_son_una_lletra_sola():
    """`ⵓ` són dos punts l'un damunt de l'altre.

    Si no s'ajunten, cadascun és un tros massa petit, el filtre de mida se'ls menja tots dos i
    la paraula perd una vocal sense dir-ho: `uɣrda` (ratolí) sortia `ɣrda`."""
    alt = 20
    #            x0, y0, x1, y1, pixels
    dalt = [10, 0, 15, 5, 20]
    baix = [10, 12, 15, 17, 20]
    fet = signes.ajunta_punts([dalt, baix], alt)
    assert len(fet) == 1, "els dos puntets havien de quedar en una sola caixa"
    assert fet[0][:4] == [10, 0, 15, 17]
    assert fet[0][4] == 40


def test_dues_lletres_de_costat_no_s_ajunten():
    """La regla d'ajuntar és «l'un damunt de l'altre», no «a prop»: dues lletres seguides han de
    seguir sent dues."""
    alt = 20
    esquerra = [0, 0, 18, 18, 120]
    dreta = [22, 0, 40, 18, 120]
    fet = signes.ajunta_punts([esquerra, dreta], alt)
    assert len(fet) == 2


def test_una_taca_del_dibuix_no_decideix_l_alcada_de_lletra():
    """Sense filtrar, una taca gran entra a la mediana, l'alçada surt el doble i després **tota**
    lletra de debò queda per sota del mínim. A la frase 27 del conte, que es veu perfectament,
    en sortien zero signes."""
    lletres = [[0, 0, 10, 14, 60] for _ in range(6)]
    taca = [0, 0, 300, 200, 40000]
    assert signes.alt_de_lletra(lletres + [taca]) == 14


def test_un_signe_que_ningu_no_ha_identificat_deixa_la_frase_per_llegir():
    """El que no se sap, no s'escriu. Una frase amb un sol signe sense identificar no es dona
    per llegida, encara que la resta es vegi claríssima."""
    linies = [
        {"frase": 1, "inici": 0, "fi": 4, "linies": [[1, 2, -1, 3]]},
        {"frase": 2, "inici": 4, "fi": 8, "linies": [[1, 2, -1, 99]]},
    ]
    fet = signes.text_de_linies(linies, {"_llegeix-me": ["no és una lletra"],
                                         "a": [1], "n": [2], "s": [3]})
    assert fet[0]["text"] == "an s"
    assert fet[0]["dubtes"] == 0 and fet[0]["llegida"] is True
    assert fet[1]["text"] == "an ·"
    assert fet[1]["dubtes"] == 1 and fet[1]["llegida"] is False


def test_els_trossos_enganxats_es_troben_un_per_un():
    mask = np.zeros((10, 20), dtype=bool)
    mask[2:6, 2:6] = True
    mask[2:6, 12:16] = True
    caixes = sorted(signes.trossos(mask), key=lambda c: c[0])
    assert len(caixes) == 2
    assert caixes[0][:4] == [2, 2, 5, 5]
    assert caixes[1][:4] == [12, 2, 15, 5]
    assert caixes[0][4] == caixes[1][4] == 16


def test_una_forma_que_torna_es_reconeix_i_una_de_nova_estrena_numero():
    """Les formes es desen perquè els números no canviïn d'una passada a l'altra. Si canviessin,
    la taula de lletres que ha escrit una persona passaria a dir una altra cosa sense avisar."""
    formes = signes.Formes()
    quadrat = np.zeros((signes.MIDA, signes.MIDA))
    quadrat[6:18, 6:18] = 1.0
    ratlla = np.zeros((signes.MIDA, signes.MIDA))
    ratlla[:, 10:13] = 1.0
    a = formes.quina(quadrat / np.linalg.norm(quadrat))
    b = formes.quina(quadrat / np.linalg.norm(quadrat))
    c = formes.quina(ratlla / np.linalg.norm(ratlla))
    assert a == b, "la mateixa forma ha de caure al mateix grup"
    assert c != a, "una forma diferent ha d'estrenar grup"


def test_les_formes_desades_es_tornen_a_llegir(tmp_path):
    formes = signes.Formes()
    quadrat = np.zeros((signes.MIDA, signes.MIDA))
    quadrat[6:18, 6:18] = 1.0
    primer = formes.quina(quadrat / np.linalg.norm(quadrat))
    fitxer = tmp_path / "formes.json"
    formes.desa(fitxer)

    import json
    tornades = signes.Formes(json.loads(fitxer.read_text(encoding="utf-8")))
    assert tornades.quina(quadrat / np.linalg.norm(quadrat)) == primer
