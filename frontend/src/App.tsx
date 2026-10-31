import { useEffect, useState, lazy, Suspense } from 'react';
import { useIsMobileLayout } from './utils/layout';
import { Network } from '@capacitor/network';
import axios from 'axios';
import { API_BASE } from './config';
import { OBERTURA_MS } from './services/biblioteca';
import { api } from './api';
import { Routes, Route, Navigate, useNavigate, useLocation } from 'react-router-dom';
import { FaLayerGroup, FaVideo, FaGraduationCap, FaComments, FaUser, FaRedo, FaFire, FaPlay, FaBook, FaBookOpen, FaMicrophone, FaInfo, FaSearch, FaPlus, FaFeatherAlt, FaFont } from 'react-icons/fa';
import { syncManager } from './services/OfflineSyncManager';
import { engegaAudios } from './services/audioLocal';
import * as cuaDeVeus from './services/cuaDeVeus';
import ToastHost from './components/ToastHost';
import StaleBuildBanner from './components/StaleBuildBanner';
import DataNotice from './components/DataNotice';
import AiCopilot from './components/AiCopilot';
import AboutPanel from './components/AboutPanel';
import MenuMobil from './components/MenuMobil';
import './App.css';

// Route-level code splitting: each page loads its chunk on first visit,
// keeping the initial bundle small (AG Grid, players, creators all split out)
/**
 * Baixar la pantalla, i si falla perquè l'app s'ha actualitzat, tornar-hi.
 *
 * Cada pantalla és un tros de programa a part i el seu nom porta una empremta del contingut.
 * En publicar una versió nova, els trossos vells deixen d'existir: qui tenia l'app oberta,
 * en canviar de pantalla, demana un fitxer que ja no hi és. Això no és «no hi ha servidor»
 * —que vol dir espera't o mira el wifi— sinó «m'acabo d'actualitzar», que vol dir recarrega.
 *
 * I si ho sabem, no cal ni dir-ho: es recarrega sol. Una vegada. Si després de recarregar
 * torna a fallar, el problema no és la versió nova i aleshores sí que s'ha de dir, perquè
 * amagar-ho deixaria l'app donant voltes.
 */
const JA_RECARREGADA = 'app.recarregada-per-versio-nova';
// Les pantalles tenen propietats de tota mena i aqui no se'n mira cap: nomes es baixen.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function lazyPagina<T extends React.ComponentType<any>>(carrega: () => Promise<{ default: T }>) {
  return lazy(async () => {
    try {
      const m = await carrega();
      try { sessionStorage.removeItem(JA_RECARREGADA); } catch { /* finestra privada */ }
      return m;
    } catch (e) {
      let tornada = true;
      try { tornada = sessionStorage.getItem(JA_RECARREGADA) !== '1'; } catch { tornada = false; }
      if (tornada) {
        try { sessionStorage.setItem(JA_RECARREGADA, '1'); } catch { /* finestra privada */ }
        window.location.reload();
        // La pàgina se'n va: aquesta promesa no s'ha de resoldre mai, o React pintaria
        // l'error mig segon abans de marxar.
        return new Promise<never>(() => {});
      }
      throw e;
    }
  });
}

