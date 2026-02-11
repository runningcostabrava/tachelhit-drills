import { useState, useEffect } from 'react';
import axios from 'axios';
import TestTaking from './TestTaking';
import TestEditPanel from './TestEditPanel';
import DrillPlayer from './DrillPlayer';
import { API_BASE } from '../config';

interface Test {
  id: number;
  title: string;
  description: string;
  date_created: string;
  question_type: string;
  hint_level: string;
  hint_percentage: number;
  hint_tries_before_reveal: number;
  time_limit_seconds: number;
  passing_score: number;
  drill_ids: string;
}

interface TestStats {
  total_attempts: number;
  average_score: number;
  completion_rate: number;
  average_time: number;
  passed_attempts: number;
}

export default function TestsDashboard({ onBackToDrills }: { onBackToDrills: () => void }) {
  const [tests, setTests] = useState<Test[]>([]);
  const [selectedTest, setSelectedTest] = useState<Test | null>(null);
  const [stats, setStats] = useState<TestStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [takingTestId, setTakingTestId] = useState<number | null>(null);
  const [editingTestId, setEditingTestId] = useState<number | null>(null);
  const [playingDrills, setPlayingDrills] = useState<any[] | null>(null);

  useEffect(() => {
    fetchTests();
  }, []);

  const fetchTests = async () => {
    try {
      const response = await axios.get(`${API_BASE}/tests/`);
      setTests(response.data);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching tests:', error);
      setLoading(false);
    }
  };

  const fetchStats = async (testId: number) => {
    try {
      const response = await axios.get(`${API_BASE}/tests/${testId}/stats`);
      setStats(response.data);
    } catch (error) {
      console.error('Error fetching stats:', error);
    }
  };

  const handleViewTest = (test: Test) => {
    setSelectedTest(test);
    fetchStats(test.id);
  };

  const handleDeleteTest = async (testId: number) => {
    if (!confirm('Are you sure you want to delete this test?')) return;

    try {
      await axios.delete(`${API_BASE}/tests/${testId}`);
      setTests(tests.filter(t => t.id !== testId));
      if (selectedTest?.id === testId) {
        setSelectedTest(null);
        setStats(null);
      }
      alert('Test deleted successfully!');
    } catch (error) {
      console.error('Error deleting test:', error);
      alert('Failed to delete test');
    }
  };

  const getQuestionTypeLabel = (type: string) => {
    const labels: any = {
      'text_input': 'Text Input',
      'audio': 'Audio Recognition',
      'video': 'Video'
    };
    return labels[type] || type;
  };

  const getHintLevelLabel = (level: string) => {
    const labels: any = {
      'none': 'No Hints',
      'partial': 'Partial Letters',
      'full_after_tries': 'Full Reveal After Tries'
    };
    return labels[level] || level;
  };

  if (loading) {
    return <div style={{ padding: '40px', textAlign: 'center' }}>Loading tests...</div>;
  }

  // If taking a test, show the test-taking interface
  if (takingTestId !== null) {
    return (
      <TestTaking
        testId={takingTestId}
        onExit={() => {
          setTakingTestId(null);
          fetchTests(); // Refresh to get updated stats
          if (selectedTest) {
            fetchStats(selectedTest.id); // Refresh stats for current test
          }
        }}
      />
    );
  }

  // If playing drills, show the drill player
  if (playingDrills !== null) {
    return (
      <DrillPlayer
        drills={playingDrills}
        onExit={() => {
          setPlayingDrills(null);
        }}
      />
    );
  }

  return (
    <div style={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <div style={{
        padding: '16px',
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        borderBottom: '2px solid #5a67d8',
        display: 'flex',
        alignItems: 'center',
        gap: '16px'
      }}>
        <button
          onClick={onBackToDrills}
          style={{
            padding: '8px 16px',
            fontSize: '14px',
            background: 'rgba(255,255,255,0.2)',
            color: 'white',
            border: '1px solid white',
            borderRadius: '6px',
            cursor: 'pointer',
            fontWeight: 600,
          }}
        >
          ← Back to Drills
        </button>
        <h1 style={{
          margin: 0,
          fontSize: '24px',
          fontWeight: 700,
          color: 'white',
          letterSpacing: '0.5px'
        }}>
          Tests Dashboard
        </h1>
        <span style={{ color: 'white', fontSize: '16px' }}>
          ({tests.length} {tests.length === 1 ? 'test' : 'tests'})
        </span>
      </div>

      {/* Content */}
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
        {/* Tests List */}
        <div style={{
          width: '400px',
          borderRight: '1px solid #e0e0e0',
          overflowY: 'auto',
          padding: '20px'
        }}>
          {tests.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '40px', color: '#999' }}>
              <p style={{ fontSize: '18px', marginBottom: '10px' }}>No tests created yet</p>
              <p style={{ fontSize: '14px' }}>Go back to drills and select some to create a test</p>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {tests.map(test => (
                <div
                  key={test.id}
                  onClick={() => handleViewTest(test)}
                  style={{
                    padding: '16px',
                    border: selectedTest?.id === test.id ? '2px solid #667eea' : '1px solid #e0e0e0',
                    borderRadius: '8px',
                    cursor: 'pointer',
                    backgroundColor: selectedTest?.id === test.id ? '#f0f4ff' : 'white',
                    transition: 'all 0.2s'
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
                    <div style={{ flex: 1 }}>
                      <h3 style={{ margin: '0 0 8px 0', fontSize: '16px', color: '#333' }}>
                        {test.title}
                      </h3>
                      <p style={{ margin: '0 0 8px 0', fontSize: '13px', color: '#666' }}>
                        {test.description || 'No description'}
                      </p>
                      <div style={{ fontSize: '12px', color: '#999' }}>
                        <div>{test.drill_ids.split(',').length} drills</div>
                        <div>{new Date(test.date_created).toLocaleDateString()}</div>
                      </div>
                    </div>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDeleteTest(test.id);
                      }}
                      style={{
                        padding: '4px 8px',
                        fontSize: '12px',
                        background: '#ff4444',
                        color: 'white',
                        border: 'none',
                        borderRadius: '4px',
                        cursor: 'pointer'
                      }}
                    >
                      Delete
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Test Details */}
        <div style={{ flex: 1, padding: '30px', overflowY: 'auto' }}>
          {selectedTest ? (
            <div>
              <h2 style={{ marginTop: 0, marginBottom: '20px', color: '#333' }}>
                {selectedTest.title}
              </h2>

              {selectedTest.description && (
                <p style={{ marginBottom: '30px', color: '#666', fontSize: '15px' }}>
                  {selectedTest.description}
                </p>
              )}

              {/* Configuration */}
              <div style={{
                padding: '20px',
                background: '#f8f9fa',
                borderRadius: '8px',
                marginBottom: '30px'
              }}>
                <h3 style={{ marginTop: 0, marginBottom: '15px', fontSize: '16px' }}>
                  Test Configuration
                </h3>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                  <div>
                    <strong>Question Type:</strong><br />
                    {getQuestionTypeLabel(selectedTest.question_type)}
                  </div>
                  <div>
                    <strong>Hint Level:</strong><br />
                    {getHintLevelLabel(selectedTest.hint_level)}
                    {selectedTest.hint_level === 'partial' && ` (${selectedTest.hint_percentage}%)`}
                    {selectedTest.hint_level === 'full_after_tries' && ` (${selectedTest.hint_tries_before_reveal} tries)`}
                  </div>
                  <div>
                    <strong>Time Limit:</strong><br />
                    {selectedTest.time_limit_seconds > 0 ? `${selectedTest.time_limit_seconds}s` : 'No limit'}
                  </div>
                  <div>
                    <strong>Passing Score:</strong><br />
                    {selectedTest.passing_score}%
                  </div>
                  <div>
                    <strong>Number of Drills:</strong><br />
                    {selectedTest.drill_ids.split(',').length}
                  </div>
                </div>
              </div>

              {/* Statistics */}
              {stats && (
                <div style={{
                  padding: '20px',
                  background: '#e8f5e9',
                  borderRadius: '8px',
                  marginBottom: '20px'
                }}>
                  <h3 style={{ marginTop: 0, marginBottom: '15px', fontSize: '16px' }}>
                    Statistics
                  </h3>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '12px' }}>
                    <div>
                      <strong>Total Attempts:</strong><br />
                      {stats.total_attempts}
                    </div>
                    <div>
                      <strong>Average Score:</strong><br />
                      {stats.average_score}%
                    </div>
                    <div>
                      <strong>Completion Rate:</strong><br />
                      {stats.completion_rate}%
                    </div>
                    <div>
                      <strong>Passed:</strong><br />
                      {stats.passed_attempts} / {stats.total_attempts}
                    </div>
                    <div>
                      <strong>Avg Time:</strong><br />
                      {stats.average_time}s
                    </div>
                  </div>
                </div>
              )}

              {/* Action Buttons */}
              <div style={{ marginTop: '30px', display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
                <button
                  onClick={() => setTakingTestId(selectedTest.id)}
                  style={{
                    padding: '12px 24px',
                    fontSize: '15px',
                    background: '#4CAF50',
                    color: 'white',
                    border: 'none',
                    borderRadius: '6px',
                    cursor: 'pointer',
                    fontWeight: 600,
                  }}
                >
                  🎯 Take Test
                </button>
                <button
                  onClick={() => setEditingTestId(selectedTest.id)}
                  style={{
                    padding: '12px 24px',
                    fontSize: '15px',
                    background: '#2196F3',
                    color: 'white',
                    border: 'none',
                    borderRadius: '6px',
                    cursor: 'pointer',
                    fontWeight: 600,
                  }}
                >
                  ✏️ Edit Test
                </button>
                <button
                  onClick={async () => {
                    // Load drills for this test
                    const drillIds = selectedTest.drill_ids.split(',').map((id: string) => parseInt(id));
                    try {
                      const drillsResponse = await axios.get(`${API_BASE}/drills/`);
                      const testDrills = drillsResponse.data.filter((d: any) => drillIds.includes(d.id));
                      setPlayingDrills(testDrills);
                    } catch (error) {
                      console.error('Error loading drills:', error);
                      alert('Failed to load drills');
                    }
                  }}
                  style={{
                    padding: '12px 24px',
                    fontSize: '15px',
                    background: '#9C27B0',
                    color: 'white',
                    border: 'none',
                    borderRadius: '6px',
                    cursor: 'pointer',
                    fontWeight: 600,
                  }}
                >
                  ▶️ Play Drills
                </button>
              </div>
            </div>
          ) : (
            <div style={{ textAlign: 'center', padding: '60px', color: '#999' }}>
              <p style={{ fontSize: '18px' }}>Select a test to view details</p>
            </div>
          )}
        </div>
      </div>

      {/* Test Edit Panel */}
      {editingTestId !== null && (
        <TestEditPanel
          testId={editingTestId}
          onClose={() => setEditingTestId(null)}
          onTestUpdated={() => {
            fetchTests();
            if (selectedTest) {
              fetchStats(selectedTest.id);
            }
          }}
        />
      )}
    </div>
  );
}
