import { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { API_BASE } from '../config';
import { AgGridReact } from 'ag-grid-react';
// Importar solo el tema Alpine CSS (versión legacy)
import 'ag-grid-community/styles/ag-grid.css';
import 'ag-grid-community/styles/ag-theme-alpine.css';
import MobileDrillEditor from './MobileDrillEditor';
import DrillsGrid from './DrillsGrid';
import MobileBottomNav from './MobileBottomNav'; // Added import
import VoiceDrillCreator from './VoiceDrillCreator'; // Added missing import
import { useLocation, useNavigate } from 'react-router-dom'; // Added imports

interface Drill {
  id: number;
  text_catalan?: string;
  text_tachelhit?: string;
  text_arabic?: string;
  audio_url?: string;
  video_url?: string;
  image_url?: string;
  tag?: string;
  is_correction_dataset?: boolean;
  date_created: string;
}

const GlossaryModal = ({ onClose }: { onClose: () => void }) => {
    const [rowData, setRowData] = useState<any[]>([]);
    const [newWord, setNewWord] = useState({ sound: '', spelling: '' });

    const fetchGlossary = async () => {
        const res = await axios.get(`${API_BASE}/glossary/`);
        setRowData(res.data);
    };

    useEffect(() => { fetchGlossary(); }, []);

    const handleAdd = async () => {
        if (!newWord.sound || !newWord.spelling) return;
        await axios.post(`${API_BASE}/glossary/`, { word_sound: newWord.sound, correct_spelling: newWord.spelling });
        setNewWord({ sound: '', spelling: '' });
        fetchGlossary();
    };

    const handleDelete = async (id: number) => {
        await axios.delete(`${API_BASE}/glossary/${id}`);
        fetchGlossary();
    };

    const columnDefs: any[] = [
        { field: 'word_sound', headerName: 'Sound', flex: 1 },
        { field: 'correct_spelling', headerName: 'Spelling', flex: 1 },
        { 
            field: 'id', 
            headerName: '', 
            width: 80, 
            cellRenderer: (p: any) => (
                <button 
                    onClick={() => handleDelete(p.value)} 
                    style={{ color: 'red', border: 'none', background: 'none', cursor: 'pointer', fontWeight: 'bold' }}
                >
                    ✕
                </button>
            )
        }
    ];

    return (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.8)', zIndex: 30000, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '10px' }}>
            <div style={{ background: 'white', padding: '16px', borderRadius: '12px', width: '100%', maxWidth: '500px', maxHeight: '90vh', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
                <h3 style={{ marginTop: 0, fontSize: '16px' }}>📖 Glossary (AI Learning)</h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginBottom: '16px' }}>
                    <input placeholder="Sound (e.g. anayr)" value={newWord.sound} onChange={e => setNewWord({...newWord, sound: e.target.value})} style={{ padding: '10px', borderRadius: '6px', border: '1px solid #ccc', fontSize: '14px' }} />
                    <input placeholder="Correct Spelling" value={newWord.spelling} onChange={e => setNewWord({...newWord, spelling: e.target.value})} style={{ padding: '10px', borderRadius: '6px', border: '1px solid #ccc', fontSize: '14px' }} />
                    <button onClick={handleAdd} style={{ padding: '10px', background: '#4CAF50', color: 'white', border: 'none', borderRadius: '6px', cursor: 'pointer', fontWeight: 'bold' }}>Add to AI</button>
                </div>
                <div className="ag-theme-alpine" style={{ flex: 1, width: '100%', minHeight: '200px' }}>
                    <AgGridReact 
                        rowData={rowData} 
                        columnDefs={columnDefs}
                        headerHeight={40}
                        rowHeight={45}
                    />
                </div>
                <button onClick={onClose} style={{ marginTop: '16px', padding: '12px', background: '#f5f5f5', border: '1px solid #ccc', borderRadius: '8px', cursor: 'pointer', fontWeight: 600 }}>Close</button>
            </div>
        </div>
    );
};

// Remove onViewTests and onViewShorts props from here
interface DrillsResponsiveProps {
  // onViewTests?: () => void;
  // onViewShorts?: () => void;
}

