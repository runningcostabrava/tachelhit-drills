import gradio as gr
import torch
from diffusers import StableDiffusionXLPipeline, EulerDiscreteScheduler
import os

# Optimized for CPU or GPU
device = "cuda" if torch.cuda.is_available() else "cpu"
model_id = "stabilityai/stable-diffusion-xl-base-1.0"

print(f"[IMAGE] Loading model {model_id} on {device}...")

# Load pipeline
if device == "cuda":
    pipe = StableDiffusionXLPipeline.from_pretrained(model_id, torch_dtype=torch.float16, variant="fp16", use_safetensors=True)
    pipe.enable_model_cpu_offload()
else:
    # CPU usage (Slow, but works on free tier)
    pipe = StableDiffusionXLPipeline.from_pretrained(model_id, use_safetensors=True)

pipe.to(device)

def generate_image(prompt):
    print(f"[IMAGE] Generating: {prompt}")
    # Add some quality modifiers
    full_prompt = f"{prompt}, high quality, realistic photo, 4k"
    image = pipe(prompt=full_prompt, num_inference_steps=30).images[0]
    return image

# Gradio Interface
with gr.Blocks(title="Tachelhit Image Generator") as demo:
    gr.Markdown("# 🎨 Generador de Imatges AI")
    with gr.Row():
        prompt_input = gr.Textbox(label="Prompt", placeholder="A beautiful sunset in the Atlas mountains...")
    generate_btn = gr.Button("Generate")
    image_output = gr.Image(label="Result", type="filepath")
    
    generate_btn.click(fn=generate_image, inputs=prompt_input, outputs=image_output, api_name="/generate")

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
