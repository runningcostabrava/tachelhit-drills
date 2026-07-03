import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Network } from '@capacitor/network';
import { API_BASE } from '../config';
import { syncManager } from '../services/OfflineSyncManager';
import type { Drill } from '../services/OfflineSyncManager';
import DrillPlayer from './DrillPlayer';

export default function DrillPlayerPage() {
  const navigate = useNavigate();
  const [drills, setDrills] = useState<Drill[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchDrills = async () => {
      try {
        const status = await Network.getStatus();
        let allDrills: Drill[] = [];

        if (status.connected) {
          const response = await axios.get(`${API_BASE}/drills/`);
          allDrills = response.data || [];
          await syncManager.saveDrillsToCache(allDrills);
        } else {
          allDrills = await syncManager.getDrills();
        }

        // Sort by date created descending
        const sorted = allDrills.sort((a, b) =>
          new Date(b.date_created).getTime() - new Date(a.date_created).getTime()
        );
        setDrills(sorted);
      } catch (error) {
        console.error('Error loading drills for player:', error);
        // Fallback to cache if network fails
        const cached = await syncManager.getDrills();
        setDrills(cached);
      } finally {
        setLoading(false);
      }
    };

    fetchDrills();
  }, []);

  if (loading) {
    return (
      <div style={{
        height: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'var(--bg)',
        fontFamily: 'var(--font-sans)'
      }}>
        <div style={{ textAlign: 'center', color: 'var(--text-soft)' }}>
          <div style={{
            width: '52px',
            height: '52px',
            margin: '0 auto 18px',
            borderRadius: 'var(--r-pill)',
            border: '4px solid var(--border)',
            borderTopColor: 'var(--brand-1)',
            animation: 'spin 0.9s linear infinite'
          }} />
          <div style={{ fontSize: '15px', fontWeight: 600, color: 'var(--text)' }}>Loading drills…</div>
        </div>
      </div>
    );
  }

  if (drills.length === 0) {
    return (
      <div style={{
        height: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'var(--bg)',
        padding: '20px',
        textAlign: 'center',
        fontFamily: 'var(--font-sans)'
      }}>
        <div style={{
          background: 'var(--surface)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--r-2xl)',
          boxShadow: 'var(--shadow-lg)',
          padding: '40px 36px',
          maxWidth: '420px'
        }}>
          <div style={{
            width: '72px',
            height: '72px',
            margin: '0 auto 22px',
            borderRadius: 'var(--r-xl)',
            background: 'var(--brand-gradient-soft)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '36px'
          }}>📭</div>
          <h2 style={{ margin: '0 0 10px', fontSize: '22px', fontWeight: 800, color: 'var(--text)' }}>No drills found</h2>
          <p style={{ color: 'var(--text-soft)', margin: '0 0 24px', fontSize: '15px', lineHeight: 1.5 }}>Create some drills first to use the player.</p>
          <button
            onClick={() => navigate('/')}
            style={{
              padding: '12px 28px',
              background: 'var(--brand-gradient)',
              color: 'white',
              border: 'none',
              borderRadius: 'var(--r-pill)',
              fontWeight: 700,
              fontSize: '15px',
              cursor: 'pointer',
              boxShadow: 'var(--shadow-brand)'
            }}
          >
            Go back
          </button>
        </div>
      </div>
    );
  }

  return (
    <DrillPlayer
      drills={drills}
      onExit={() => navigate('/')}
    />
  );
}
