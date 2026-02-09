import { useState } from 'react';
import DrillsResponsive from './components/DrillsResponsive';
import TestsDashboard from './components/TestsDashboard';
import YouTubeShorts from './components/YouTubeShorts';
import './App.css'; // optional – you can remove this line

function App() {
  const [view, setView] = useState<'drills' | 'tests' | 'shorts'>('drills');

  return (
    <div style={{ height: '100vh' }}>
      {view === 'drills' && (
        <DrillsResponsive
          onViewTests={() => setView('tests')}
          onViewShorts={() => setView('shorts')}
        />
      )}
      {view === 'tests' && (
        <TestsDashboard onBackToDrills={() => setView('drills')} />
      )}
      {view === 'shorts' && (
        <YouTubeShorts onBackToDrills={() => setView('drills')} />
      )}
    </div>
  );
}

export default App;