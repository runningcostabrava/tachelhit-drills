import { useEffect, useState } from 'react';
import { Network } from '@capacitor/network';
import axios from 'axios';
import { API_BASE } from './config';
import { Routes, Route, useNavigate, useLocation } from 'react-router-dom';
import { syncManager } from './services/OfflineSyncManager';
import DrillsResponsive from './components/DrillsResponsive';
import TestsDashboard from './components/TestsDashboard';
import YouTubeShorts from './components/YouTubeShorts';
import DrillPlayerPage from './components/DrillPlayerPage';
import PublicTestView from './components/PublicTestView';
import MediaRecorderTest from './components/MediaRecorderTest';
import VideoDrillCreator from './components/VideoDrillCreator';
import SrtImport from './components/SrtImport';
import VideoLibraryPage from './components/VideoLibraryPage';
import ProfilePage from './components/ProfilePage';
import CorpusPage from './components/CorpusPage';
import { getUserName, getUserToken } from './config';
import './App.css';

// Floating spaced-repetition entry point, shown on the home screen when
// there are cards due or new drills to learn
const ReviewFab = () => {
  const navigate = useNavigate();
  const [counts, setCounts] = useState<{ due: number; new: number } | null>(null);

  useEffect(() => {
    axios.get(`${API_BASE}/reviews/stats`)
      .then(r => setCounts({ due: r.data.due, new: r.data.new }))
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
    </div>
  );
}

export default App;
