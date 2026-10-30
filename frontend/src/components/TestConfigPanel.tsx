import { useState, useEffect } from 'react';
import axios from 'axios';
import { API_BASE } from '../config';
import { toast } from '../toast';
import { whyItFailed } from '../utils/errors';
import { TOPIC_LABELS, parseTopics, topicLabel, topicsSearchText } from '../utils/topics';
import { bibliotecaAlDia } from '../services/biblioteca';

interface Drill {
  id: number;
  text_catalan: string;
  text_tachelhit: string;
  text_arabic?: string;
  tag?: string;
  topics?: string; // subject catalogue slugs (utils/topics.ts)
  verified?: boolean;
  // Add other fields from Drill model if needed for display/search
}

interface TestConfigPanelProps {
  onClose: () => void;
  onTestCreated: (testId: number) => void;
  initialSelectedDrillIds?: number[]; // Optional initial drills
}

const labelStyle: React.CSSProperties = {
  display: 'block',
  marginBottom: '8px',
  fontWeight: 600,
  fontSize: '13px',
  color: 'var(--text-soft)',
};

const inputStyle: React.CSSProperties = {
  width: '100%',
  padding: '11px 14px',
  fontSize: '14px',
  border: '1px solid var(--border)',
  borderRadius: 'var(--r-md)',
  backgroundColor: 'var(--surface-2)',
  color: 'var(--text)',
  fontFamily: 'var(--font-sans)',
  outline: 'none',
  boxSizing: 'border-box',
};

