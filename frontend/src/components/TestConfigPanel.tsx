import { useState, useEffect } from 'react';
import axios from 'axios';
import { API_BASE } from '../config';

interface Drill {
  id: number;
  text_catalan: string;
  text_tachelhit: string;
  text_arabic?: string;
  // Add other fields from Drill model if needed for display/search
}

interface TestConfigPanelProps {
  onClose: () => void;
  onTestCreated: (testId: number) => void;
  initialSelectedDrillIds?: number[]; // Optional initial drills
}

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
      const response = await axios.get(`${API_BASE}/drills/`);
      setAllDrills(response.data);
    } catch (error) {
      console.error('Error loading all drills:', error);
    }
  };

  const handleCreate = async () => {
    if (!config.title.trim()) {
      alert('Please enter a test title');
      return;
    }

    if (selectedDrills.length === 0) {
      alert('Please select at least one drill');
      return;
    }

    try {
      const response = await axios.post(`${API_BASE}/tests/`, {
        ...config,
        drill_ids: selectedDrills.map(d => d.id).join(','),
        time_limit_seconds: config.time_limit_seconds || null,
      });

      alert('Test created successfully!');
      onTestCreated(response.data.id);
      onClose();
    } catch (error) {
      console.error('Error creating test:', error);
      alert('Failed to create test');
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

  const filteredAvailableDrills = allDrills.filter(drill =>
    !selectedDrills.some(sd => sd.id === drill.id) &&
    (drill.text_catalan.toLowerCase().includes(drillSearchTerm.toLowerCase()) ||
     drill.text_tachelhit.toLowerCase().includes(drillSearchTerm.toLowerCase()) ||
     (drill.text_arabic && drill.text_arabic.toLowerCase().includes(drillSearchTerm.toLowerCase())) ||
     drill.id.toString().includes(drillSearchTerm)))
  ;

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
        width: '600px',
        maxHeight: '90vh',
        overflow: 'auto',
      }}>
        <h2 style={{ marginTop: 0, marginBottom: '20px' }}>Create Test Configuration</h2>

        {/* Drill Management Section for New Test */}
        <div style={{ marginBottom: '20px', border: '1px solid #e0e0e0', borderRadius: '8px', padding: '15px' }}>
          <h3 style={{ marginTop: 0, marginBottom: '15px', fontSize: '18px' }}>Select Drills ({selectedDrills.length})</h3>

          {/* Currently selected drills (for display, no reorder for creation) */}
          <div style={{ marginBottom: '15px', maxHeight: '150px', overflowY: 'auto', border: '1px solid #f0f0f0', borderRadius: '4px', padding: '10px' }}>
            {selectedDrills.length === 0 ? (
              <p style={{ color: '#888', textAlign: 'center', padding: '20px' }}>No drills selected for this test.</p>
            ) : (
              selectedDrills.map((drill, index) => (
                <div key={drill.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 0', borderBottom: index < selectedDrills.length - 1 ? '1px dashed #eee' : 'none' }}>
                  <span>{index + 1}. {drill.text_catalan} ({drill.id})</span>
                  <button
                    onClick={() => handleRemoveDrill(drill.id)}
                    style={{ background: '#ff4444', color: 'white', border: 'none', borderRadius: '4px', padding: '4px 8px', cursor: 'pointer' }}
                  >
                    Remove
                  </button>
                </div>
              ))
            )}
          </div>

          {/* Add new drills search */}
          <div style={{ marginBottom: '10px', paddingTop: '10px', borderTop: '1px dashed #e0e0e0' }}>
            <h4 style={{ margin: 0, marginBottom: '10px', fontSize: '16px' }}>Available Drills:</h4>
            <input
              type='text'
              placeholder='Search by ID or text...'
              value={drillSearchTerm}
              onChange={(e) => setDrillSearchTerm(e.target.value)}
              style={{ padding: '8px', border: '1px solid #ccc', borderRadius: '4px', width: '100%' }}
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

        {/* Playback Direction Field */}
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
            onClick={handleCreate}
            style={{
              padding: '10px 20px',
              fontSize: '14px',
              border: 'none',
              borderRadius: '4px',
              backgroundColor: '#4CAF50',
              color: 'white',
              cursor: 'pointer',
              fontWeight: 'bold',
            }}
          >
            Create Test
          </button>
        </div>
      </div>
    </div>
  );
}
