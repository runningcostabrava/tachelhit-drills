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
  const [generatingDemoVideoId, setGeneratingDemoVideoId] = useState<number | null>(null);
  const [showTestList, setShowTestList] = useState(isMobile ? true : true);

  useEffect(() => {
    fetchTests();
  }, []);

  const fetchTests = async (testIdToRefresh?: number) => {
    try {
      if (testIdToRefresh) {
        const response = await axios.get(`${API_BASE}/tests/${testIdToRefresh}`);
        setTests(prevTests => 
          prevTests.map(test => (test.id === testIdToRefresh ? response.data : test))
        );
        if (selectedTest?.id === testIdToRefresh) {
          setSelectedTest(response.data);
        }
      } else {
        const response = await axios.get(`${API_BASE}/tests/`);
        setTests(response.data);
      }
      setLoading(false); // Only set to false for initial load
    } catch (error) {
      console.error('Error fetching tests:', error);
      setLoading(false); // Only set to false for initial load
    }
  };

  const startPollingForDemoVideo = (testId: number) => {
    setGeneratingDemoVideoId(testId);
    const interval = setInterval(async () => {
      try {
        const response = await axios.get(`${API_BASE}/tests/${testId}`);
        const updatedTest = response.data;
        if (updatedTest.video_url) {
          clearInterval(interval);
          setGeneratingDemoVideoId(null);
          setTests(prevTests =>
            prevTests.map(test => (test.id === testId ? updatedTest : test))
          );
          setSelectedTest(updatedTest);
          alert(`Demo video is ready! You can watch it here: ${updatedTest.video_url}`);
          // Optionally open the video in a new tab
          window.open(updatedTest.video_url, '_blank');
        }
      } catch (error) {
        console.error('Error polling for demo video:', error);
        clearInterval(interval);
        setGeneratingDemoVideoId(null);
        alert('Failed to get demo video status. Please try again or check logs.');
      }
    }, 10000); // Poll every 10 seconds

    // Optional: Add a timeout to stop polling after a certain period (e.g., 5 minutes)
    setTimeout(() => {
      if (generatingDemoVideoId === testId) {
        clearInterval(interval);
        setGeneratingDemoVideoId(null);
        alert('Demo video generation is taking longer than expected. Please check back later.');
      }
    }, 5 * 60 * 1000); // 5 minutes timeout
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

        {/* Test Details - Show only when a test is selected on mobile */}
        {(!isMobile || selectedTest) && selectedTest && (
          <div style={{ 
            flex: 1, 
            padding: isMobile ? '16px' : '30px', 
            overflowY: 'auto',
            background: 'white'
          }}>
            {/* Mobile back button */}
            {isMobile && selectedTest && (
              <button
                onClick={() => {
                  setSelectedTest(null);
                  setShowTestList(true);
                }}
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
              marginBottom: '16px', 
              color: '#333',
              fontSize: isMobile ? '22px' : '28px'
            }}>
              {selectedTest.title}
            </h2>


            {selectedTest.description && (
              <p style={{ 
                marginBottom: '20px', 
                color: '#666', 
                fontSize: isMobile ? '15px' : '15px',
                lineHeight: 1.5,
                padding: isMobile ? '12px' : '16px',
                background: '#f8f9fa',
                borderRadius: '8px'
              }}>
                {selectedTest.description}
              </p>
            )}

            {/* Configuration - Compact */}
            <div style={{
              padding: isMobile ? '12px' : '16px',
              background: '#f8f9fa',
              borderRadius: '10px',
              marginBottom: '16px',
              borderLeft: '4px solid #667eea'
            }}>
              <h3 style={{ 
                marginTop: 0, 
                marginBottom: '12px', 
                fontSize: isMobile ? '16px' : '16px',
                fontWeight: 600,
                color: '#333',
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
              }}>
                <span>⚙️</span> Test Configuration
              </h3>
              <div style={{ 
                display: 'grid', 
                gridTemplateColumns: isMobile ? 'repeat(2, 1fr)' : 'repeat(2, 1fr)', 
                gap: isMobile ? '10px' : '12px',
                fontSize: isMobile ? '13px' : '14px'
              }}>
                <div style={{ padding: '8px', background: 'white', borderRadius: '6px' }}>
                  <div style={{ fontWeight: 600, color: '#667eea', marginBottom: '4px' }}>Type</div>
                  <div>{getQuestionTypeLabel(selectedTest.question_type)}</div>
                </div>
                <div style={{ padding: '8px', background: 'white', borderRadius: '6px' }}>
                  <div style={{ fontWeight: 600, color: '#667eea', marginBottom: '4px' }}>Hints</div>
                  <div>
                    {getHintLevelLabel(selectedTest.hint_level)}
                    {selectedTest.hint_level === 'partial' && ` (${selectedTest.hint_percentage}%)`}
                    {selectedTest.hint_level === 'full_after_tries' && ` (${selectedTest.hint_tries_before_reveal})`}
                  </div>
                </div>
                <div style={{ padding: '8px', background: 'white', borderRadius: '6px' }}>
                  <div style={{ fontWeight: 600, color: '#667eea', marginBottom: '4px' }}>Time</div>
                  <div>{selectedTest.time_limit_seconds > 0 ? `${selectedTest.time_limit_seconds}s` : 'No limit'}</div>
                </div>
                <div style={{ padding: '8px', background: 'white', borderRadius: '6px' }}>
                  <div style={{ fontWeight: 600, color: '#667eea', marginBottom: '4px' }}>Passing</div>
                  <div>{selectedTest.passing_score}%</div>
                </div>
                <div style={{ padding: '8px', background: 'white', borderRadius: '6px', gridColumn: isMobile ? 'span 2' : 'span 1' }}>
                  <div style={{ fontWeight: 600, color: '#667eea', marginBottom: '4px' }}>Drills</div>
                  <div>{selectedTest.drill_ids.split(',').length} drills</div>
                </div>
              </div>
            </div>

            {/* Statistics - Compact */}
            {stats && stats.total_attempts > 0 && (
              <div style={{
                padding: isMobile ? '12px' : '16px',
                background: '#e8f5e9',
                borderRadius: '10px',
                marginBottom: '16px',
                borderLeft: '4px solid #4CAF50'
              }}>
                <h3 style={{ 
                  marginTop: 0, 
                  marginBottom: '12px', 
                  fontSize: isMobile ? '16px' : '16px',
                  fontWeight: 600,
                  color: '#2e7d32',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px'
                }}>
                  <span>📊</span> Statistics
                </h3>
                <div style={{ 
                  display: 'grid', 
                  gridTemplateColumns: isMobile ? 'repeat(2, 1fr)' : 'repeat(3, 1fr)', 
                  gap: isMobile ? '10px' : '12px',
                  fontSize: isMobile ? '13px' : '14px'
                }}>
                  <div style={{ padding: '8px', background: 'rgba(255,255,255,0.7)', borderRadius: '6px' }}>
                    <div style={{ fontWeight: 600, color: '#2e7d32', marginBottom: '4px' }}>Attempts</div>
                    <div>{stats.total_attempts}</div>
                  </div>
                  <div style={{ padding: '8px', background: 'rgba(255,255,255,0.7)', borderRadius: '6px' }}>
                    <div style={{ fontWeight: 600, color: '#2e7d32', marginBottom: '4px' }}>Avg Score</div>
                    <div>{stats.average_score}%</div>
                  </div>
                  <div style={{ padding: '8px', background: 'rgba(255,255,255,0.7)', borderRadius: '6px' }}>
                    <div style={{ fontWeight: 600, color: '#2e7d32', marginBottom: '4px' }}>Completion</div>
                    <div>{stats.completion_rate}%</div>
                  </div>
                  <div style={{ padding: '8px', background: 'rgba(255,255,255,0.7)', borderRadius: '6px' }}>
                    <div style={{ fontWeight: 600, color: '#2e7d32', marginBottom: '4px' }}>Passed</div>
                    <div>{stats.passed_attempts}/{stats.total_attempts}</div>
                  </div>
                  <div style={{ padding: '8px', background: 'rgba(255,255,255,0.7)', borderRadius: '6px', gridColumn: isMobile ? 'span 2' : 'span 1' }}>
                    <div style={{ fontWeight: 600, color: '#2e7d32', marginBottom: '4px' }}>Avg Time</div>
                    <div>{stats.average_time}s</div>
                  </div>
                </div>
              </div>
            )}

            {/* Action Buttons - Moved to top */}
            <div style={{ 
              marginBottom: '20px', 
              display: 'grid',
              gridTemplateColumns: isMobile ? 'repeat(2, 1fr)' : 'repeat(4, 1fr)',
              gap: '10px',
              justifyContent: isMobile ? 'center' : 'flex-start'
            }}>
              <button
                onClick={() => setTakingTestId(selectedTest.id)}
                style={{
                  padding: isMobile ? '14px 20px' : '12px 24px',
                  fontSize: isMobile ? '15px' : '15px',
                  background: '#4CAF50',
                  color: 'white',
                  border: 'none',
                  borderRadius: '8px',
                  cursor: 'pointer',
                  fontWeight: 600,
                  width: '100%',
                  boxShadow: '0 2px 4px rgba(0,0,0,0.2)'
                }}
              >
                🎯 Take Test
              </button>
              <button
                onClick={() => setEditingTestId(selectedTest.id)}
                style={{
                  padding: isMobile ? '14px 20px' : '12px 24px',
                  fontSize: isMobile ? '15px' : '15px',
                  background: '#2196F3',
                  color: 'white',
                  border: 'none',
                  borderRadius: '8px',
                  cursor: 'pointer',
                  fontWeight: 600,
                  width: '100%',
                  boxShadow: '0 2px 4px rgba(0,0,0,0.2)'
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
                  padding: isMobile ? '14px 20px' : '12px 24px',
                  fontSize: isMobile ? '15px' : '15px',
                  background: '#9C27B0',
                  color: 'white',
                  border: 'none',
                  borderRadius: '8px',
                  cursor: 'pointer',
                  fontWeight: 600,
                  width: '100%',
                  boxShadow: '0 2px 4px rgba(0,0,0,0.2)'
                }}
              >
                ▶️ Play Drills
              </button>
              <button
                onClick={async () => {
                  if (!selectedTest) return;
                  if (!confirm('This will generate a demo video showing the Drill Player interface for this test. It may take a a few minutes. Continue?')) {
                    return;
                  }
                  // Start the background generation
                  try {
                    setGeneratingDemoVideoId(selectedTest.id); // Set state to show loading
                    const response = await axios.post(`${API_BASE}/generate-drillplayer-demo/${selectedTest.id}`);
                    alert(response.data.message || 'Video generation started. Polling for completion...');
                    startPollingForDemoVideo(selectedTest.id); // Start polling
                  } catch (error: any) {
                    console.error('Error generating demo video:', error);
                    setGeneratingDemoVideoId(null); // Clear loading state on error
                    alert(`Failed to generate demo video: ${error.response?.data?.detail || error.message}`);
                  }
                }}
                style={{
                  padding: isMobile ? '14px 20px' : '12px 24px',
                  fontSize: isMobile ? '15px' : '15px',
                  background: '#FF9800',
                  color: 'white',
                  border: 'none',
                  borderRadius: '8px',
                  cursor: 'pointer',
                  fontWeight: 600,
                  width: '100%',
                  boxShadow: '0 2px 4px rgba(0,0,0,0.2)'
                }}
              >
                🎬 Generate Demo Video
              </button>
            </div>

            {selectedTest.video_url && (
              <div style={{
                marginTop: '20px',
                padding: '16px',
                background: '#e6ffed',
                borderLeft: '4px solid #4CAF50',
                borderRadius: '8px',
                display: 'flex',
                flexDirection: 'column',
                gap: '10px',
                alignItems: 'flex-start'
              }}>
                <h3 style={{ margin: 0, color: '#2e7d32', fontSize: '18px' }}>✅ Demo Video Ready!</h3>
                <a 
                  href={selectedTest.video_url} 
                  target="_blank" 
                  rel="noopener noreferrer"
                  style={{ color: '#1976D2', textDecoration: 'underline', fontSize: '16px' }}
                >
                  Watch Demo Video
                </a>
                <video controls src={selectedTest.video_url} style={{ maxWidth: '100%', borderRadius: '8px' }} />
              </div>
            )}

            {generatingDemoVideoId === selectedTest.id && (
              <div style={{
                marginTop: '20px',
                padding: '16px',
                background: '#fff3e0',
                borderLeft: '4px solid #FF9800',
                borderRadius: '8px',
                display: 'flex',
                alignItems: 'center',
                gap: '10px'
              }}>
                <div className="spinner" style={{ border: '4px solid rgba(0, 0, 0, 0.1)', width: '24px', height: '24px', borderRadius: '50%', borderLeftColor: '#FF9800', animation: 'spin 1s ease infinite' }}></div>
                <p style={{ margin: 0, color: '#E65100', fontSize: '16px' }}>Generating demo video... This may take a few minutes. Please keep this page open.</p>
                <style>{`
                  @keyframes spin {
                    0% { transform: rotate(0deg); }
                    100% { transform: rotate(360deg); }
                  }
                `}</style>
              </div>
            )}
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
        {/* No test selected (mobile) - Show message if list is hidden */}
        {isMobile && !selectedTest && !showTestList && (
          <div style={{ flex: 1, padding: '30px', overflowY: 'auto', background: 'white' }}>
            <div style={{ textAlign: 'center', padding: '60px', color: '#999' }}>
              <p style={{ fontSize: '18px' }}>No test selected</p>
              <button
                onClick={() => setShowTestList(true)}
                style={{
                  marginTop: '20px',
                  padding: '12px 24px',
                  background: '#667eea',
                  color: 'white',
                  border: 'none',
                  borderRadius: '8px',
                  fontSize: '16px',
                  fontWeight: 600,
                  cursor: 'pointer'
                }}
              >
                Show Tests List
              </button>
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
