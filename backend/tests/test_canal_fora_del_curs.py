"""Una etiqueta de regió no converteix un canal en veu nostra."""
from types import SimpleNamespace

import grammar
import main


def _fila(**c):
    base = dict(audio_url="https://x/a.mp3", speaker=None, author=None, source_channel=None, region="Ait Mraw", tag=None)
    return SimpleNamespace(**{**base, **c})


def test_el_canal_no_es_veu_nostra_encara_que_digui_ait_mraw():
    d = _fila(author="Tamazight For All", speaker="Tamazight For All", source_channel="Tamazight For All")
    assert grammar.qui_ho_diu(d)["mena"] == "canal" and not grammar.per_imitar(d)
    assert grammar.origin(d) != grammar.AIT_MRAW


def test_una_altra_veu_daquell_poble_segueix_sent_nostra():
    d = _fila(author="Fatima")
    assert grammar.qui_ho_diu(d)["mena"] == "nostra" and grammar.origin(d) == grammar.AIT_MRAW


def test_not_excluded_treu_el_canal():
    with main.SessionLocal() as db:
        fora = main.DrillModel(text_catalan="prova canal", text_tachelhit="prova", author="Tamazight For All (Naceur)", region="Ait Mraw")
        dins = main.DrillModel(text_catalan="prova nostra", text_tachelhit="prova", author="Halima", region="Ait Mraw")
        db.add_all([fora, dins]); db.commit()
        ids = {r.id for r in grammar.not_excluded(db.query(main.DrillModel), main.DrillModel).all()}
        assert dins.id in ids and fora.id not in ids
        db.delete(fora); db.delete(dins); db.commit()
