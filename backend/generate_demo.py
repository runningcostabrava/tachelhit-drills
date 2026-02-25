"""
Endpoint para generar videos demo usando el espacio de Hugging Face.
"""
import os
import json
import requests
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional
import time

router = APIRouter()

# URL del espacio de Hugging Face
HF_SPACE_URL = os.getenv("HUGGINGFACE_SPACE_URL", "josepabloucr/huggingface-space")

class DrillData(BaseModel):
    id: int
    text_catalan: Optional[str] = ""
    text_tachelhit: Optional[str] = ""
    text_arabic: Optional[str] = ""
    image_url: Optional[str] = ""
    audio_url: Optional[str] = ""
    audio_tts_url: Optional[str] = None

class GenerateDemoRequest(BaseModel):
    test_id: int
    drills: List[DrillData]
    output_filename: str

def call_huggingface_space_async(drills_data_str: str, test_id: int, output_filename: str):
    """
    Llama al espacio de Hugging Face en segundo plano.
    """
    try:
        # Esperar un momento para asegurar que la respuesta HTTP ya se envió
        time.sleep(2)
        
        # Preparar la URL del endpoint de la API del espacio
        # El espacio debe tener una API expuesta. Por ahora, usamos la interfaz web
        # En el futuro, podemos usar la API de Hugging Face Spaces
        print(f"[BACKGROUND] Enviando datos al espacio de Hugging Face para test {test_id}")
        print(f"[BACKGROUND] Datos: {drills_data_str[:100]}...")
        
        # Aquí podríamos hacer una solicitud HTTP real al espacio si tiene una API
        # Por ahora, solo registramos
        print(f"[BACKGROUND] Visita manualmente: {HF_SPACE_URL}")
        print(f"[BACKGROUND] Y usa los datos proporcionados para generar el video")
        
    except Exception as e:
        print(f"[BACKGROUND] Error al llamar al espacio de Hugging Face: {e}")

@router.post("/generate-drillplayer-demo")
async def generate_drillplayer_demo(
    request: GenerateDemoRequest,
    background_tasks: BackgroundTasks
):
    """
    Genera un video demo del Drill Player.
    """
    try:
        # Preparar los datos para enviar al espacio de Hugging Face
        drills_data = []
        for drill in request.drills:
            # Para el espacio de Hugging Face, necesitamos URLs completas
            # Asegurarse de que las URLs sean absolutas
            image_url = drill.image_url
            audio_url = drill.audio_url
            audio_tts_url = drill.audio_tts_url
            
            # Si las URLs son relativas, convertirlas a absolutas usando la URL base del backend
            # Esto depende de tu configuración
            # Por ahora, las dejamos como están
            
            drills_data.append({
                "id": drill.id,
                "text_catalan": drill.text_catalan or "",
                "text_tachelhit": drill.text_tachelhit or "",
                "text_arabic": drill.text_arabic or "",
                "image_url": image_url or "",
                "audio_url": audio_url or "",
                "audio_tts_url": audio_tts_url
            })
        
        # Convertir a JSON string como espera hf_space_app.py
        drills_data_str = json.dumps(drills_data)
        
        # Agregar tarea en segundo plano para llamar al espacio de Hugging Face
        background_tasks.add_task(
            call_huggingface_space_async,
            drills_data_str,
            request.test_id,
            request.output_filename
        )
        
        # Devolver información para que el usuario pueda visitar el espacio
        return {
            "message": "Generación de video demo iniciada en segundo plano",
            "test_id": request.test_id,
            "drills_count": len(request.drills),
            "output_filename": request.output_filename,
            "status_url": f"{HF_SPACE_URL}",
            "instructions": f"Visita {HF_SPACE_URL} y pega los datos JSON en la pestaña 'Generate Demo'",
            "drills_data_sample": drills_data_str[:200] + "..." if len(drills_data_str) > 200 else drills_data_str,
            "note": "El video se generará en el espacio de Hugging Face. Puedes descargarlo desde allí."
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al generar video demo: {str(e)}")