const HomePage = lazyPagina(() => import('./components/HomePage'));
const SearchPage = lazyPagina(() => import('./components/SearchPage'));
const AddSentencePage = lazyPagina(() => import('./components/AddSentencePage'));
const DrillsResponsive = lazyPagina(() => import('./components/DrillsResponsive'));
const TestsDashboard = lazyPagina(() => import('./components/TestsDashboard'));
const PracticePage = lazyPagina(() => import('./components/PracticePage'));
const PracticeSession = lazyPagina(() => import('./components/PracticeSession'));
const PracticeGroupPage = lazyPagina(() => import('./components/PracticeGroupPage'));
const VeusPage = lazyPagina(() => import('./components/VeusPage'));
const UserPage = lazyPagina(() => import('./components/UserPage'));
const DrillPlayerPage = lazyPagina(() => import('./components/DrillPlayerPage'));
const PublicTestView = lazyPagina(() => import('./components/PublicTestView'));
const VideoDrillCreator = lazyPagina(() => import('./components/VideoDrillCreator'));
const SrtImport = lazyPagina(() => import('./components/SrtImport'));
const VideoLibraryPage = lazyPagina(() => import('./components/VideoLibraryPage'));
const CaptureReview = lazyPagina(() => import('./components/CaptureReview'));
const MethodPage = lazyPagina(() => import('./components/MethodPage'));
const MethodChapter = lazyPagina(() => import('./components/MethodChapter'));
const ProfilePage = lazyPagina(() => import('./components/ProfilePage'));
const AuthPage = lazyPagina(() => import('./components/AuthPage'));
const CorpusPage = lazyPagina(() => import('./components/CorpusPage'));
const CreditsPage = lazyPagina(() => import('./components/CreditsPage'));
const ServeisPage = lazyPagina(() => import('./components/ServeisPage'));
const LessonEditor = lazyPagina(() => import('./components/LessonEditor'));
const StoriesPage = lazyPagina(() => import('./components/StoriesPage'));
const ListenPage = lazyPagina(() => import('./components/ListenPage'));
const GrammarPage = lazyPagina(() => import('./components/GrammarPage'));
const AlfabetPage = lazyPagina(() => import('./components/AlfabetPage'));
// The one page in English (#487): the first words for someone coming to run in the Atlas.
const StartEnglish = lazyPagina(() => import('./components/StartEnglish'));
const PracticeEditor = lazyPagina(() => import('./components/PracticeEditor'));
const VerifyQueue = lazyPagina(() => import('./components/VerifyQueue'));
const RevisaPage = lazyPagina(() => import('./components/RevisaPage'));