export default function TestConfigPanel({ onClose, onTestCreated, initialSelectedDrillIds = [] }: TestConfigPanelProps) {
  const [config, setConfig] = useState({
    title: '',
    description: '',
    question_type: 'text_input',
    hint_level: 'none',
    hint_percentage: 30,
    hint_tries_before_reveal: 3,
    time_limit_seconds: 0,
    passing_score: 70,
    playback_direction: 'cat-tash', // Default value
  });

  const [allDrills, setAllDrills] = useState<Drill[]>([]);
  const [selectedDrills, setSelectedDrills] = useState<Drill[]>([]);
  const [drillSearchTerm, setDrillSearchTerm] = useState('');

  useEffect(() => {
    loadAllDrills();
  }, []);

  useEffect(() => {
    // Initialize selected drills from initialSelectedDrillIds prop
    if (allDrills.length > 0 && initialSelectedDrillIds.length > 0) {
      const initialSelection = initialSelectedDrillIds.map(id => allDrills.find(drill => drill.id === id)).filter((d): d is Drill => d !== undefined);
      setSelectedDrills(initialSelection);
    }
  }, [allDrills, initialSelectedDrillIds]);

  const loadAllDrills = async () => {
    try {
      setAllDrills(await bibliotecaAlDia());
    } catch (error) {
      console.error('Error loading all drills:', error);
    }
  };

  const handleCreate = async () => {
    if (!config.title.trim()) {
      toast.error('Posa un títol al test');
      return;
    }

    if (selectedDrills.length === 0) {
      toast.error('Selecciona almenys un drill');
      return;
    }

    try {
      const response = await axios.post(`${API_BASE}/tests/`, {
        ...config,
        drill_ids: selectedDrills.map(d => d.id).join(','),
        time_limit_seconds: config.time_limit_seconds || null,
      });

      toast.success('Test creat correctament');
      onTestCreated(response.data.id);
      onClose();
    } catch (error) {
      console.error('Error creating test:', error);
      toast.error(whyItFailed(error, 'No s\'ha pogut crear el test'));
    }
  };

  const handleRemoveDrill = (drillId: number) => {
    setSelectedDrills(prev => prev.filter(d => d.id !== drillId));
  };

  const handleAddDrill = (drill: Drill) => {
    if (!selectedDrills.some(d => d.id === drill.id)) {
      setSelectedDrills(prev => [...prev, drill]);
    }
    setDrillSearchTerm(''); // Clear search after adding
  };

  // Subject filter: a test is usually about ONE subject (verbs, greetings…), so the picker
  // can show every drill of a subject and add them all at once.
  const [topicFilter, setTopicFilter] = useState('');
  const subjectCounts = (() => {
    const c = new Map<string, number>();
    for (const d of allDrills) for (const t of parseTopics(d.topics)) c.set(t, (c.get(t) || 0) + 1);
    return [...c.entries()].sort((a, b) => b[1] - a[1]);
  })();
  const filteredAvailableDrills = allDrills.filter(drill =>
    !selectedDrills.some(sd => sd.id === drill.id) &&
    (!topicFilter || parseTopics(drill.topics).includes(topicFilter)) &&
    ((drill.text_catalan?.toLowerCase() || '').includes(drillSearchTerm.toLowerCase()) ||
      (drill.text_tachelhit?.toLowerCase() || '').includes(drillSearchTerm.toLowerCase()) ||
      (drill.text_arabic?.toLowerCase() || '').includes(drillSearchTerm.toLowerCase()) ||
      (drill.tag?.toLowerCase() || '').includes(drillSearchTerm.toLowerCase()) ||
      topicsSearchText(drill.topics).includes(drillSearchTerm.toLowerCase()) ||
      drill.id.toString().includes(drillSearchTerm)))
    ;
  // Verified drills first: a test should prefer what a speaker has confirmed.
  filteredAvailableDrills.sort((a, b) => Number(!!b.verified) - Number(!!a.verified));
  const addAllShown = () => {
    const shown = filteredAvailableDrills.slice(0, 200);
    if (!shown.length) return;
    setSelectedDrills(prev => [...prev, ...shown.filter(d => !prev.some(p => p.id === d.id))]);
    if (!config.title && topicFilter) setConfig({ ...config, title: topicLabel(topicFilter) });
  };

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(15,23,42,0.7)',
      backdropFilter: 'blur(6px)',
      WebkitBackdropFilter: 'blur(6px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 10000,
      padding: 'max(12px, env(safe-area-inset-top, 0px)) 12px max(12px, env(safe-area-inset-bottom, 0px))',
      fontFamily: 'var(--font-sans)',
    }}>
      <div style={{
        backgroundColor: 'var(--surface)',
        padding: 'clamp(16px, 4vw, 28px)',
        borderRadius: 'var(--r-2xl)',
        width: '600px',
        maxWidth: '100%',
        maxHeight: '90vh',
        overflow: 'auto',
        boxShadow: 'var(--shadow-xl)',
        border: '1px solid var(--border)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '22px' }}>
          <h2 style={{ margin: 0, fontSize: '22px', fontWeight: 800, color: 'var(--text)', letterSpacing: '-0.02em' }}>
            Nou test
          </h2>
          <button
            onClick={onClose}
            aria-label='Tanca'
            style={{
              border: 'none',
              background: 'var(--surface-2)',
              color: 'var(--text-soft)',
              width: '34px',
              height: '34px',
              borderRadius: 'var(--r-pill)',
              cursor: 'pointer',
              fontSize: '18px',
              lineHeight: 1,
            }}
          >
            ×
          </button>
        </div>

        {/* Drill Management Section for New Test */}
        <div style={{ marginBottom: '20px', background: 'var(--surface-2)', border: '1px solid var(--border)', borderRadius: 'var(--r-xl)', padding: '18px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '14px' }}>
            <h3 style={{ margin: 0, fontSize: '16px', fontWeight: 700, color: 'var(--text)' }}>Tria els drills</h3>
            <span style={{
              background: 'var(--brand-gradient-soft)',
              color: 'var(--brand-1)',
              fontSize: '12px',
              fontWeight: 700,
              padding: '2px 10px',
              borderRadius: 'var(--r-pill)',
            }}>
              {selectedDrills.length}
            </span>
          </div>

          {/* Currently selected drills (for display, no reorder for creation) */}
          <div style={{ marginBottom: '14px', maxHeight: '150px', overflowY: 'auto', background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--r-md)', padding: '8px' }}>
            {selectedDrills.length === 0 ? (
              <p style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '20px', margin: 0, fontSize: '13px' }}>Encara no has triat cap drill.</p>
            ) : (
              selectedDrills.map((drill, index) => (
                <div key={drill.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '10px', padding: '8px 10px', borderRadius: 'var(--r-sm)', marginBottom: index < selectedDrills.length - 1 ? '4px' : 0, background: 'var(--surface-2)' }}>
                  <span style={{ fontSize: '14px', color: 'var(--text)' }}>
                    <span style={{ color: 'var(--text-muted)', fontWeight: 600 }}>{index + 1}.</span> {drill.text_catalan}
                    <span style={{ color: 'var(--text-muted)', fontSize: '12px' }}> (#{drill.id})</span>
                  </span>
                  <button
                    onClick={() => handleRemoveDrill(drill.id)}
                    style={{ background: 'var(--rose-soft)', color: 'var(--rose)', border: 'none', borderRadius: 'var(--r-sm)', padding: '5px 12px', cursor: 'pointer', fontSize: '12px', fontWeight: 600 }}
                  >
                    Treu
                  </button>
                </div>
              ))
            )}
          </div>

          {/* Add new drills search */}
          <div style={{ paddingTop: '14px', borderTop: '1px solid var(--border)' }}>
            <h4 style={{ margin: '0 0 10px 0', fontSize: '13px', fontWeight: 600, color: 'var(--text-soft)' }}>Drills disponibles</h4>
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center', marginBottom: '8px', flexWrap: 'wrap' }}>
              <select value={topicFilter} onChange={(e) => setTopicFilter(e.target.value)} aria-label="Tema"
                style={{ ...inputStyle, width: 'auto', flex: 1, minWidth: '160px', margin: 0 }}>
                <option value="">Tots els temes</option>
                {subjectCounts.map(([slug, n]) => <option key={slug} value={slug}>{TOPIC_LABELS[slug] || slug} ({n})</option>)}
              </select>
              <button type="button" onClick={addAllShown} disabled={!filteredAvailableDrills.length}
                title="Afegeix al test tots els drills que es mostren (màxim 200)"
                style={{ padding: '8px 12px', background: 'var(--brand-gradient)', color: 'white', border: 'none', borderRadius: 'var(--r-md)', fontWeight: 700, cursor: 'pointer', fontSize: '13px', opacity: filteredAvailableDrills.length ? 1 : 0.5 }}>
                Afegeix-los tots ({Math.min(filteredAvailableDrills.length, 200)})
              </button>
            </div>
            <input
              type='text'
              placeholder='Cerca per text, tema, etiqueta o ID…'
              value={drillSearchTerm}
              onChange={(e) => setDrillSearchTerm(e.target.value)}
              style={inputStyle}
            />
            <div style={{ maxHeight: '150px', overflowY: 'auto', background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--r-md)', marginTop: '10px', padding: '6px' }}>
              {filteredAvailableDrills.length > 0 ? (
                (drillSearchTerm.length > 0 ? filteredAvailableDrills : filteredAvailableDrills.slice(0, 30)).map(drill => (
                  <div key={drill.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '10px', padding: '8px 10px', borderRadius: 'var(--r-sm)', marginBottom: '4px', background: 'var(--surface-2)' }}>
                    <span style={{ fontSize: '14px', color: 'var(--text)' }}>
                      <span style={{ color: 'var(--text-muted)', fontSize: '12px' }}>#{drill.id}</span> {drill.verified ? <span title="Verificat" style={{ color: 'var(--emerald)', fontWeight: 800 }}>✓ </span> : null}{drill.text_catalan}
                    </span>
                    <button
                      onClick={() => handleAddDrill(drill)}
                      style={{ background: 'var(--brand-gradient)', color: 'white', border: 'none', borderRadius: 'var(--r-sm)', padding: '5px 14px', cursor: 'pointer', fontSize: '12px', fontWeight: 600, boxShadow: 'var(--shadow-brand)' }}
                    >
                      Afegeix
                    </button>
                  </div>
                ))
              ) : (
                <p style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '12px', margin: 0, fontSize: '13px' }}>Cap drill coincideix.</p>
              )}
            </div>
          </div>
        </div>

        <div style={{ marginBottom: '16px' }}>
          <label style={labelStyle}>
            Títol del test *
          </label>
          <input
            type='text'
            value={config.title}
            onChange={(e) => setConfig({ ...config, title: e.target.value })}
            placeholder='p. ex. Salutacions bàsiques'
            style={inputStyle}
          />
        </div>

        <div style={{ marginBottom: '16px' }}>
          <label style={labelStyle}>
            Descripció
          </label>
          <textarea
            value={config.description}
            onChange={(e) => setConfig({ ...config, description: e.target.value })}
            placeholder='Descripció (opcional)'
            rows={3}
            style={{ ...inputStyle, resize: 'vertical' }}
          />
        </div>

        <div style={{ marginBottom: '16px' }}>
          <label style={labelStyle}>
            Tipus de pregunta
          </label>
          <select
            value={config.question_type}
            onChange={(e) => setConfig({ ...config, question_type: e.target.value })}
            style={inputStyle}
          >
            <option value='text_input'>Text · l'alumne escriu la resposta</option>
            <option value='audio'>Àudio · escolta i escriu</option>
            <option value='video'>Vídeo · mira i escriu</option>
            <option value='combined'>Combinat · fa servir el mèdia disponible</option>
          </select>
        </div>

        {/* Playback Direction Field */}
        <div style={{ marginBottom: '16px' }}>
          <label style={labelStyle}>
            Direcció
          </label>
          <select
            value={config.playback_direction}
            onChange={(e) => setConfig({ ...config, playback_direction: e.target.value })}
            style={inputStyle}
          >
            <option value='cat-tash'>Català (pregunta) → Tachelhit (resposta)</option>
            <option value='tash-cat'>Tachelhit (pregunta) → Català (resposta)</option>
            <option value='ar-tash'>Àrab (pregunta) → Tachelhit (resposta)</option>
            <option value='tash-ar'>Tachelhit (pregunta) → Àrab (resposta)</option>
          </select>
        </div>

        <div style={{ marginBottom: '16px' }}>
          <label style={labelStyle}>
            Pistes
          </label>
          <select
            value={config.hint_level}
            onChange={(e) => setConfig({ ...config, hint_level: e.target.value })}
            style={inputStyle}
          >
            <option value='none'>Sense pistes</option>
            <option value='partial'>Algunes lletres (%)</option>
            <option value='full_after_tries'>Resposta sencera després de N intents</option>
          </select>
        </div>

        {config.hint_level === 'partial' && (
          <div style={{ marginBottom: '16px', marginLeft: '4px', padding: '14px 16px', background: 'var(--brand-gradient-soft)', borderRadius: 'var(--r-md)', border: '1px solid var(--border)' }}>
            <label style={{ ...labelStyle, marginBottom: '10px', color: 'var(--text)' }}>
              Percentatge de lletres mostrades: <span style={{ color: 'var(--brand-1)', fontWeight: 700 }}>{config.hint_percentage}%</span>
            </label>
            <input
              type='range'
              min='10'
              max='80'
              value={config.hint_percentage}
              onChange={(e) => setConfig({ ...config, hint_percentage: parseInt(e.target.value) })}
              style={{ width: '100%', accentColor: 'var(--brand-1)' }}
            />
          </div>
        )}

        {config.hint_level === 'full_after_tries' && (
          <div style={{ marginBottom: '16px', marginLeft: '4px', padding: '14px 16px', background: 'var(--brand-gradient-soft)', borderRadius: 'var(--r-md)', border: '1px solid var(--border)' }}>
            <label style={{ ...labelStyle, marginBottom: '10px', color: 'var(--text)' }}>
              Intents abans de mostrar la resposta:
            </label>
            <input
              type='number'
              min='1'
              max='10'
              value={config.hint_tries_before_reveal}
              onChange={(e) => setConfig({ ...config, hint_tries_before_reveal: parseInt(e.target.value) })}
              style={{ ...inputStyle, width: '110px' }}
            />
          </div>
        )}

        <div style={{ marginBottom: '16px' }}>
          <label style={labelStyle}>
            Temps límit (segons per pregunta, 0 = sense límit)
          </label>
          <input
            type='number'
            min='0'
            value={config.time_limit_seconds}
            onChange={(e) => setConfig({ ...config, time_limit_seconds: parseInt(e.target.value) })}
            style={{ ...inputStyle, width: '160px' }}
          />
        </div>

        <div style={{ marginBottom: '24px', padding: '14px 16px', background: 'var(--emerald-soft)', borderRadius: 'var(--r-md)', border: '1px solid var(--border)' }}>
          <label style={{ ...labelStyle, marginBottom: '10px', color: 'var(--text)' }}>
            Nota per aprovar: <span style={{ color: 'var(--emerald)', fontWeight: 700 }}>{config.passing_score}%</span>
          </label>
          <input
            type='range'
            min='0'
            max='100'
            value={config.passing_score}
            onChange={(e) => setConfig({ ...config, passing_score: parseInt(e.target.value) })}
            style={{ width: '100%', accentColor: 'var(--emerald)' }}
          />
        </div>

        <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
          <button
            onClick={onClose}
            style={{
              padding: '11px 22px',
              fontSize: '14px',
              border: '1px solid var(--border-strong)',
              borderRadius: 'var(--r-md)',
              backgroundColor: 'var(--surface)',
              color: 'var(--text-soft)',
              cursor: 'pointer',
              fontWeight: 600,
            }}
          >
            Cancel·la
          </button>
          <button
            onClick={handleCreate}
            style={{
              padding: '11px 26px',
              fontSize: '14px',
              border: 'none',
              borderRadius: 'var(--r-md)',
              background: 'var(--brand-gradient)',
              color: 'white',
              cursor: 'pointer',
              fontWeight: 700,
              boxShadow: 'var(--shadow-brand)',
            }}
          >
            Crea el test
          </button>
        </div>
      </div>
    </div>
  );
}
