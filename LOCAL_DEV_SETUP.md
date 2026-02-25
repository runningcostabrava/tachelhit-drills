# Desarrollo Local

Para ejecutar la aplicación localmente, sigue estos pasos:

## 1. Configurar variables de entorno

### Backend
Copia el archivo de ejemplo en backend/.env:

```powershell
cd backend
copy .env.example .env
```

Ajusta las variables si es necesario.

### Frontend
Copia el archivo de ejemplo en frontend/.env:

```powershell
cd frontend
copy .env.example .env
```

## 2. Instalar dependencias

### Backend
Crea un entorno virtual e instala dependencias:

```powershell
cd backend
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Frontend
Instala paquetes npm:

```powershell
cd frontend
npm install
```

## 3. Ejecutar servidores

### Backend
En una terminal (con el entorno virtual activado):

```powershell
cd backend
python main.py
```

El archivo `main.py` ahora incluye un bloque que inicia el servidor automáticamente (usando `uvicorn`). El backend estará disponible en http://localhost:8000

### Frontend
En otra terminal:

```powershell
cd frontend
npm run dev
```

El frontend se abrirá en http://localhost:5173

## 4. Script de inicio automático (Windows PowerShell)

También puedes usar el script `start-local.ps1` ubicado en la raíz del proyecto. Ejecútalo en PowerShell:

```powershell
.\start-local.ps1
```

Nota: Es posible que necesites ajustar la política de ejecución:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

El script mejorado:
- Comprueba si el puerto 8000 está ocupado.
- Espera a que el backend responda antes de abrir el frontend.
- Muestra mensajes de éxito/error claros.

## 5. Verificar

- Abre el navegador en http://localhost:5173
- La API backend responderá en http://localhost:8000/health
- Revisa la consola del backend para ver logs de CORS.

### 6. Datos de ejemplo

El backend incluye un mecanismo que, si la base de datos está vacía, crea automáticamente un drill de ejemplo. Esto asegura que al abrir la aplicación local por primera vez veas al menos una tarjeta en la lista.

Si deseas cargar más datos, puedes utilizar la funcionalidad de importación (disponible en la interfaz de administración) o agregar drills manualmente haciendo clic en "+ New Drill".

### 7. Verificar que los datos se carguen

Después de iniciar el backend, puedes comprobar que los datos se estén sirviendo correctamente con estos pasos:

1. **Abrir la consola del navegador** (F12) y mirar la pestaña "Console". Deberías ver mensajes como "✅ Backend connection successful" y "✅ Drills fetch successful, count: 3". Si hay errores, aparecerán en rojo.

2. **Verificar el endpoint de drills** directamente en el navegador:  
   Ve a [http://localhost:8000/drills/](http://localhost:8000/drills/). Deberías obtener un JSON con una lista de drills. Si la lista está vacía (`[]`), significa que la base de datos no tiene datos.

3. **Depurar la base de datos**:  
   Puedes visitar [http://localhost:8000/debug/db](http://localhost:8000/debug/db) para ver estadísticas de la base de datos (`drill_count`, `test_count`, etc.) y confirmar que `drill_count` sea mayor que cero.

4. **Revisar logs del backend**:  
   En la ventana de PowerShell donde se ejecuta el backend, busca líneas que comiencen con `[INIT] Adding sample drills...` y `[INIT] Added sample drill id`. Si no aparecen, es posible que la base de datos ya existiera y no estuviera vacía.

5. **Si no hay drills, puedes agregar ejemplos manualmente**:  
   Abre [http://localhost:8000/debug/seed](http://localhost:8000/debug/seed) en tu navegador (método GET). Esto agregará tres drills de ejemplo a la base de datos. Después de recargar la página principal ([http://localhost:5173](http://localhost:5173)) deberían aparecer las tarjetas.

## Solución de problemas

- Si el backend no inicia, comprueba que no haya otro proceso usando el puerto 8000. En Windows, puedes usar `netstat -ano | findstr :8000`.
- Si el frontend no se conecta al backend, revisa que la variable `VITE_API_URL` en frontend/.env sea `http://localhost:8000`.
- Si hay errores de CORS, asegúrate de que `FRONTEND_URL` en backend/.env incluya `http://localhost:5173`.
- Si ves errores sobre ag‑grid, es un problema de versión de la librería de tablas. No afecta la funcionalidad principal. Para resolverlo, puedes actualizar la configuración de ag‑grid en los componentes React (consulta la documentación de migración).

### Solución de problemas detallada

#### 1. El backend no se inicia

- **Verifica que Python esté instalado**: Ejecuta `python --version` en una terminal. Debe mostrar Python 3.8 o superior.
- **Instala las dependencias**: En la carpeta `backend`, activa el entorno virtual y ejecuta `pip install -r requirements.txt`. Asegúrate de que no haya errores.
- **Puerto 8000 ocupado**: Usa `netstat -ano | findstr :8000` para ver el proceso que escucha. Puedes finalizarlo con `taskkill /PID <PID> /F` (reemplaza `<PID>` con el número de proceso).
- **Errores de importación**: Si falta algún módulo, el backend fallará. Revisa la ventana del backend para mensajes de error.

#### 2. El frontend no se conecta al backend

- **Verifica que el backend esté en ejecución**: Abre http://localhost:8000/health en el navegador. Deberías ver un JSON con `{"status":"healthy"}`.
- **Configuración de entorno**: Asegúrate de que el archivo `frontend/.env` existe y contiene `VITE_API_URL=http://localhost:8000`.
- **CORS**: El backend permite orígenes de `http://localhost:5173`. Si usas otra URL, añádela en `backend/.env` como `FRONTEND_URL`.

#### 3. Errores de AG Grid

La versión 35.0.1 de AG Grid introdujo cambios en el sistema de temas. Para usar el modo legacy (CSS clásico) temporalmente, puedes agregar la propiedad `theme="legacy"` al componente `<AgGridReact>`.

Ejemplo:
```jsx
<AgGridReact
  theme="legacy"
  // ... otras props
/>
```

#### 4. Problemas con el script start-local.ps1

Si el script se cierra sin iniciar los servidores, ejecuta PowerShell como administrador y cambia la política de ejecución:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Luego ejecuta manualmente los pasos descritos en la sección 3 (Ejecutar servidores) de esta guía.
