import { useState } from 'react';
import axios from 'axios';
import { API_BASE } from '../config';

interface TestConfigPanelProps {
  selectedDrillIds: number[];
  onClose: () => void;
  onTestCreated: (testId: number) => void;
}

export default function TestConfigPanel({ selectedDrillIds, onClose, onTestCreated }: TestConfigPanelProps) {
  const [config, setConfig] = useState({
    title: '',
    description: '',
    question_type: 'text_input',
    hint_level: 'none',
    hint_percentage: 30,
    hint_tries_before_reveal: 3,
    time_limit_seconds: 0,
    passing_score: 70,
  });

  const handleCreate = async () => {
    if (!config.title.trim()) {
      alert('Please enter a test title');
      return;
    }

    if (selectedDrillIds.length === 0) {
      alert('Please select at least one drill');
      return;
    }

    try {
      const response = await axios.post(`${API_BASE}/tests/`, {
        ...config,
        drill_ids: selectedDrillIds.join(','),
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

        <p style={{ marginBottom: '20px', color: '#666' }}>
          Selected drills: <strong>{selectedDrillIds.length}</strong>
        </p>

        <div style={{ marginBottom: '15px' }}>
          <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>
            Test Title *
          </label>
          <input
            type="text"
            value={config.title}
            onChange={(e) => setConfig({ ...config, title: e.target.value })}
            placeholder="e.g., Basic Greetings Test"
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
            placeholder="Optional description"
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
            <option value="text_input">Text Input - Student writes Tachelhit</option>
            <option value="audio">Audio Recognition - Listen and write</option>
            <option value="video">Video - Watch and write</option>
            <option value="combined">Combined - Mix of all types (uses available media)</option>
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
            <option value="none">No Hints</option>
            <option value="partial">Partial Letters (%)</option>
            <option value="full_after_tries">Full Reveal After X Tries</option>
          </select>
        </div>

        {config.hint_level === 'partial' && (
          <div style={{ marginBottom: '15px', marginLeft: '20px' }}>
            <label style={{ display: 'block', marginBottom: '5px' }}>
              Percentage of letters to reveal: {config.hint_percentage}%
            </label>
            <input
              type="range"
              min="10"
              max="80"
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
              type="number"
              min="1"
              max="10"
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
            type="number"
            min="0"
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
            type="range"
            min="0"
            max="100"
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
