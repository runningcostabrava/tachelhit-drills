import { Routes, Route, useNavigate } from 'react-router-dom'; // Added imports
import DrillsResponsive from './components/DrillsResponsive';
import TestsDashboard from './components/TestsDashboard';
import YouTubeShorts from './components/YouTubeShorts';
import DrillPlayer from './components/DrillPlayer'; // Assuming this is used for a specific drill player route
import PublicTestView from './components/PublicTestView'; // Added import
import MediaRecorderTest from './components/MediaRecorderTest';
import VideoDrillCreator from './components/VideoDrillCreator'; // Added import
import './App.css'; // optional – you can remove this line

// Placeholder component for /demo-videos
const DemoVideosPage = () => (
  <div style={{ padding: '20px', textAlign: 'center' }}>
    <h1>Demo Videos</h1>
    <p>This page will contain various demo videos.</p>
    {/* You can add more content here later */}
  </div>
);

function App() {
  const navigate = useNavigate(); // Initialize useNavigate hook

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}> {/* minHeight here too */}
      <Routes>
        <Route path="/" element={<DrillsResponsive />} />
        <Route path="/tests" element={<TestsDashboard onBackToDrills={() => navigate('/')} />} />
        <Route path="/tests/:testId" element={<PublicTestView />} /> {/* Updated route */}
        <Route path="/shorts" element={<YouTubeShorts onBackToDrills={() => navigate('/')} />} />
        <Route path="/video-creator" element={<VideoDrillCreator />} /> {/* New route for video creator */}
        {/*
          TODO: This DrillPlayer needs to be updated to take drill data dynamically,
          or a test ID. For now, it's a placeholder.
        */}
        <Route path="/player" element={
          <DrillPlayer
            drills={[]} // Needs dynamic data
            onExit={() => navigate('/')}
          />
        } />
        <Route path="/media-test" element={<MediaRecorderTest />} />
        <Route path="/demo-videos" element={<DemoVideosPage />} /> {/* New route for demo videos */}
      </Routes>
    </div>
  );
}

export default App;
