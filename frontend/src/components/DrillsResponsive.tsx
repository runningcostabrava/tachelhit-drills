import { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { API_BASE } from '../config';
import { AgGridReact } from 'ag-grid-react';
// Importar solo el tema Alpine CSS (versión legacy)
import 'ag-grid-community/styles/ag-grid.css';
import 'ag-grid-community/styles/ag-theme-alpine.css';
import MobileDrillEditor from './MobileDrillEditor';
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
  const [editingDrill, setEditingDrill] = useState<Drill | null>(null);
  const gridRef = useRef<any>(null);

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
      const response = await axios.post(`${API_BASE}/drills/`, {});
      // Actualizar la lista de drills
      await fetchDrills();
      // Open the newly created drill in editor
      if (isMobile && response.data) {
        // Asegurarse de que el drill tiene todos los campos necesarios
        const newDrill = {
          ...response.data,
          text_catalan: response.data.text_catalan || '',
          text_tachelhit: response.data.text_tachelhit || '',
          text_arabic: response.data.text_arabic || '',
          audio_url: response.data.audio_url || '',
          video_url: response.data.video_url || '',
          image_url: response.data.image_url || '',
          tag: response.data.tag || '',
          date_created: response.data.date_created || new Date().toISOString()
        };
        // Esperar un momento para asegurar que el drill está completamente creado
        setTimeout(() => {
          setEditingDrill(newDrill);
        }, 100);
      }
    } catch (error) {
      console.error('Error creating drill:', error);
      alert('Failed to create drill');
    }
  };

  const handleRowClick = (event: any) => {
    if (isMobile && event.data) {
      setEditingDrill(event.data);
    }
  };

  const handleNavigate = (direction: 'next' | 'prev') => {
    if (!editingDrill) return;

    const currentIndex = drills.findIndex(d => d.id === editingDrill.id);
    if (direction === 'next' && currentIndex < drills.length - 1) {
      setEditingDrill(drills[currentIndex + 1]);
    } else if (direction === 'prev' && currentIndex > 0) {
      setEditingDrill(drills[currentIndex - 1]);
    }
  };

  // Desktop: use existing grid
  if (!isMobile) {
    return <DrillsGrid onViewTests={onViewTests} onViewShorts={onViewShorts} />;
  }

  const columnDefs: any[] = [
    { field: 'id', width: 60, headerName: '#' },
    { field: 'text_catalan', width: 150, headerName: 'Català' },
    { field: 'text_tachelhit', width: 150, headerName: 'Tachelhit' },
    {
      field: 'audio_url',
      width: 70,
      headerName: '🎤',
      cellRenderer: (params: any) => params.value ? '✓' : ''
    },
    {
      field: 'video_url',
      width: 70,
      headerName: '🎥',
      cellRenderer: (params: any) => params.value ? '✓' : ''
    },
  ];

  // Mobile: Excel-like grid with full-screen editor
  return (
    <>
      <div style={{
        height: '100vh',
        display: 'flex',
        flexDirection: 'column'
      }}>
        {/* Header */}
        <div style={{
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
          padding: '16px',
          boxShadow: '0 2px 8px rgba(0,0,0,0.15)'
        }}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            marginBottom: '12px'
          }}>
            <h1 style={{
              margin: 0,
              fontSize: '20px',
              fontWeight: 700,
              color: 'white'
            }}>
              Tachelhit Drills
            </h1>
            <button
              onClick={addNewDrill}
              style={{
                padding: '10px 20px',
                background: 'white',
                color: '#667eea',
                border: 'none',
                borderRadius: '8px',
                fontSize: '15px',
                fontWeight: 700,
                cursor: 'pointer'
              }}
            >
              + New
            </button>
          </div>
          <div style={{ fontSize: '13px', color: 'rgba(255,255,255,0.9)' }}>
            Tap any row to edit
          </div>
        </div>

        {/* Grid */}
        <div
          className="ag-theme-alpine"
          style={{
            flex: 1,
            width: '100%'
          }}
        >
          <AgGridReact
            ref={gridRef}
            rowData={drills}
            columnDefs={columnDefs}
            defaultColDef={{
              sortable: true,
              filter: false,
              resizable: false,
              minWidth: 60
            }}
            getRowId={(params) => params.data.id.toString()}
            onRowClicked={handleRowClick}
            rowHeight={50}
            suppressHorizontalScroll={false}
            domLayout="normal"
            // Configurar tema legacy para evitar conflictos
            theme="legacy"          />
        </div>

        {/* Bottom Navigation */}
        <div style={{
          background: 'white',
          borderTop: '1px solid #e0e0e0',
          display: 'grid',
          gridTemplateColumns: '1fr 1fr 1fr',
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

      {/* Full-screen Editor */}
      {editingDrill && (
        <MobileDrillEditor
          drill={editingDrill}
          allDrills={drills}
          onClose={() => setEditingDrill(null)}
          onUpdate={() => {
            fetchDrills();
            // Refresh the editing drill with latest data
            if (editingDrill) {
              axios.get(`${API_BASE}/drills/`).then(response => {
                const updated = response.data.find((d: Drill) => d.id === editingDrill.id);
                if (updated) setEditingDrill(updated);
              });
            }
          }}
          onNavigate={handleNavigate}
        />
      )}
    </>
  );
}
