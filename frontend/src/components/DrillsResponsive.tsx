import '../agGridSetup';
import { useState, useEffect, useRef, useMemo } from 'react';
import { VARIETIES } from '../varieties';
import { FaMicrophone, FaPlay, FaPlus, FaTimes, FaLink, FaChevronDown, FaSearch, FaBook, FaTrash, FaFileImport, FaFilm, FaBookOpen } from 'react-icons/fa';
import axios from 'axios';
import { API_BASE, hasIdentity } from '../config';
import { syncManager } from '../services/OfflineSyncManager';
import { AgGridReact } from 'ag-grid-react';
import 'ag-grid-community/styles/ag-grid.css';
import 'ag-grid-community/styles/ag-theme-alpine.css';
import MobileDrillEditor from './MobileDrillEditor';
import DrillPlayer from './DrillPlayer';
import DrillsGrid from './DrillsGrid';
import { parseTopics, topicLabel, topicsSearchText, topicsMatch } from '../utils/topics';
import VoiceDrillCreator from './VoiceDrillCreator';
import MobileDrillCreator from './MobileDrillCreator';
import { useLocation, useNavigate } from 'react-router-dom';
import { isMobileLayout } from '../utils/layout';
import { toast } from '../toast';

import type { Drill } from '../types';

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
    { field: 'word_sound', headerName: 'So', flex: 1, cellStyle: { fontWeight: 600 } },
    { field: 'correct_spelling', headerName: 'Ortografia', flex: 1, cellStyle: { color: 'var(--brand-1)', fontWeight: 700 } },
    {
      field: 'id',
      headerName: '',
      width: 60,
      cellRenderer: (p: any) => (
        <button
          onClick={() => handleDelete(p.value)}
          style={{ color: 'var(--rose)', border: 'none', background: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', width: '100%' }}
        >
          <FaTrash size={14} />
        </button>
      )
    }
  ];

  return (
    <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(17, 24, 39, 0.8)', zIndex: 30000, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '20px', backdropFilter: 'blur(4px)' }}>
      <div style={{ background: 'var(--surface)', padding: '30px', borderRadius: 'var(--r-xl)', width: '100%', maxWidth: '500px', maxHeight: '90vh', overflow: 'hidden', display: 'flex', flexDirection: 'column', boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <FaBook style={{ color: 'var(--brand-1)' }} />
            <h3 style={{ margin: 0, fontSize: '20px', fontWeight: 800, color: 'var(--text)', fontFamily: 'var(--font-display)' }}>Glossari (IA)</h3>
          </div>
          <button onClick={onClose} style={{ background: 'var(--surface-2)', border: 'none', borderRadius: '50%', width: '32px', height: '32px', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer', color: 'var(--text-soft)' }}><FaTimes /></button>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginBottom: '20px', padding: '15px', background: 'var(--surface-2)', borderRadius: 'var(--r-lg)', border: '1px solid var(--border)' }}>
          <input placeholder="So (p. ex. anayr)" value={newWord.sound} onChange={e => setNewWord({ ...newWord, sound: e.target.value })} style={{ padding: '12px', borderRadius: 'var(--r-md)', border: '1px solid var(--border)', background: 'var(--surface)', color: 'var(--text)', fontSize: '14px' }} />
          <input placeholder="Ortografia correcta" value={newWord.spelling} onChange={e => setNewWord({ ...newWord, spelling: e.target.value })} style={{ padding: '12px', borderRadius: 'var(--r-md)', border: '1px solid var(--border)', background: 'var(--surface)', color: 'var(--text)', fontSize: '14px' }} />
          <button onClick={handleAdd} style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', padding: '12px', background: 'var(--brand-1)', color: 'white', border: 'none', borderRadius: 'var(--r-md)', cursor: 'pointer', fontWeight: 'bold' }}><FaPlus /> Afegeix a l'aprenentatge de la IA</button>
        </div>
        <div className="ag-theme-alpine" style={{ flex: 1, width: '100%', minHeight: '250px', borderRadius: 'var(--r-md)', overflow: 'hidden', border: '1px solid var(--border)' }}>
          <AgGridReact
            rowData={rowData}
            columnDefs={columnDefs}
            headerHeight={45}
            rowHeight={50}
            theme="legacy"
            rowSelection={{ mode: 'multiRow', checkboxes: false, headerCheckbox: false }}
          />
        </div>
        <button onClick={onClose} style={{ marginTop: '20px', padding: '14px', background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--r-md)', cursor: 'pointer', fontWeight: 600, color: 'var(--text-soft)' }}>Tanca</button>
      </div>
    </div>
  );
};

export default function DrillsResponsive() {
  const location = useLocation();
  const navigate = useNavigate();

  const [isMobile, setIsMobile] = useState(isMobileLayout);
  const [drills, setDrills] = useState<Drill[]>([]);
  const [editingDrill, setEditingDrill] = useState<Drill | null>(null);
  const [showVoiceCreator, setShowVoiceCreator] = useState(false);
  const [showMobileDrillCreator, setShowMobileDrillCreator] = useState(false);
  const [showNewDrillOptions, setShowNewDrillOptions] = useState(false);
  const [showGlossary, setShowGlossary] = useState(false);
  const initialParams = new URLSearchParams(location.search);
  const [searchQuery, setSearchQuery] = useState(initialParams.get('q') || '');
  const [searchCategory, setSearchCategory] = useState(initialParams.get('in') || 'all');
  const [filteredDrills, setFilteredDrills] = useState<Drill[]>([]);
  // What to play when you press «Reprodueix-ne N» (#201): the rows you ticked if you ticked
  // any, otherwise everything the current filter left on screen.
  const [selectedDrills, setSelectedDrills] = useState<Drill[]>([]);
  const [playing, setPlaying] = useState<Drill[] | null>(null);
  const [varietyFilter, setVarietyFilter] = useState(initialParams.get('variety') || '');
  // Order: oldest first by default (the course order); newest first right after you create a
  // drill, so you see it; the toggle changes it and the choice is remembered.
  const [newestFirst, setNewestFirstState] = useState<boolean>(() => {
    try { return localStorage.getItem('drills.order') === 'newest'; } catch { return false; }
  });
  const setNewestFirst = (v: boolean) => {
    setNewestFirstState(v);
    try { localStorage.setItem('drills.order', v ? 'newest' : 'oldest'); } catch { /* private mode */ }
  };
  const newDrillOptionsRef = useRef<HTMLDivElement>(null);

  // Dismiss the "Més" dropdown on outside-click or Escape
  useEffect(() => {
    if (!showNewDrillOptions) return;
    const handleMouseDown = (e: MouseEvent) => {
      if (newDrillOptionsRef.current && !newDrillOptionsRef.current.contains(e.target as Node)) {
        setShowNewDrillOptions(false);
      }
    };
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setShowNewDrillOptions(false);
    };
    document.addEventListener('mousedown', handleMouseDown);
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('mousedown', handleMouseDown);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [showNewDrillOptions]);

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
            drill.author?.toLowerCase() || '',
            topicsSearchText(drill.topics)
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
            case 'topic':
              return topicsMatch(drill.topics, searchTerm);
            case 'author':
              return (drill.author?.toLowerCase() || '').includes(searchTerm);
            default:
              return true;
          }
        }
      });
    }

    if (varietyFilter) {
      result = result.filter((drill: Drill) => (drill.variety || '') === varietyFilter);
    }

    // A filtered list that comes from ONE captured video (a story, a lesson) reads
    // in the video's order, not newest-first: sort by the clip's start second.
    const filtering = Boolean(searchQuery.trim() || varietyFilter);
    const sources = new Set(result.map((d: Drill) => d.source_url || ''));
    const timed = result.filter((d: Drill) => d.video_start_time != null).length;
    if (filtering && result.length > 1 && sources.size === 1 && !sources.has('') && timed >= result.length * 0.5) {
      result = [...result].sort((a: Drill, b: Drill) =>
        (a.video_start_time ?? Number.MAX_SAFE_INTEGER) - (b.video_start_time ?? Number.MAX_SAFE_INTEGER) || a.id - b.id);
    } else {
      const t = (d: Drill) => new Date(d.date_created).getTime() || 0;
      result = [...result].sort((a: Drill, b: Drill) => (newestFirst ? t(b) - t(a) || b.id - a.id : t(a) - t(b) || a.id - b.id));
    }

    setFilteredDrills(result);
  }, [drills, searchQuery, searchCategory, varietyFilter, location.search, newestFirst]);

  const collections = useMemo(() => {
    const counts = new Map<string, number>();
    for (const d of drills) {
      // a drill can carry several tags, comma-separated: one chip per tag
      for (const t of (d.tag || '').split(',').map((x) => x.trim()).filter(Boolean)) counts.set(t, (counts.get(t) || 0) + 1);
    }
    return [...counts.entries()].map(([tag, count]) => ({ tag, count })).sort((a, b) => b.count - a.count || a.tag.localeCompare(b.tag));
  }, [drills]);
  // Subjects: what the drills are about (verbs, greetings, food…), from the catalogue in `topics`.
  const subjects = useMemo(() => {
    const counts = new Map<string, number>();
    for (const d of drills) for (const t of parseTopics(d.topics)) counts.set(t, (counts.get(t) || 0) + 1);
    return [...counts.entries()].map(([slug, count]) => ({ slug, count })).sort((a, b) => b.count - a.count || topicLabel(a.slug).localeCompare(topicLabel(b.slug)));
  }, [drills]);

  useEffect(() => {
    const handleResize = () => setIsMobile(isMobileLayout());
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const [loadError, setLoadError] = useState<'error' | 'cached' | null>(null);
  // Adding to the library needs a name (#184). Nobody is registered behind their back: the
  // profile page explains what contributing means, so this asks and takes you there (#202).
  const needsName = () => {
    if (hasIdentity()) return false;
    toast.error('Per afegir-hi coses et cal un nom. Te’n fas un en un moment.');
    navigate('/profile');
    return true;
  };

  // A sentence with no voice would be a silent card: left out of the session, and counted so
  // the person knows why the number shrank.
  const playable = (list: Drill[]) => list.filter((d) => (d.audio_url || '').trim() || (d.audio_tts_shi_url || '').trim());
  const toPlay = selectedDrills.length ? selectedDrills : filteredDrills;
  const startPlaying = () => {
    const withVoice = playable(toPlay);
    if (!withVoice.length) { toast.error('Cap d\u2019aquestes frases t\u00e9 veu encara.'); return; }
    const silent = toPlay.length - withVoice.length;
    if (silent) toast.info(`${silent} ${silent === 1 ? 'frase no t\u00e9 veu i no sonar\u00e0' : 'frases no tenen veu i no sonaran'}.`);
    setPlaying(withVoice);
  };

  const fetchDrills = async () => {
    try {
      let allDrills: Drill[] = [];

      // Always try the server first — Capacitor's Network.getStatus() can
      // misreport "offline" on the web, which used to strand the app on an
      // empty local cache. The cache is only a fallback when the request
      // genuinely fails (real offline / native app without connectivity).
      try {
        const response = await axios.get(`${API_BASE}/drills/`);
        allDrills = Array.isArray(response.data) ? response.data : [];
        setLoadError(null);
      } catch (netErr) {
        console.warn('Server fetch failed, falling back to cached drills:', netErr);
        allDrills = await syncManager.getDrills();
        // Tell the grid the list may be stale/empty because of the network, not
        // because there are no drills (a cold Render start used to show
        // "Encara no hi ha cap drill" on a 600-drill database).
        setLoadError(allDrills.length ? 'cached' : 'error');
        if (allDrills.length) toast.error('Sense resposta del servidor: es mostra la còpia local.');
      }
      // Saving the offline copy happens AFTER, and on its own: a full local storage used to throw
      // here, be caught as a network error, and show «no response from the server» over a library
      // the server had just sent in full.
      if (allDrills.length) syncManager.saveDrillsToCache(allDrills).catch(() => {});

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

  // Refresh when the AI copilot creates/edits drills
  useEffect(() => {
    const onChanged = () => fetchDrills();
    window.addEventListener('drills-changed', onChanged);
    return () => window.removeEventListener('drills-changed', onChanged);
  }, []);

  useEffect(() => {
    if (drills.length === 0) {
      const timer = setTimeout(() => {
        if (drills.length === 0) {
          const popup = document.createElement('div');
          popup.id = 'loading-drills-popup';
          popup.innerHTML = `
            <div style="position: fixed; top: 20px; left: 50%; transform: translateX(-50%); background: #333; color: white; padding: 12px 24px; border-radius: 30px; z-index: 99999; box-shadow: 0 4px 12px rgba(0,0,0,0.3); font-weight: bold; font-size: 14px; display: flex; align-items: center; gap: 8px;">
              <span class="spinner">⏳</span> Carregant els drills de l'emmagatzematge local...
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
      <div className="app-page-fixed" style={{ display: 'flex', flexDirection: 'column', background: 'var(--bg)', paddingBottom: isMobile ? 'env(safe-area-inset-bottom, 0px)' : '0', boxSizing: 'border-box' }}>
        <div style={{ background: 'var(--surface)', padding: isMobile ? '12px 14px' : '14px 24px', borderBottom: '1px solid var(--border)', display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', position: 'relative', gap: '12px', flexWrap: 'wrap' }}>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '10px' }}>
              <h1 style={{ margin: 0, fontSize: isMobile ? '19px' : '22px', fontWeight: 700, color: 'var(--text)', letterSpacing: '-0.02em', fontFamily: 'var(--font-display)' }}>Drills</h1>
              <span style={{ fontSize: '13px', color: 'var(--text-muted)', fontWeight: 600 }}>{filteredDrills.length}</span>
              {playable(toPlay).length > 0 && (
                <button
                  onClick={startPlaying}
                  title={selectedDrills.length ? 'Reprodueix les frases que has triat' : 'Reprodueix el que hi ha filtrat ara mateix'}
                  style={{ padding: '6px 12px', background: 'var(--surface-2)', color: 'var(--brand-1)', border: '1px solid var(--border)', borderRadius: 'var(--r-pill)', fontSize: '13px', fontWeight: 700, cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: '6px', whiteSpace: 'nowrap' }}
                >
                  <FaPlay size={10} /> Reprodueix-ne {playable(toPlay).length}
                  {selectedDrills.length ? ' (triades)' : ''}
                </button>
              )}
            </div>
            <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
              <button
                onClick={() => { if (!needsName()) setShowMobileDrillCreator(true); }}
                aria-label="Nou drill"
                style={{ padding: '10px 16px', background: 'var(--brand-1)', color: '#fff', border: 'none', borderRadius: 'var(--r-md)', fontSize: '14px', fontWeight: 700, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '8px' }}
              >
                <FaPlus /> {isMobile ? '' : 'Nou drill'}
              </button>

              {!isMobile && (
                <button
                  onClick={() => navigate('/tests')}
                  style={{ padding: '10px 16px', background: 'var(--surface)', color: 'var(--emerald)', border: '1px solid var(--emerald)', borderRadius: 'var(--r-md)', fontSize: '14px', fontWeight: 700, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '8px' }}
                >
                  Practica
                </button>
              )}

              <button
                onClick={() => {
                  const u = new URL(window.location.href);
                  u.search = '';
                  if (searchQuery.trim()) u.searchParams.set('q', searchQuery.trim());
                  if (searchCategory !== 'all') u.searchParams.set('in', searchCategory);
                  if (varietyFilter) u.searchParams.set('variety', varietyFilter);
                  navigator.clipboard.writeText(u.toString()).then(() => toast.success('Enllaç filtrat copiat')).catch(() => toast.error("No s'ha pogut copiar"));
                }}
                title="Copia l'enllaç filtrat"
                aria-label="Copia l'enllaç filtrat"
                style={{ width: '40px', height: '40px', background: 'var(--surface-2)', color: 'var(--text-soft)', border: '1px solid var(--border)', borderRadius: 'var(--r-md)', fontSize: '15px', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
              >
                <FaLink />
              </button>
              <div ref={newDrillOptionsRef} style={{ position: 'relative' }}>
                <button
                  onClick={() => setShowNewDrillOptions(!showNewDrillOptions)}
                  style={{ padding: '10px 14px', background: 'var(--surface-2)', color: 'var(--text-soft)', border: '1px solid var(--border)', borderRadius: 'var(--r-md)', fontSize: '14px', fontWeight: 700, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '8px' }}
                >
                  Més <FaChevronDown size={11} />
                </button>
                {showNewDrillOptions && (
                  <div style={{ position: 'absolute', top: 'calc(100% + 10px)', right: 0, backgroundColor: 'var(--surface)', borderRadius: 'var(--r-lg)', boxShadow: 'var(--shadow-xl)', zIndex: 1000, minWidth: '230px', display: 'flex', flexDirection: 'column', overflow: 'hidden', border: '1px solid var(--border)' }}>
                    <button
                      onClick={() => { setShowNewDrillOptions(false); if (!needsName()) setShowMobileDrillCreator(true); }}
                      style={{ display: 'flex', alignItems: 'center', gap: '10px', padding: '14px 16px', fontSize: '14px', background: 'none', border: 'none', textAlign: 'left', cursor: 'pointer', color: 'var(--text)', fontWeight: 600, whiteSpace: 'nowrap' }}
                    >
                      <FaPlus style={{ color: 'var(--emerald)' }} /> Crea un drill buit
                    </button>
                    <button
                      onClick={() => { setShowNewDrillOptions(false); if (!needsName()) navigate('/srt-import'); }}
                      style={{ display: 'flex', alignItems: 'center', gap: '10px', padding: '14px 16px', fontSize: '14px', background: 'none', border: 'none', borderTop: '1px solid var(--border)', textAlign: 'left', cursor: 'pointer', color: 'var(--text)', fontWeight: 600, whiteSpace: 'nowrap' }}
                    >
                      <FaFileImport style={{ color: 'var(--sky)' }} /> Importa subtítols (SRT)
                    </button>
                    <button
                      onClick={() => { navigate('/library'); setShowNewDrillOptions(false); }}
                      style={{ display: 'flex', alignItems: 'center', gap: '10px', padding: '14px 16px', fontSize: '14px', background: 'none', border: 'none', borderTop: '1px solid var(--border)', textAlign: 'left', cursor: 'pointer', color: 'var(--text)', fontWeight: 600, whiteSpace: 'nowrap' }}
                    >
                      <FaFilm style={{ color: 'var(--amber-strong)' }} /> Biblioteca de vídeos
                    </button>
                    <button
                      onClick={() => { navigate('/corpus'); setShowNewDrillOptions(false); }}
                      style={{ display: 'flex', alignItems: 'center', gap: '10px', padding: '14px 16px', fontSize: '14px', background: 'none', border: 'none', borderTop: '1px solid var(--border)', textAlign: 'left', cursor: 'pointer', color: 'var(--text)', fontWeight: 600, whiteSpace: 'nowrap' }}
                    >
                      <FaBookOpen style={{ color: 'var(--sky)' }} /> Corpus i exportacions
                    </button>
                    <button
                      onClick={() => { setShowGlossary(true); setShowNewDrillOptions(false); }}
                      style={{ display: 'flex', alignItems: 'center', gap: '10px', padding: '14px 16px', fontSize: '14px', background: 'none', border: 'none', borderTop: '1px solid var(--border)', textAlign: 'left', cursor: 'pointer', color: 'var(--text)', fontWeight: 600, whiteSpace: 'nowrap' }}
                    >
                      <FaBook style={{ color: 'var(--brand-1)' }} /> Gestiona el glossari
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>
          <div style={{ width: '100%', display: 'flex', flexWrap: isMobile ? 'wrap' : 'nowrap', gap: '10px', alignItems: 'center', background: 'var(--surface-2)', borderRadius: 'var(--r-md)', padding: '10px 14px', border: '1px solid var(--border)', position: 'relative', boxSizing: 'border-box' }}>
            <div style={{ color: 'var(--text-muted)', fontSize: '15px', flexShrink: 0 }}><FaSearch /></div>
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Cerca drills…"
              aria-label="Cerca drills"
              style={{ flex: '1 1 140px', background: 'transparent', border: 'none', color: 'var(--text)', fontSize: '15px', minWidth: '0', fontWeight: 500 }}
            />
            <select
              value={searchCategory}
              onChange={(e) => setSearchCategory(e.target.value)}
              aria-label="Filtra per camp"
              style={{ background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--text-soft)', borderRadius: 'var(--r-sm)', padding: '6px 9px', fontSize: '12px', fontWeight: 600, cursor: 'pointer', flexShrink: 0 }}
            >
              <option value="all">Totes</option>
              <option value="catalan">Català</option>
              <option value="tachelhit">Tamazight</option>
              <option value="arabic">Àrab</option>
              <option value="tag">Etiqueta</option>
              <option value="topic">Tema</option>
              <option value="author">Autor</option>
            </select>
            <select
              value={varietyFilter}
              onChange={(e) => setVarietyFilter(e.target.value)}
              aria-label="Filtra per varietat"
              title="Filtra per varietat"
              style={{ background: 'var(--surface)', border: `1px solid ${varietyFilter ? 'var(--saffron)' : 'var(--border)'}`, color: varietyFilter ? 'var(--saffron-strong)' : 'var(--text-soft)', borderRadius: 'var(--r-sm)', padding: '6px 9px', fontSize: '12px', fontWeight: 700, cursor: 'pointer', flexShrink: isMobile ? 1 : 0, minWidth: 0, maxWidth: '100%' }}
            >
              <option value="">Totes les varietats</option>
              {VARIETIES.map((v) => <option key={v.code} value={v.code}>{v.label}</option>)}
            </select>
            <button
              onClick={() => setNewestFirst(!newestFirst)}
              aria-label={newestFirst ? 'Ordre: més nous primer (canvia a més antics primer)' : 'Ordre: més antics primer (canvia a més nous primer)'}
              title={newestFirst ? 'Més nous primer · clica per veure els més antics primer' : 'Més antics primer · clica per veure els més nous primer'}
              style={{ background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--text-soft)', borderRadius: 'var(--r-sm)', padding: '6px 9px', fontSize: '12px', fontWeight: 700, cursor: 'pointer', flexShrink: 0, whiteSpace: 'nowrap' }}
            >
              {newestFirst ? '↓ Més nous' : '↑ Més antics'}
            </button>
            {searchQuery && <button onClick={() => setSearchQuery('')} aria-label="Esborra la cerca" style={{ background: 'none', border: 'none', color: 'var(--text-muted)', fontSize: '16px', cursor: 'pointer', padding: '0 6px', flexShrink: 0 }}>✕</button>}
          </div>
        </div>
        {/* Collections: one chip per tag (a captured song, story or lesson), by size.
            A tap filters the list to that collection; the same chip again clears it. */}
        {collections.length > 1 && (
          <div role="group" aria-label="Col·leccions" style={{ display: 'flex', gap: '6px', overflowX: 'auto', scrollbarWidth: 'none', padding: isMobile ? '8px 8px 2px' : '8px 0 2px', flexShrink: 0 }}>
            {[{ tag: '', count: drills.length }, ...collections].map(({ tag, count }) => {
              const active = tag ? (searchCategory === 'tag' && searchQuery === tag) : (!searchQuery && !varietyFilter);
              return (
                <button
                  key={tag || '__all'}
                  onClick={() => {
                    if (!tag || active) { setSearchQuery(''); setSearchCategory('all'); setVarietyFilter(''); }
                    else { setSearchCategory('tag'); setSearchQuery(tag); }
                  }}
                  aria-pressed={active}
                  style={{ flexShrink: 0, padding: '6px 11px', borderRadius: 'var(--r-pill)', fontSize: '12px', fontWeight: 700, cursor: 'pointer', whiteSpace: 'nowrap',
                    border: `1px solid ${active ? 'var(--brand-1)' : 'var(--border)'}`, background: active ? 'var(--brand-gradient-soft)' : 'var(--surface)', color: active ? 'var(--brand-1)' : 'var(--text-soft)' }}
                >
                  {tag || 'Tots'} <span style={{ opacity: 0.7, fontWeight: 600 }}>{count}</span>
                </button>
              );
            })}
          </div>
        )}
        {/* Subjects: one chip per topic of the catalogue (what the drill teaches), by size.
            With a subject selected, «Test del tema» makes a test of every drill shown. */}
        {subjects.length > 0 && (
          <div role="group" aria-label="Temes" style={{ display: 'flex', gap: '6px', overflowX: 'auto', scrollbarWidth: 'none', padding: isMobile ? '2px 8px 6px' : '2px 0 6px', flexShrink: 0, alignItems: 'center' }}>
            <span style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-muted)', flexShrink: 0, textTransform: 'uppercase', letterSpacing: '0.04em' }}>Temes</span>
            {searchCategory === 'topic' && searchQuery && filteredDrills.length > 0 && (
              <button
                onClick={async () => {
                  const ids = filteredDrills.slice(0, 200).map((d: Drill) => d.id);
                  try {
                    await axios.post(`${API_BASE}/tests/`, {
                      title: topicLabel(searchQuery), description: `Test del tema «${topicLabel(searchQuery)}» (${ids.length} drills)`,
                      question_type: 'text_input', hint_level: 'none', hint_percentage: 30, hint_tries_before_reveal: 3,
                      time_limit_seconds: null, passing_score: 70, drill_ids: ids.join(','),
                    });
                    toast.success(`Test «${topicLabel(searchQuery)}» creat amb ${ids.length} drills`);
                    navigate('/tests');
                  } catch { toast.error('No s\'ha pogut crear el test'); }
                }}
                title={`Crea un test amb els ${Math.min(filteredDrills.length, 200)} drills d'aquest tema`}
                style={{ flexShrink: 0, padding: '5px 10px', borderRadius: 'var(--r-pill)', fontSize: '12px', fontWeight: 700, cursor: 'pointer', whiteSpace: 'nowrap', border: '1px solid var(--brand-1)', background: 'var(--brand-gradient-soft)', color: 'var(--brand-1)' }}
              >
                🎓 Test del tema ({Math.min(filteredDrills.length, 200)})
              </button>
            )}
            {subjects.map(({ slug, count }) => {
              const active = searchCategory === 'topic' && searchQuery === slug;
              return (
                <button
                  key={slug}
                  onClick={() => {
                    if (active) { setSearchQuery(''); setSearchCategory('all'); }
                    else { setSearchCategory('topic'); setSearchQuery(slug); }
                  }}
                  aria-pressed={active}
                  title={topicLabel(slug)}
                  style={{ flexShrink: 0, padding: '5px 10px', borderRadius: 'var(--r-pill)', fontSize: '12px', fontWeight: 700, cursor: 'pointer', whiteSpace: 'nowrap',
                    border: `1px solid ${active ? 'var(--saffron)' : 'var(--border)'}`, background: active ? 'var(--saffron-soft, var(--surface-2))' : 'var(--surface)', color: active ? 'var(--saffron-strong)' : 'var(--text-soft)' }}
                >
                  {topicLabel(slug)} <span style={{ opacity: 0.7, fontWeight: 600 }}>{count}</span>
                </button>
              );
            })}
          </div>
        )}
        <div style={{ flex: 1, width: '100%', overflowX: 'hidden', overflowY: 'auto', padding: isMobile ? '12px 4px' : '0', position: 'relative', boxSizing: 'border-box' }}>
          <DrillsGrid rowData={filteredDrills} refreshData={fetchDrills} onEditDrill={(drill) => setEditingDrill(drill)} loadError={loadError} onSelectionChange={setSelectedDrills} />
        </div>
      </div>

      {editingDrill && (
        <MobileDrillEditor
          drill={editingDrill}
          onClose={() => setEditingDrill(null)}
          onUpdate={() => {
            fetchDrills();
            if (editingDrill) {
              // Just the one drill (`ids=`), not the whole library again: this used to pull every
              // row a second time to pick a single one out of it (issue #190).
              axios.get(`${API_BASE}/drills/?ids=${editingDrill.id}`).then(response => {
                const updated = response.data[0];
                if (updated) setEditingDrill(updated);
              });
            }
          }}
          onNavigate={handleNavigate}
        />
      )}

      {showVoiceCreator && (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(17, 24, 39, 0.95)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 20000, backdropFilter: 'blur(8px)' }}>
          <div style={{ backgroundColor: 'var(--surface)', padding: '40px', borderRadius: 'var(--r-xl)', width: '600px', maxWidth: '90vw', maxHeight: '90vh', overflow: 'auto', boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '25px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
                <div style={{ background: 'var(--brand-gradient-soft)', color: 'var(--brand-1)', width: '50px', height: '50px', borderRadius: 'var(--r-md)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <FaMicrophone size={24} />
                </div>
                <h2 style={{ margin: 0, fontSize: '24px', fontWeight: 800, color: 'var(--text)', fontFamily: 'var(--font-display)' }}>Creador de drills per veu</h2>
              </div>
              <button onClick={() => setShowVoiceCreator(false)} style={{ background: 'var(--surface-2)', border: 'none', borderRadius: '50%', width: '40px', height: '40px', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer', color: 'var(--text-soft)' }}><FaTimes size={20} /></button>
            </div>
            <VoiceDrillCreator onClose={() => setShowVoiceCreator(false)} onDrillCreated={() => { setNewestFirst(true); fetchDrills(); setShowVoiceCreator(false); }} />
          </div>
        </div>
      )}

      {playing && <DrillPlayer drills={playing} onExit={() => setPlaying(null)} />}
      {showGlossary && <GlossaryModal onClose={() => setShowGlossary(false)} />}

      {showMobileDrillCreator && (
        <MobileDrillCreator onClose={() => setShowMobileDrillCreator(false)} onDrillCreated={() => { setNewestFirst(true); fetchDrills(); setShowMobileDrillCreator(false); }} />
      )}
    </>
  );
}

