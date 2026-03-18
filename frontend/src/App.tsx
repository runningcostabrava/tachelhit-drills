import { Routes, Route, useNavigate } from 'react-router-dom';
import DrillsResponsive from './components/DrillsResponsive';
import TestsDashboard from './components/TestsDashboard';
import YouTubeShorts from './components/YouTubeShorts';
import DrillPlayer from './components/DrillPlayer';
import PublicTestView from './components/PublicTestView';
import MediaRecorderTest from './components/MediaRecorderTest';
import VideoDrillCreator from './components/VideoDrillCreator';
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

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <Routes>
        <Route path="/" element={<DrillsResponsive />} />
        <Route path="/tests" element={<TestsDashboard onBackToDrills={() => navigate('/')} />} />
        <Route path="/tests/:testId" element={<PublicTestView />} />
        <Route path="/shorts" element={<YouTubeShorts onBackToDrills={() => navigate('/')} />} />
        <Route path="/video-creator" element={<VideoDrillCreator />} />
        <Route path="/player" element={
          <DrillPlayer
            drills={[]} // Needs dynamic data
            onExit={() => navigate('/')}
          />
        } />
        <Route path="/media-test" element={<MediaRecorderTest />} />
        <Route path="/demo-videos" element={<DemoVideosPage />} />
      </Routes>
    </div>
  );
}

export default App;
