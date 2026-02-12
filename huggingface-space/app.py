import os
import tempfile
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import json
import sys

# Añadir el directorio actual al path para importar shorts_generator
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Importar funciones de generación
from shorts_generator import generate_youtube_short, generate_drillplayer_demo

app = FastAPI(title="Tachelhit Video Generator")

class GenerateRequest(BaseModel):
    drill_id: Optional[int] = None
    test_id: Optional[int] = None
    drill_data: Optional[dict] = None
    drills_data: Optional[List[dict]] = None
    filename: str
    type: str  # 'short' or 'demo'

@app.post("/generate")
async def generate_video(request: GenerateRequest):
    try:
        if request.type == 'short':
            if not request.drill_data:
                raise HTTPException(status_code=400, detail="Missing drill_data for short")
            output_path = generate_youtube_short(request.drill_data, request.filename)
        elif request.type == 'demo':
            if not request.drills_data:
                raise HTTPException(status_code=400, detail="Missing drills_data for demo")
            output_path = generate_drillplayer_demo(request.test_id, request.drills_data, request.filename)
        else:
            raise HTTPException(status_code=400, detail="Invalid type")

        # Devolver la ruta del video
        return {
            "video_path": f"/media/shorts/{request.filename}",
            "output_path": output_path,
            "status": "success"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "tachelhit-video-generator"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)
