import gradio as gr
import torch
from diffusers import AutoPipelineForText2Image

# SD-Turbo: distilled, 1-2 step generation. Small + fast enough to run on the
# free CPU tier (no GPU), and near-instant on a GPU. Device-aware so it never
# crashes when there's no CUDA (the old SDXL + hardcoded .to("cuda") did).
device = "cuda" if torch.cuda.is_available() else "cpu"
dtype = torch.float16 if device == "cuda" else torch.float32
model_id = "stabilityai/sd-turbo"

print(f"[IMAGE] Loading {model_id} on {device} (dtype={dtype})...")
pipe = AutoPipelineForText2Image.from_pretrained(model_id, torch_dtype=dtype)
pipe = pipe.to(device)
print("[IMAGE] Pipeline ready.")


def generate_image(prompt):
    print(f"[IMAGE] Generating: {prompt}")
    full_prompt = f"{prompt}, high quality, realistic photo"
    # SD-Turbo: few steps, no classifier-free guidance
    image = pipe(prompt=full_prompt, num_inference_steps=2, guidance_scale=0.0).images[0]
    return image


with gr.Blocks(title="Tachelhit Image Generator") as demo:
    gr.Markdown("# Generador d'imatges")
    with gr.Row():
        prompt_input = gr.Textbox(label="Prompt", placeholder="A friend, two people talking...")
    generate_btn = gr.Button("Generate")
    image_output = gr.Image(label="Result", type="filepath")

    generate_btn.click(fn=generate_image, inputs=prompt_input, outputs=image_output, api_name="/generate")

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
