// src/main.tsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'
import './index.css'
import { BrowserRouter } from 'react-router-dom';
import { restoreUserIdentity } from './config';
import { watchForStaleBuild } from './utils/freshness';
import { prune } from './utils/readCache';

// AG Grid registration lives in src/agGridSetup.ts, imported only by the
// grid components so the library stays out of the entry bundle.

// Restore the identity from the native store before the first request fires.
// Un desplegament mentre tens la pestanya oberta deixa trossos de l'app sense servidor.
watchForStaleBuild();

// El cau de lectura es poda un cop en arrencar: el que és vell no s'ensenya mai i només ocupa
// lloc al telèfon. No bloqueja res.
prune().catch(() => {});

restoreUserIdentity().finally(() => {
  ReactDOM.createRoot(document.getElementById('root')!).render(
    <React.StrictMode>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </React.StrictMode>,
  );
});