import { useState, useEffect } from 'react';
import axios from 'axios';
import { Network } from '@capacitor/network';
import { API_BASE } from '../config';
import { syncManager } from '../services/OfflineSyncManager';
import { AgGridReact } from 'ag-grid-react';
import 'ag-grid-community/styles/ag-grid.css';
import 'ag-grid-community/styles/ag-theme-alpine.css';
import MobileDrillEditor from './MobileDrillEditor';
import DrillsGrid from './DrillsGrid';
import MobileBottomNav from './MobileBottomNav';
import VoiceDrillCreator from './VoiceDrillCreator';
import MobileDrillCreator from './MobileDrillCreator';
import { useLocation } from 'react-router-dom';

interface Drill {
  id: number;
  text_catalan?: string;
  text_tachelhit?: string;
  text_arabic?: string;
  audio_url?: string;
  video_url?: string;
  image_url?: string;
  tag?: string;
  author?: string;
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
          <input placeholder="Sound (e.g. anayr)" value={newWord.sound} onChange={e => setNewWord({ ...newWord, sound: e.target.value })} style={{ padding: '10px', borderRadius: '6px', border: '1px solid #ccc', fontSize: '14px' }} />
          <input placeholder="Correct Spelling" value={newWord.spelling} onChange={e => setNewWord({ ...newWord, spelling: e.target.value })} style={{ padding: '10px', borderRadius: '6px', border: '1px solid #ccc', fontSize: '14px' }} />
          <button onClick={handleAdd} style={{ padding: '10px', background: '#4CAF50', color: 'white', border: 'none', borderRadius: '6px', cursor: 'pointer', fontWeight: 'bold' }}>Add to AI</button>
        </div>
        <div className="ag-theme-alpine" style={{ flex: 1, width: '100%', minHeight: '200px' }}>
          <AgGridReact
            rowData={rowData}
            columnDefs={columnDefs}
            headerHeight={40}
            rowHeight={45}
            theme="legacy"
            rowSelection={{ mode: 'multiRow', checkboxes: false, headerCheckbox: false }}
          />
        </div>
        <button onClick={onClose} style={{ marginTop: '16px', padding: '12px', background: '#f5f5f5', border: '1px solid #ccc', borderRadius: '8px', cursor: 'pointer', fontWeight: 600 }}>Close</button>
      </div>
    </div>
  );
};

interface DrillsResponsiveProps { }

