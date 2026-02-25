# Tachelhit Translation Space

Este espacio proporciona una API de traducción entre catalán y tachelhit (Tamazight del Atlas Central) utilizando el modelo NLLB fine‑tuned de Tamazight‑NLP.

## Uso

### Interfaz web
Accede a la interfaz web del espacio para traducir texto de forma interactiva.

### API
Para usar la API desde tu backend, puedes hacer una solicitud POST al endpoint `/api/translate` con un cuerpo JSON:

```json
{
  "text": "Texto a traducir",
  "src_lang": "cat_Latn",
  "tgt_lang": "ber_Tfng"
}
```

La respuesta será:

```json
{
  "translation": "Texto traducido"
}
```

Códigos de idioma soportados: 
- `cat_Latn` (catalán)
- `ber_Tfng` (tachelhit)
- `eng_Latn` (inglés)
- `fra_Latn` (francés)
- `arb_Arab` (árabe estándar)

## Ejecución local

Instala las dependencias:

```bash
pip install -r requirements.txt
```

Lanza la aplicación Gradio:

```bash
python app.py
```

El espacio estará disponible en `http://localhost:7860`.

## Despliegue en Hugging Face Spaces

Este espacio está configurado para desplegarse automáticamente en Hugging Face Spaces usando el SDK de Gradio.

Si necesitas actualizar el espacio, modifica los archivos y ejecuta el script de despliegue (asegúrate de tener configurada la variable de entorno `HUGGINGFACE_API_TOKEN`):

```bash
python deploy_space.py
```

Recuerda configurar el secret `HF_TOKEN` en la web del espacio (Settings > Repository secrets) para que el modelo se cargue correctamente.

## Notas

- El modelo puede tardar unos segundos en cargarse la primera vez.
- Las traducciones son de alta calidad para el par catalán‑tachelhit, pero pueden variar para otros idiomas.
- El espacio utiliza hardware gratuito (`cpu‑basic`), por lo que puede haber límites de uso.

## Verificación del espacio

Para comprobar si el espacio se ha creado correctamente, visita la siguiente URL:

https://huggingface.co/spaces/josepabloucr/tamazight-translation-space

También puedes usar el endpoint de diagnóstico en el backend `/debug/translation-space-status` que intentará contactar al espacio y devolverá su estado.

Si el espacio aún no existe, ejecuta el script de despliegue:

```bash
cd huggingface-translation-space
python deploy_space.py
```

Asegúrate de tener configurada la variable de entorno `HUGGINGFACE_API_TOKEN` con tu token.
