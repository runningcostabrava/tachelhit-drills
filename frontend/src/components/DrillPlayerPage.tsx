import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Network } from '@capacitor/network';
import { API_BASE } from '../config';
import { syncManager, Drill } from '../services/OfflineSyncManager';
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
        background: '#f3f4f6'
      }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '24px', marginBottom: '10px' }}>⏳</div>
          <div>Loading Drills...</div>
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
        background: '#f3f4f6',
        padding: '20px',
        textAlign: 'center'
      }}>
        <div>
          <div style={{ fontSize: '48px', marginBottom: '20px' }}>📭</div>
          <h2 style={{ marginBottom: '10px' }}>No Drills Found</h2>
          <p style={{ color: '#666', marginBottom: '20px' }}>Create some drills first to use the player.</p>
          <button
            onClick={() => navigate('/')}
            style={{
              padding: '10px 20px',
              background: '#4f46e5',
              color: 'white',
              border: 'none',
              borderRadius: '8px',
              fontWeight: 'bold',
              cursor: 'pointer'
            }}
          >
            Go Back
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
