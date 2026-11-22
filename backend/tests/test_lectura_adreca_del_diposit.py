"""Una gravació del nostre dipòsit s'ha de poder llegir, i un client llençat s'ha de tancar.

El 20-11-2026 el servidor de producció es moria de memòria cada ~70 minuts (512 MB) tota la nit.
La cadena, mesurada:

* Les adreces que aquest servidor dóna són `/mitjans/...` (la clau de R2), i `/transcribe/` les
  passava tal com són. El nostre lector fa `requests.get(adreça)` i es queixava que no tenen
  esquema; el de fora, igual. **Cada frase amb una adreça d'aquestes fallava sempre.**
* L'app hi torna mentre quedi cap gravació sense lectura: de vuit en vuit, cada deu minuts, per
  sempre. A la biblioteca d'en Pablo n'hi havia **201, totes amb adreça relativa**.
* I cada fallada construeix clients de Gradio que es llencen sense tancar. Mesurat: sis clients
  construïts i deixats anar són sis fils vius i +5 MB que no tornen; amb `close()`, la memòria
  queda plana.

Res d'això era visible des de fora: només es veia el web dient «només per a administradors»,
que és el que passa quan la crida per preguntar-ho cau amb el servidor.
"""
import main


def test_una_adreca_del_diposit_arriba_sencera_al_lector(monkeypatch):
    """`/mitjans/...` és una clau de R2: al lector hi ha d'arribar l'adreça sencera."""
    from test_api import client

    main._GEMINI_ASR_BUIDES = 0
    main._GEMINI_ASR_FINS = 0.0
    vistes = []

    def el_nostre(url):
        vistes.append(url)
        return "ihla ġuri udġar"

    monkeypatch.setattr(main, "_transcribe_short_clip_with_gemini", lambda *a, **k: None)
    monkeypatch.setattr(main, "_space_mms_text", el_nostre)

    r = client.post("/transcribe/", json={"audio_url": "/mitjans/tachelhit/tutlait/tl_test_1.flac"})

    assert r.status_code == 200, r.text
    assert vistes, "el lector no ha arribat a rebre cap adreça"
    assert vistes[0].startswith("http"), f"adreça sense esquema: {vistes[0]}"
    assert vistes[0].endswith("/mitjans/tachelhit/tutlait/tl_test_1.flac"), vistes[0]


def test_una_adreca_sencera_no_es_toca(monkeypatch):
    """La correcció no ha de reescriure el que ja era bo."""
    from test_api import client

    main._GEMINI_ASR_BUIDES = 0
    main._GEMINI_ASR_FINS = 0.0
    vistes = []

    monkeypatch.setattr(main, "_transcribe_short_clip_with_gemini", lambda *a, **k: None)
    monkeypatch.setattr(main, "_space_mms_text", lambda url: vistes.append(url) or "ihla ġuri")

    r = client.post("/transcribe/", json={"audio_url": "https://exemple.org/clip.m4a"})

    assert r.status_code == 200, r.text
    assert vistes == ["https://exemple.org/clip.m4a"], vistes


def test_un_client_que_falla_es_tanca(monkeypatch):
    """Un client de Gradio llençat sense tancar es queda amb el fil viu i no s'allibera mai."""
    tancats = []

    class ClientDeMentida:
        def __init__(self, *a, **k):
            pass

        def submit(self, *a, **k):
            raise RuntimeError("l'Space no contesta")

        def close(self):
            tancats.append(True)

    monkeypatch.setattr(main, "Client", ClientDeMentida)
    monkeypatch.setattr(main.time, "sleep", lambda *_: None, raising=False)
    main._hf_clients.clear()

    try:
        main.hf_predict("algu/un-space", "clip.wav", retries=2)
    except RuntimeError:
        pass

    assert len(tancats) == 2, f"s'han tancat {len(tancats)} clients dels 2 que s'han llençat"
    assert not main._hf_clients, "el client mort no pot quedar-se a la memòria cau"
