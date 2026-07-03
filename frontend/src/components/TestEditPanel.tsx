import { useState, useEffect } from 'react';
import axios from 'axios';
import { API_BASE } from '../config';
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
} from '@dnd-kit/core';
import type { DragEndEvent } from '@dnd-kit/core';
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';

// Define Test and Drill interfaces for better typing
interface Test {
  id: number;
  title: string;
  description: string;
  question_type: string;
  hint_level: string;
  hint_percentage: number;
  hint_tries_before_reveal: number;
  time_limit_seconds: number;
  passing_score: number;
  drill_ids: string;
  playback_direction: string; // New field
}

interface Drill {
  id: number;
  text_catalan: string;
  text_tachelhit: string;
  text_arabic?: string;
  // Include other fields if needed for display or filtering
}

interface TestEditPanelProps {
  testId: number;
  onClose: () => void;
  onTestUpdated: () => void;
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

// SortableItem component for drag and drop
function SortableItem({ drill, index, onRemove }: { drill: Drill; index: number; onRemove: (id: number) => void }) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: drill.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  return (
    <div
      ref={setNodeRef}
      style={{
        ...style,
        userSelect: 'none',
        padding: '10px 12px',
        margin: '0 0 6px 0',
        minHeight: '30px',
        backgroundColor: 'var(--surface-2)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--r-md)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        gap: '10px',
        boxShadow: isDragging ? 'var(--shadow-md)' : 'var(--shadow-xs)',
        cursor: 'grab',
      }}
      {...attributes}
      {...listeners}
    >
      <span style={{ fontSize: '14px', color: 'var(--text)', display: 'flex', alignItems: 'center', gap: '8px' }}>
        <span style={{ color: 'var(--text-muted)' }}>⠿</span>
        <span><span style={{ color: 'var(--text-muted)', fontWeight: 600 }}>{index + 1}.</span> {drill.text_catalan}
        <span style={{ color: 'var(--text-muted)', fontSize: '12px' }}> (#{drill.id})</span></span>
      </span>
      <button
        onClick={(e) => {
          e.stopPropagation();
          onRemove(drill.id);
        }}
        style={{ background: 'var(--rose-soft)', color: 'var(--rose)', border: 'none', borderRadius: 'var(--r-sm)', padding: '5px 12px', cursor: 'pointer', fontSize: '12px', fontWeight: 600 }}
      >
        Remove
      </button>
    </div>
  );
}

export default function TestEditPanel({ testId, onClose, onTestUpdated }: TestEditPanelProps) {
  const [config, setConfig] = useState<Test>({
    id: 0, // Placeholder
    title: '',
    description: '',
    question_type: 'text_input',
    hint_level: 'none',
    hint_percentage: 30,
    hint_tries_before_reveal: 3,
    time_limit_seconds: 0,
    passing_score: 70,
    drill_ids: '',
    playback_direction: 'cat-tash', // Default value
  });
  const [loading, setLoading] = useState(true);
  const [allDrills, setAllDrills] = useState<Drill[]>([]);
  const [selectedDrills, setSelectedDrills] = useState<Drill[]>([]);
  const [drillSearchTerm, setDrillSearchTerm] = useState('');

  // Set up sensors for drag and drop
  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  useEffect(() => {
    loadTestAndDrills();
  }, [testId]);

  const loadTestAndDrills = async () => {
    setLoading(true);
    try {
      const [testResponse, drillsResponse] = await Promise.all([
        axios.get(`${API_BASE}/tests/${testId}`),
        axios.get(`${API_BASE}/drills/`)
      ]);

      const testData = testResponse.data;
      const allDrillsData: Drill[] = drillsResponse.data;

      setConfig({
        id: testData.id,
        title: testData.title,
        description: testData.description || '',
        question_type: testData.question_type,
        hint_level: testData.hint_level,
        hint_percentage: testData.hint_percentage || 30,
        hint_tries_before_reveal: testData.hint_tries_before_reveal || 3,
        time_limit_seconds: testData.time_limit_seconds || 0,
        passing_score: testData.passing_score,
        drill_ids: testData.drill_ids,
        playback_direction: testData.playback_direction || 'cat-tash',
      });
      setAllDrills(allDrillsData);

      if (testData.drill_ids) {
        const ids = testData.drill_ids.split(',').map(Number);
        const currentSelected = ids.map((id: number) => allDrillsData.find((d: Drill) => d.id === id)).filter((d: Drill | undefined): d is Drill => d !== undefined);
        setSelectedDrills(currentSelected);
      } else {
        setSelectedDrills([]);
      }
      setLoading(false);
    } catch (error) {
      console.error('Error loading test or drills:', error);
      alert('Failed to load test or drills');
      onClose();
    }
  };

  const handleUpdate = async () => {
    if (!config.title.trim()) {
      alert('Please enter a test title');
      return;
    }

    try {
      await axios.put(`${API_BASE}/tests/${testId}`, {
        ...config,
        drill_ids: selectedDrills.map(d => d.id).join(','), // Update drill_ids from state
        time_limit_seconds: config.time_limit_seconds || null,
      });

      alert('Test updated successfully!');
      onTestUpdated();
      onClose();
    } catch (error) {
      console.error('Error updating test:', error);
      alert('Failed to update test');
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

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;

    if (active.id !== over?.id) {
      setSelectedDrills((items) => {
        const oldIndex = items.findIndex((item) => item.id === active.id);
        const newIndex = items.findIndex((item) => item.id === over?.id);

        return arrayMove(items, oldIndex, newIndex);
      });
    }
  };

  const filteredAvailableDrills = allDrills.filter(drill =>
    !selectedDrills.some(sd => sd.id === drill.id) &&
    ((drill.text_catalan?.toLowerCase() || '').includes(drillSearchTerm.toLowerCase()) ||
      (drill.text_tachelhit?.toLowerCase() || '').includes(drillSearchTerm.toLowerCase()) ||
      (drill.text_arabic?.toLowerCase() || '').includes(drillSearchTerm.toLowerCase()) ||
      drill.id.toString().includes(drillSearchTerm)))
    ;

  if (loading) {
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
        fontFamily: 'var(--font-sans)',
      }}>
        <div style={{ color: 'white', fontSize: '16px', fontWeight: 600 }}>Loading test...</div>
      </div>
    );
  }

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
      padding: '20px',
      fontFamily: 'var(--font-sans)',
    }}>
      <div style={{
        backgroundColor: 'var(--surface)',
        padding: '28px',
        borderRadius: 'var(--r-2xl)',
        width: '700px', // Increased width
        maxWidth: '100%',
        maxHeight: '90vh',
        overflow: 'auto',
        boxShadow: 'var(--shadow-xl)',
        border: '1px solid var(--border)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '22px' }}>
          <h2 style={{ margin: 0, fontSize: '22px', fontWeight: 800, color: 'var(--text)', letterSpacing: '-0.02em' }}>
            Edit Test
          </h2>
          <button
            onClick={onClose}
            aria-label='Close'
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

        <div style={{ marginBottom: '16px' }}>
          <label style={labelStyle}>
            Test Title *
          </label>
          <input
            type='text'
            value={config.title}
            onChange={(e) => setConfig({ ...config, title: e.target.value })}
            placeholder='e.g., Basic Greetings Test'
            style={inputStyle}
          />
        </div>

        <div style={{ marginBottom: '16px' }}>
          <label style={labelStyle}>
            Description
          </label>
          <textarea
            value={config.description}
            onChange={(e) => setConfig({ ...config, description: e.target.value })}
            placeholder='Optional description'
            rows={3}
            style={{ ...inputStyle, resize: 'vertical' }}
          />
        </div>

        <div style={{ marginBottom: '16px' }}>
          <label style={labelStyle}>
            Question Type
          </label>
          <select
            value={config.question_type}
            onChange={(e) => setConfig({ ...config, question_type: e.target.value })}
            style={inputStyle}
          >
            <option value='text_input'>Text Input - Student writes Tachelhit</option>
            <option value='audio'>Audio Recognition - Listen and write</option>
            <option value='video'>Video - Watch and write</option>
            <option value='combined'>Combined - Mix of all types (uses available media)</option>
          </select>
        </div>

        {/* New Playback Direction Field */}
        <div style={{ marginBottom: '16px' }}>
          <label style={labelStyle}>
            Playback Direction
          </label>
          <select
            value={config.playback_direction}
            onChange={(e) => setConfig({ ...config, playback_direction: e.target.value })}
            style={inputStyle}
          >
            <option value='cat-tash'>Catalan (Question) → Tachelhit (Answer)</option>
            <option value='tash-cat'>Tachelhit (Question) → Catalan (Answer)</option>
            <option value='ar-tash'>Arabic (Question) → Tachelhit (Answer)</option>
            <option value='tash-ar'>Tachelhit (Question) → Arabic (Answer)</option>
          </select>
        </div>

        <div style={{ marginBottom: '16px' }}>
          <label style={labelStyle}>
            Hint Level
          </label>
          <select
            value={config.hint_level}
            onChange={(e) => setConfig({ ...config, hint_level: e.target.value })}
            style={inputStyle}
          >
            <option value='none'>No Hints</option>
            <option value='partial'>Partial Letters (%)</option>
            <option value='full_after_tries'>Full Reveal After X Tries</option>
          </select>
        </div>

        {config.hint_level === 'partial' && (
          <div style={{ marginBottom: '16px', marginLeft: '4px', padding: '14px 16px', background: 'var(--brand-gradient-soft)', borderRadius: 'var(--r-md)', border: '1px solid var(--border)' }}>
            <label style={{ ...labelStyle, marginBottom: '10px', color: 'var(--text)' }}>
              Percentage of letters to reveal: <span style={{ color: 'var(--brand-1)', fontWeight: 700 }}>{config.hint_percentage}%</span>
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
              Number of tries before revealing:
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
            Time Limit (seconds per question, 0 = no limit)
          </label>
          <input
            type='number'
            min='0'
            value={config.time_limit_seconds}
            onChange={(e) => setConfig({ ...config, time_limit_seconds: parseInt(e.target.value) })}
            style={{ ...inputStyle, width: '160px' }}
          />
        </div>

        <div style={{ marginBottom: '20px', padding: '14px 16px', background: 'var(--emerald-soft)', borderRadius: 'var(--r-md)', border: '1px solid var(--border)' }}>
          <label style={{ ...labelStyle, marginBottom: '10px', color: 'var(--text)' }}>
            Passing Score: <span style={{ color: 'var(--emerald)', fontWeight: 700 }}>{config.passing_score}%</span>
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

        {/* Drill Management Section - Updated */}
        <div style={{ marginBottom: '24px', background: 'var(--surface-2)', border: '1px solid var(--border)', borderRadius: 'var(--r-xl)', padding: '18px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '14px' }}>
            <h3 style={{ margin: 0, fontSize: '16px', fontWeight: 700, color: 'var(--text)' }}>Manage Drills</h3>
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
            <span style={{ marginLeft: 'auto', fontSize: '12px', color: 'var(--text-muted)' }}>Drag to reorder</span>
          </div>

          <DndContext
            sensors={sensors}
            collisionDetection={closestCenter}
            onDragEnd={handleDragEnd}
          >
            <SortableContext
              items={selectedDrills.map(d => d.id)}
              strategy={verticalListSortingStrategy}
            >
              <div style={{ marginBottom: '14px', maxHeight: '250px', overflowY: 'auto', background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--r-md)', padding: '8px' }}>
                {selectedDrills.length === 0 ? (
                  <p style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '20px', margin: 0, fontSize: '13px' }}>No drills selected for this test.</p>
                ) : (
                  selectedDrills.map((drill, index) => (
                    <SortableItem
                      key={drill.id}
                      drill={drill}
                      index={index}
                      onRemove={handleRemoveDrill}
                    />
                  ))
                )}
              </div>
            </SortableContext>
          </DndContext>

          {/* Add new drills section */}
          <div style={{ paddingTop: '14px', borderTop: '1px solid var(--border)' }}>
            <h4 style={{ margin: '0 0 10px 0', fontSize: '13px', fontWeight: 600, color: 'var(--text-soft)' }}>Add Drills</h4>
            <input
              type='text' // Changed to text for search
              placeholder='Search by ID or text...'
              value={drillSearchTerm}
              onChange={(e) => setDrillSearchTerm(e.target.value)}
              style={inputStyle}
            />
            <div style={{ maxHeight: '150px', overflowY: 'auto', background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--r-md)', marginTop: '10px', padding: '6px' }}>
              {drillSearchTerm.length > 0 && filteredAvailableDrills.length > 0 ? (
                filteredAvailableDrills.map(drill => (
                  <div key={drill.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '10px', padding: '8px 10px', borderRadius: 'var(--r-sm)', marginBottom: '4px', background: 'var(--surface-2)' }}>
                    <span style={{ fontSize: '14px', color: 'var(--text)' }}>
                      <span style={{ color: 'var(--text-muted)', fontSize: '12px' }}>#{drill.id}</span> {drill.text_catalan}
                    </span>
                    <button
                      onClick={() => handleAddDrill(drill)}
                      style={{ background: 'var(--brand-gradient)', color: 'white', border: 'none', borderRadius: 'var(--r-sm)', padding: '5px 14px', cursor: 'pointer', fontSize: '12px', fontWeight: 600, boxShadow: 'var(--shadow-brand)' }}
                    >
                      Add
                    </button>
                  </div>
                ))
              ) : drillSearchTerm.length > 0 ? (
                <p style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '12px', margin: 0, fontSize: '13px' }}>No matching drills found.</p>
              ) : (
                <p style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '12px', margin: 0, fontSize: '13px' }}>Type to search available drills.</p>
              )}
            </div>
          </div>
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
            Cancel
          </button>
          <button
            onClick={handleUpdate}
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
            Update Test
          </button>
        </div>
      </div>
    </div>
  );
}
