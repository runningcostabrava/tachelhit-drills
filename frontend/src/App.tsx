import { useEffect, useState, lazy, Suspense } from 'react';
import { useIsMobileLayout } from './utils/layout';
import { Network } from '@capacitor/network';
import axios from 'axios';
import { API_BASE } from './config';
import { api } from './api';
import { Routes, Route, Navigate, useNavigate, useLocation } from 'react-router-dom';
import { FaLayerGroup, FaVideo, FaBookOpen, FaGraduationCap, FaFilm, FaComments, FaUser, FaRedo, FaFire, FaPlay, FaBook } from 'react-icons/fa';
import { syncManager } from './services/OfflineSyncManager';
import ToastHost from './components/ToastHost';
import AiCopilot from './components/AiCopilot';
import './App.css';

// Route-level code splitting: each page loads its chunk on first visit,
// keeping the initial bundle small (AG Grid, players, creators all split out)
const DrillsResponsive = lazy(() => import('./components/DrillsResponsive'));
const TestsDashboard = lazy(() => import('./components/TestsDashboard'));
const PracticePage = lazy(() => import('./components/PracticePage'));
const PracticeSession = lazy(() => import('./components/PracticeSession'));
const YouTubeShorts = lazy(() => import('./components/YouTubeShorts'));
const DrillPlayerPage = lazy(() => import('./components/DrillPlayerPage'));
const PublicTestView = lazy(() => import('./components/PublicTestView'));
const VideoDrillCreator = lazy(() => import('./components/VideoDrillCreator'));
const SrtImport = lazy(() => import('./components/SrtImport'));
const VideoLibraryPage = lazy(() => import('./components/VideoLibraryPage'));
const ProfilePage = lazy(() => import('./components/ProfilePage'));
const AuthPage = lazy(() => import('./components/AuthPage'));
const CorpusPage = lazy(() => import('./components/CorpusPage'));
const GrammarPage = lazy(() => import('./components/GrammarPage'));
const VerifyQueue = lazy(() => import('./components/VerifyQueue'));

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

  const pending = (counts?.due || 0) + (counts?.new || 0);

  if (!pending) {
    return (
      <button
        onClick={() => navigate('/player')}
        title="Practica tots els drills"
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
      <FaRedo size={13} /> {counts!.due > 0 ? counts!.due : compact ? counts!.new : `${counts!.new} nous`}
      {streak > 0 && !compact && <span style={{ display: 'inline-flex', alignItems: 'center', gap: '3px' }}><FaFire size={12} />{streak}</span>}
    </button>
  );
};

function App() {
  const navigate = useNavigate();
  const location = useLocation();
  const [aiOpen, setAiOpen] = useState(false);

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

      try {
        const [drillsRes, testsRes] = await Promise.all([
          axios.get(`${API_BASE}/drills/`),
          axios.get(`${API_BASE}/tests/`),
        ]);
        // saveDrillsToCache also kicks off background media caching
        // (audio & images only; videos are cached on demand)
        await syncManager.saveDrillsToCache(drillsRes.data);
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
  const compactNav = useIsMobileLayout(); // phones: icon-only tabs so Tests and Reels are not hidden off-screen
  const navLinks = [
    { to: '/', label: 'Drills', Icon: FaLayerGroup },
    { to: '/video-creator', label: 'Captura', Icon: FaVideo },
    { to: '/grammar', label: 'Gramàtica', Icon: FaBook },
    { to: '/corpus', label: 'Corpus', Icon: FaBookOpen },
    { to: '/tests', label: 'Pràctica', Icon: FaGraduationCap },
    { to: '/shorts', label: 'Reels', Icon: FaFilm },
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
      {aiOpen && <AiCopilot onClose={() => setAiOpen(false)} />}

      {showNav && (
        <nav style={{
          position: 'sticky', top: 0, zIndex: 1000, background: 'var(--surface)',
          borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', gap: compactNav ? '6px' : '10px',
          padding: compactNav ? 'calc(10px + env(safe-area-inset-top, 0px)) 8px 10px' : 'calc(10px + env(safe-area-inset-top, 0px)) 14px 10px', boxSizing: 'border-box',
          height: 'var(--nav-h)', boxShadow: '0 1px 3px rgba(15,23,42,0.04)'
        }}>
          <button onClick={() => navigate('/')} style={{ flexShrink: 0, display: 'flex', alignItems: 'center', gap: '8px', background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}>
            <span style={{ width: '30px', height: '30px', borderRadius: '9px', background: 'var(--brand-gradient)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '16px' }}>ⵣ</span>
            {!compactNav && <span style={{ fontWeight: 800, fontSize: '16px', color: 'var(--text)', letterSpacing: '-0.01em' }}>Tamazight</span>}
          </button>
          <div style={{ display: 'flex', gap: compactNav ? '2px' : '4px', overflowX: 'auto', flex: 1, minWidth: 0, padding: '2px 0', scrollbarWidth: 'none' }}>
            {navLinks.map(l => (
              <button key={l.to} onClick={() => navigate(l.to)} title={l.label} aria-label={l.label}
                style={navBtn(l.to === '/' ? location.pathname === '/' : location.pathname.startsWith(l.to))}>
                <l.Icon size={compactNav ? 16 : 14} />{!compactNav && l.label}
              </button>
            ))}
          </div>
          <ReviewNavButton compact={compactNav} />
          <button onClick={() => setAiOpen(v => !v)} title="Copilot" aria-label="Copilot" style={{ flexShrink: 0, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', padding: compactNav ? '9px 10px' : '9px 12px', borderRadius: 'var(--r-pill)', cursor: 'pointer', border: 'none', background: aiOpen ? 'var(--brand-1)' : 'var(--brand-gradient)', color: '#fff' }}><FaComments size={15} /></button>
          <button onClick={() => navigate('/profile')} title="Perfil" aria-label="Perfil" style={{ flexShrink: 0, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', padding: compactNav ? '9px 10px' : '9px 12px', borderRadius: 'var(--r-pill)', cursor: 'pointer', border: '1px solid var(--border)', background: 'var(--surface)', color: 'var(--text-soft)' }}><FaUser size={15} /></button>
        </nav>
      )}

      <main style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
      <Suspense fallback={<RouteLoader />}>
      <Routes>
        <Route path="/" element={<DrillsResponsive />} />
        <Route path="/tests" element={<PracticePage />} />
        <Route path="/tests/sessio" element={<PracticeSession />} />
        <Route path="/tests/llistes" element={<TestsDashboard />} />
        <Route path="/tests/:testId" element={<PublicTestView />} />
        <Route path="/tests/:testId/listen" element={<PublicTestView initialView="listening" />} />
        <Route path="/shorts" element={<YouTubeShorts />} />
        <Route path="/video-creator" element={<VideoDrillCreator />} />
        <Route path="/srt-import" element={<SrtImport />} />
        <Route path="/player" element={<DrillPlayerPage />} />
        <Route path="/library" element={<VideoLibraryPage />} />
        <Route path="/profile" element={<ProfilePage />} />
        <Route path="/signin" element={<AuthPage />} />
        <Route path="/corpus" element={<CorpusPage />} />
        <Route path="/grammar" element={<GrammarPage />} />
        <Route path="/grammar/:slug" element={<GrammarPage />} />
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
