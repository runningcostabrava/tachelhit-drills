import { useState, useEffect } from 'react';
import axios from 'axios';
import { API_BASE } from '../config';
import DrillCard from './DrillCard';
import DrillsGrid from './DrillsGrid';

interface Drill {
  id: number;
  text_catalan?: string;
  text_tachelhit?: string;
  text_arabic?: string;
  audio_url?: string;
  video_url?: string;
  image_url?: string;
  tag?: string;
  date_created: string;
}

interface DrillsResponsiveProps {
  onViewTests?: () => void;
  onViewShorts?: () => void;
}

export default function DrillsResponsive({ onViewTests, onViewShorts }: DrillsResponsiveProps) {
  const [isMobile, setIsMobile] = useState(window.innerWidth < 768);
  const [drills, setDrills] = useState<Drill[]>([]);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [showCreateTest, setShowCreateTest] = useState(false);

  useEffect(() => {
    const handleResize = () => {
      setIsMobile(window.innerWidth < 768);
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  useEffect(() => {
    fetchDrills();
  }, []);

  const fetchDrills = async () => {
    try {
      const response = await axios.get(`${API_BASE}/drills/`);
      const sorted = [...(response.data || [])].sort((a: Drill, b: Drill) =>
        new Date(b.date_created).getTime() - new Date(a.date_created).getTime()
      );
      setDrills(sorted);
    } catch (error) {
      console.error('Error loading drills:', error);
    }
  };

  const addNewDrill = async () => {
    try {
      await axios.post(`${API_BASE}/drills/`, {});
      fetchDrills();
    } catch (error) {
      console.error('Error creating drill:', error);
      alert('Failed to create drill');
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm(`Delete drill #${id}?`)) return;

    try {
      await axios.delete(`${API_BASE}/drills/${id}`);
      fetchDrills();
    } catch (error) {
      console.error('Error deleting drill:', error);
      alert('Failed to delete drill');
    }
  };

  const toggleSelect = (id: number, selected: boolean) => {
    const newSelected = new Set(selectedIds);
    if (selected) {
      newSelected.add(id);
    } else {
      newSelected.delete(id);
    }
    setSelectedIds(newSelected);
  };

  const handleCreateTest = () => {
    if (selectedIds.size === 0) {
      alert('Please select at least one drill');
      return;
    }
    setShowCreateTest(true);
  };

  // Desktop: use existing grid
  if (!isMobile) {
    return <DrillsGrid onViewTests={onViewTests} onViewShorts={onViewShorts} />;
  }

  // Mobile: use card view
  return (
    <div style={{
      minHeight: '100vh',
      background: '#f5f5f5',
      paddingBottom: '80px' // Space for bottom nav
    }}>
      {/* Mobile Header */}
      <div style={{
        position: 'sticky',
        top: 0,
        zIndex: 100,
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        padding: '16px',
        boxShadow: '0 2px 8px rgba(0,0,0,0.15)'
      }}>
        <h1 style={{
          margin: '0 0 12px 0',
          fontSize: '22px',
          fontWeight: 700,
          color: 'white'
        }}>
          Tachelhit Drills
        </h1>

        {/* Selection Info */}
        {selectedIds.size > 0 && (
          <div style={{
            background: 'rgba(255,255,255,0.2)',
            padding: '12px',
            borderRadius: '8px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginTop: '12px'
          }}>
            <span style={{ color: 'white', fontWeight: 600, fontSize: '14px' }}>
              {selectedIds.size} selected
            </span>
            <div style={{ display: 'flex', gap: '8px' }}>
              <button
                onClick={() => setSelectedIds(new Set())}
                style={{
                  padding: '8px 16px',
                  background: 'rgba(255,255,255,0.3)',
                  color: 'white',
                  border: 'none',
                  borderRadius: '6px',
                  fontSize: '13px',
                  fontWeight: 600,
                  cursor: 'pointer'
                }}
              >
                Clear
              </button>
              <button
                onClick={handleCreateTest}
                style={{
                  padding: '8px 16px',
                  background: '#FFD700',
                  color: '#333',
                  border: 'none',
                  borderRadius: '6px',
                  fontSize: '13px',
                  fontWeight: 600,
                  cursor: 'pointer'
                }}
              >
                📝 Create Test
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Drill Cards */}
      <div style={{ padding: '16px' }}>
        {drills.length === 0 ? (
          <div style={{
            textAlign: 'center',
            padding: '40px 20px',
            color: '#666'
          }}>
            <div style={{ fontSize: '48px', marginBottom: '16px' }}>📝</div>
            <div style={{ fontSize: '18px', fontWeight: 600, marginBottom: '8px' }}>
              No drills yet
            </div>
            <div style={{ fontSize: '14px' }}>
              Tap the + button to create your first drill
            </div>
          </div>
        ) : (
          drills.map(drill => (
            <DrillCard
              key={drill.id}
              drill={drill}
              onUpdate={fetchDrills}
              onDelete={() => handleDelete(drill.id)}
              onSelect={(selected) => toggleSelect(drill.id, selected)}
              isSelected={selectedIds.has(drill.id)}
            />
          ))
        )}
      </div>

      {/* Floating Action Button */}
      <button
        onClick={addNewDrill}
        style={{
          position: 'fixed',
          bottom: '90px',
          right: '20px',
          width: '60px',
          height: '60px',
          borderRadius: '50%',
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
          color: 'white',
          border: 'none',
          fontSize: '28px',
          fontWeight: 700,
          cursor: 'pointer',
          boxShadow: '0 4px 16px rgba(102, 126, 234, 0.4)',
          zIndex: 99,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          transition: 'transform 0.2s'
        }}
        onTouchStart={(e) => {
          e.currentTarget.style.transform = 'scale(0.95)';
        }}
        onTouchEnd={(e) => {
          e.currentTarget.style.transform = 'scale(1)';
        }}
      >
        +
      </button>

      {/* Bottom Navigation */}
      <div style={{
        position: 'fixed',
        bottom: 0,
        left: 0,
        right: 0,
        background: 'white',
        borderTop: '1px solid #e0e0e0',
        display: 'grid',
        gridTemplateColumns: '1fr 1fr 1fr',
        zIndex: 100,
        boxShadow: '0 -2px 10px rgba(0,0,0,0.1)'
      }}>
        <button
          style={{
            padding: '12px',
            background: 'white',
            border: 'none',
            borderRight: '1px solid #e0e0e0',
            cursor: 'pointer',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '4px'
          }}
        >
          <span style={{ fontSize: '24px' }}>📚</span>
          <span style={{ fontSize: '11px', fontWeight: 600, color: '#667eea' }}>Drills</span>
        </button>

        {onViewTests && (
          <button
            onClick={onViewTests}
            style={{
              padding: '12px',
              background: 'white',
              border: 'none',
              borderRight: '1px solid #e0e0e0',
              cursor: 'pointer',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: '4px'
            }}
          >
            <span style={{ fontSize: '24px' }}>📊</span>
            <span style={{ fontSize: '11px', fontWeight: 600, color: '#666' }}>Tests</span>
          </button>
        )}

        {onViewShorts && (
          <button
            onClick={onViewShorts}
            style={{
              padding: '12px',
              background: 'white',
              border: 'none',
              cursor: 'pointer',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: '4px'
            }}
          >
            <span style={{ fontSize: '24px' }}>📱</span>
            <span style={{ fontSize: '11px', fontWeight: 600, color: '#666' }}>Shorts</span>
          </button>
        )}
      </div>
    </div>
  );
}
