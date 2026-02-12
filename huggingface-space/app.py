import gradio as gr
import os
import sys
import json
import traceback
from typing import Optional, List

# Add current directory to path so we can import shorts_generator
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from shorts_generator import generate_youtube_short, generate_drillplayer_demo

# Directory to save generated videos
SHORTS_DIR = "media/shorts"
os.makedirs(SHORTS_DIR, exist_ok=True)

# --- CORE LOGIC ---
def api_generate(type: str, drill_data: Optional[any] = None, drills_data: Optional[any] = None, 
                 filename: str = "output.mp4", test_id: Optional[int] = None):
    """
    Core generation logic. 
    Handles both Dicts (if passed directly) and JSON Strings (from Backend/UI).
    """
    try:
        # 1. PARSING LOGIC
        # If input is a string (from UI or json.dumps in backend), convert to Dict/List
        if isinstance(drill_data, str) and drill_data.strip():
            try:
                drill_data = json.loads(drill_data)
            except Exception as e:
                print(f"Error parsing drill_data: {e}")
            
        if isinstance(drills_data, str) and drills_data.strip():
            try:
                drills_data = json.loads(drills_data)
            except Exception as e:
                print(f"Error parsing drills_data: {e}")

        # 2. ROUTING LOGIC
        if type == 'short':
            if not drill_data:
                return {"error": "Missing drill_data for short"}
            output_path = generate_youtube_short(drill_data, filename)
            
        elif type == 'demo':
            if not drills_data:
                return {"error": "Missing drills_data for demo"}
            output_path = generate_drillplayer_demo(test_id or 0, drills_data, filename)
            
        else:
            return {"error": "Invalid type. Must be 'short' or 'demo'"}

        # 3. SUCCESS RESPONSE
        return {
            "video_path": f"/media/shorts/{filename}",
            "output_path": output_path,
            "status": "success"
        }
    except Exception as e:
        traceback.print_exc()
        return {"error": f"Generator Error: {str(e)}"}

# --- HELPER FUNCTIONS FOR UI TABS ---
def generate_short_ui(drill_data_json: str, filename: str):
    """Wrapper for the YouTube Short UI Tab"""
    return api_generate(type="short", drill_data=drill_data_json, filename=filename)

def generate_demo_ui(test_id_str: str, drills_data_json: str, filename: str):
    """Wrapper for the Drill Player Demo UI Tab"""
    test_id = int(test_id_str) if test_id_str and test_id_str.isdigit() else 0
    return api_generate(type="demo", drills_data=drills_data_json, filename=filename, test_id=test_id)

# --- GRADIO INTERFACE ---
with gr.Blocks(title="Tachelhit Video Generator") as demo:
    gr.Markdown("# 🎬 Generador de Videos Tachelhit")
    
    # 1. API Interface (Hidden or Visible - serves the Backend)
    # This matches the "data" array order in main.py: [type, drill_data, drills_data, filename, test_id]
    api_interface = gr.Interface(
        fn=api_generate,
        inputs=[
            gr.Dropdown(["short", "demo"], label="type"),
            gr.Textbox(label="drill_data (JSON)"),       
            gr.Textbox(label="drills_data (JSON array)"), 
            gr.Textbox(label="filename"),
            gr.Number(label="test_id (optional)")
        ],
        outputs=gr.JSON(label="API Response"),
        api_name="predict" # IMPORTANT: Matches 'call_huggingface_space("predict", ...)' in main.py
    )
    
    gr.Markdown("---")
    gr.Markdown("### Manual Generation Tools")

    # 2. UI Tabs for Manual Testing
    with gr.Tab("YouTube Short"):
        with gr.Row():
            short_json = gr.Textbox(label="Drill Data (JSON)", placeholder='{"text_catalan": "Hola"}', lines=5)
            short_file = gr.Textbox(label="Filename", value="short_test.mp4")
        short_btn = gr.Button("Generate Short")
        short_out = gr.JSON(label="Result")
        short_btn.click(generate_short_ui, inputs=[short_json, short_file], outputs=short_out)

    with gr.Tab("Drill Player Demo"):
        with gr.Row():
            demo_id = gr.Textbox(label="Test ID", value="1")
            demo_json = gr.Textbox(label="Drills Data (Array)", placeholder='[{"text_catalan": "Hola"}]', lines=5)
            demo_file = gr.Textbox(label="Filename", value="demo_test.mp4")
        demo_btn = gr.Button("Generate Demo")
        demo_out = gr.JSON(label="Result")
        demo_btn.click(generate_demo_ui, inputs=[demo_id, demo_json, demo_file], outputs=demo_out)

app = demo.app

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)