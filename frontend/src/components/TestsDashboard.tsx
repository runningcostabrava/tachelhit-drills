import { useState, useEffect } from 'react';
import axios from 'axios';
import TestTaking from './TestTaking';
import TestEditPanel from './TestEditPanel';
import DrillPlayer from './DrillPlayer';
import { API_BASE } from '../config';

// Hook para detectar móvil
const useIsMobile = () => {
  const [isMobile, setIsMobile] = useState(window.innerWidth < 768);
  useEffect(() => {
    const handleResize = () => setIsMobile(window.innerWidth < 768);
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);
  return isMobile;
};

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
  const isMobile = useIsMobile();
  const [tests, setTests] = useState<Test[]>([]);
  const [selectedTest, setSelectedTest] = useState<Test | null>(null);
  const [stats, setStats] = useState<TestStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [takingTestId, setTakingTestId] = useState<number | null>(null);
  const [editingTestId, setEditingTestId] = useState<number | null>(null);
  const [playingDrills, setPlayingDrills] = useState<any[] | null>(null);
  const [showTestList, setShowTestList] = useState(isMobile ? false : true);

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
    if (isMobile) {
      setShowTestList(false);
    }
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
      <div style={{ 
        flex: 1, 
        display: 'flex', 
        overflow: 'hidden',
        flexDirection: isMobile ? 'column' : 'row'
      }}>
        {/* Tests List - hidden on mobile when a test is selected */}
        {(showTestList || !isMobile) && (
          <div style={{
            width: isMobile ? '100%' : '400px',
            borderRight: isMobile ? 'none' : '1px solid #e0e0e0',
            overflowY: 'auto',
            padding: isMobile ? '16px' : '20px',
            background: isMobile ? '#f8f9fa' : 'white'
          }}>
            {isMobile && (
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                <h2 style={{ margin: 0, fontSize: '20px', color: '#333' }}>Tests</h2>
                <button
                  onClick={() => setShowTestList(false)}
                  style={{
                    padding: '8px 16px',
                    background: '#667eea',
                    color: 'white',
                    border: 'none',
                    borderRadius: '6px',
                    fontSize: '14px',
                    fontWeight: 600,
                    cursor: 'pointer'
                  }}
                >
                  Close
                </button>
              </div>
            )}
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
                      padding: isMobile ? '20px' : '16px',
                      border: selectedTest?.id === test.id ? '2px solid #667eea' : '1px solid #e0e0e0',
                      borderRadius: '12px',
                      cursor: 'pointer',
                      backgroundColor: selectedTest?.id === test.id ? '#f0f4ff' : 'white',
                      transition: 'all 0.2s'
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
                      <div style={{ flex: 1 }}>
                        <h3 style={{ 
                          margin: '0 0 8px 0', 
                          fontSize: isMobile ? '18px' : '16px', 
                          color: '#333',
                          fontWeight: 600 
                        }}>
                          {test.title}
                        </h3>
                        <p style={{ margin: '0 0 8px 0', fontSize: isMobile ? '14px' : '13px', color: '#666' }}>
                          {test.description || 'No description'}
                        </p>
                        <div style={{ fontSize: isMobile ? '13px' : '12px', color: '#999' }}>
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
                          padding: isMobile ? '8px 12px' : '4px 8px',
                          fontSize: isMobile ? '14px' : '12px',
                          background: '#ff4444',
                          color: 'white',
                          border: 'none',
                          borderRadius: '6px',
                          cursor: 'pointer',
                          fontWeight: 600
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
        )}

        {/* Test Details */}
        {(!isMobile || !showTestList) && selectedTest && (
          <div style={{ 
            flex: 1, 
            padding: isMobile ? '16px' : '30px', 
            overflowY: 'auto',
            background: 'white'
          }}>
            {/* Mobile back button */}
            {isMobile && (
              <button
                onClick={() => setShowTestList(true)}
                style={{
                  marginBottom: '20px',
                  padding: '10px 16px',
                  background: '#667eea',
                  color: 'white',
                  border: 'none',
                  borderRadius: '8px',
                  fontSize: '16px',
                  fontWeight: 600,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px'
                }}
              >
                ← Back to Tests
              </button>
            )}
            <h2 style={{ 
              marginTop: 0, 
              marginBottom: '20px', 
              color: '#333',
              fontSize: isMobile ? '24px' : '28px'
            }}>
              {selectedTest.title}
            </h2>

            {selectedTest.description && (
              <p style={{ 
                marginBottom: '30px', 
                color: '#666', 
                fontSize: isMobile ? '16px' : '15px',
                lineHeight: 1.5
              }}>
                {selectedTest.description}
              </p>
            )}

            {/* Configuration */}
            <div style={{
              padding: isMobile ? '16px' : '20px',
              background: '#f8f9fa',
              borderRadius: '12px',
              marginBottom: '20px'
            }}>
              <h3 style={{ 
                marginTop: 0, 
                marginBottom: '15px', 
                fontSize: isMobile ? '18px' : '16px',
                fontWeight: 600
              }}>
                Test Configuration
              </h3>
              <div style={{ 
                display: 'grid', 
                gridTemplateColumns: isMobile ? '1fr' : '1fr 1fr', 
                gap: isMobile ? '16px' : '12px'
              }}>
                <div style={{ padding: isMobile ? '12px' : '8px' }}>
                  <strong style={{ fontSize: isMobile ? '15px' : '14px' }}>Question Type:</strong><br />
                  <span style={{ fontSize: isMobile ? '16px' : '14px' }}>{getQuestionTypeLabel(selectedTest.question_type)}</span>
                </div>
                <div style={{ padding: isMobile ? '12px' : '8px' }}>
                  <strong style={{ fontSize: isMobile ? '15px' : '14px' }}>Hint Level:</strong><br />
                  <span style={{ fontSize: isMobile ? '16px' : '14px' }}>
                    {getHintLevelLabel(selectedTest.hint_level)}
                    {selectedTest.hint_level === 'partial' && ` (${selectedTest.hint_percentage}%)`}
                    {selectedTest.hint_level === 'full_after_tries' && ` (${selectedTest.hint_tries_before_reveal} tries)`}
                  </span>
                </div>
                <div style={{ padding: isMobile ? '12px' : '8px' }}>
                  <strong style={{ fontSize: isMobile ? '15px' : '14px' }}>Time Limit:</strong><br />
                  <span style={{ fontSize: isMobile ? '16px' : '14px' }}>
                    {selectedTest.time_limit_seconds > 0 ? `${selectedTest.time_limit_seconds}s` : 'No limit'}
                  </span>
                </div>
                <div style={{ padding: isMobile ? '12px' : '8px' }}>
                  <strong style={{ fontSize: isMobile ? '15px' : '14px' }}>Passing Score:</strong><br />
                  <span style={{ fontSize: isMobile ? '16px' : '14px' }}>{selectedTest.passing_score}%</span>
                </div>
                <div style={{ padding: isMobile ? '12px' : '8px' }}>
                  <strong style={{ fontSize: isMobile ? '15px' : '14px' }}>Number of Drills:</strong><br />
                  <span style={{ fontSize: isMobile ? '16px' : '14px' }}>{selectedTest.drill_ids.split(',').length}</span>
                </div>
              </div>
            </div>

            {/* Statistics */}
            {stats && (
              <div style={{
                padding: isMobile ? '16px' : '20px',
                background: '#e8f5e9',
                borderRadius: '12px',
                marginBottom: '20px'
              }}>
                <h3 style={{ 
                  marginTop: 0, 
                  marginBottom: '15px', 
                  fontSize: isMobile ? '18px' : '16px',
                  fontWeight: 600
                }}>
                  Statistics
                </h3>
                <div style={{ 
                  display: 'grid', 
                  gridTemplateColumns: isMobile ? '1fr' : '1fr 1fr 1fr', 
                  gap: isMobile ? '16px' : '12px'
                }}>
                  <div style={{ padding: isMobile ? '12px' : '8px' }}>
                    <strong style={{ fontSize: isMobile ? '15px' : '14px' }}>Total Attempts:</strong><br />
                    <span style={{ fontSize: isMobile ? '16px' : '14px' }}>{stats.total_attempts}</span>
                  </div>
                  <div style={{ padding: isMobile ? '12px' : '8px' }}>
                    <strong style={{ fontSize: isMobile ? '15px' : '14px' }}>Average Score:</strong><br />
                    <span style={{ fontSize: isMobile ? '16px' : '14px' }}>{stats.average_score}%</span>
                  </div>
                  <div style={{ padding: isMobile ? '12px' : '8px' }}>
                    <strong style={{ fontSize: isMobile ? '15px' : '14px' }}>Completion Rate:</strong><br />
                    <span style={{ fontSize: isMobile ? '16px' : '14px' }}>{stats.completion_rate}%</span>
                  </div>
                  <div style={{ padding: isMobile ? '12px' : '8px' }}>
                    <strong style={{ fontSize: isMobile ? '15px' : '14px' }}>Passed:</strong><br />
                    <span style={{ fontSize: isMobile ? '16px' : '14px' }}>{stats.passed_attempts} / {stats.total_attempts}</span>
                  </div>
                  <div style={{ padding: isMobile ? '12px' : '8px' }}>
                    <strong style={{ fontSize: isMobile ? '15px' : '14px' }}>Avg Time:</strong><br />
                    <span style={{ fontSize: isMobile ? '16px' : '14px' }}>{stats.average_time}s</span>
                  </div>
                </div>
              </div>
            )}

            {/* Action Buttons */}
            <div style={{ 
              marginTop: '30px', 
              display: 'flex', 
              gap: '12px', 
              flexWrap: 'wrap',
              justifyContent: isMobile ? 'center' : 'flex-start'
            }}>
              <button
                onClick={() => setTakingTestId(selectedTest.id)}
                style={{
                  padding: isMobile ? '16px 24px' : '12px 24px',
                  fontSize: isMobile ? '16px' : '15px',
                  background: '#4CAF50',
                  color: 'white',
                  border: 'none',
                  borderRadius: '10px',
                  cursor: 'pointer',
                  fontWeight: 600,
                  flex: isMobile ? '1 1 100%' : 'none',
                  minWidth: isMobile ? '100%' : 'auto'
                }}
              >
                🎯 Take Test
              </button>
              <button
                onClick={() => setEditingTestId(selectedTest.id)}
                style={{
                  padding: isMobile ? '16px 24px' : '12px 24px',
                  fontSize: isMobile ? '16px' : '15px',
                  background: '#2196F3',
                  color: 'white',
                  border: 'none',
                  borderRadius: '10px',
                  cursor: 'pointer',
                  fontWeight: 600,
                  flex: isMobile ? '1 1 100%' : 'none',
                  minWidth: isMobile ? '100%' : 'auto'
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
                  padding: isMobile ? '16px 24px' : '12px 24px',
                  fontSize: isMobile ? '16px' : '15px',
                  background: '#9C27B0',
                  color: 'white',
                  border: 'none',
                  borderRadius: '10px',
                  cursor: 'pointer',
                  fontWeight: 600,
                  flex: isMobile ? '1 1 100%' : 'none',
                  minWidth: isMobile ? '100%' : 'auto'
                }}
              >
                ▶️ Play Drills
              </button>
            </div>
          </div>
        )}

        {/* No test selected (desktop) */}
        {!isMobile && !selectedTest && (
          <div style={{ flex: 1, padding: '30px', overflowY: 'auto' }}>
            <div style={{ textAlign: 'center', padding: '60px', color: '#999' }}>
              <p style={{ fontSize: '18px' }}>Select a test to view details</p>
            </div>
          </div>
        )}
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
