import { useState } from 'react';
import DrillsResponsive from './components/DrillsResponsive';
import TestsDashboard from './components/TestsDashboard';
import YouTubeShorts from './components/YouTubeShorts';
import DrillPlayer from './components/DrillPlayer';
import MediaRecorderTest from './components/MediaRecorderTest';
import './App.css'; // optional – you can remove this line

// Datos de ejemplo para drills
const sampleDrills = [
  {
    id: 1,
    text_catalan: 'Hola',
    text_tachelhit: 'Azul',
    text_arabic: 'مرحبا',
    audio_url: '/media/audio/hola.mp3',
    video_url: '',
    image_url: '/media/images/hola.jpg',
    tag: 'saludo',
    date_created: '2024-01-01'
  },
  {
    id: 2,
    text_catalan: 'Com estàs?',
    text_tachelhit: 'Manik ayt?',
    text_arabic: 'كيف حالك؟',
    audio_url: '/media/audio/com_estas.mp3',
    video_url: '',
    image_url: '/media/images/com_estas.jpg',
    tag: 'saludo',
    date_created: '2024-01-02'
  },
  {
    id: 3,
    text_catalan: 'Gràcies',
    text_tachelhit: 'Tanmirt',
    text_arabic: 'شكرا',
    audio_url: '/media/audio/gracies.mp3',
    video_url: '',
    image_url: '/media/images/gracies.jpg',
    tag: 'cortesia',
    date_created: '2024-01-03'
  }
];

function App() {
  const [view, setView] = useState<'drills' | 'tests' | 'shorts' | 'player' | 'mediaTest'>('drills');

  // Si estamos en la vista de drills, mostrar un botón para abrir el DrillPlayer
  const renderDrillsView = () => {
    return (
      <div style={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
        <DrillsResponsive
          onViewTests={() => setView('tests')}
          onViewShorts={() => setView('shorts')}
        />
        <div style={{ 
          padding: '20px', 
          background: '#f5f5f5', 
          borderTop: '1px solid #ddd',
          display: 'flex',
          justifyContent: 'center',
          gap: '10px'
        }}>
          <button
            onClick={() => setView('player')}
            style={{
              padding: '10px 20px',
              background: '#4CAF50',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer',
              fontSize: '16px'
            }}
          >
            🎵 Abrir Drill Player (Demo)
          </button>
          <button
            onClick={() => setView('tests')}
            style={{
              padding: '10px 20px',
              background: '#2196F3',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer',
              fontSize: '16px'
            }}
          >
            📝 Tests
          </button>
          <button
            onClick={() => setView('shorts')}
            style={{
              padding: '10px 20px',
              background: '#9C27B0',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer',
              fontSize: '16px'
            }}
          >
            🎬 Shorts
          </button>
          <button
            onClick={() => setView('mediaTest')}
            style={{
              padding: '10px 20px',
              background: '#f44336',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer',
              fontSize: '16px'
            }}
          >
            🎤 Media Test
          </button>
        </div>
      </div>
    );
  };

  return (
    <div style={{ height: '100vh' }}>
      {view === 'drills' && renderDrillsView()}
      {view === 'tests' && (
        <TestsDashboard onBackToDrills={() => setView('drills')} />
      )}
      {view === 'shorts' && (
        <YouTubeShorts onBackToDrills={() => setView('drills')} />
      )}
      {view === 'player' && (
        <DrillPlayer 
          drills={sampleDrills} 
          onExit={() => setView('drills')} 
        />
      )}
      {view === 'mediaTest' && (
        <MediaRecorderTest />
      )}
    </div>
  );
}

export default App;