export default function DrillsResponsive({ }: DrillsResponsiveProps) {
  const location = useLocation();

  const [isMobile, setIsMobile] = useState(window.innerWidth < 768 || /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent));
  const [drills, setDrills] = useState<Drill[]>([]);
  const [editingDrill, setEditingDrill] = useState<Drill | null>(null);
  const [showVoiceCreator, setShowVoiceCreator] = useState(false);
  const [showMobileDrillCreator, setShowMobileDrillCreator] = useState(false);
  const [showNewDrillOptions, setShowNewDrillOptions] = useState(false);
  const [showGlossary, setShowGlossary] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchCategory, setSearchCategory] = useState('all');
  const [filteredDrills, setFilteredDrills] = useState<Drill[]>([]);

  useEffect(() => {
    let result = [...drills];

    if (searchQuery.trim()) {
      const searchTerm = searchQuery.toLowerCase();
      result = result.filter((drill: Drill) => {
        if (searchCategory === 'all') {
          const fieldsToSearch = [
            drill.text_catalan?.toLowerCase() || '',
            drill.text_tachelhit?.toLowerCase() || '',
            drill.text_arabic?.toLowerCase() || '',
            drill.tag?.toLowerCase() || '',
            drill.author?.toLowerCase() || ''
          ];
          return fieldsToSearch.some(field => field.includes(searchTerm));
        } else {
          switch (searchCategory) {
            case 'catalan':
              return (drill.text_catalan?.toLowerCase() || '').includes(searchTerm);
            case 'tachelhit':
              return (drill.text_tachelhit?.toLowerCase() || '').includes(searchTerm);
            case 'arabic':
              return (drill.text_arabic?.toLowerCase() || '').includes(searchTerm);
            case 'tag':
              return (drill.tag?.toLowerCase() || '').includes(searchTerm);
            case 'author':
              return (drill.author?.toLowerCase() || '').includes(searchTerm);
            default:
              return true;
          }
        }
      });
    }

    setFilteredDrills(result);
  }, [drills, searchQuery, searchCategory, location.search]);

  useEffect(() => {
    const handleResize = () => setIsMobile(window.innerWidth < 768 || /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent));
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const fetchDrills = async () => {
    try {
      const status = await Network.getStatus();
      let allDrills = [];

      if (status.connected) {
        // Sync pending changes first
        await syncManager.sync();
        const response = await axios.get(`${API_BASE}/drills/`);
        allDrills = response.data || [];
        await syncManager.saveDrillsToCache(allDrills);
      } else {
        allDrills = await syncManager.getDrills();
      }

      const queryParams = new URLSearchParams(location.search);
      const tag = queryParams.get('tag');
      const author = queryParams.get('author');
      const text = queryParams.get('text');

      if (tag || author || text) {
        allDrills = allDrills.filter((drill: Drill) => {
          const tagMatch = tag ? (drill.tag?.toLowerCase() || '').includes(tag.toLowerCase()) : false;
          const authorMatch = author ? (drill.author?.toLowerCase() || '').includes(author.toLowerCase()) : false;
          const textMatch = text ? (
            (drill.text_catalan?.toLowerCase() || '').includes(text.toLowerCase()) ||
            (drill.text_tachelhit?.toLowerCase() || '').includes(text.toLowerCase()) ||
            (drill.text_arabic?.toLowerCase() || '').includes(text.toLowerCase())
          ) : false;

          const matches = [];
          if (tag) matches.push(tagMatch);
          if (author) matches.push(authorMatch);
          if (text) matches.push(textMatch);

          return matches.some(match => match === true);
        });
      }

      const sorted = allDrills.sort((a: Drill, b: Drill) =>
        new Date(b.date_created).getTime() - new Date(a.date_created).getTime()
      );
      setDrills(sorted);
    } catch (error) {
      console.error('Error loading drills, using fallback:', error);
      const cachedData = localStorage.getItem('cached_drills');
      if (cachedData) {
        const allDrills = JSON.parse(cachedData);
        const sorted = allDrills.sort((a: Drill, b: Drill) =>
          new Date(b.date_created).getTime() - new Date(a.date_created).getTime()
        );
        setDrills(sorted);
      }
    }
  };

  useEffect(() => { fetchDrills(); }, [location.search]);

  const addNewDrill = async () => {
    try {
      const status = await Network.getStatus();
      const tempId = Date.now();
      const newDrillData = {
        id: tempId,
        text_catalan: '',
        text_tachelhit: '',
        text_arabic: '',
        date_created: new Date().toISOString(),
        is_local: true
      };

      if (status.connected) {
        const response = await axios.post(`${API_BASE}/drills/`, {});
        await fetchDrills();
        if (isMobile && response.data) {
          setTimeout(() => setEditingDrill(response.data), 100);
        }
      } else {
        // Offline creation
        const currentDrills = await syncManager.getDrills();
        const updatedDrills = [newDrillData, ...currentDrills];
        await syncManager.saveDrillsToCache(updatedDrills);
        setDrills(updatedDrills);
        
        await syncManager.queueAction({
          type: 'CREATE',
          drillId: tempId,
          payload: {}
        });
        
        if (isMobile) {
          setTimeout(() => setEditingDrill(newDrillData), 100);
        }
      }
    } catch (error) {
      console.error('Error creating drill:', error);
      alert('Failed to create drill');
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

  if (!isMobile) {
    return <DrillsGrid rowData={drills} refreshData={fetchDrills} onEditDrill={(drill) => setEditingDrill(drill)} />;
  }

  return (
    <>
      <div style={{ height: '100vh', display: 'flex', flexDirection: 'column', paddingBottom: '60px' }}>
        {/* Header */}
        <div style={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', padding: '16px', boxShadow: '0 2px 8px rgba(0,0,0,0.15)' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
            <h1 style={{ margin: 0, fontSize: '20px', fontWeight: 700, color: 'white' }}>Tachelhit Drills</h1>
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
              <button
                onClick={() => setShowMobileDrillCreator(true)}
                style={{ padding: '10px 16px', background: '#FFD700', color: '#333', border: 'none', borderRadius: '8px', fontSize: '15px', fontWeight: 700, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px', boxShadow: '0 2px 8px rgba(0,0,0,0.2)' }}
              >
                📱 New Drill
              </button>

              <button
                onClick={() => {
                  const url = window.location.href;
                  navigator.clipboard.writeText(url);
                  alert(`Filtered link copied to clipboard!\n${url}`);
                }}
                style={{ padding: '8px', background: 'rgba(255,255,255,0.2)', color: 'white', border: 'none', borderRadius: '8px', fontSize: '18px', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
              >
                🔗
              </button>
              <div style={{ position: 'relative' }}>
                <button
                  onClick={() => setShowNewDrillOptions(!showNewDrillOptions)}
                  style={{ padding: '10px 20px', background: 'white', color: '#667eea', border: 'none', borderRadius: '8px', fontSize: '15px', fontWeight: 700, cursor: 'pointer' }}
                >
                  + More ▼
                </button>
                {showNewDrillOptions && (
                  <div style={{ position: 'absolute', top: 'calc(100% + 10px)', right: 0, backgroundColor: 'white', borderRadius: '8px', boxShadow: '0 4px 12px rgba(0,0,0,0.15)', zIndex: 1000, minWidth: '220px', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
                    <button
                      onClick={() => { addNewDrill(); setShowNewDrillOptions(false); }}
                      style={{ padding: '10px 15px', fontSize: '15px', background: 'none', border: 'none', textAlign: 'left', cursor: 'pointer', color: '#333', fontWeight: 500, whiteSpace: 'nowrap' }}
                    >
                      ➕ Create Empty Drill
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>
          {/* Search Box */}
          <div style={{ width: '100%', display: 'flex', gap: '8px', alignItems: 'center', background: 'rgba(255, 255, 255, 0.15)', borderRadius: '8px', padding: '8px 12px', backdropFilter: 'blur(10px)', border: '1px solid rgba(255, 255, 255, 0.2)', marginTop: '12px' }}>
            <div style={{ color: 'white', fontSize: '16px', flexShrink: 0 }}>🔍</div>
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search drills..."
              style={{ flex: 1, background: 'transparent', border: 'none', color: 'white', fontSize: '14px', outline: 'none', minWidth: '0' }}
            />
            <select
              value={searchCategory}
              onChange={(e) => setSearchCategory(e.target.value)}
              style={{ background: 'rgba(255, 255, 255, 0.2)', border: '1px solid rgba(255, 255, 255, 0.3)', color: 'white', borderRadius: '6px', padding: '6px 8px', fontSize: '12px', outline: 'none', cursor: 'pointer', flexShrink: 0 }}
            >
              <option value="all">All</option>
              <option value="catalan">Català</option>
              <option value="tachelhit">Tachelhit</option>
              <option value="arabic">Arabic</option>
              <option value="tag">Tag</option>
              <option value="author">Author</option>
            </select>
            {searchQuery && <button onClick={() => setSearchQuery('')} style={{ background: 'none', border: 'none', color: 'white', fontSize: '16px', cursor: 'pointer', padding: '0 6px', flexShrink: 0 }}>✕</button>}
          </div>
          <div style={{ fontSize: '13px', color: 'rgba(255,255,255,0.9)', marginTop: '8px' }}>Tap any card to view details</div>
        </div>

        {/* Card Stream */}
        <div style={{ flex: 1, width: '100%', overflow: 'auto', padding: '12px 4px' }}>
          <DrillsGrid rowData={filteredDrills} refreshData={fetchDrills} onEditDrill={(drill) => setEditingDrill(drill)} />
        </div>

        <MobileBottomNav />
      </div>

      {editingDrill && (
        <MobileDrillEditor
          drill={editingDrill}
          onClose={() => setEditingDrill(null)}
          onUpdate={() => {
            fetchDrills();
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

      {showVoiceCreator && (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0,0,0,0.9)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 20000 }}>
          <div style={{ backgroundColor: 'white', padding: '30px', borderRadius: '12px', width: '600px', maxWidth: '90vw', maxHeight: '90vh', overflow: 'auto', boxShadow: '0 10px 50px rgba(0,0,0,0.5)' }}>
            <h2 style={{ marginTop: 0, marginBottom: '20px' }}>🎤 Create Drill with Voice</h2>
            <VoiceDrillCreator onClose={() => setShowVoiceCreator(false)} onDrillCreated={() => { fetchDrills(); setShowVoiceCreator(false); }} />
          </div>
        </div>
      )}

      {showGlossary && <GlossaryModal onClose={() => setShowGlossary(false)} />}

      {showMobileDrillCreator && (
        <MobileDrillCreator onClose={() => setShowMobileDrillCreator(false)} onDrillCreated={() => { fetchDrills(); setShowMobileDrillCreator(false); }} />
      )}
    </>
  );
}