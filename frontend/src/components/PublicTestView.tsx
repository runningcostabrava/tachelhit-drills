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

  if (loading) return <div style={{ padding: '40px', textAlign: 'center', fontFamily: 'var(--font-sans)', color: 'var(--text-soft)' }}>Loading test...</div>;
  if (!test) return <div style={{ padding: '40px', textAlign: 'center', fontFamily: 'var(--font-sans)', color: 'var(--text-soft)' }}>Test not found.</div>;

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
      background: 'var(--bg)',
      fontFamily: 'var(--font-sans)'
    }}>
      {/* Header */}
      <div style={{
        padding: '18px 24px 26px',
        background: 'var(--brand-gradient)',
        color: '#fff',
        display: 'flex',
        alignItems: 'center',
        gap: '15px',
        borderBottomLeftRadius: '26px',
        borderBottomRightRadius: '26px',
        boxShadow: 'var(--shadow-md)'
      }}>
        <button
          onClick={() => navigate('/')}
          style={{
            background: 'rgba(255,255,255,0.18)',
            border: '1px solid rgba(255,255,255,0.4)',
            color: '#fff',
            padding: '8px 14px',
            borderRadius: 'var(--r-pill)',
            cursor: 'pointer',
            fontSize: '14px',
            fontWeight: 600
          }}
        >
          ← Home
        </button>
        <h1 style={{ margin: 0, fontSize: '20px', fontWeight: 800, color: '#fff' }}>Tachelhit Drills</h1>
      </div>

      {/* Main Content */}
      <div style={{
        flex: 1,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '24px'
      }}>
        <div style={{
          background: 'var(--surface)',
          border: '1px solid var(--border)',
          padding: '40px',
          borderRadius: 'var(--r-xl)',
          boxShadow: 'var(--shadow-sm)',
          width: '100%',
          maxWidth: '500px',
          textAlign: 'center'
        }}>
          <div style={{
            width: '84px',
            height: '84px',
            margin: '0 auto 22px',
            borderRadius: 'var(--r-lg)',
            background: 'var(--brand-gradient-soft)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '42px',
            boxShadow: 'var(--shadow-xs)'
          }}>📊</div>
          <h2 style={{ margin: '0 0 10px 0', fontSize: '28px', color: 'var(--text)', fontWeight: 800 }}>{test.title}</h2>
          {test.description && (
            <p style={{ margin: '0 0 30px 0', color: 'var(--text-soft)', lineHeight: 1.5 }}>
              {test.description}
            </p>
          )}

          <div style={{
            display: 'flex',
            flexDirection: 'column',
            gap: '14px'
          }}>
            <button
              onClick={() => setView('taking')}
              style={{
                padding: '16px 24px',
                fontSize: '17px',
                background: 'var(--brand-gradient)',
                color: '#fff',
                border: 'none',
                borderRadius: 'var(--r-lg)',
                cursor: 'pointer',
                fontWeight: 700,
                boxShadow: 'var(--shadow-brand)',
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
                fontSize: '17px',
                background: 'var(--surface)',
                color: 'var(--brand-1)',
                border: '1px solid var(--border)',
                borderRadius: 'var(--r-lg)',
                cursor: 'pointer',
                fontWeight: 700,
                boxShadow: 'var(--shadow-xs)',
                transition: 'transform 0.2s'
              }}
              onMouseEnter={(e) => e.currentTarget.style.transform = 'scale(1.02)'}
              onMouseLeave={(e) => e.currentTarget.style.transform = 'scale(1)'}
            >
              ▶️ Play Drills
            </button>
          </div>

          <div style={{ marginTop: '28px', color: 'var(--text-muted)', fontSize: '14px' }}>
            {drills.length} exercises in this test
          </div>
        </div>
      </div>
    </div>
  );
}
