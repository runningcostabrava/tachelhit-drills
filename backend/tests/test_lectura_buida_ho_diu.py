"""Una lectura buida no és una lectura: es diu (#556).

L'amo (2-11-2026): «review the process to record new drills; when it records, if the
transcription haven't happened, give me a message».

Repassat el camí sencer, el problema no era que la lectura fallés —fallarà sempre alguna vegada:
Gemini té pausa, l'Space dorm, el senyal no hi és— sinó que **quan fallava no ho deia ningú**. I
el pitjor cas sortia d'aquí: quan el lector de fora tornava una cadena buida, l'endpoint
contestava **200 amb la lectura buida**. Una fallada disfressada d'encert. El davant feia
`if (!text) return;` i es quedava mut, i qui acabava de gravar no sabia si tenia lectura, si
arribaria, o si no vindria mai.

Ara és un 502 que diu què ha passat. El davant ja el sap llegir (`services/lectura.ts`) i el
distingeix d'un «ara no hi ha senyal», que és l'altra cosa que cal poder dir.
"""
import main


def _sense_pausa():
    main._GEMINI_ASR_BUIDES = 0
    main._GEMINI_ASR_FINS = 0.0


def test_cap_lector_no_enten_res_i_es_diu(monkeypatch):
    """Els tres callen: 502 amb motiu, no 200 amb el camp buit."""
    from test_api import client
    _sense_pausa()

    monkeypatch.setattr(main, "_transcribe_short_clip_with_gemini", lambda *a, **k: None)
    monkeypatch.setattr(main, "_space_mms_text", lambda url: "")
    monkeypatch.setattr(main, "hf_predict", lambda *a, **k: "", raising=False)

    r = client.post("/transcribe/", json={"audio_url": "https://exemple/vent.m4a"})
    assert r.status_code == 502, r.text
    assert "entès" in r.json()["detail"], r.json()


def test_dues_lletres_del_de_fora_tampoc_no_son_una_lectura(monkeypatch):
    """El mateix llindar que Gemini: menys de tres lletres no és ningú parlant."""
    from test_api import client
    _sense_pausa()

    monkeypatch.setattr(main, "_transcribe_short_clip_with_gemini", lambda *a, **k: None)
    monkeypatch.setattr(main, "_space_mms_text", lambda url: "")
    monkeypatch.setattr(main, "hf_predict", lambda *a, **k: " .. ", raising=False)

    r = client.post("/transcribe/", json={"audio_url": "https://exemple/silenci.m4a"})
    assert r.status_code == 502, r.text


def test_una_lectura_de_debo_segueix_passant(monkeypatch):
    """La xarxa de seguretat segueix servint: això no ha de tancar el camí del de fora."""
    from test_api import client
    _sense_pausa()

    monkeypatch.setattr(main, "_transcribe_short_clip_with_gemini", lambda *a, **k: None)
    monkeypatch.setattr(main, "_space_mms_text", lambda url: "")
    monkeypatch.setattr(main, "hf_predict", lambda *a, **k: "ⴰⵣⵓⵍ ⴼⵍⵍ ⴰⵖ", raising=False)

    r = client.post("/transcribe/", json={"audio_url": "https://exemple/clip.m4a"})
    assert r.status_code == 200, r.text
    assert r.json()["corrected_transcription"].strip()
