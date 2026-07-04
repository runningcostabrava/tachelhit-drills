import { useEffect, useState, lazy, Suspense } from 'react';
import { Network } from '@capacitor/network';
import axios from 'axios';
import { API_BASE } from './config';
import { api } from './api';
import { Routes, Route, useNavigate, useLocation } from 'react-router-dom';
import { syncManager } from './services/OfflineSyncManager';
import ToastHost from './components/ToastHost';
import AiCopilot from './components/AiCopilot';
import './App.css';

// Route-level code splitting: each page loads its chunk on first visit,
// keeping the initial bundle small (AG Grid, players, creators all split out)
const DrillsResponsive = lazy(() => import('./components/DrillsResponsive'));
const TestsDashboard = lazy(() => import('./components/TestsDashboard'));
const YouTubeShorts = lazy(() => import('./components/YouTubeShorts'));
const DrillPlayerPage = lazy(() => import('./components/DrillPlayerPage'));
const PublicTestView = lazy(() => import('./components/PublicTestView'));
const MediaRecorderTest = lazy(() => import('./components/MediaRecorderTest'));
const VideoDrillCreator = lazy(() => import('./components/VideoDrillCreator'));
const SrtImport = lazy(() => import('./components/SrtImport'));
const VideoLibraryPage = lazy(() => import('./components/VideoLibraryPage'));
const ProfilePage = lazy(() => import('./components/ProfilePage'));
const CorpusPage = lazy(() => import('./components/CorpusPage'));

const RouteLoader = () => (
  <div style={{ minHeight: '60vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
    <div style={{ width: '44px', height: '44px', borderRadius: '50%', border: '4px solid var(--border)', borderTopColor: 'var(--brand-1)', animation: 'spin 0.9s linear infinite' }} />
  </div>
);

// Spaced-repetition entry point in the top nav (saffron signature accent).
// Self-hides when there's nothing due or new to learn.
const ReviewNavButton = () => {
  const navigate = useNavigate();
  const [counts, setCounts] = useState<{ due: number; new: number } | null>(null);
  const [streak, setStreak] = useState(0);

  useEffect(() => {
    api.reviewStats().then(s => setCounts({ due: s.due, new: s.new })).catch(() => {});
    api.reviewStreak().then(s => setStreak(s.streak_days || 0)).catch(() => {});
  }, []);

  const pending = (counts?.due || 0) + (counts?.new || 0);
  if (!pending) return null;

  return (
    <button
      onClick={() => navigate('/player?mode=review')}
      title="Repàs espaiat"
      style={{
        flexShrink: 0, display: 'flex', alignItems: 'center', gap: '6px', whiteSpace: 'nowrap',
        padding: '8px 14px', background: 'var(--saffron)', color: '#fff',
        border: 'none', borderRadius: 'var(--r-pill)', fontWeight: 700, fontSize: '14px', cursor: 'pointer'
      }}
    >
      🧠 {counts!.due > 0 ? counts!.due : `${counts!.new} nous`}
      {streak > 0 && <span>🔥{streak}</span>}
    </button>
  );
};

// Placeholder component for /demo-videos
const DemoVideosPage = () => (
  <div style={{ padding: '20px', textAlign: 'center' }}>
    <h1>Demo Videos</h1>
    <p>This page will contain various demo videos.</p>
    {/* You can add more content here later */}
  </div>
);

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
  const showNav = !location.pathname.startsWith('/player') && !/^\/tests\/\d/.test(location.pathname);
  const navLinks = [
    { to: '/', label: 'Drills', icon: '📚' },
    { to: '/video-creator', label: 'Captura', icon: '🎬' },
    { to: '/corpus', label: 'Corpus', icon: '📖' },
    { to: '/tests', label: 'Tests', icon: '📝' },
    { to: '/shorts', label: 'Reels', icon: '🎞️' },
  ];
  const navBtn = (active: boolean): React.CSSProperties => ({
    flexShrink: 0, padding: '8px 14px', borderRadius: 'var(--r-pill)', fontWeight: 700, fontSize: '14px',
    cursor: 'pointer', border: '1px solid transparent', whiteSpace: 'nowrap',
    background: active ? 'var(--brand-gradient-soft)' : 'transparent',
    color: active ? 'var(--brand-1)' : 'var(--text-soft)',
  });

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <ToastHost />
      {aiOpen && <AiCopilot onClose={() => setAiOpen(false)} />}

      {showNav && (
        <nav style={{
          position: 'sticky', top: 0, zIndex: 1000, background: 'var(--surface)',
          borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', gap: '10px',
          padding: '10px 14px', boxShadow: '0 1px 3px rgba(15,23,42,0.04)'
        }}>
          <button onClick={() => navigate('/')} style={{ flexShrink: 0, display: 'flex', alignItems: 'center', gap: '8px', background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}>
            <span style={{ width: '30px', height: '30px', borderRadius: '9px', background: 'var(--brand-gradient)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '16px' }}>ⵣ</span>
            <span style={{ fontWeight: 800, fontSize: '16px', color: 'var(--text)', letterSpacing: '-0.01em' }}>Tamazight</span>
          </button>
          <div style={{ display: 'flex', gap: '4px', overflowX: 'auto', flex: 1, minWidth: 0, padding: '2px 0', scrollbarWidth: 'none' }}>
            {navLinks.map(l => (
              <button key={l.to} onClick={() => navigate(l.to)}
                style={navBtn(l.to === '/' ? location.pathname === '/' : location.pathname.startsWith(l.to))}>
                <span style={{ marginRight: '5px' }}>{l.icon}</span>{l.label}
              </button>
            ))}
          </div>
          <ReviewNavButton />
          <button onClick={() => setAiOpen(v => !v)} title="Copilot IA" style={{ flexShrink: 0, padding: '8px 12px', borderRadius: 'var(--r-pill)', fontWeight: 700, fontSize: '14px', cursor: 'pointer', border: 'none', background: aiOpen ? 'var(--brand-1)' : 'var(--brand-gradient)', color: '#fff' }}>🤖</button>
          <button onClick={() => navigate('/profile')} title="Perfil" style={{ flexShrink: 0, padding: '8px 12px', borderRadius: 'var(--r-pill)', fontWeight: 700, fontSize: '14px', cursor: 'pointer', border: '1px solid var(--border)', background: 'var(--surface)', color: 'var(--text)' }}>👤</button>
        </nav>
      )}

      <Suspense fallback={<RouteLoader />}>
      <Routes>
        <Route path="/" element={<DrillsResponsive />} />
        <Route path="/tests" element={<TestsDashboard />} />
        <Route path="/tests/:testId" element={<PublicTestView />} />
        <Route path="/shorts" element={<YouTubeShorts />} />
        <Route path="/video-creator" element={<VideoDrillCreator />} />
        <Route path="/srt-import" element={<SrtImport />} />
        <Route path="/player" element={<DrillPlayerPage />} />
        <Route path="/media-test" element={<MediaRecorderTest />} />
        <Route path="/demo-videos" element={<DemoVideosPage />} />
        <Route path="/library" element={<VideoLibraryPage />} />
        <Route path="/profile" element={<ProfilePage />} />
        <Route path="/corpus" element={<CorpusPage />} />
      </Routes>
      </Suspense>
    </div>
  );
}

export default App;
