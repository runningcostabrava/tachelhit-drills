"""El nostre model llegeix abans que el d'un tercer (#554).

L'Space en porta dos lectors i el servidor només feia servir el de fora: `ayymen/
stt_zgh_fastconformer_ctc_small`, que escriu tifinag. El nostre —MMS-1b-all amb l'adaptador shi
afinat— hi era des del primer dia, darrere de `/transcribe_mms`, i no el cridava ningú.

Mesurat l'1-11-2026 sobre catorze gravacions nostres d'Aït Mraw i Beni Mellal, comparant per clau
fonèmica contra el text que havia escrit una persona: **el nostre 0,279, el de fora 0,448**.

L'ordre va per com de bé llegeix cadascun: Gemini primer (0,19 a la prova del 17-10), el nostre
després, i el de fora com a xarxa de seguretat. Això és el que guarden aquestes proves, perquè
l'ordre és tota la decisió.
"""
import main


def test_el_nostre_va_abans_que_el_de_fora(monkeypatch):
    from test_api import client

    main._GEMINI_ASR_BUIDES = 0
    main._GEMINI_ASR_FINS = 0.0

    crides = []

    def sense_gemini(*a, **k):
        crides.append("gemini")
        return None

    def el_nostre(url):
        crides.append("nostre")
        return "ihla ġuri udġar"

    def el_de_fora(*a, **k):
        crides.append("fora")
        raise AssertionError("no s'hi ha d'arribar quan el nostre contesta")

    monkeypatch.setattr(main, "_transcribe_short_clip_with_gemini", sense_gemini)
    monkeypatch.setattr(main, "_space_mms_text", el_nostre)
    monkeypatch.setattr(main, "hf_predict", el_de_fora, raising=False)

    r = client.post("/transcribe/", json={"audio_url": "https://exemple/clip.m4a"})
    assert r.status_code == 200, r.text
    assert r.json()["corrected_transcription"] == "ihla ġuri udġar"
    assert crides == ["gemini", "nostre"], crides


def test_si_el_nostre_no_pot_encara_hi_ha_el_de_fora(monkeypatch):
    from test_api import client

    main._GEMINI_ASR_BUIDES = 0
    main._GEMINI_ASR_FINS = 0.0

    vist = []

    monkeypatch.setattr(main, "_transcribe_short_clip_with_gemini", lambda *a, **k: None)
    # Buit: és el que torna quan l'Space encara carrega el model (503) o quan falla.
    monkeypatch.setattr(main, "_space_mms_text", lambda url: (vist.append("nostre"), "")[1])

    def fora(*a, **k):
        vist.append("fora")
        return "ⴰⵣⵓⵍ ⴼⵍⵍ ⴰⵖ"

    monkeypatch.setattr(main, "hf_predict", fora, raising=False)
    r = client.post("/transcribe/", json={"audio_url": "https://exemple/clip.m4a"})
    assert vist[:2] == ["nostre", "fora"], vist
    assert r.status_code in (200, 502)


def test_una_lectura_de_dues_lletres_no_val(monkeypatch):
    """Dues lletres no són una frase: si el nostre no sent res, que passi el següent."""
    from test_api import client

    main._GEMINI_ASR_BUIDES = 0
    main._GEMINI_ASR_FINS = 0.0

    vist = []
    monkeypatch.setattr(main, "_transcribe_short_clip_with_gemini", lambda *a, **k: None)
    monkeypatch.setattr(main, "_space_mms_text", lambda url: (vist.append("nostre"), "ab")[1])
    monkeypatch.setattr(main, "hf_predict", lambda *a, **k: (vist.append("fora"), "ⴰⵣⵓⵍ")[1], raising=False)
    client.post("/transcribe/", json={"audio_url": "https://exemple/clip.m4a"})
    assert vist == ["nostre", "fora"], vist


def test_si_gemini_no_contesta_mai_es_deixa_de_preguntar(monkeypatch):
    """L'amo: «we don't have gemini». De 1.500 lectures escrites aquella nit, cap no era seva:
    totes en tifinag pur, que és el que escriu el model de fora. Pagar-li l'espera a cada
    gravació no té sentit, i `gemini_available()` no ho pot saber —només mira si hi ha la clau."""
    from test_api import client

    main._GEMINI_ASR_BUIDES = 0
    main._GEMINI_ASR_FINS = 0.0
    provat = []
    monkeypatch.setattr(main, "_transcribe_short_clip_with_gemini",
                        lambda *a, **k: (provat.append(1), None)[1])
    monkeypatch.setattr(main, "_space_mms_text", lambda url: "ihla ġuri udġar")

    for _ in range(main._GEMINI_ASR_PROVES):
        client.post("/transcribe/", json={"audio_url": "https://exemple/clip.m4a"})
    assert len(provat) == main._GEMINI_ASR_PROVES, provat
    assert main._GEMINI_ASR_FINS > 0, "hauria d'haver plegat"

    # I a partir d'aquí ja no se li pregunta.
    r = client.post("/transcribe/", json={"audio_url": "https://exemple/clip.m4a"})
    assert r.status_code == 200
    assert r.json()["corrected_transcription"] == "ihla ġuri udġar"
    assert len(provat) == main._GEMINI_ASR_PROVES, "no li ha de tornar a preguntar"
    main._GEMINI_ASR_FINS = 0.0


def test_una_resposta_torna_a_obrir_la_porta(monkeypatch):
    """La pausa es desfà sola: si Gemini torna, es torna a comptar des de zero."""
    main._GEMINI_ASR_BUIDES = main._GEMINI_ASR_PROVES - 1
    main._GEMINI_ASR_FINS = 0.0
    main._gemini_asr_resultat(True)
    assert main._GEMINI_ASR_BUIDES == 0 and main._GEMINI_ASR_FINS == 0.0
