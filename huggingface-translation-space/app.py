import gradio as gr
import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, pipeline
import os

# Cargar modelo
model_name = "Tamazight-NLP/Finetuned-NLLB"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
device = 0 if torch.cuda.is_available() else -1
translator = pipeline("translation", model=model, tokenizer=tokenizer, device=device)

def translate_text(text: str, src_lang: str, tgt_lang: str):
    """Traduce texto usando el modelo fine-tuned NLLB."""
    try:
        result = translator(text, src_lang=src_lang, tgt_lang=tgt_lang)
        translation = result[0]['translation_text']
        return translation
    except Exception as e:
        return f"Error: {str(e)}"

# Interfaz Gradio
demo = gr.Interface(
    fn=translate_text,
    inputs=[
        gr.Textbox(label="Texto a traducir", placeholder="Introduce el texto aquí..."),
        gr.Dropdown(
            label="Idioma fuente",
            choices=["cat_Latn", "ber_Tfng", "eng_Latn", "fra_Latn", "arb_Arab"],
            value="cat_Latn"
        ),
        gr.Dropdown(
            label="Idioma destino",
            choices=["cat_Latn", "ber_Tfng", "eng_Latn", "fra_Latn", "arb_Arab"],
            value="ber_Tfng"
        )
    ],
    outputs=gr.Textbox(label="Traducción"),
    title="Traductor Tamazight (NLLB Fine‑tuned)",
    description="Traducción entre catalán y tachelhit (Tamazight del Atlas Central) usando el modelo NLLB fine‑tuned."
)

# Para compatibilidad con FastAPI, también exponemos la función
if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
