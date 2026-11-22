import { useState, useEffect } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { Network } from '@capacitor/network';
import { syncManager } from '../services/OfflineSyncManager';
import TestTaking from './TestTaking';
import TestEditPanel from './TestEditPanel';
import TestConfigPanel from './TestConfigPanel';
import TestsGallery from './TestsGallery';
import { useIsMobileLayout } from '../utils/layout';
import DrillPlayer from './DrillPlayer';
import VideoLoopPlayer from './VideoLoopPlayer';
import { API_BASE, hasIdentity } from '../config';
import { toast } from '../toast';
import { FaPlus, FaDumbbell } from 'react-icons/fa';


export interface Test {
  id: number;
  title: string;
  description?: string;
  date_created: string;
  question_type: string;
  hint_level: string;
  hint_percentage?: number;
  hint_tries_before_reveal?: number;
  time_limit_seconds?: number;
  passing_score: number;
  video_url?: string;
  drill_ids: string;
  /** How many steps it holds. The server works it out; `drill_ids` is only the fallback. */
  step_count?: number | null;
}

interface TestStats {
  total_attempts: number;
  average_score: number;
  completion_rate: number;
  average_time: number;
  passed_attempts: number;
}

export default function TestsDashboard() {
  const isMobile = useIsMobileLayout();
  const navigate = useNavigate();
  const [showCreate, setShowCreate] = useState(false);
  const [tests, setTests] = useState<Test[]>([]);
  const [selectedTest, setSelectedTest] = useState<Test | null>(null);
  const [stats, setStats] = useState<TestStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [takingTestId, setTakingTestId] = useState<number | null>(null);
  const [editingTestId, setEditingTestId] = useState<number | null>(null);
  const [playingDrills, setPlayingDrills] = useState<any[] | null>(null);
  const [generatingDemoVideoId, setGeneratingDemoVideoId] = useState<number | null>(null);
  const [viewingVideoUrl, setViewingVideoUrl] = useState<string | null>(null);


  useEffect(() => {
    fetchTests();
  }, []);

  const fetchTests = async (testIdToRefresh?: number) => {
    try {
      const status = await Network.getStatus();

      if (testIdToRefresh) {
        if (status.connected) {
          const response = await axios.get(`${API_BASE}/tests/${testIdToRefresh}`);
          setTests(prevTests =>
            prevTests.map(test => (test.id === testIdToRefresh ? response.data : test))
          );
          if (selectedTest?.id === testIdToRefresh) {
            setSelectedTest(response.data);
          }
        }
      } else {
        if (status.connected) {
          // «Les meves llistes»: the practices this person may change. Without `mine` the screen
          // showed everyone's, offered a Delete that came back 403, and nobody could tell which
          // were theirs. Without a name there are none, and that is what we say.
          if (!hasIdentity()) { setTests([]); setLoading(false); return; }
          const response = await axios.get(`${API_BASE}/tests/`, { params: { mine: 1 } });
          setTests(response.data);
          await syncManager.saveTestsToCache(response.data);
        } else {
          const cachedTests = await syncManager.getTests();
          setTests(cachedTests);
        }
      }
      setLoading(false);
    } catch (error) {
      console.error('Error fetching tests, using cache:', error);
      const cachedTests = await syncManager.getTests();
      setTests(cachedTests);
      setLoading(false);
    }
  };

  const startPollingForDemoVideo = (testId: number) => {
    setGeneratingDemoVideoId(testId);
    const interval = setInterval(async () => {
      try {
        const response = await axios.get(`${API_BASE}/tests/${testId}`);
        const updatedTest = response.data;
        if (updatedTest.video_url) {
          clearInterval(interval);
          setGeneratingDemoVideoId(null);
          setTests(prevTests =>
            prevTests.map(test => (test.id === testId ? updatedTest : test))
          );
          setSelectedTest(updatedTest);
          // No alert or window.open, just update the state
        }
      } catch (error) {
        console.error('Error polling for demo video:', error);
        clearInterval(interval);
        setGeneratingDemoVideoId(null);
        toast.error('No s\'ha pogut obtenir l\'estat del vídeo de demostració. Torna-ho a provar o revisa els registres.');
      }
    }, 10000); // Poll every 10 seconds

    // Optional: Add a timeout to stop polling after a certain period (e.g., 5 minutes)
    setTimeout(() => {
      if (generatingDemoVideoId === testId) {
        clearInterval(interval);
        setGeneratingDemoVideoId(null);
        toast.error('La generació del vídeo de demostració està trigant més del que s\'esperava. Torna-hi més tard.');
      }
    }, 5 * 60 * 1000); // 5 minutes timeout
  };

  const fetchStats = async (testId: number) => {
    try {
      const status = await Network.getStatus();
      if (!status.connected) return;

      const response = await axios.get(`${API_BASE}/tests/${testId}/stats`);
      setStats(response.data);
    } catch (error) {
      console.error('Error fetching stats:', error);
    }
  };

  const handleDeleteTest = async (testId: number) => {
    if (!confirm('Segur que vols eliminar aquest test?')) return;

    try {
      await axios.delete(`${API_BASE}/tests/${testId}`);
      setTests(tests.filter(t => t.id !== testId));
      if (selectedTest?.id === testId) {
        setSelectedTest(null);
        setStats(null);
      }
      toast.success('Test eliminat correctament!');
    } catch (error) {
      console.error('Error deleting test:', error);
      toast.error('No s\'ha pogut eliminar el test');
    }
  };

  const getQuestionTypeLabel = (type: string) => {
    const labels: any = {
      'text_input': 'Entrada de text',
      'audio': 'Reconeixement d\'àudio',
      'video': 'Vídeo'
    };
    return labels[type] || type;
  };

  const getHintLevelLabel = (level: string) => {
    const labels: any = {
      'none': 'Sense pistes',
      'partial': 'Lletres parcials',
      'full_after_tries': 'Revelació completa després d\'intents'
    };
    return labels[level] || level;
  };

  if (loading) {
    return (
      <div style={{
        height: '100vh',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '16px',
        background: 'var(--bg)',
        color: 'var(--text-soft)',
        fontFamily: 'var(--font-sans)'
      }}>
        <div className="spinner" style={{
          border: '4px solid var(--border)',
          width: '40px',
          height: '40px',
          borderRadius: '50%',
          borderLeftColor: 'var(--brand-1)',
          animation: 'spin 1s linear infinite'
        }}></div>
        <p style={{ margin: 0, fontSize: '16px', fontWeight: 600 }}>Carregant els tests…</p>
      </div>
    );
  }

  // If taking a test, show the test-taking interface
  if (takingTestId !== null) {
    return (
      <TestTaking
        testId={takingTestId}
        onExit={() => {
          setTakingTestId(null);
          fetchTests(); // Refresh to get updated stats
          if (selectedTest) {
            fetchStats(selectedTest.id); // Refresh stats for current test
          }
        }}
      />
    );
  }

  // If playing drills, show the drill player
  if (playingDrills !== null) {
    return (
      <DrillPlayer
        drills={playingDrills}
        onExit={() => {
          setPlayingDrills(null);
        }}
      />
    );
  }

  if (viewingVideoUrl) {
    return <VideoLoopPlayer videoUrl={viewingVideoUrl} onBack={() => setViewingVideoUrl(null)} />;
  }

  if (showCreate) {
    return (
      <TestConfigPanel
        onClose={() => setShowCreate(false)}
        onTestCreated={async () => { setShowCreate(false); await fetchTests(); }}
      />
    );
  }

  return (
    <div className="app-page-fixed" style={{ display: 'flex', flexDirection: 'column', background: 'var(--bg)', fontFamily: 'var(--font-sans)' }}>
      {/* Header */}
      <div style={{
        padding: '16px 24px',
        background: 'var(--surface)',
        borderBottom: '1px solid var(--border)',
        display: 'flex',
        alignItems: 'center',
        gap: '16px',
        flexWrap: 'wrap'
      }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
          <h1 style={{
            margin: 0,
            fontFamily: 'var(--font-display)',
            fontSize: '22px',
            fontWeight: 700,
            color: 'var(--text)',
            letterSpacing: '-0.02em'
          }}>
            Tests
          </h1>
          <span style={{ color: 'var(--text-soft)', fontSize: '14px', fontWeight: 500 }}>
            Gestiona tests i comença a practicar
          </span>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          aria-label="Nou test"
          style={{ marginLeft: 'auto', padding: '10px 16px', background: 'var(--brand-1)', color: '#fff', border: 'none', borderRadius: 'var(--r-md)', fontSize: '14px', fontWeight: 700, cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: '8px', minHeight: '44px' }}
        >
          <FaPlus /> {isMobile ? 'Nou' : 'Nou test'}
        </button>
        <button
          onClick={async () => {
            try {
              const res = await axios.post(`${API_BASE}/tests/from-weakest`, { count: 10 });
              await fetchTests();
              toast.success(`💪 ${res.data.title}: ${res.data.drill_count} preguntes creades!`);
            } catch (e: any) {
              toast.error(e?.response?.data?.detail || 'No s\'ha pogut crear el test');
            }
          }}
          title="Crea un test automàtic amb les teves targetes més difícils (SRS)"
          style={{
            marginLeft: '8px',
            padding: '8px 16px',
            background: 'var(--saffron-soft)',
            color: 'var(--saffron-strong)',
            border: '1px solid var(--saffron)',
            borderRadius: 'var(--r-pill)',
            fontWeight: 700,
            fontSize: '13px',
            cursor: 'pointer'
          }}
        >
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}><FaDumbbell /> Test dels punts febles</span>
        </button>
        <span style={{
          color: 'var(--text-soft)',
          fontSize: '13px',
          fontWeight: 700,
          padding: '6px 14px',
          background: 'var(--surface-2)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--r-pill)'
        }}>
          {tests.length} {tests.length === 1 ? 'test' : 'tests'}
        </span>
      </div>

      {/* A practice belongs to whoever made it, so without a name there are none to manage. */}
      {!hasIdentity() && !loading && (
        <p style={{ color: 'var(--text-soft)', fontSize: '14px', margin: '0 0 16px' }}>
          Aquí hi ha les pràctiques que has fet tu. Per tenir-ne, fes-te un nom al teu perfil:
          és gratis, triga un moment, i és el que fa que les puguis tornar a obrir i canviar.
        </p>
      )}

      {/* Content: a gallery of tests (one card per test, with a picture) and a detail sheet */}
      <TestsGallery
        tests={tests}
        selectedTest={selectedTest}
        stats={stats}
        isMobile={isMobile}
        generatingDemoVideoId={generatingDemoVideoId}
        onSelect={(t) => { setSelectedTest(t); setStats(null); if (t) fetchStats(t.id); }}
        onTake={(t) => setTakingTestId(t.id)}
        onListen={(t) => navigate(`/tests/${t.id}/listen`)}
        // One place edits a practice, and it is the workshop. The old panel edits the flat
        // list of ids a practice used to be, which is a different thing wearing the same name.
        onEdit={(t) => navigate(`/tests/${t.id}/editor`)}
        onPlayDrills={async (t) => {
          const drillIds = t.drill_ids.split(',').map((id: string) => parseInt(id));
          try {
            const drillsResponse = await axios.get(`${API_BASE}/drills/`, { params: { ids: drillIds.join(',') } });
            setPlayingDrills(drillsResponse.data);
          } catch (error) {
            console.error('Error loading drills:', error);
            toast.error('No s\'han pogut carregar els drills');
          }
        }}
        onMakeVideo={async (t) => {
          if (!confirm('Això generarà un vídeo de demostració que mostra la interfície del reproductor de drills per a aquest test. Pot trigar uns quants minuts. Vols continuar?')) return;
          try {
            setGeneratingDemoVideoId(t.id);
            const response = await axios.post(`${API_BASE}/generate-drillplayer-demo/${t.id}`);
            toast.success(response.data.message || 'S\'ha iniciat la generació del vídeo. Comprovant si ha acabat...');
            startPollingForDemoVideo(t.id);
          } catch (error: any) {
            setGeneratingDemoVideoId(null);
            toast.error(error?.response?.data?.detail || 'No s\'ha pogut iniciar la generació del vídeo');
          }
        }}
        onViewVideo={(url) => setViewingVideoUrl(url)}
        onDelete={(t) => handleDeleteTest(t.id)}
        onCreate={() => setShowCreate(true)}
        questionTypeLabel={getQuestionTypeLabel}
        hintLevelLabel={getHintLevelLabel}
      />

      {/* Test Edit Panel */}
      {editingTestId !== null && (
        <TestEditPanel
          testId={editingTestId}
          onClose={() => setEditingTestId(null)}
          onTestUpdated={() => {
            fetchTests();
            if (selectedTest) {
              fetchStats(selectedTest.id);
            }
          }}
        />
      )}
    </div>
  );
}
