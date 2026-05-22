import { useEffect } from 'react';
import { Network } from '@capacitor/network';
import { Filesystem, Directory } from '@capacitor/filesystem';
import axios from 'axios';
import { API_BASE } from './config';
import { Routes, Route, useNavigate } from 'react-router-dom';
import { syncManager } from './services/OfflineSyncManager';
import DrillsResponsive from './components/DrillsResponsive';
import TestsDashboard from './components/TestsDashboard';
import YouTubeShorts from './components/YouTubeShorts';
import DrillPlayer from './components/DrillPlayer';
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

  // THE OFFLINE SYNC LOGIC
  useEffect(() => {
    const processSyncQueue = async () => {
      const status = await Network.getStatus();

      // Ensure cache is updated even if no queue
      if (status.connected) {
        try {
          const drillsRes = await axios.get(`${API_BASE}/drills/`);
          await syncManager.saveDrillsToCache(drillsRes.data);
          const testsRes = await axios.get(`${API_BASE}/tests/`);
          await syncManager.saveTestsToCache(testsRes.data);
          // Sync audio & images only by default (videos are typically large and can be cached on-demand)
          syncManager.syncAllMedia({ includeVideos: false });
        } catch (e) {
          console.error('Failed to pre-cache data', e);
        }
      }

      // Only attempt sync if we have internet connection
      if (!status.connected) {
        console.log("✈️ Device is offline. Sync paused.");
        return;
      }

      // 1. Grab the pending drills from local storage
      const queue = JSON.parse(localStorage.getItem('sync_queue') || '[]');
      if (queue.length === 0) return;

      console.log(`🔄 Internet detected! Starting background sync for ${queue.length} drills...`);

      // Update tests cache and media
      try {
        const testsRes = await axios.get(`${API_BASE}/tests/`);
        await syncManager.saveTestsToCache(testsRes.data);
        // Sync audio & images only (videos are large and should be cached on-demand)
        syncManager.syncAllMedia({ includeVideos: false });
      } catch (e) { console.error('Failed to sync tests cache', e); }

      // 2. Process each drill one by one
      for (const drill of queue) {
        try {
          // Note: If drill.id is a timestamp (large number), it's a new drill created offline
          const isNewOfflineDrill = drill.id > 1000000;
          let serverDrillId = drill.id;

          // Step A: Sync Text Data
          if (isNewOfflineDrill) {
            // Create a totally new drill on the server
            const { id, ...drillWithoutTempId } = drill; // Remove the fake ID
            const res = await axios.post(`${API_BASE}/drills/`, drillWithoutTempId);
            serverDrillId = res.data.id;
          } else {
            // Update an existing drill on the server
            await axios.put(`${API_BASE}/drills/${drill.id}`, drill);
          }

          // Step B: Sync Media Files (If they exist)
          const mediaFields = ['audio_url', 'video_url', 'image_url'] as const;

          for (const field of mediaFields) {
            const localUri = drill[field];

            // If it starts with file://, we know it's a local file that needs uploading
            if (localUri && localUri.startsWith('file://')) {

              // Extract the filename from the path
              const pathParts = localUri.split('/');
              const fileName = pathParts[pathParts.length - 1];

              // Read the file off the phone's hard drive
              const fileData = await Filesystem.readFile({
                path: `drills_media/${fileName}`,
                directory: Directory.Data
              });

              // Convert the base64 back into a Blob so Axios can send it as a file
              const res = await fetch(`data:application/octet-stream;base64,${fileData.data}`);
              const blob = await res.blob();

              // Determine type for the endpoint url
              const typeMap: Record<string, string> = {
                'audio_url': 'audio',
                'video_url': 'video',
                'image_url': 'image'
              };

              const formData = new FormData();
              formData.append('file', blob, fileName);

              console.log(`⬆️ Uploading ${typeMap[field]} to server...`);
              await axios.post(`${API_BASE}/upload-media/${serverDrillId}/${typeMap[field]}`, formData);

              // Clean up: Delete the local file now that it's safe in Cloudinary
              await Filesystem.deleteFile({
                path: `drills_media/${fileName}`,
                directory: Directory.Data
              });
            }
          }

          // Step C: Remove this drill from the queue now that it is synced
          const updatedQueue = JSON.parse(localStorage.getItem('sync_queue') || '[]');
          const filteredQueue = updatedQueue.filter((d: any) => d.id !== drill.id);
          localStorage.setItem('sync_queue', JSON.stringify(filteredQueue));

          console.log(`✅ Drill ${drill.id} successfully synced and removed from queue.`);

        } catch (err) {
          console.error(`❌ Failed to sync drill ${drill.id}:`, err);
          // It stays in the queue to try again next time
        }
      }
    };

    // Run sync immediately when the app boots
    processSyncQueue();

    // Also listen for network changes (e.g., turning off Airplane mode) and trigger sync
    const listener = Network.addListener('networkStatusChange', status => {
      if (status.connected) {
        processSyncQueue();
      }
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
        <Route path="/player" element={
          <DrillPlayer
            drills={[]} // Needs dynamic data
            onExit={() => navigate('/')}
          />
        } />
        <Route path="/media-test" element={<MediaRecorderTest />} />
        <Route path="/demo-videos" element={<DemoVideosPage />} />
        <Route path="/library" element={<VideoLibraryPage />} />
      </Routes>
    </div>
  );
}

export default App;
