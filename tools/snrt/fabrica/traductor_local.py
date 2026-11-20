# -*- coding: utf-8 -*-
"""El nostre NLLB afinat, a casa i en CPU (ADR 0014).

Fins ara el tifinag es traduïa demanant-ho a un Space gratuït d'HuggingFace, i el Space es dorm:
el 20-11-2026 l'episodi de prova va sortir amb `Space no disponible: The read operation timed
out` i **zero** rèpliques amb la comparació entre les dues vies. Un testimoni que no es presenta
mai no és un testimoni.

`josepabloucr/nllb-600m-tamazight-catala-ct2-int8` és el mateix model afinat, quantitzat a
CTranslate2 int8: corre en CPU, no demana GPU, no es dorm i no costa diners — que des que la
quota del Model Studio es va esgotar ha deixat de ser una comoditat.

Es baixa un cop a `<TD_TV>/models/nllb-ca-ct2/` (uns 620 MB) i es carrega una sola vegada.
"""
import os
import threading

NOM = "nllb-600m-tamazight-catala-ct2-int8"
REPO = os.environ.get("TD_MODEL_NLLB_REPO", "josepabloucr/" + NOM)
#: `zgh_Tfng` és el codi amb què el Space el cridava («Standard Moroccan Tamazight»); el model
#: també en coneix d'altres, i per això es pot canviar sense tocar el codi.
ORIGEN = os.environ.get("TD_NLLB_ORIGEN", "zgh_Tfng")
DESTI = os.environ.get("TD_NLLB_DESTI", "cat_Latn")

_pany = threading.Lock()
_tr = None
_tok = None


def cami():
    """On viu el model. `TD_MODEL_NLLB` el pot apuntar a una còpia ja baixada."""
    d = os.environ.get("TD_MODEL_NLLB")
    if d:
        return d
    import comu
    return os.path.join(comu.td_tv(), "models", "nllb-ca-ct2")


def carrega():
    """Baixa el model si cal i el deixa a punt. Es crida un cop, abans dels fils."""
    global _tr, _tok
    with _pany:
        if _tr is not None:
            return
        import ctranslate2
        from transformers import AutoTokenizer
        d = cami()
        if not os.path.exists(os.path.join(d, "model.bin")):
            from huggingface_hub import snapshot_download
            os.makedirs(d, exist_ok=True)
            snapshot_download(REPO, local_dir=d, token=os.environ.get("HF_TOKEN"))
        _tok = AutoTokenizer.from_pretrained(d, src_lang=ORIGEN)
        _tr = ctranslate2.Translator(d, device="cpu", compute_type="int8")


def disponible():
    try:
        carrega()
        return True
    except Exception:
        return False


def tradueix(text, max_fitxes=256):
    """El català d'un text en tifinag (o en llatí amazic). Cadena buida si no es pot."""
    if not (text or "").strip():
        return ""
    carrega()
    trossos = _tok.convert_ids_to_tokens(_tok.encode(text.strip()))
    r = _tr.translate_batch([trossos], target_prefix=[[DESTI]], beam_size=4,
                            max_decoding_length=max_fitxes)
    sortida = r[0].hypotheses[0]
    #: la primera fitxa és el codi de la llengua de destí, que no forma part de la frase
    if sortida and sortida[0] == DESTI:
        sortida = sortida[1:]
    return _tok.decode(_tok.convert_tokens_to_ids(sortida), skip_special_tokens=True).strip()