const RouteLoader = () => (
  <div style={{ minHeight: '60vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
    <div style={{ width: '44px', height: '44px', borderRadius: '50%', border: '4px solid var(--border)', borderTopColor: 'var(--brand-1)', animation: 'spin 0.9s linear infinite' }} />
  </div>
);

// Learner entry point in the top nav (saffron signature accent): review when
// something is due/new, otherwise plain practice — never hidden.
const ReviewNavButton = ({ compact = false }: { compact?: boolean }) => {
  const navigate = useNavigate();
  const [counts, setCounts] = useState<{ due: number; new: number } | null>(null);
  const [streak, setStreak] = useState(0);

  useEffect(() => {
    api.reviewStats().then(s => setCounts({ due: s.due, new: s.new })).catch(() => {});
    api.reviewStreak().then(s => setStreak(s.streak_days || 0)).catch(() => {});
  }, []);

  // El que toca avui és el que ja has vist i torna. Les que no has vist mai no són un deute:
  // sumades aquí, el botó deia «4811 nous» i el de la portada «Repassa 4815» (#416).
  const toca = counts?.due || 0;

  if (!toca) {
    return (
      <button
        onClick={() => navigate('/player')}
        title="Practica: comença frases que encara no has vist"
        style={{
          flexShrink: 0, display: 'flex', alignItems: 'center', gap: '6px', whiteSpace: 'nowrap',
          padding: compact ? '8px 10px' : '8px 14px', background: 'var(--emerald-soft)', color: 'var(--emerald)',
          border: '1px solid var(--emerald)', borderRadius: 'var(--r-pill)', fontWeight: 700, fontSize: compact ? '13px' : '14px', cursor: 'pointer'
        }}
      >
        <FaPlay size={12} />{!compact && ' Practica'}
        {streak > 0 && !compact && <span style={{ display: 'inline-flex', alignItems: 'center', gap: '3px' }}><FaFire size={12} />{streak}</span>}
      </button>
    );
  }

  return (
    <button
      onClick={() => navigate('/player?mode=review')}
      title="Repàs espaiat"
      style={{
        flexShrink: 0, display: 'flex', alignItems: 'center', gap: '6px', whiteSpace: 'nowrap',
        padding: compact ? '8px 10px' : '8px 14px', background: 'var(--saffron)', color: '#fff',
        border: 'none', borderRadius: 'var(--r-pill)', fontWeight: 700, fontSize: compact ? '13px' : '14px', cursor: 'pointer'
      }}
    >
      <FaRedo size={13} /> {toca}
      {streak > 0 && !compact && <span style={{ display: 'inline-flex', alignItems: 'center', gap: '3px' }}><FaFire size={12} />{streak}</span>}
    </button>
  );
};

function App() {
  const navigate = useNavigate();
  const location = useLocation();
  const [aiOpen, setAiOpen] = useState(false);
  const [aboutOpen, setAboutOpen] = useState(false);
  const [veusPendents, setVeusPendents] = useState(0);
  useEffect(() => cuaDeVeus.escolta(setVeusPendents), []);
  useEffect(() => { void engegaAudios(); }, []);

  // Offline sync bootstrap. All queue processing lives in OfflineSyncManager;
  // this effect just pushes pending actions and refreshes the local caches on
  // boot and whenever the network comes back.
  useEffect(() => {
    const runSync = async () => {
      const status = await Network.getStatus();
      if (!status.connected) {
        console.log('✈️ Device is offline. Sync paused.');
        return;
      }

      // Push queued offline actions first so the cache refresh sees the result
      await syncManager.sync();
      // I les veus que esperin al dispositiu. Van per la seva banda (#370): una presa no cap a
      // la cua de `Preferences` sense menjar-se el lloc de la biblioteca, i tampoc no ha
      // d'esperar que acabi la còpia dels drills per pujar. `engega` també escolta el `online`
      // del navegador, que al web és qui avisa que ha tornat el senyal.
      cuaDeVeus.engega();

      try {
        const [, testsRes] = await Promise.all([
          syncManager.refreshDrills(OBERTURA_MS),
          axios.get(`${API_BASE}/tests/`),
        ]);
        await syncManager.saveTestsToCache(testsRes.data);
      } catch (e) {
        console.error('Failed to pre-cache data', e);
      }
    };

    runSync();

    const listener = Network.addListener('networkStatusChange', status => {
      if (status.connected) runSync();
    });

    return () => { listener.then(l => l.remove()); };
  }, []);


  // Immersive routes render full-screen; the nav would collide with them
  const showNav = !location.pathname.startsWith('/player') && !/^\/tests\/\d/.test(location.pathname) && location.pathname !== '/tests/sessio';
  const compactNav = useIsMobileLayout(); // phones: icon-only tabs, so none of them is hidden off-screen
  // Each one is something you DO: look at the library, record new material, learn, practise, lend
  // your voice. What only an editor needs (the corpus and its exports) hangs off the Drills
  // page's "Més" menu instead of standing in the main menu.
  //
  // The logo goes home, and home is now a page of its own: the library's grid weighs six megabytes
  // and was no way to open the app.
  // «Drills» no és una paraula de ningú: és com es diu l'exercici a dins, i al menú hi havia
  // d'anar com se'n diu el que trobes en obrir-lo. El que hi ha són FRASES, dites per algú. La
  // ruta es queda `/drills` perquè els enllaços que corren per fora continuïn funcionant.
  //
  // Les Històries hi entren: eren una porta de la portada i prou, de manera que qui no passava
  // per la portada no sabia que existien.
  const navLinks = [
    { to: '/drills', label: 'Frases', Icon: FaLayerGroup },
    { to: '/stories', label: 'Històries', Icon: FaFeatherAlt },
    { to: '/metode', label: 'Mètode', Icon: FaBookOpen },
    { to: '/grammar', label: 'Gramàtica', Icon: FaBook },
    // Els sons i l'escriptura són una secció pròpia, al mateix nivell que la Gramàtica i el
    // Mètode (#368): l'abecedari que sona no és un apèndix d'una lliçó.
    { to: '/alfabet', label: 'Sons', Icon: FaFont },
    { to: '/tests', label: 'Pràctica', Icon: FaGraduationCap },
    { to: '/veus', label: 'Posa-hi veu', Icon: FaMicrophone },   // the route keeps its old name: links point at it
    { to: '/video-creator', label: 'Captura', Icon: FaVideo },
  ];
  const navBtn = (active: boolean): React.CSSProperties => ({
    flexShrink: 0, display: 'inline-flex', alignItems: 'center', gap: '6px',
    padding: compactNav ? '8px 7px' : '8px 14px', borderRadius: 'var(--r-pill)', fontWeight: 700, fontSize: '14px',
    cursor: 'pointer', border: '1px solid transparent', whiteSpace: 'nowrap',
    background: active ? 'var(--brand-gradient-soft)' : 'transparent',
    color: active ? 'var(--brand-1)' : 'var(--text-soft)',
  });

  return (
    <div style={{ minHeight: '100dvh', display: 'flex', flexDirection: 'column' }}>
      <ToastHost />
      <StaleBuildBanner />
      {aiOpen && <AiCopilot onClose={() => setAiOpen(false)} />}
      {aboutOpen && <AboutPanel onClose={() => setAboutOpen(false)} />}

      {showNav && (
        <nav style={{
          position: 'sticky', top: 0, zIndex: 1000, background: 'var(--surface)',
          borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', gap: compactNav ? '6px' : '10px',
          padding: compactNav ? 'calc(10px + env(safe-area-inset-top, 0px)) 8px 10px' : 'calc(10px + env(safe-area-inset-top, 0px)) 14px 10px', boxSizing: 'border-box',
          height: 'var(--nav-h)', boxShadow: '0 1px 3px rgba(15,23,42,0.04)'
        }}>
          <button onClick={() => navigate('/')} style={{ flexShrink: 0, display: 'flex', alignItems: 'center', gap: '8px', background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}>
            <span style={{ width: '30px', height: '30px', borderRadius: '9px', background: 'var(--brand-gradient)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '16px' }}>ⵣ</span>
            <span style={{ fontWeight: 800, fontSize: '16px', color: 'var(--text)', letterSpacing: '-0.01em' }}>Tamazight</span>
          </button>
          {/* Al mòbil les seccions són a baix, amb nom i al polze (#372): aquí dalt només hi
              queda el que es fa servir des de qualsevol pantalla, amb objectius de 44 px. */}
          {compactNav ? <div style={{ flex: 1, minWidth: 0 }} /> : (
            <div style={{ display: 'flex', gap: '4px', overflowX: 'auto', flex: 1, minWidth: 0, padding: '2px 0', scrollbarWidth: 'none' }}>
              {navLinks.map(l => (
                <button key={l.to} onClick={() => navigate(l.to)} title={l.label} aria-label={l.label}
                  style={navBtn(location.pathname === l.to || (l.to !== '/' && location.pathname.startsWith(l.to + '/')))}>
                  <l.Icon size={14} />{l.label}
                </button>
              ))}
            </div>
          )}
          {/* Cercar una frase: a l'abast des de qualsevol pantalla. L'amo ho va dir: «una cosa
              primordial a l'aplicació hauria de ser buscar una frase o paraula». */}
          {/* Fer una frase nova: amb nom, no només una icona. Al mòbil té el lloc del mig de la
              barra de baix, i aquí a l'escriptori diu què és. */}
          {!compactNav && (
            <button onClick={() => navigate('/afegeix')} title="Fes una frase nova" aria-label="Fes una frase nova"
                    style={{ flexShrink: 0, display: 'inline-flex', alignItems: 'center', gap: 7, whiteSpace: 'nowrap', padding: '9px 14px', height: 35, boxSizing: 'border-box', borderRadius: 'var(--r-pill)', cursor: 'pointer', border: 'none', background: 'var(--brand-gradient)', color: '#fff', fontWeight: 700, fontSize: '13px' }}>
              <FaPlus size={13} /> Nova frase
            </button>
          )}
          <button onClick={() => navigate('/cerca')} title="Cerca una frase" aria-label="Cerca una frase"
                  style={{ flexShrink: 0, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: compactNav ? 44 : 35, height: compactNav ? 44 : 35, borderRadius: 'var(--r-pill)', cursor: 'pointer', border: '1px solid var(--border)', background: location.pathname === '/cerca' ? 'var(--brand-gradient-soft)' : 'var(--surface)', color: location.pathname === '/cerca' ? 'var(--brand-1)' : 'var(--text-soft)' }}>
            <FaSearch size={compactNav ? 16 : 13} />
          </button>
          <ReviewNavButton compact={compactNav} />
          {/* Per què existeix això: al menú, que és d'on es pot arribar des de qualsevol pantalla.
              Al mòbil és una fila amb nom dins de «Més», que no competeix amb les seccions. */}
          {!compactNav && (
            <button onClick={() => setAboutOpen(true)} title="Per què existeix això" aria-label="Per què existeix això"
                    style={{ flexShrink: 0, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: 35, height: 35, borderRadius: 'var(--r-pill)', cursor: 'pointer', border: '1px solid var(--border)', background: 'var(--surface)', color: 'var(--text-soft)' }}>
              <FaInfo size={13} />
            </button>
          )}
          {/* Les veus que encara no han pujat.
              Una cua silenciosa és una cua que algú es pensa que ha perdut: si una presa espera
              el senyal, s'ha de veure que hi és i que puja sola (#370). */}
          {veusPendents > 0 && (
            <span title={`${veusPendents} ${veusPendents === 1 ? 'veu gravada que encara no ha pujat' : 'veus gravades que encara no han pujat'}. Pugen soles quan hi hagi senyal.`}
                  style={{ flexShrink: 0, display: 'inline-flex', alignItems: 'center', gap: 5, padding: '6px 10px', borderRadius: 'var(--r-pill)', background: 'var(--rose-soft)', color: 'var(--rose)', fontWeight: 800, fontSize: 12 }}>
              <FaMicrophone size={11} /> {veusPendents}
            </span>
          )}
          {!compactNav && <button onClick={() => setAiOpen(v => !v)} title="Copilot" aria-label="Copilot" style={{ flexShrink: 0, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', padding: '9px 12px', borderRadius: 'var(--r-pill)', cursor: 'pointer', border: 'none', background: aiOpen ? 'var(--brand-1)' : 'var(--brand-gradient)', color: '#fff' }}><FaComments size={15} /></button>}
          {!compactNav && <button onClick={() => navigate('/profile')} title="Perfil" aria-label="Perfil" style={{ flexShrink: 0, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', padding: '9px 12px', borderRadius: 'var(--r-pill)', cursor: 'pointer', border: '1px solid var(--border)', background: 'var(--surface)', color: 'var(--text-soft)' }}><FaUser size={15} /></button>}
        </nav>
      )}

      {/* D'on surt el que s'està veient. Va AQUÍ, entre el menú i el contingut, i no flotant
          per damunt: en un telèfon una fitxa flotant de 320 px tapa el títol de la pàgina, i
          no hi ha cap racó lliure on posar-la (#447). Dins del flux, empeny i no tapa. */}
      <DataNotice />

      {showNav && compactNav && <MenuMobil onCopilot={() => setAiOpen(true)} onAbout={() => setAboutOpen(true)} />}

      <main style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column', paddingBottom: 'var(--menu-mobil-h, 0px)' }}>
      <Suspense fallback={<RouteLoader />}>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/drills" element={<DrillsResponsive />} />
        <Route path="/revisa" element={<RevisaPage />} />
        <Route path="/cerca" element={<SearchPage />} />
        <Route path="/afegeix" element={<AddSentencePage />} />
        <Route path="/tests" element={<PracticePage />} />
        <Route path="/tests/sessio" element={<PracticeSession />} />
        <Route path="/tests/grup" element={<PracticeGroupPage />} />
        <Route path="/tests/llistes" element={<TestsDashboard />} />
        <Route path="/tests/:testId/editor" element={<PracticeEditor />} />
        {/* El Mètode: deu capítols fets amb la nostra biblioteca (ADR 0003). */}
        <Route path="/metode" element={<MethodPage />} />
        <Route path="/metode/:slug" element={<MethodChapter />} />
        <Route path="/veus" element={<VeusPage />} />
        <Route path="/u/:username" element={<UserPage />} />
        <Route path="/tests/:testId" element={<PublicTestView />} />
        <Route path="/tests/:testId/listen" element={<PublicTestView initialView="listening" />} />
        <Route path="/video-creator" element={<VideoDrillCreator />} />
        <Route path="/srt-import" element={<SrtImport />} />
        <Route path="/player" element={<DrillPlayerPage />} />
        <Route path="/library" element={<VideoLibraryPage />} />
        {/* What a video gave us, and the chance to move a cut or correct its words. */}
        <Route path="/captura/video" element={<CaptureReview />} />
        <Route path="/profile" element={<ProfilePage />} />
        <Route path="/signin" element={<AuthPage />} />
        <Route path="/corpus" element={<CorpusPage />} />
        <Route path="/credits" element={<CreditsPage />} />
        {/* Quina màquina fa cada feina, i què passa quan una no contesta (#295). */}
        <Route path="/serveis" element={<ServeisPage />} />
        <Route path="/listen" element={<ListenPage />} />
        <Route path="/stories" element={<StoriesPage />} />
        <Route path="/stories/:slug" element={<StoriesPage />} />
        <Route path="/alfabet" element={<AlfabetPage />} />
        <Route path="/start" element={<StartEnglish />} />
        <Route path="/grammar" element={<GrammarPage />} />
        <Route path="/grammar/:slug" element={<GrammarPage />} />
        <Route path="/grammar/:slug/editor" element={<LessonEditor />} />
        <Route path="/grammar/:slug/a-fons" element={<GrammarPage deep />} />
        <Route path="/verify" element={<VerifyQueue />} />
        {/* An unknown path (old link, typo, stale app shell) used to render an empty page. */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      </Suspense>
      </main>
    </div>
  );
}

export default App;