export default function DrillsResponsive({}: DrillsResponsiveProps) {
  const [isMobile, setIsMobile] = useState(window.innerWidth < 768);
  const [drills, setDrills] = useState<Drill[]>([]);
  const [editingDrill, setEditingDrill] = useState<Drill | null>(null);
  const [showVoiceCreator, setShowVoiceCreator] = useState(false); // New state for VoiceDrillCreator modal
  const [showNewDrillOptions, setShowNewDrillOptions] = useState(false); // New state for dropdown
  const [showGlossary, setShowGlossary] = useState(false);
  const gridRef = useRef<any>(null); // This ref is for DrillsGrid when in mobile view.
  
  const location = useLocation(); // Initialize useLocation
  const navigate = useNavigate(); // Initialize useNavigate

  useEffect(() => {
    const handleResize = () => {
      setIsMobile(window.innerWidth < 768);
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const fetchDrills = async () => {
    try {
      // Construct API URL with query parameters from the URL
      const queryParams = new URLSearchParams(location.search);
      let apiUrl = `${API_BASE}/drills/`;
      if (queryParams.toString()) {
          apiUrl += `?${queryParams.toString()}`;
      }

      const response = await axios.get(apiUrl);
      const sorted = [...(response.data || [])].sort((a: Drill, b: Drill) =>
        new Date(b.date_created).getTime() - new Date(a.date_created).getTime()
      );
      setDrills(sorted);
    } catch (error) {
      console.error('Error loading drills:', error);
    }
  };

  useEffect(() => {
    fetchDrills();
  }, [location.search]); // Re-fetch drills when URL search params change

  const addNewDrill = async () => {
    try {
      const response = await axios.post(`${API_BASE}/drills/`, {});
      // Actualizar la lista de drills
      await fetchDrills();
      // Open the newly created drill in editor (mobile view only)
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
    return <DrillsGrid rowData={drills} refreshData={fetchDrills} />;
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
        flexDirection: 'column',
        paddingBottom: '60px' // Space for bottom nav
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
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
               <button
                  onClick={() => {
                    const url = window.location.href;
                    navigator.clipboard.writeText(url);
                    alert(`Filtered link copied to clipboard!\n${url}`);
                  }}
                  style={{
                    padding: '8px',
                    background: 'rgba(255,255,255,0.2)',
                    color: 'white',
                    border: 'none',
                    borderRadius: '8px',
                    fontSize: '18px',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center'
                  }}
                  title="Copy link"
                >
                  🔗
                </button>
               <button
                  onClick={() => setShowGlossary(true)}
                  style={{
                    padding: '8px',
                    background: 'rgba(255,255,255,0.2)',
                    color: 'white',
                    border: 'none',
                    borderRadius: '8px',
                    fontSize: '18px',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center'
                  }}
                  title="Glossary"
                >
                  📖
                </button>
              <div style={{ position: 'relative' }}>
                <button
                  onClick={() => setShowNewDrillOptions(!showNewDrillOptions)}
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
                  + New ▼
                </button>
              {showNewDrillOptions && (
                <div style={{
                  position: 'absolute',
                  top: 'calc(100% + 10px)',
                  right: 0,
                  backgroundColor: 'white',
                  borderRadius: '8px',
                  boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
                  zIndex: 1000,
                  minWidth: '220px',
                  display: 'flex',
                  flexDirection: 'column',
                  overflow: 'hidden',
                }}>
                  <button
                    onClick={() => {
                      addNewDrill(); // Creates an empty drill
                      setShowNewDrillOptions(false);
                    }}
                    style={{
                      padding: '10px 15px',
                      fontSize: '15px',
                      background: 'none',
                      border: 'none',
                      textAlign: 'left',
                      cursor: 'pointer',
                      color: '#333',
                      fontWeight: 500,
                      whiteSpace: 'nowrap'
                    }}
                  >
                    ➕ Create Empty Drill
                  </button>
                                      <button
                                      onClick={() => {
                                        const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
                                        if (!SpeechRecognition) {
                                          alert('Speech recognition is not supported in your browser. Please use Chrome or Edge for voice features. You can still create a drill manually.');
                                        }
                                        setShowVoiceCreator(true);
                                        setShowNewDrillOptions(false);
                                      }}
                                      style={{
                                        padding: '10px 15px',
                                        fontSize: '15px',
                                        background: 'none',
                                        border: 'none',
                                        textAlign: 'left',
                                        cursor: 'pointer',
                                        color: '#333',
                                        fontWeight: 500,
                                        whiteSpace: 'nowrap'
                                      }}
                                    >
                                      🎤 Create Drill with Voice
                                    </button>
                                    <button
                                      onClick={() => {
                                        navigate('/video-creator');
                                        setShowNewDrillOptions(false);
                                      }}
                                      style={{
                                        padding: '10px 15px',
                                        fontSize: '15px',
                                        background: 'none',
                                        border: 'none',
                                        textAlign: 'left',
                                        cursor: 'pointer',
                                        color: '#333',
                                        fontWeight: 500,
                                        whiteSpace: 'nowrap'
                                      }}
                                    >
                                      🎬 Create from Video (YouTube)
                                    </button>
                                  </div>
                                )}
                              </div>
                            </div>          <div style={{ fontSize: '13px', color: 'rgba(255,255,255,0.9)' }}>
            Tap any row to edit
          </div>
        </div>



        {/* Grid */}
        <div
          className="ag-theme-alpine"
          style={{
            flex: 1,
            width: '100%',
            overflow: 'auto'
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
          />
        </div>

        {/* Mobile Bottom Navigation */}
        <MobileBottomNav />
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

      {/* VoiceDrillCreator Modal for Mobile View */}
      {showVoiceCreator && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0,0,0,0.9)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 20000,
        }}>
          <div style={{
            backgroundColor: 'white',
            padding: '30px',
            borderRadius: '12px',
            width: '600px',
            maxWidth: '90vw',
            maxHeight: '90vh',
            overflow: 'auto',
            boxShadow: '0 10px 50px rgba(0,0,0,0.5)',
          }}>
            <h2 style={{ marginTop: 0, marginBottom: '20px' }}>
              🎤 Create Drill with Voice
            </h2>
            <p style={{ color: '#667eea', marginBottom: '20px' }}>
              Use speech‑to‑text to quickly create a drill in Catalan, then add translations and media.
            </p>
            <VoiceDrillCreator
              onClose={() => {
                console.log('Cerrando VoiceDrillCreator (Mobile)');
                setShowVoiceCreator(false);
              }}
              onDrillCreated={() => {
                console.log('Drill creado, refrescando lista (Mobile)');
                fetchDrills();
                setShowVoiceCreator(false);
              }}
            />
          </div>
        </div>
      )}

      {showGlossary && <GlossaryModal onClose={() => setShowGlossary(false)} />}
    </>
  );
}
