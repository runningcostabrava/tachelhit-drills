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
        padding: '8px',
        margin: '0 0 8px 0',
        minHeight: '30px',
        backgroundColor: 'white',
        border: '1px solid #ddd',
        borderRadius: '4px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
        cursor: 'grab',
      }}
      {...attributes}
      {...listeners}
    >
      <span>{index + 1}. {drill.text_catalan} ({drill.id})</span>
      <button
        onClick={(e) => {
          e.stopPropagation();
          onRemove(drill.id);
        }}
        style={{ background: '#ff4444', color: 'white', border: 'none', borderRadius: '4px', padding: '4px 8px', cursor: 'pointer' }}
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
    (drill.text_catalan.toLowerCase().includes(drillSearchTerm.toLowerCase()) ||
      drill.text_tachelhit.toLowerCase().includes(drillSearchTerm.toLowerCase()) ||
      (drill.text_arabic && drill.text_arabic.toLowerCase().includes(drillSearchTerm.toLowerCase())) ||
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
        backgroundColor: 'rgba(0,0,0,0.7)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 10000,
      }}>
        <div style={{ color: 'white', fontSize: '18px' }}>Loading test...</div>
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
      backgroundColor: 'rgba(0,0,0,0.7)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 10000,
    }}>
      <div style={{
        backgroundColor: 'white',
        padding: '30px',
        borderRadius: '12px',
        width: '700px', // Increased width
        maxHeight: '90vh',
        overflow: 'auto',
      }}>
        <h2 style={{ marginTop: 0, marginBottom: '20px' }}>Edit Test Configuration</h2>

        <div style={{ marginBottom: '15px' }}>
          <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>
            Test Title *
          </label>
          <input
            type='text'
            value={config.title}
            onChange={(e) => setConfig({ ...config, title: e.target.value })}
            placeholder='e.g., Basic Greetings Test'
            style={{
              width: '100%',
              padding: '8px',
              fontSize: '14px',
              border: '1px solid #ccc',
              borderRadius: '4px',
            }}
          />
        </div>

        <div style={{ marginBottom: '15px' }}>
          <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>
            Description
          </label>
          <textarea
            value={config.description}
            onChange={(e) => setConfig({ ...config, description: e.target.value })}
            placeholder='Optional description'
            rows={3}
            style={{
              width: '100%',
              padding: '8px',
              fontSize: '14px',
              border: '1px solid #ccc',
              borderRadius: '4px',
            }}
          />
        </div>

        <div style={{ marginBottom: '15px' }}>
          <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>
            Question Type
          </label>
          <select
            value={config.question_type}
            onChange={(e) => setConfig({ ...config, question_type: e.target.value })}
            style={{
              width: '100%',
              padding: '8px',
              fontSize: '14px',
              border: '1px solid #ccc',
              borderRadius: '4px',
            }}
          >
            <option value='text_input'>Text Input - Student writes Tachelhit</option>
            <option value='audio'>Audio Recognition - Listen and write</option>
            <option value='video'>Video - Watch and write</option>
            <option value='combined'>Combined - Mix of all types (uses available media)</option>
          </select>
        </div>

        {/* New Playback Direction Field */}
        <div style={{ marginBottom: '15px' }}>
          <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>
            Playback Direction
          </label>
          <select
            value={config.playback_direction}
            onChange={(e) => setConfig({ ...config, playback_direction: e.target.value })}
            style={{
              width: '100%',
              padding: '8px',
              fontSize: '14px',
              border: '1px solid #ccc',
              borderRadius: '4px',
            }}
          >
            <option value='cat-tash'>Catalan (Question) → Tachelhit (Answer)</option>
            <option value='tash-cat'>Tachelhit (Question) → Catalan (Answer)</option>
            <option value='ar-tash'>Arabic (Question) → Tachelhit (Answer)</option>
            <option value='tash-ar'>Tachelhit (Question) → Arabic (Answer)</option>
          </select>
        </div>

        <div style={{ marginBottom: '15px' }}>
          <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>
            Hint Level
          </label>
          <select
            value={config.hint_level}
            onChange={(e) => setConfig({ ...config, hint_level: e.target.value })}
            style={{
              width: '100%',
              padding: '8px',
              fontSize: '14px',
              border: '1px solid #ccc',
              borderRadius: '4px',
            }}
          >
            <option value='none'>No Hints</option>
            <option value='partial'>Partial Letters (%)</option>
            <option value='full_after_tries'>Full Reveal After X Tries</option>
          </select>
        </div>

        {config.hint_level === 'partial' && (
          <div style={{ marginBottom: '15px', marginLeft: '20px' }}>
            <label style={{ display: 'block', marginBottom: '5px' }}>
              Percentage of letters to reveal: {config.hint_percentage}%
            </label>
            <input
              type='range'
              min='10'
              max='80'
              value={config.hint_percentage}
              onChange={(e) => setConfig({ ...config, hint_percentage: parseInt(e.target.value) })}
              style={{ width: '100%' }}
            />
          </div>
        )}

        {config.hint_level === 'full_after_tries' && (
          <div style={{ marginBottom: '15px', marginLeft: '20px' }}>
            <label style={{ display: 'block', marginBottom: '5px' }}>
              Number of tries before revealing:
            </label>
            <input
              type='number'
              min='1'
              max='10'
              value={config.hint_tries_before_reveal}
              onChange={(e) => setConfig({ ...config, hint_tries_before_reveal: parseInt(e.target.value) })}
              style={{
                padding: '8px',
                fontSize: '14px',
                border: '1px solid #ccc',
                borderRadius: '4px',
                width: '100px',
              }}
            />
          </div>
        )}

        <div style={{ marginBottom: '15px' }}>
          <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>
            Time Limit (seconds per question, 0 = no limit)
          </label>
          <input
            type='number'
            min='0'
            value={config.time_limit_seconds}
            onChange={(e) => setConfig({ ...config, time_limit_seconds: parseInt(e.target.value) })}
            style={{
              padding: '8px',
              fontSize: '14px',
              border: '1px solid #ccc',
              borderRadius: '4px',
              width: '150px',
            }}
          />
        </div>

        <div style={{ marginBottom: '20px' }}>
          <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>
            Passing Score (%): {config.passing_score}%
          </label>
          <input
            type='range'
            min='0'
            max='100'
            value={config.passing_score}
            onChange={(e) => setConfig({ ...config, passing_score: parseInt(e.target.value) })}
            style={{ width: '100%' }}
          />
        </div>

        {/* Drill Management Section - Updated */}
        <div style={{ marginBottom: '20px', border: '1px solid #e0e0e0', borderRadius: '8px', padding: '15px' }}>
          <h3 style={{ marginTop: '0', marginBottom: '15px', fontSize: '18px' }}>Manage Drills ({selectedDrills.length})</h3>

          <DndContext
            sensors={sensors}
            collisionDetection={closestCenter}
            onDragEnd={handleDragEnd}
          >
            <SortableContext
              items={selectedDrills.map(d => d.id)}
              strategy={verticalListSortingStrategy}
            >
              <div style={{ marginBottom: '15px', maxHeight: '250px', overflowY: 'auto', border: '1px solid #f0f0f0', borderRadius: '4px', padding: '10px' }}>
                {selectedDrills.length === 0 ? (
                  <p style={{ color: '#888', textAlign: 'center', padding: '20px' }}>No drills selected for this test.</p>
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
          <div style={{ marginBottom: '10px', paddingTop: '10px', borderTop: '1px dashed #e0e0e0' }}>
            <h4 style={{ margin: '0 0 10px 0', fontSize: '16px' }}>Add Drills:</h4>
            <input
              type='text' // Changed to text for search
              placeholder='Search by ID or text...'
              value={drillSearchTerm}
              onChange={(e) => setDrillSearchTerm(e.target.value)}
              style={{ padding: '8px', border: '1px solid #ccc', borderRadius: '4px', width: 'calc(100% - 80px)' }}
            />
            <div style={{ maxHeight: '150px', overflowY: 'auto', border: '1px solid #f0f0f0', borderRadius: '4px', marginTop: '10px', padding: '5px' }}>
              {drillSearchTerm.length > 0 && filteredAvailableDrills.length > 0 ? (
                filteredAvailableDrills.map(drill => (
                  <div key={drill.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '6px 0', borderBottom: '1px dotted #eee' }}>
                    <span>{drill.id}. {drill.text_catalan}</span>
                    <button
                      onClick={() => handleAddDrill(drill)}
                      style={{ background: '#2196F3', color: 'white', border: 'none', borderRadius: '4px', padding: '4px 8px', cursor: 'pointer' }}
                    >
                      Add
                    </button>
                  </div>
                ))
              ) : drillSearchTerm.length > 0 ? (
                <p style={{ color: '#888', textAlign: 'center', padding: '10px' }}>No matching drills found.</p>
              ) : (
                <p style={{ color: '#888', textAlign: 'center', padding: '10px' }}>Type to search available drills.</p>
              )}
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
          <button
            onClick={onClose}
            style={{
              padding: '10px 20px',
              fontSize: '14px',
              border: '1px solid #ccc',
              borderRadius: '4px',
              backgroundColor: 'white',
              cursor: 'pointer',
            }}
          >
            Cancel
          </button>
          <button
            onClick={handleUpdate}
            style={{
              padding: '10px 20px',
              fontSize: '14px',
              border: 'none',
              borderRadius: '4px',
              backgroundColor: '#2196F3',
              color: 'white',
              cursor: 'pointer',
              fontWeight: 'bold',
            }}
          >
            Update Test
          </button>
        </div>
      </div>
    </div>
  );
}
