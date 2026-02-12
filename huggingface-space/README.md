---
title: Tachelhit Video Generator
emoji: 🎬
colorFrom: purple
colorTo: pink
sdk: gradio
sdk_version: 4.36.0
app_file: app.py
pinned: false
license: mit
---

# Tachelhit Video Generator

Genera YouTube Shorts y videos demo para la plataforma Tachelhit Drills.

## Uso

1. En la pestaña **YouTube Short**, proporciona un JSON con los datos del drill (textos, URL de imagen, audio) y un nombre de archivo.
2. En la pestaña **Drill Player Demo**, proporciona un array de drills y un ID de test opcional.

El video generado se podrá descargar directamente desde la interfaz.

## Requisitos

Las dependencias están listadas en `requirements.txt`. El Space incluye FFmpeg para procesamiento de video.

## API

Este Space también puede ser llamado mediante API HTTP (POST) desde tu backend. Consulta el código fuente para más detalles.
