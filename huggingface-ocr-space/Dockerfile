# Docker Space so /ocr is a first-class FastAPI route served by uvicorn
# (same pattern as huggingface-asr-space).
FROM python:3.10-slim

# System deps: libgl/libglib for opencv (EasyOCR dependency).
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Run as the non-root "user" expected by HF Spaces, with a writable cache.
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

WORKDIR /home/user/app

COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Bake the EasyOCR model weights into the image so cold starts don't
# re-download ~100MB on every container boot.
RUN python -c "import easyocr; easyocr.Reader(['en','fr','es'], gpu=False); easyocr.Reader(['ar','en'], gpu=False)"

COPY --chown=user . .

EXPOSE 7860
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860"]
