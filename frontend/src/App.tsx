import { useEffect, useState, lazy, Suspense } from 'react';
import { Network } from '@capacitor/network';
import axios from 'axios';
import { API_BASE, getUserName, getUserToken } from './config';
import { api } from './api';
import { Routes, Route, useNavigate, useLocation } from 'react-router-dom';
import { syncManager } from './services/OfflineSyncManager';
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

// Floating spaced-repetition entry point, shown on the home screen when
// there are cards due or new drills to learn
const ReviewFab = () => {
  const navigate = useNavigate();
  const [counts, setCounts] = useState<{ due: number; new: number } | null>(null);
  const [streak, setStreak] = useState(0);

  useEffect(() => {
    api.reviewStats()
      .then(s => setCounts({ due: s.due, new: s.new }))
      .catch(() => {});
    api.reviewStreak()
      .then(s => setStreak(s.streak_days || 0))
      .catch(() => {});
  }, []);

  const pending = (counts?.due || 0) + (counts?.new || 0);
  if (!pending) return null;

  return (
    <button
      onClick={() => navigate('/player?mode=review')}
      style={{
        position: 'fixed', bottom: '86px', right: '16px', zIndex: 900,
        padding: '13px 20px', background: 'var(--brand-gradient)', color: 'white',
        border: 'none', borderRadius: 'var(--r-pill)', fontWeight: 800, fontSize: '15px',
        boxShadow: 'var(--shadow-brand)', cursor: 'pointer',
        display: 'flex', alignItems: 'center', gap: '8px'
      }}
    >
      🧠 Repàs {counts!.due > 0 ? `(${counts!.due})` : `(${counts!.new} nous)`}
      {streak > 0 && <span style={{ marginLeft: '4px' }}>🔥{streak}</span>}
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


  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      {location.pathname === '/' && <ReviewFab />}
      {location.pathname === '/' && (
        <button
          onClick={() => navigate('/profile')}
          title={getUserToken() ? 'El teu perfil' : 'Crea el teu compte'}
          style={{
            position: 'fixed', top: '12px', right: '12px', zIndex: 900,
            padding: '9px 14px', background: 'var(--surface)', color: 'var(--text)',
            border: '1px solid var(--border)', borderRadius: 'var(--r-pill)',
            fontWeight: 700, fontSize: '14px', boxShadow: 'var(--shadow-sm)', cursor: 'pointer'
          }}
        >
          👤 {getUserName() || 'Entra'}
        </button>
      )}
      {location.pathname === '/' && (
        <button
          onClick={() => navigate('/corpus')}
          title="Explora i revisa el corpus"
          style={{
            position: 'fixed', top: '12px', right: '110px', zIndex: 900,
            padding: '9px 14px', background: 'var(--surface)', color: 'var(--text)',
            border: '1px solid var(--border)', borderRadius: 'var(--r-pill)',
            fontWeight: 700, fontSize: '14px', boxShadow: 'var(--shadow-sm)', cursor: 'pointer'
          }}
        >
          📖 Corpus
        </button>
      )}
      <Suspense fallback={<RouteLoader />}>
      <Routes>
        <Route path="/" element={<DrillsResponsive />} />
        <Route path="/tests" element={<TestsDashboard onBackToDrills={() => navigate('/')} />} />
        <Route path="/tests/:testId" element={<PublicTestView />} />
        <Route path="/shorts" element={<YouTubeShorts onBackToDrills={() => navigate('/')} />} />
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
