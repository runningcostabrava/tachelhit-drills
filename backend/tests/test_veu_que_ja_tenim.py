"""La línia muda del Mètode que la biblioteca ja sap dir (#495).

En Pablo va veure «tifawin» marcada «sense veu encara» amb mitja dotzena de frases gravades
que la diuen, i va dir que li semblava molt fort. Comptat: de 1.756 línies dels capítols,
1.262 eren mudes i 268 d'aquelles la biblioteca les sabia dir.

El que es prova aquí és el que ha de passar i, sobretot, **el que no ha de passar**: que una
veu prestada no es faci passar per la veu de la línia.
"""
import pytest

import method


class _Drill:
    """Prou d'un drill per a aquesta funció. Sense base de dades ni models."""

    def __init__(self, id, shi, ca="un significat", audio="https://x/a.mp3",
                 speaker=None, author=None, region=None, tag=""):
        self.id, self.text_tachelhit, self.text_catalan = id, shi, ca
        self.audio_url, self.speaker, self.author = audio, speaker, author
        self.region, self.tag = region, tag


class _Db:
    def __init__(self, drills):
        self._d = drills

    def query(self, *_cols):
        #: el servidor demana nomes les columnes que fa servir; aqui tant li fa
        return self

    def filter(self, *_a, **_k):
        return self

    def all(self):
        return self._d


def _cos(linies):
    return {"vocabulary": list(linies)}


def _posa(linies, drills):
    return method.attach_la_veu_que_ja_tenim(_Db(drills), _cos(linies))


def test_una_paraula_muda_troba_la_frase_que_la_diu():
    """El cas d'en Pablo: la paraula és al capítol sense veu i algú l'ha dita en una frase."""
    cos = _posa([{"shi": "tifawin", "ca": "bon dia"}],
                [_Drill(7, "tifawin a tawjja", speaker="Halima", region="Aït Mraw")])

    heard = cos["vocabulary"][0]["heard"]
    assert heard["drill_id"] == 7
    assert heard["speaker"] == "Halima" and heard["region"] == "Aït Mraw"


def test_la_veu_prestada_no_es_fa_passar_per_la_de_la_linia():
    """És la distinció del #288: una veu d'un canal no pot passar per una de nostra."""
    cos = _posa([{"shi": "atay", "ca": "te"}], [_Drill(7, "ar ssuɣ atay")])

    linia = cos["vocabulary"][0]
    assert "heard" in linia
    assert not linia.get("audio_url"), "la línia segueix sense veu pròpia"


def test_una_linia_que_ja_sona_no_es_toca():
    cos = _posa([{"shi": "atay", "ca": "te", "audio_url": "https://x/seva.mp3"}],
                [_Drill(7, "ar ssuɣ atay")])

    assert "heard" not in cos["vocabulary"][0]


def test_una_linia_amb_la_veu_del_cd_tampoc():
    """Ja se sent. Afegir-hi una frase prestada hi posaria dues veus i no resoldria res."""
    cos = _posa([{"shi": "atay", "ca": "te", "cd": {"url": "https://x/cd.mp3"}}],
                [_Drill(7, "ar ssuɣ atay")])

    assert "heard" not in cos["vocabulary"][0]


def test_la_frase_exacta_guanya_la_que_nomes_la_conte():
    cos = _posa([{"shi": "atay", "ca": "te"}],
                [_Drill(7, "ar ssuɣ atay"), _Drill(9, "atay")])

    assert cos["vocabulary"][0]["heard"]["drill_id"] == 9


def test_entre_dues_que_la_contenen_mana_la_del_cd_del_manual():
    """El capítol surt d'aquell llibre: la veu de l'autor és la que hi encaixa."""
    cos = _posa([{"shi": "atay", "ca": "te"}],
                [_Drill(7, "ar ssuɣ atay d sskkʷar"),
                 _Drill(9, "ar ssuɣ atay", tag="metode-cd, del llibre")])

    assert cos["vocabulary"][0]["heard"]["drill_id"] == 9


def test_no_totes_les_linies_amb_la_mateixa_gravacio():
    """Trenta línies amb la mateixa frase no és sentir-les: és sentir-ne una."""
    cos = _posa([{"shi": "atay", "ca": "te"}, {"shi": "atay", "ca": "te (una altra)"}],
                [_Drill(7, "ar ssuɣ atay"), _Drill(9, "nkki ar ssuɣ atay")])

    quines = {l["heard"]["drill_id"] for l in cos["vocabulary"]}
    assert len(quines) == 2


def test_una_frase_sense_traduccio_no_serveix():
    """Una frase que no es pot entendre no ensenya el significat de res."""
    cos = _posa([{"shi": "atay", "ca": "te"}], [_Drill(7, "ar ssuɣ atay", ca="")])

    assert "heard" not in cos["vocabulary"][0]


def test_una_frase_amb_restes_de_transcripcio_no_serveix():
    cos = _posa([{"shi": "atay", "ca": "te"}], [_Drill(7, "[? ar ssuɣ atay]")])

    assert "heard" not in cos["vocabulary"][0]


def test_auto_capture_no_es_ningu():
    """Dir «ho diu Auto Capture» fa passar el nom d'un procés per una persona."""
    cos = _posa([{"shi": "atay", "ca": "te"}],
                [_Drill(7, "ar ssuɣ atay", author="Auto Capture")])

    heard = cos["vocabulary"][0]["heard"]
    assert heard["speaker"] is None and heard["captured"] is True


@pytest.mark.parametrize("escrit", ["aɣrum", "aghrum", "ⴰⵖⵔⵓⵎ"])
def test_casa_pel_so_i_no_per_les_lletres(escrit):
    """`aɣrum`, `aghrum` i el tifinag són la mateixa paraula; la biblioteca les té de totes tres."""
    cos = _posa([{"shi": escrit, "ca": "pa"}], [_Drill(7, "ar ttɣ aghrum")])

    assert cos["vocabulary"][0]["heard"]["drill_id"] == 7


def test_sense_cap_veu_la_linia_es_queda_com_era():
    """No s'inventa res: 1.024 línies no tenen veu enlloc i han de seguir dient-ho."""
    cos = _posa([{"shi": "amuddu", "ca": "viatge"}], [_Drill(7, "ar ssuɣ atay")])

    assert "heard" not in cos["vocabulary"][0]
