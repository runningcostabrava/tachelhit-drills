"""L'amazic → català passa per l'anglès.

Mesurat el 16-11-2026 sobre les 60 frases de sempre (docs/recerca/models-de-text.md): el mateix
NLLB afinat de l'Space dona chrF 0,424 quan se li demana català directe amb la fitxa «Tachelhit»
(taq_Tfng), 0,447 amb la fitxa «Standard Moroccan Tamazight» (tzm_Tfng), i **0,521** si se li
demana anglès amb tzm_Tfng i un model de text passa l'anglès al català. Això no prova cap
traductor: prova QUIN CAMÍ es fa i que, si el pont cau, es torna al català directe.
"""
import main
import pytest


@pytest.fixture(autouse=True)
def _sense_gemini(monkeypatch):
    """El Gemini va primer (test_el_gemini_va_primer); aqui es tanca per provar el pont sol."""
    monkeypatch.setattr(main, "_esborrany_amb_gemini", lambda t: "")


def _space_que_apunta(on):
    def crida(t, s, g):
        on.append((s, g))
        return f"[space {s}->{g}] {t}"
    return crida


def test_el_pont_per_l_angles(monkeypatch):
    cridat = []
    monkeypatch.setattr(main, "translate_with_hf", _space_que_apunta(cridat))
    monkeypatch.setattr(main, "_angles_a_catala", lambda en: f"[ca de] {en}")
    assert main.tradueix("azul", "Tachelhit/Central Atlas Tamazight", "Catalan") == \
        "[ca de] [space Standard Moroccan Tamazight->English] azul"
    #: la font que rep l'Space és la fitxa tzm, no la taq, i es demana anglès
    assert cridat == [("Standard Moroccan Tamazight", "English")]


def test_des_del_llati_es_queda_la_fitxa_llatina(monkeypatch):
    cridat = []
    monkeypatch.setattr(main, "translate_with_hf", _space_que_apunta(cridat))
    monkeypatch.setattr(main, "_angles_a_catala", lambda en: "ca")
    main.tradueix("azul", "Tachelhit/Central Atlas Tamazight (Latin)", "Catalan")
    assert cridat == [("Tachelhit/Central Atlas Tamazight (Latin)", "English")]


def test_si_cap_model_passa_l_angles_es_cau_al_catala_directe(monkeypatch):
    cridat = []
    monkeypatch.setattr(main, "translate_with_hf", _space_que_apunta(cridat))
    monkeypatch.setattr(main, "_angles_a_catala", lambda en: "")
    assert main.tradueix("azul", "Standard Moroccan Tamazight", "Catalan") == \
        "[space Standard Moroccan Tamazight->Catalan] azul"
    assert cridat == [("Standard Moroccan Tamazight", "English"), ("Standard Moroccan Tamazight", "Catalan")]


def test_si_l_space_no_dona_angles_es_cau_al_catala_directe(monkeypatch):
    """L'Space torna el text tal qual quan tot li falla: això no és anglès i no s'ha d'enviar al
    model de text."""
    def space(t, s, g):
        return t if g == "English" else "[ca directe]"
    cridat = []
    monkeypatch.setattr(main, "translate_with_hf", space)
    monkeypatch.setattr(main, "_angles_a_catala", lambda en: cridat.append(en) or "mai")
    assert main.tradueix("azul", "Standard Moroccan Tamazight", "Catalan") == "[ca directe]"
    assert cridat == []


def test_el_sentit_catala_a_amazic_no_canvia(monkeypatch):
    cridat = []
    monkeypatch.setattr(main, "translate_with_hf", _space_que_apunta(cridat))
    monkeypatch.setattr(main, "_angles_a_catala", lambda en: "mai")
    main.tradueix("hola", "Catalan", "Tachelhit/Central Atlas Tamazight")
    assert cridat == [("Catalan", "Tachelhit/Central Atlas Tamazight")]


def test_sense_cap_model_de_text_no_es_queda_penjat(monkeypatch):
    import deepseek_client, qwen_client
    monkeypatch.setattr(deepseek_client, "deepseek_available", lambda: False)
    monkeypatch.setattr(qwen_client, "qwen_available", lambda: False)
    assert main._angles_a_catala("God gave abundance this year.") == ""


def test_el_gemini_va_primer(monkeypatch):
    """Mesurat el 16-11-2026: el Gemini traduint directe (0,57-0,60) guanya el pont (0,52)."""
    cridat = []
    monkeypatch.setattr(main, "_esborrany_amb_gemini", lambda t: f"[gemini] {t}")
    monkeypatch.setattr(main, "translate_with_hf", _space_que_apunta(cridat))
    assert main.tradueix("azul", "Tachelhit/Central Atlas Tamazight", "Catalan") == "[gemini] azul"
    assert cridat == [], "amb el Gemini contestant, l'Space no s'havia de cridar"


def test_sense_gemini_es_cau_al_pont(monkeypatch):
    cridat = []
    monkeypatch.setattr(main, "_esborrany_amb_gemini", lambda t: "")
    monkeypatch.setattr(main, "translate_with_hf", _space_que_apunta(cridat))
    monkeypatch.setattr(main, "_angles_a_catala", lambda en: "[ca]")
    assert main.tradueix("azul", "Tachelhit/Central Atlas Tamazight", "Catalan") == "[ca]"
    assert cridat == [("Standard Moroccan Tamazight", "English")]


def test_sense_clau_de_gemini_no_es_queda_penjat(monkeypatch):
    import gemini_client
    monkeypatch.setattr(gemini_client, "gemini_available", lambda: False)
    assert main._esborrany_amb_gemini("azul") == ""
