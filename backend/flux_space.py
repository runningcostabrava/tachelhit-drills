"""Dibuixar amb un Space públic de FLUX a Hugging Face, quan Gemini no pot.

Per què existeix: el compte de Gemini —el que dibuixa les il·lustracions de les frases— es va
quedar sense crèdit (402 RESOURCE_EXHAUSTED) i l'app va deixar de poder dibuixar res. Un Space
públic de FLUX dibuixa igual de bé amb el token de Hugging Face que el projecte ja té, no costa
res i no estampa cap marca a la imatge.

El que NO fem: fer servir un servei lliure sense clau que posa la seva marca d'aigua a sobre.
A la portada d'una app que parla de qui diu cada frase, una marca d'un altre no hi va.

Límit honest: la quota de ZeroGPU d'un compte gratuït és d'uns pocs minuts de GPU al dia, i
quan s'acaba el Space contesta «You have exceeded your free ZeroGPU quota». Llavors això torna
a dir que no, i qui ho ha demanat ho sap.
"""
from __future__ import annotations

import os
import shutil
import tempfile

#: Spaces públics de FLUX, per ordre. Si el primer no té quota, es prova el segon.
SPACES = ("black-forest-labs/FLUX.1-schnell", "multimodalart/FLUX.1-merged")


def token() -> str | None:
    return os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_API_KEY")


def available() -> bool:
    """Si hi ha token. Que la quota del dia hi sigui, només es veu provant-ho."""
    return bool(token())


def draw(prompt: str, width: int = 1024, height: int = 1024, steps: int = 4) -> bytes:
    """Els bytes de la imatge. Aixeca RuntimeError si cap Space ha pogut dibuixar."""
    from gradio_client import Client

    last = ""
    for space in SPACES:
        try:
            client = Client(space, token=token(), verbose=False)
            got = client.predict(prompt=prompt, seed=0, randomize_seed=True,
                                 width=width, height=height, num_inference_steps=steps,
                                 api_name="/infer")
            path = got[0] if isinstance(got, (list, tuple)) else got
            if isinstance(path, dict):
                path = path.get("path") or path.get("url")
            if not path or not os.path.exists(path):
                raise RuntimeError("el Space no ha tornat cap fitxer")
            tmp = os.path.join(tempfile.mkdtemp(), "flux.webp")
            shutil.copyfile(path, tmp)
            with open(tmp, "rb") as f:
                data = f.read()
            try:
                os.remove(tmp)
            except OSError:
                pass
            if not data:
                raise RuntimeError("el Space ha tornat un fitxer buit")
            print(f"[FLUX] dibuixat amb {space} ({len(data)} bytes)")
            return data
        except Exception as e:
            last = f"{space}: {type(e).__name__}: {str(e)[:160]}"
            print(f"[FLUX] {last}")
    raise RuntimeError(f"cap Space de FLUX ha dibuixat ({last})")
