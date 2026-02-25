import { useState, useEffect } from 'react';
import axios from 'axios';
import { useParams, useNavigate } from 'react-router-dom';
import { API_BASE } from '../config';
import TestTaking from './TestTaking';
import DrillPlayer from './DrillPlayer';

interface Test {
  id: number;
  title: string;
  description?: string;
  drill_ids: string;
}

export default function PublicTestView() {
  const { testId } = useParams<{ testId: string }>();
  const navigate = useNavigate();
  const [test, setTest] = useState<Test | null>(null);
  const [drills, setDrills] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState<'landing' | 'taking' | 'playing'>('landing');

  useEffect(() => {
    const fetchData = async () => {
      try {
        const testRes = await axios.get(`${API_BASE}/tests/${testId}`);
        setTest(testRes.data);

        const drillIds = testRes.data.drill_ids.split(',').map((id: string) => parseInt(id));
        const drillsRes = await axios.get(`${API_BASE}/drills/`);
        const testDrills = drillsRes.data.filter((d: any) => drillIds.includes(d.id));
        setDrills(testDrills);
        
        setLoading(false);
      } catch (error) {
        console.error('Error fetching test data:', error);
        setLoading(false);
      }
    };
    if (testId) fetchData();
  }, [testId]);

  if (loading) return <div style={{ padding: '40px', textAlign: 'center' }}>Loading test...</div>;
  if (!test) return <div style={{ padding: '40px', textAlign: 'center' }}>Test not found.</div>;

  if (view === 'taking') {
    return <TestTaking testId={test.id} onExit={() => setView('landing')} />;
  }

  if (view === 'playing') {
    return <DrillPlayer drills={drills} onExit={() => setView('landing')} />;
  }

  return (
    <div style={{ 
      minHeight: '100vh', 
      display: 'flex', 
      flexDirection: 'column',
      background: '#f5f7fa'
    }}>
      {/* Header */}
      <div style={{
        padding: '16px 20px',
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        color: 'white',
        display: 'flex',
        alignItems: 'center',
        gap: '15px',
        boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
      }}>
        <button 
          onClick={() => navigate('/')}
          style={{
            background: 'rgba(255,255,255,0.2)',
            border: '1px solid rgba(255,255,255,0.4)',
            color: 'white',
            padding: '6px 12px',
            borderRadius: '6px',
            cursor: 'pointer',
            fontSize: '14px',
            fontWeight: 600
          }}
        >
          ← Home
        </button>
        <h1 style={{ margin: 0, fontSize: '20px', fontWeight: 700 }}>Tachelhit Drills</h1>
      </div>

      {/* Main Content */}
      <div style={{ 
        flex: 1, 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'center',
        padding: '20px'
      }}>
        <div style={{
          background: 'white',
          padding: '40px',
          borderRadius: '16px',
          boxShadow: '0 10px 25px rgba(0,0,0,0.05)',
          width: '100%',
          maxWidth: '500px',
          textAlign: 'center'
        }}>
          <div style={{ fontSize: '50px', marginBottom: '20px' }}>📊</div>
          <h2 style={{ margin: '0 0 10px 0', fontSize: '28px', color: '#333' }}>{test.title}</h2>
          {test.description && (
            <p style={{ margin: '0 0 30px 0', color: '#666', lineHeight: 1.5 }}>
              {test.description}
            </p>
          )}

          <div style={{ 
            display: 'flex', 
            flexDirection: 'column', 
            gap: '15px' 
          }}>
            <button
              onClick={() => setView('taking')}
              style={{
                padding: '16px 24px',
                fontSize: '18px',
                background: '#4CAF50',
                color: 'white',
                border: 'none',
                borderRadius: '12px',
                cursor: 'pointer',
                fontWeight: 700,
                boxShadow: '0 4px 12px rgba(76, 175, 80, 0.3)',
                transition: 'transform 0.2s'
              }}
              onMouseEnter={(e) => e.currentTarget.style.transform = 'scale(1.02)'}
              onMouseLeave={(e) => e.currentTarget.style.transform = 'scale(1)'}
            >
              🎯 Take Test
            </button>

            <button
              onClick={() => setView('playing')}
              style={{
                padding: '16px 24px',
                fontSize: '18px',
                background: '#9C27B0',
                color: 'white',
                border: 'none',
                borderRadius: '12px',
                cursor: 'pointer',
                fontWeight: 700,
                boxShadow: '0 4px 12px rgba(156, 39, 176, 0.3)',
                transition: 'transform 0.2s'
              }}
              onMouseEnter={(e) => e.currentTarget.style.transform = 'scale(1.02)'}
              onMouseLeave={(e) => e.currentTarget.style.transform = 'scale(1)'}
            >
              ▶️ Play Drills
            </button>
          </div>

          <div style={{ marginTop: '30px', color: '#999', fontSize: '14px' }}>
            {drills.length} exercises in this test
          </div>
        </div>
      </div>
    </div>
  );
}
