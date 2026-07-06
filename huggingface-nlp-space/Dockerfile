# Docker Space: FastAPI (uvicorn) serving /transcribe, /translate, /ocr as
# first-class routes, with the Gradio UI mounted at / for the client.predict
# api_names. Mirrors huggingface-asr-space; adds OpenCV libs for EasyOCR.
FROM python:3.10-slim

# ffmpeg + libsndfile -> librosa audio decode ; libgl1 + libglib2 -> EasyOCR/opencv
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg libsndfile1 libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Non-root "user" expected by HF Spaces, with a writable HF cache.
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    HF_HOME=/home/user/.cache/huggingface

WORKDIR /home/user/app

COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY --chown=user . .

EXPOSE 7860
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860"]
