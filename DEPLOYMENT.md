# 🚀 Guia de Desplegament - Tachelhit Drills

## 📋 Prerequisits

1. Compte de [GitHub](https://github.com)
2. Compte de [Render](https://render.com) (Backend + Database)
3. Compte de [Vercel](https://vercel.com) (Frontend)

---

## 🔧 Pas 1: Preparar el Codi

### 1.1 Crear repositori a GitHub

```bash
cd C:\Users\josep\app2\tachelhit-drills
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/tachelhit-drills.git
git push -u origin main
```

### 1.2 Crear fitxer .gitignore

```bash
cat > .gitignore << 'GITIGNORE'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
*.egg-info/
drills.db
*.sqlite

# Media files (opcional - si vols pujar media, comenta aquestes línies)
media/audio/
media/video/
media/images/
media/shorts/

# Environment variables
.env
backend/.env
frontend/.env

# Node
node_modules/
dist/
.vite/
.DS_Store

# IDE
.vscode/
.idea/
GITIGNORE
```

---

## 🗄️ Pas 2: Desplegar Backend a Render

### 2.1 Crear Base de Dades PostgreSQL

1. Ves a [Render Dashboard](https://dashboard.render.com/)
2. Click **"New +"** → **"PostgreSQL"**
3. Configura:
   - **Name**: `tachelhit-drills-db`
   - **Database**: `tachelhit_drills`
   - **User**: `tachelhit_user`
   - **Region**: Frankfurt (més proper a Europa)
   - **Plan**: Free
4. Click **"Create Database"**
5. **GUARDA** la **Internal Database URL** (la necessitaràs)

### 2.2 Desplegar el Backend

1. A Render Dashboard, click **"New +"** → **"Web Service"**
2. Connecta el teu repositori de GitHub
3. Configura:
   - **Name**: `tachelhit-drills-api`
   - **Region**: Frankfurt
   - **Branch**: `main`
   - **Root Directory**: `backend`
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. **Environment Variables** (Click "Advanced"):
   ```
   DATABASE_URL = [La Internal Database URL que has guardat]
   PEXELS_API_KEY = dX9JkRJYfaRQUZdi6tKsF1TfJT44HnZMAPu2RyA4vt0JyRbzmdiVYGgW
   FRONTEND_URL = https://TU-APP.vercel.app
   ```
5. Click **"Create Web Service"**
6. Espera que es desplegui (5-10 minuts)
7. **GUARDA la URL del backend**: `https://tachelhit-drills-api.onrender.com`

---

## 🎨 Pas 3: Desplegar Frontend a Vercel

### 3.1 Actualitzar els components per usar config.ts

**IMPORTANT**: Canvia `const API_BASE = 'http://localhost:8000'` per:
```typescript
import { API_BASE } from '../config';
```

En aquests fitxers:
- `frontend/src/components/DrillsGrid.tsx`
- `frontend/src/components/TestConfigPanel.tsx`
- `frontend/src/components/TestEditPanel.tsx`
- `frontend/src/components/TestsDashboard.tsx`
- `frontend/src/components/TestTaking.tsx`
- `frontend/src/components/YouTubeShorts.tsx`

### 3.2 Desplegar a Vercel

1. Ves a [Vercel](https://vercel.com)
2. Click **"Add New"** → **"Project"**
3. Importa el repositori de GitHub
4. Configura:
   - **Framework Preset**: Vite
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
5. **Environment Variables**:
   ```
   VITE_API_URL = https://tachelhit-drills-api.onrender.com
   ```
6. Click **"Deploy"**
7. Espera que es desplegui (2-3 minuts)
8. **GUARDA la URL**: `https://tachelhit-drills.vercel.app`

### 3.3 Actualitzar FRONTEND_URL a Render

1. Torna a Render Dashboard
2. Selecciona el teu Web Service (backend)
3. Ves a **"Environment"**
4. Actualitza `FRONTEND_URL` amb la URL de Vercel
5. Guarda i redesplega

---

## ✅ Pas 4: Verificar el Desplegament

1. Obre la URL de Vercel al navegador
2. Verifica que carrega l'aplicació
3. Prova crear un drill
4. Verifica que funcionen:
   - CRUD de drills
   - Pujada d'àudio/vídeo/imatge
   - Generació d'imatges amb Pexels
   - Creació de tests
   - Generació de YouTube Shorts

---

## 🔧 Troubleshooting

### Error: "Network Error" o CORS
- Verifica que `FRONTEND_URL` a Render sigui correcte
- Verifica que `VITE_API_URL` a Vercel sigui correcte
- Redesplega el backend després de canviar variables

### Error: Database connection
- Verifica que `DATABASE_URL` sigui correcte
- Verifica que la base de dades estigui en funcionament

### Els media files no es guarden
- Render té disc efímer (es borra en redesplegar)
- Solució: Usar cloud storage (AWS S3, Cloudinary, etc.)

---

## 📊 Monitorització

- **Backend logs**: Render Dashboard → Service → Logs
- **Frontend logs**: Vercel Dashboard → Project → Deployments → Logs
- **Database**: Render Dashboard → Database → Metrics

---

## 💰 Costos

- **Render Free Tier**:
  - Web Service: Dorm després de 15 min d'inactivitat
  - Database: 90 dies gratuïts, després $7/mes
  - 750 hores/mes

- **Vercel Free Tier**:
  - 100 GB bandwidth/mes
  - Il·limitat deploys

---

## 🔄 Actualitzacions

Per actualitzar l'aplicació:

1. Fes canvis al codi localment
2. Commit i push a GitHub:
   ```bash
   git add .
   git commit -m "Descripció dels canvis"
   git push
   ```
3. Render i Vercel es redespleguaran automàticament

---

## 📝 Notes Importants

1. **Media files**: Render no guarda fitxers permanentment. Considera usar:
   - AWS S3
   - Cloudinary
   - Google Cloud Storage

2. **Database backups**: Fes backups regulars des de Render

3. **Environment variables**: Mai puges `.env` a GitHub

4. **Performance**: El tier gratuït de Render dorm després de 15 min. Primera càrrega serà lenta.

---

## 🎉 Fet!

La teva aplicació ja està accessible des d'internet! 🌍

URL Frontend: `https://tachelhit-drills.vercel.app`
URL Backend: `https://tachelhit-drills-api.onrender.com`
