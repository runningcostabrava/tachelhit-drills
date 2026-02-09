import { useState, useEffect } from 'react';
import axios from 'axios';
import { API_BASE } from '../config';

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
}

interface TestEditPanelProps {
  testId: number;
  onClose: () => void;
  onTestUpdated: () => void;
}

export default function TestEditPanel({ testId, onClose, onTestUpdated }: TestEditPanelProps) {
  const [config, setConfig] = useState({
    title: '',
    description: '',
    question_type: 'text_input',
    hint_level: 'none',
    hint_percentage: 30,
    hint_tries_before_reveal: 3,
    time_limit_seconds: 0,
    passing_score: 70,
    drill_ids: '',
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadTest();
  }, [testId]);

  const loadTest = async () => {
    try {
      const response = await axios.get(`${API_BASE}/tests/${testId}`);
      setConfig({
        title: response.data.title,
        description: response.data.description || '',
        question_type: response.data.question_type,
        hint_level: response.data.hint_level,
        hint_percentage: response.data.hint_percentage || 30,
        hint_tries_before_reveal: response.data.hint_tries_before_reveal || 3,
        time_limit_seconds: response.data.time_limit_seconds || 0,
        passing_score: response.data.passing_score,
        drill_ids: response.data.drill_ids,
      });
      setLoading(false);
    } catch (error) {
      console.error('Error loading test:', error);
      alert('Failed to load test');
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

  const drillCount = config.drill_ids ? config.drill_ids.split(',').length : 0;

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
        <h2 style={{ marginTop: 0, marginBottom: '20px' }}>Edit Test Configuration</h2>

        <p style={{ marginBottom: '20px', color: '#666' }}>
          Number of drills: <strong>{drillCount}</strong>
          <br />
          <span style={{ fontSize: '12px', color: '#999' }}>
            (To change drills, create a new test)
          </span>
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
