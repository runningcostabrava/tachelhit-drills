import { useState, useEffect } from 'react';
import { FaMicrophone, FaPlus, FaTimes, FaLink, FaChevronDown, FaSearch, FaBook, FaTrash } from 'react-icons/fa';
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
import { useLocation, useNavigate } from 'react-router-dom';

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
  is_local?: boolean;
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
    { field: 'word_sound', headerName: 'Sound', flex: 1, cellStyle: { fontWeight: 600 } },
    { field: 'correct_spelling', headerName: 'Spelling', flex: 1, cellStyle: { color: '#4F46E5', fontWeight: 700 } },
    {
      field: 'id',
      headerName: '',
      width: 60,
      cellRenderer: (p: any) => (
        <button
          onClick={() => handleDelete(p.value)}
          style={{ color: '#EF4444', border: 'none', background: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', width: '100%' }}
        >
          <FaTrash size={14} />
        </button>
      )
    }
  ];

  return (
    <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(17, 24, 39, 0.8)', zIndex: 30000, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '20px', backdropFilter: 'blur(4px)' }}>
      <div style={{ background: 'white', padding: '30px', borderRadius: '24px', width: '100%', maxWidth: '500px', maxHeight: '90vh', overflow: 'hidden', display: 'flex', flexDirection: 'column', boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <FaBook style={{ color: '#4F46E5' }} />
            <h3 style={{ margin: 0, fontSize: '20px', fontWeight: 800, color: '#111827' }}>Glossary (AI)</h3>
          </div>
          <button onClick={onClose} style={{ background: '#F3F4F6', border: 'none', borderRadius: '50%', width: '32px', height: '32px', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer', color: '#6B7280' }}><FaTimes /></button>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginBottom: '20px', padding: '15px', background: '#F9FAFB', borderRadius: '16px', border: '1px solid #E5E7EB' }}>
          <input placeholder="Sound (e.g. anayr)" value={newWord.sound} onChange={e => setNewWord({ ...newWord, sound: e.target.value })} style={{ padding: '12px', borderRadius: '10px', border: '1px solid #D1D5DB', fontSize: '14px', outline: 'none' }} />
          <input placeholder="Correct Spelling" value={newWord.spelling} onChange={e => setNewWord({ ...newWord, spelling: e.target.value })} style={{ padding: '12px', borderRadius: '10px', border: '1px solid #D1D5DB', fontSize: '14px', outline: 'none' }} />
          <button onClick={handleAdd} style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', padding: '12px', background: '#4F46E5', color: 'white', border: 'none', borderRadius: '10px', cursor: 'pointer', fontWeight: 'bold' }}><FaPlus /> Add to AI Learning</button>
        </div>
        <div className="ag-theme-alpine" style={{ flex: 1, width: '100%', minHeight: '250px', borderRadius: '12px', overflow: 'hidden', border: '1px solid #E5E7EB' }}>
          <AgGridReact
            rowData={rowData}
            columnDefs={columnDefs}
            headerHeight={45}
            rowHeight={50}
            theme="legacy"
            rowSelection={{ mode: 'multiRow', checkboxes: false, headerCheckbox: false }}
          />
        </div>
        <button onClick={onClose} style={{ marginTop: '20px', padding: '14px', background: 'white', border: '1px solid #D1D5DB', borderRadius: '12px', cursor: 'pointer', fontWeight: 600, color: '#374151' }}>Dismiss</button>
      </div>
    </div>
  );
};

export default function DrillsResponsive() {
  const location = useLocation();
  const navigate = useNavigate();

  const [isMobile, setIsMobile] = useState(window.innerWidth < 768 || /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent));
  const [drills, setDrills] = useState<Drill[]>([]);
  const [editingDrill, setEditingDrill] = useState<Drill | null>(null);
  const [showVoiceCreator, setShowVoiceCreator] = useState(false);
  const [showMobileDrillCreator, setShowMobileDrillCreator] = useState(false);
  const [showNewDrillOptions, setShowNewDrillOptions] = useState(false);
  const [showGlossary, setShowGlossary] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
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
      let allDrills: Drill[] = [];

      if (status.connected) {
        await syncManager.sync();
        const response = await axios.get(`${API_BASE}/drills/`);
        allDrills = response.data || [];
        await syncManager.saveDrillsToCache(allDrills);
        // Trigger media sync (audio & images only; videos are large and cached on-demand)
        syncManager.syncAllMedia({ includeVideos: false });
      } else {
        allDrills = await syncManager.getDrills();
      }

      const queue = await syncManager.getQueue();
      const localCreates = queue
        .filter(a => a.type === 'CREATE')
        .map(a => ({
          ...a.payload,
          id: a.drillId,
          is_local: true,
          date_created: a.payload.date_created || new Date().toISOString()
        }));

      const serverIds = new Set(allDrills.map(d => d.id));
      const uniqueLocals = localCreates.filter(d => !serverIds.has(d.id));
      allDrills = [...uniqueLocals, ...allDrills];

      const sorted = allDrills.sort((a: Drill, b: Drill) =>
        new Date(b.date_created).getTime() - new Date(a.date_created).getTime()
      );
      setDrills(sorted);
    } catch (error) {
      console.error('Error loading drills:', error);
    }
  };

  useEffect(() => { fetchDrills(); }, [location.search]);

  useEffect(() => {
    if (drills.length === 0) {
      const timer = setTimeout(() => {
        if (drills.length === 0) {
          const popup = document.createElement('div');
          popup.id = 'loading-drills-popup';
          popup.innerHTML = `
            <div style="position: fixed; top: 20px; left: 50%; transform: translateX(-50%); background: #333; color: white; padding: 12px 24px; borderRadius: 30px; zIndex: 99999; boxShadow: 0 4px 12px rgba(0,0,0,0.3); fontWeight: bold; fontSize: 14px; display: flex; alignItems: center; gap: 8px;">
              <span class="spinner">⏳</span> Loading drills from local storage...
            </div>
          `;
          document.body.appendChild(popup);
          setTimeout(() => {
            const p = document.getElementById('loading-drills-popup');
            if (p) p.remove();
          }, 3000);
        }
      }, 500);
      return () => clearTimeout(timer);
    }
  }, [drills]);

  const addNewDrill = async () => {
    if (isCreating) return;
    setIsCreating(true);
    try {
      const tempId = Date.now();
      const newDrillData = {
        id: tempId,
        text_catalan: '',
        text_tachelhit: '',
        text_arabic: '',
        date_created: new Date().toISOString(),
        is_local: true
      };

      await syncManager.queueAction({
        type: 'CREATE',
        drillId: tempId,
        payload: newDrillData
      });

      await new Promise(resolve => setTimeout(resolve, 50));
      await fetchDrills();

      if (isMobile) {
        setEditingDrill(newDrillData);
      }
    } catch (error) {
      console.error('Error creating drill:', error);
      alert('Failed to create drill');
    } finally {
      setIsCreating(false);
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

  return (
    <>
      <div style={{ height: '100vh', display: 'flex', flexDirection: 'column', background: 'var(--bg)', paddingBottom: isMobile ? '64px' : '0' }}>
        <div style={{ background: 'var(--brand-gradient)', padding: isMobile ? '18px 16px' : '22px 28px', boxShadow: 'var(--shadow-lg)', borderBottomLeftRadius: '26px', borderBottomRightRadius: '26px', position: 'relative', overflow: 'hidden' }}>
          {/* decorative glow */}
          <div style={{ position: 'absolute', top: '-60px', right: '-40px', width: '200px', height: '200px', background: 'rgba(255,255,255,0.12)', borderRadius: '50%', filter: 'blur(8px)', pointerEvents: 'none' }} />
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px', position: 'relative', gap: '12px', flexWrap: 'wrap' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <div style={{ width: '44px', height: '44px', borderRadius: '14px', background: 'rgba(255,255,255,0.18)', backdropFilter: 'blur(8px)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '22px', boxShadow: 'inset 0 0 0 1px rgba(255,255,255,0.25)' }}>📚</div>
              <div>
                <h1 style={{ margin: 0, fontSize: isMobile ? '20px' : '24px', fontWeight: 900, color: 'white', letterSpacing: '-0.03em', lineHeight: 1.1 }}>Tachelhit Drills</h1>
                <div style={{ fontSize: '12px', color: 'rgba(255,255,255,0.75)', fontWeight: 600 }}>{filteredDrills.length} drill{filteredDrills.length === 1 ? '' : 's'}</div>
              </div>
            </div>
            <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
              <button
                onClick={() => setShowMobileDrillCreator(true)}
                style={{ padding: '11px 18px', background: 'white', color: 'var(--brand-1)', border: 'none', borderRadius: '12px', fontSize: '14px', fontWeight: 800, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '8px', boxShadow: 'var(--shadow-md)' }}
              >
                <FaPlus /> {isMobile ? '' : 'New Drill'}
              </button>

              {!isMobile && (
                <button
                  onClick={() => navigate('/tests')}
                  style={{ padding: '11px 18px', background: 'var(--emerald)', color: 'white', border: 'none', borderRadius: '12px', fontSize: '14px', fontWeight: 800, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '8px', boxShadow: '0 6px 16px rgba(16,185,129,0.4)' }}
                >
                  📊 Practica
                </button>
              )}

              <button
                onClick={() => {
                  const url = window.location.href;
                  navigator.clipboard.writeText(url);
                  alert(`Filtered link copied to clipboard!\n${url}`);
                }}
                title="Copy filtered link"
                style={{ width: '44px', height: '44px', background: 'rgba(255,255,255,0.16)', color: 'white', border: '1px solid rgba(255,255,255,0.22)', borderRadius: '12px', fontSize: '17px', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', backdropFilter: 'blur(8px)' }}
              >
                <FaLink />
              </button>
              <div style={{ position: 'relative' }}>
                <button
                  disabled={isCreating}
                  onClick={() => setShowNewDrillOptions(!showNewDrillOptions)}
                  style={{ padding: '11px 16px', background: 'rgba(255,255,255,0.16)', color: 'white', border: '1px solid rgba(255,255,255,0.22)', borderRadius: '12px', fontSize: '14px', fontWeight: 700, cursor: 'pointer', opacity: isCreating ? 0.7 : 1, display: 'flex', alignItems: 'center', gap: '8px', backdropFilter: 'blur(8px)' }}
                >
                  {isCreating ? 'Creating…' : 'More'} <FaChevronDown size={11} />
                </button>
                {showNewDrillOptions && (
                  <div style={{ position: 'absolute', top: 'calc(100% + 10px)', right: 0, backgroundColor: 'white', borderRadius: '16px', boxShadow: 'var(--shadow-xl)', zIndex: 1000, minWidth: '230px', display: 'flex', flexDirection: 'column', overflow: 'hidden', border: '1px solid var(--border)' }}>
                    <button
                      onClick={() => { addNewDrill(); setShowNewDrillOptions(false); }}
                      style={{ display: 'flex', alignItems: 'center', gap: '10px', padding: '14px 16px', fontSize: '14px', background: 'none', border: 'none', textAlign: 'left', cursor: 'pointer', color: 'var(--text)', fontWeight: 600, whiteSpace: 'nowrap' }}
                    >
                      <FaPlus style={{ color: 'var(--emerald)' }} /> Create Empty Drill
                    </button>
                    <button
                      onClick={() => { setShowGlossary(true); setShowNewDrillOptions(false); }}
                      style={{ display: 'flex', alignItems: 'center', gap: '10px', padding: '14px 16px', fontSize: '14px', background: 'none', border: 'none', borderTop: '1px solid var(--border)', textAlign: 'left', cursor: 'pointer', color: 'var(--text)', fontWeight: 600, whiteSpace: 'nowrap' }}
                    >
                      <FaBook style={{ color: 'var(--brand-1)' }} /> Manage Glossary
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>
          <div style={{ width: '100%', display: 'flex', gap: '10px', alignItems: 'center', background: 'rgba(255, 255, 255, 0.16)', borderRadius: '14px', padding: '11px 16px', backdropFilter: 'blur(12px)', border: '1px solid rgba(255, 255, 255, 0.22)', position: 'relative', boxSizing: 'border-box' }}>
            <div style={{ color: 'white', opacity: 0.85, fontSize: '16px', flexShrink: 0 }}><FaSearch /></div>
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search drills…"
              style={{ flex: 1, background: 'transparent', border: 'none', color: 'white', fontSize: '15px', outline: 'none', minWidth: '0', fontWeight: 500 }}
            />
            <select
              value={searchCategory}
              onChange={(e) => setSearchCategory(e.target.value)}
              style={{ background: 'rgba(255, 255, 255, 0.22)', border: '1px solid rgba(255, 255, 255, 0.3)', color: 'white', borderRadius: '8px', padding: '7px 9px', fontSize: '12px', fontWeight: 600, outline: 'none', cursor: 'pointer', flexShrink: 0 }}
            >
              <option style={{ color: '#111' }} value="all">All</option>
              <option style={{ color: '#111' }} value="catalan">Català</option>
              <option style={{ color: '#111' }} value="tachelhit">Tachelhit</option>
              <option style={{ color: '#111' }} value="arabic">Arabic</option>
              <option style={{ color: '#111' }} value="tag">Tag</option>
              <option style={{ color: '#111' }} value="author">Author</option>
            </select>
            {searchQuery && <button onClick={() => setSearchQuery('')} style={{ background: 'none', border: 'none', color: 'white', fontSize: '16px', cursor: 'pointer', padding: '0 6px', flexShrink: 0 }}>✕</button>}
          </div>
        </div>
        <div style={{ flex: 1, width: '100%', overflowX: 'hidden', overflowY: 'auto', padding: isMobile ? '12px 4px' : '0', position: 'relative', boxSizing: 'border-box' }}>
          {isCreating && (
            <div style={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(255,255,255,0.5)', zIndex: 10, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <div style={{ padding: '10px 20px', background: '#333', color: 'white', borderRadius: '20px', fontWeight: 'bold' }}>Creating...</div>
            </div>
          )}
          <DrillsGrid rowData={filteredDrills} refreshData={fetchDrills} onEditDrill={(drill) => setEditingDrill(drill)} />
        </div>
        {isMobile && <MobileBottomNav />}
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
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(17, 24, 39, 0.95)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 20000, backdropFilter: 'blur(8px)' }}>
          <div style={{ backgroundColor: 'white', padding: '40px', borderRadius: '24px', width: '600px', maxWidth: '90vw', maxHeight: '90vh', overflow: 'auto', boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '25px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
                <div style={{ background: '#EEF2FF', color: '#4F46E5', width: '50px', height: '50px', borderRadius: '12px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <FaMicrophone size={24} />
                </div>
                <h2 style={{ margin: 0, fontSize: '24px', fontWeight: 800, color: '#111827' }}>Voice Drill Creator</h2>
              </div>
              <button onClick={() => setShowVoiceCreator(false)} style={{ background: '#F3F4F6', border: 'none', borderRadius: '50%', width: '40px', height: '40px', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer', color: '#6B7280' }}><FaTimes size={20} /></button>
            </div>
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

