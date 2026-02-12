import gradio as gr
import os
import sys
import json
import tempfile
from typing import Optional, List
import traceback

# Añadir el directorio actual al path para importar shorts_generator
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from shorts_generator import generate_youtube_short, generate_drillplayer_demo

# Directorio para guardar videos generados
SHORTS_DIR = "media/shorts"
os.makedirs(SHORTS_DIR, exist_ok=True)

# Función para manejar solicitudes POST de API
def api_generate(type: str, drill_data: Optional[dict] = None, drills_data: Optional[List[dict]] = None, 
                 filename: str = "output.mp4", test_id: Optional[int] = None):
    """
    Endpoint de API para generación de videos.
    Compatible con las llamadas del backend.
    """
    try:
        if type == 'short':
            if not drill_data:
                return {"error": "Missing drill_data for short"}
            output_path = generate_youtube_short(drill_data, filename)
        elif type == 'demo':
            if not drills_data:
                return {"error": "Missing drills_data for demo"}
            output_path = generate_drillplayer_demo(test_id or 0, drills_data, filename)
        else:
            return {"error": "Invalid type"}

        return {
            "video_path": f"/media/shorts/{filename}",
            "output_path": output_path,
            "status": "success"
        }
    except Exception as e:
        traceback.print_exc()
        return {"error": str(e)}

# Funciones para la interfaz de Gradio
def generate_short(drill_data_json: str, filename: str):
    """Genera un YouTube Short a partir de JSON de datos del drill."""
    try:
        drill_data = json.loads(drill_data_json)
        if not filename.endswith('.mp4'):
            filename += '.mp4'
        output_path = generate_youtube_short(drill_data, filename)
        return output_path
    except Exception as e:
        raise gr.Error(f"Error generando short: {str(e)}")

def generate_demo(test_id_str: str, drills_data_json: str, filename: str):
    """Genera un video demo del Drill Player."""
    try:
        test_id = int(test_id_str) if test_id_str else 0
        drills_data = json.loads(drills_data_json)
        if not filename.endswith('.mp4'):
            filename += '.mp4'
        output_path = generate_drillplayer_demo(test_id, drills_data, filename)
        return output_path
    except Exception as e:
        raise gr.Error(f"Error generando demo: {str(e)}")

# Interfaz de Gradio
with gr.Blocks(title="Tachelhit Video Generator") as demo:
    gr.Markdown("# 🎬 Generador de Videos Tachelhit")
    gr.Markdown("Genera YouTube Shorts o videos demo del Drill Player.")
    
    # API endpoint para POST /generate
    # Usamos un componente oculto para exponer la función como API
    gr.Interface(
        fn=api_generate,
        inputs=[
            gr.Dropdown(["short", "demo"], label="type", value="short"),
            gr.Textbox(label="drill_data (JSON)", placeholder='{"text_catalan": "..."}'),
            gr.Textbox(label="drills_data (JSON array)", placeholder='[{"text_catalan": "..."}]'),
            gr.Textbox(label="filename", value="output.mp4"),
            gr.Number(label="test_id (optional)", value=0)
        ],
        outputs=gr.JSON(label="API Response"),
        api_name="generate",
        title="API Endpoint",
        description="Endpoint para llamadas del backend. Usa POST /api/generate/",
        allow_flagging="never"
    ).queue()
    
    with gr.Tab("YouTube Short"):
        gr.Markdown("### Generar un YouTube Short")
        drill_json = gr.Textbox(
            label="Datos del Drill (JSON)",
            placeholder='{"text_catalan": "Hola", "text_tachelhit": "Azul", "text_arabic": "مرحبا", "image_url": "...", "audio_url": "..."}',
            lines=5
        )
        short_name = gr.Textbox(label="Nombre del archivo (sin extensión)", value="short_1")
        short_btn = gr.Button("Generar Short")
        short_output = gr.File(label="Video generado", interactive=False)
        
        short_btn.click(
            fn=generate_short,
            inputs=[drill_json, short_name],
            outputs=short_output
        )
        
        # Ejemplo de JSON
        example_json = {
            "text_catalan": "Hola",
            "text_tachelhit": "Azul",
            "text_arabic": "مرحبا",
            "image_url": "",
            "audio_url": ""
        }
        gr.Examples(
            examples=[[json.dumps(example_json, indent=2), "ejemplo_short"]],
            inputs=[drill_json, short_name],
            outputs=short_output,
            fn=generate_short,
            cache_examples=False
        )
    
    with gr.Tab("Drill Player Demo"):
        gr.Markdown("### Generar video demo del Drill Player")
        test_id_input = gr.Textbox(label="ID del Test (opcional)", value="1")
        drills_json = gr.Textbox(
            label="Datos de Drills (JSON array)",
            placeholder='[{"text_catalan": "Hola", "text_tachelhit": "Azul", "text_arabic": "مرحبا", "image_url": "...", "audio_tts_url": "..."}]',
            lines=6
        )
        demo_name = gr.Textbox(label="Nombre del archivo (sin extensión)", value="demo_1")
        demo_btn = gr.Button("Generar Demo")
        demo_output = gr.File(label="Video demo generado", interactive=False)
        
        demo_btn.click(
            fn=generate_demo,
            inputs=[test_id_input, drills_json, demo_name],
            outputs=demo_output
        )
        
        # Ejemplo de JSON array
        example_drills = [
            {
                "text_catalan": "Hola",
                "text_tachelhit": "Azul",
                "text_arabic": "مرحبا",
                "image_url": "",
                "audio_tts_url": ""
            },
            {
                "text_catalan": "Com estàs?",
                "text_tachelhit": "Manik ayt?",
                "text_arabic": "كيف حالك؟",
                "image_url": "",
                "audio_tts_url": ""
            }
        ]
        gr.Examples(
            examples=[[ "1", json.dumps(example_drills, indent=2), "ejemplo_demo"]],
            inputs=[test_id_input, drills_json, demo_name],
            outputs=demo_output,
            fn=generate_demo,
            cache_examples=False
        )
    
    gr.Markdown("---")
    gr.Markdown("### 📁 Archivos generados")
    gr.Markdown(f"Los videos se guardan en `{SHORTS_DIR}` dentro del espacio.")
    
    # Estado del sistema
    gr.Markdown("### 🔍 Estado del sistema")
    status = gr.Textbox(label="Estado", value="✅ Listo", interactive=False)

# Configurar la aplicación para Hugging Face Spaces
if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
