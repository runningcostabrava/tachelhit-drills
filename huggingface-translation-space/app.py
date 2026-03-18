import gradio as gr
import torch
from transformers import NllbTokenizerFast, AutoModelForSeq2SeqLM
import os
import time

# Configuración del token y modelo
hf_token = os.environ.get("HF_TOKEN")
model_name = "Tamazight-NLP/NLLB-200-600M-Tamazight-All-Data-3-epoch"

print(f"[{time.ctime()}] Cargando modelo y tokenizer: {model_name}")
tokenizer = NllbTokenizerFast.from_pretrained(model_name, token=hf_token)
model = AutoModelForSeq2SeqLM.from_pretrained(model_name, token=hf_token)

device = "cuda" if torch.cuda.is_available() else "cpu"
model.to(device)
print(f"[{time.ctime()}] Modelo cargado en {device}")

def tifinagh_to_latin(text):
    """Conversor básico de Tifinagh a Latín."""
    mapping = {
        'ⴰ': 'a', 'ⴱ': 'b', 'ⴳ': 'g', 'ⴷ': 'd', 'ⴹ': 'ḍ', 'ⴻ': 'e', 'ⴼ': 'f', 'ⴽ': 'k',
        'ⵀ': 'h', 'ⵃ': 'ḥ', 'ⵅ': 'x', 'ⵇ': 'q', 'ⵉ': 'i', 'ⵊ': 'j', 'ⵍ': 'l', 'ⵎ': 'm',
        'ⵏ': 'n', 'ⵓ': 'u', 'ⵔ': 'r', 'ⵕ': 'ṛ', 'ⵖ': 'ɣ', 'ⵙ': 's', 'ⵚ': 'ṣ', 'ⵛ': 'š',
        'ⵜ': 't', 'ⵟ': 'ṭ', 'ⵡ': 'w', 'ⵢ': 'y', 'ⵣ': 'z', 'ⵥ': 'ẓ', 'ⵯ': 'w', 'ⵒ': 'p',
        'ⵠ': 'v', 'ⵞ': 'č', 'ⵒ': 'p'
    }
    latin_text = "".join(mapping.get(c, c) for c in text)
    return latin_text

def translate_text(text: str, src_lang: str, tgt_lang: str):
    """Traduce texto y añade transcripción si el destino es Tamazight."""
    start_time = time.time()
    print(f"\n[{time.ctime()}] --- NUEVA SOLICITUD DE TRADUCCIÓN ---")
    print(f"Texto: '{text}'")
    print(f"Fuente: {src_lang} -> Destino: {tgt_lang}")
    
    try:
        if not text.strip():
            return ""

        # Configurar idiomas
        tokenizer.src_lang = src_lang
        print(f"Tokenizer src_lang establecido en: {tokenizer.src_lang}")
        
        # Tokenizar
        inputs = tokenizer(text, return_tensors="pt").to(device)
        print(f"Inputs tokenizados. Shape: {inputs.input_ids.shape}")
        
        # Obtener ID del idioma destino de forma robusta
        tgt_lang_id = tokenizer.convert_tokens_to_ids(tgt_lang)
        print(f"ID del idioma destino ({tgt_lang}): {tgt_lang_id}")

        # Generar traducción
        # Para NLLB, a veces es necesario forzar el bos_token_id al principio
        print("Generando tokens...")
        generated_tokens = model.generate(
            **inputs,
            forced_bos_token_id=tgt_lang_id,
            max_length=128,
            num_beams=5,
            early_stopping=True
        )
        print(f"Tokens generados. Cantidad: {generated_tokens.shape[1]}")
        
        # Decodificar texto principal
        translation = tokenizer.batch_decode(generated_tokens, skip_special_tokens=True)[0]
        print(f"Traducción decodificada: '{translation}'")
        
        # Verificación de "copy-paste"
        if translation.strip().lower() == text.strip().lower() and len(text.strip()) > 3:
            print("AVISO: La traducción parece ser una copia exacta del original.")
        
        elapsed = time.time() - start_time
        print(f"Tiempo total: {elapsed:.2f}s")

        # Si el idioma destino es Tamazight (Tifinagh), añadir transcripción
        if tgt_lang == "ber_Tfng":
            latin_version = tifinagh_to_latin(translation)
            return f"Tifinagh: {translation}\nLatín: {latin_version}"
        
        return translation
        
    except Exception as e:
        print(f"ERROR DURANTE LA TRADUCCIÓN: {str(e)}")
        import traceback
        traceback.print_exc()
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
    outputs=gr.Textbox(label="Resultado (Traducción + Transcripción)"),
    title="Traductor Tamazight con Transcripción (Debug Mode)",
    description="Traducción profesional con transcripción automática a caracteres latinos para Tamazight. Incluye logs detallados en la consola."
)

if __name__ == "__main__":
    # Importante para Spaces: launch() sin parámetros o con los necesarios para HF
    demo.launch()
