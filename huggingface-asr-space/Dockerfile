# Docker Space so /transcribe is a first-class FastAPI route served by uvicorn
# (not a Gradio-mounted route subject to Gradio's catch-all / CSRF protection).
FROM python:3.10-slim

# System deps: ffmpeg + libsndfile for librosa to decode audio out of mp4/wav.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Run as the non-root "user" expected by HF Spaces, with a writable HF cache.
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
