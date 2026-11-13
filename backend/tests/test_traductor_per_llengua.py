"""Cada llengua amb el seu traductor.

L'Space de traducció és un NLLB **afinat per a amazic↔català**. Fora d'aquell parell no s'hi
pot confiar, i no és una opinió: les mateixes línies d'àrab del Baba Ali, el 13-11-2026,

    سترافقني إلى بيت القائد
      l'Space    → «Ens acompañaràs a la casa del capità.»   (amb ñ i tot)
      el DeepSeek → «M'acompanyaràs a casa del caid»

i el segon casa paraula per paraula amb el que ja hi ha desat als 3.621 drills de la sèrie,
que és com es va saber qui els havia traduït.

Això no prova cap traductor: prova **qui es crida**. Si un dia algú torna a enviar l'àrab a
l'Space, aquestes proves cauen.
"""
import main


def _apunta(on):
    """Un guàrdia que APUNTA que l'han cridat, i no que llança.

    Llançant no val: `tradueix` captura qualsevol excepció del DeepSeek per caure a l'Space, de
    manera que es menjaria l'avís de la prova i la prova passaria igual. Comprovat el
    13-11-2026: amb el guàrdia que llançava, enviar-ho TOT al DeepSeek no feia caure res.
    """
    def crida(*a, **k):
        on.append(a)
        return "[cridat]"
    return crida


def test_l_amazic_va_a_l_space(monkeypatch):
    """L'Space hi és per a això i ha de seguir fent-ho tot."""
    cridat = []
    monkeypatch.setattr(main, "translate_with_hf", lambda t, s, g: f"[space] {t}")
    monkeypatch.setattr(main, "_tradueix_amb_deepseek", _apunta(cridat))
    assert main.tradueix("bonjorn", "Catalan",
                         "Tachelhit/Central Atlas Tamazight") == "[space] bonjorn"
    assert main.tradueix("azul", "Standard Moroccan Tamazight", "Catalan") == "[space] azul"
    assert cridat == [], "el DeepSeek no s'havia de cridar per a l'amazic"


def test_l_arab_va_al_deepseek(monkeypatch):
    cridat = []
    monkeypatch.setattr(main, "translate_with_hf", _apunta(cridat))
    monkeypatch.setattr(main, "_tradueix_amb_deepseek", lambda t, s, g: f"[deepseek] {t}")
    assert main.tradueix("مرحبا", "Modern Standard Arabic",
                         "Catalan") == "[deepseek] مرحبا"
    #: i en el sentit contrari també
    assert main.tradueix("hola", "Catalan",
                         "Modern Standard Arabic") == "[deepseek] hola"
    assert cridat == [], "l'Space no s'havia de cridar per a l'àrab"


def test_l_angles_i_el_frances_tambe(monkeypatch):
    cridat = []
    monkeypatch.setattr(main, "translate_with_hf", _apunta(cridat))
    monkeypatch.setattr(main, "_tradueix_amb_deepseek", lambda t, s, g: "[deepseek]")
    for llengua in ("English", "French", "Spanish"):
        assert main.tradueix("x", llengua, "Catalan") == "[deepseek]", llengua
    assert cridat == [], "l'Space no s'havia de cridar"


def test_si_el_deepseek_calla_es_cau_a_l_space(monkeypatch):
    """Val més una traducció fluixa que cap. Sense això, una frase en àrab es quedaria sense
    traduir el dia que el DeepSeek no hi sigui."""
    monkeypatch.setattr(main, "translate_with_hf", lambda t, s, g: "[space]")
    monkeypatch.setattr(main, "_tradueix_amb_deepseek", lambda t, s, g: "")
    assert main.tradueix("مرحبا", "Modern Standard Arabic", "Catalan") == "[space]"


def test_si_el_deepseek_peta_es_cau_a_l_space(monkeypatch):
    def peta(*a, **k):
        raise RuntimeError("sense quota")
    monkeypatch.setattr(main, "translate_with_hf", lambda t, s, g: "[space]")
    monkeypatch.setattr(main, "_tradueix_amb_deepseek", peta)
    assert main.tradueix("مرحبا", "Modern Standard Arabic", "Catalan") == "[space]"


def test_l_endpoint_fa_servir_la_tria(monkeypatch):
    """La tria ha de valer per a qui crida /translate, que és per on passa l'app."""
    from test_api import client
    monkeypatch.setattr(main, "tradueix", lambda t, s, g: f"triat:{s}->{g}")
    r = client.post("/translate", json={"text": "مرحبا", "source_lang": "ar",
                                        "target_lang": "ca"})
    assert r.status_code == 200, r.text
    assert r.json()["translated_text"] == "triat:Modern Standard Arabic->Catalan"


def test_sense_deepseek_configurat_no_es_queda_penjat(monkeypatch):
    """Sense clau, `_tradueix_amb_deepseek` torna buit i no llança: el servidor de qualsevol
    que no en tingui ha de seguir traduint."""
    import deepseek_client
    monkeypatch.setattr(deepseek_client, "deepseek_available", lambda: False)
    assert main._tradueix_amb_deepseek("مرحبا", "Modern Standard Arabic", "Catalan") == ""
