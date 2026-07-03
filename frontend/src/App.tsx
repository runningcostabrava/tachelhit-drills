import { useEffect } from 'react';
import { Network } from '@capacitor/network';
import axios from 'axios';
import { API_BASE } from './config';
import { Routes, Route, useNavigate } from 'react-router-dom';
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
import './App.css';

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
      </Routes>
    </div>
  );
}

export default App;
