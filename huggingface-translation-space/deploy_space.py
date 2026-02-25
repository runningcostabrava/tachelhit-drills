#!/usr/bin/env python3
"""
Script para crear y desplegar el espacio de traducción en Hugging Face Spaces.
Requiere tener configurada la variable de entorno HUGGINGFACE_API_TOKEN.
"""

import os
import sys
import argparse
from pathlib import Path
from huggingface_hub import HfApi, create_repo, upload_folder

# Configuración
SPACE_NAME = "tamazight-translation-space"  # Cambia esto si quieres otro nombre
SPACE_SDK = "gradio"  # Usamos gradio porque FastAPI no está en la lista, gradio es compatible
SPACE_HARDWARE = "cpu-basic"  # Gratuito
AUTHOR = "josepabloucr"  # Tu nombre de usuario

def parse_args():
    parser = argparse.ArgumentParser(description="Despliega el espacio de traducción en Hugging Face.")
    parser.add_argument("--token", type=str, help="Token de Hugging Face (opcional, por defecto usa HUGGINGFACE_API_TOKEN)")
    return parser.parse_args()

def main():
    args = parse_args()
    
    # Verificar token desde las variables de entorno o argumento
    token = args.token or os.getenv("HUGGINGFACE_API_TOKEN")
    if not token:
        print("❌ ERROR: La variable de entorno HUGGINGFACE_API_TOKEN no está definida.")
        print("   Por favor, configura tu token de Hugging Face.")
        print("   Puedes hacerlo temporalmente en Linux/Mac con:")
        print("   export HUGGINGFACE_API_TOKEN=tu_nuevo_token")
        print("   o ejecutar el script con:")
        print("   HUGGINGFACE_API_TOKEN=tu_nuevo_token python deploy_space.py")
        print("   o usar el argumento --token")
        sys.exit(1)

    # Mostrar token truncado para depuración
    token_display = token[:8] + "..." + token[-4:] if len(token) > 12 else token[:8] + "..."
    print(f"[TOKEN] Usando token: {token_display}")

    # Inicializar API
    api = HfApi(token=token)

    # Determinar el ID del espacio (usuario/space_name)
    space_id = f"{AUTHOR}/{SPACE_NAME}"

    print(f"🔄 Creando/actualizando espacio: {space_id}")
    print(f"   Usuario: {AUTHOR}")
    print(f"   Nombre del espacio: {SPACE_NAME}")
    print(f"   SDK: {SPACE_SDK} | Hardware: {SPACE_HARDWARE}")

    # Verificar si el token es válido
    try:
        user_info = api.whoami()
        print(f"   ✅ Token válido para usuario: {user_info.get('name', 'N/A')}")
    except Exception as e:
        print(f"❌ Token inválido o error de autenticación: {e}")
        sys.exit(1)

    # Crear el repositorio (espacio) si no existe
    try:
        create_repo(
            repo_id=space_id,
            repo_type="space",
            space_sdk=SPACE_SDK,
            token=token,
            exist_ok=True,
            space_hardware=SPACE_HARDWARE,
            private=False,  # Espacio público
        )
        print(f"✅ Espacio '{space_id}' creado o ya existente.")
    except Exception as e:
        print(f"❌ Error al crear el espacio: {e}")
        sys.exit(1)

    # Subir archivos desde el directorio actual
    current_dir = Path(__file__).parent.absolute()
    print(f"📂 Subiendo archivos desde: {current_dir}")

    # Archivos a subir (todos los necesarios)
    allowed_extensions = {".py", ".txt", ".md", ".json", ".yaml", ".yml", ".dockerfile", "Dockerfile"}
    files_to_upload = []
    for ext in allowed_extensions:
        files_to_upload.extend(current_dir.glob(f"*{ext}"))

    # También incluir archivos específicos importantes
    important_files = ["app.py", "requirements.txt", "README.md", "DEPLOY.md"]
    for fname in important_files:
        fpath = current_dir / fname
        if fpath.exists() and fpath not in files_to_upload:
            files_to_upload.append(fpath)

    # Filtrar solo los que existen
    files_to_upload = [f for f in files_to_upload if f.exists()]

    if not files_to_upload:
        print("⚠️ No se encontraron archivos para subir. Asegúrate de tener al menos un app.py.")
    else:
        try:
            for file_path in files_to_upload:
                relative_path = file_path.relative_to(current_dir)
                print(f"   📄 {relative_path}")

            # Subir la carpeta entera excluyendo la basura
            upload_folder(
                folder_path=current_dir,
                repo_id=space_id,
                repo_type="space",
                token=token,
                ignore_patterns=["*.pyc", "__pycache__", "*.log", "deploy_space.py", "*.tmp"],
            )
            print("✅ Archivos subidos exitosamente.")
        except Exception as e:
            print(f"❌ Error al subir archivos: {e}")
            # Intentar subir archivo por archivo
            print("   Intentando subir archivos uno por uno...")
            for file_path in files_to_upload:
                try:
                    relative_path = file_path.relative_to(current_dir)
                    with open(file_path, "rb") as f:
                        api.upload_file(
                            path_or_fileobj=f,
                            path_in_repo=str(relative_path),
                            repo_id=space_id,
                            repo_type="space",
                        )
                    print(f"   ✅ {relative_path}")
                except Exception as e2:
                    print(f"   ❌ {relative_path}: {e2}")
            print("   Subida finalizada (con posibles errores).")

    print("\n⚠️  NOTA: Si tu aplicación requiere el token para correr, debes configurarlo en la web del espacio.")
    print("   Ve a Settings > Repository secrets > Add a new secret.")
    print("   Nombre: HF_TOKEN")
    print(f"   Valor: {token_display}... (secreto)")

    print("\n🎉 ¡Despliegue completado!")
    print(f"🌐 Tu espacio está disponible en: https://huggingface.co/spaces/{space_id}")

    # URL de la aplicación en directo
    space_app_url = f"https://{space_id.replace('/', '-').lower()}.hf.space"
    print(f"🌐 URL de la aplicación (live): {space_app_url}")

    print("\n📌 Nota: El espacio puede tardar unos minutos en construirse e iniciarse.")
    print("   Puedes monitorear el progreso en la pestaña 'Logs' del espacio.")

    # Guardar la URL en un archivo para referencia posterior
    url_file = current_dir / "deployed_url.txt"
    with open(url_file, "w") as f:
        f.write(f"https://huggingface.co/spaces/{space_id}")
    print(f"📝 URL guardada en: {url_file}")

    # Crear también un archivo con la URL de la aplicación en vivo
    live_url_file = current_dir / "live_url.txt"
    with open(live_url_file, "w") as f:
        f.write(space_app_url)
    print(f"📝 URL live guardada en: {live_url_file}")

    print("\n✅ ¡Todo listo! El espacio debería estar visible en unos minutos.")
    print("   Si el espacio no aparece, revisa los logs en Hugging Face.")

if __name__ == "__main__":
    main()
