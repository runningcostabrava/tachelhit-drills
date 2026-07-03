import { useState, useEffect } from 'react';
import axios from 'axios';
import { Network } from '@capacitor/network';
import { syncManager } from '../services/OfflineSyncManager';
import TestTaking from './TestTaking';
import TestEditPanel from './TestEditPanel';
import DrillPlayer from './DrillPlayer';
import VideoLoopPlayer from './VideoLoopPlayer';
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

export interface Test {
  id: number;
  title: string;
  description?: string;
  date_created: string;
  question_type: string;
  hint_level: string;
  hint_percentage?: number;
  hint_tries_before_reveal?: number;
  time_limit_seconds?: number;
  passing_score: number;
  video_url?: string;
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
  const [viewingVideoUrl, setViewingVideoUrl] = useState<string | null>(null);
  const [showTestList, setShowTestList] = useState(isMobile ? true : true);


  useEffect(() => {
    fetchTests();
  }, []);

  const fetchTests = async (testIdToRefresh?: number) => {
    try {
      const status = await Network.getStatus();
      
      if (testIdToRefresh) {
        if (status.connected) {
          const response = await axios.get(`${API_BASE}/tests/${testIdToRefresh}`);
          setTests(prevTests => 
            prevTests.map(test => (test.id === testIdToRefresh ? response.data : test))
          );
          if (selectedTest?.id === testIdToRefresh) {
            setSelectedTest(response.data);
          }
        }
      } else {
        if (status.connected) {
          const response = await axios.get(`${API_BASE}/tests/`);
          setTests(response.data);
          await syncManager.saveTestsToCache(response.data);
        } else {
          const cachedTests = await syncManager.getTests();
          setTests(cachedTests);
        }
      }
      setLoading(false);
    } catch (error) {
      console.error('Error fetching tests, using cache:', error);
      const cachedTests = await syncManager.getTests();
      setTests(cachedTests);
      setLoading(false);
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
          // No alert or window.open, just update the state
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
      const status = await Network.getStatus();
      if (!status.connected) return;
      
      const response = await axios.get(`${API_BASE}/tests/${testId}/stats`);
      setStats(response.data);
    } catch (error) {
      console.error('Error fetching stats:', error);
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
    return (
      <div style={{
        height: '100vh',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '16px',
        background: 'var(--bg)',
        color: 'var(--text-soft)',
        fontFamily: 'var(--font-sans)'
      }}>
        <div className="spinner" style={{
          border: '4px solid var(--border)',
          width: '40px',
          height: '40px',
          borderRadius: '50%',
          borderLeftColor: 'var(--brand-1)',
          animation: 'spin 1s linear infinite'
        }}></div>
        <p style={{ margin: 0, fontSize: '16px', fontWeight: 600 }}>Loading tests…</p>
      </div>
    );
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

  if (viewingVideoUrl) {
    return <VideoLoopPlayer videoUrl={viewingVideoUrl} onBack={() => setViewingVideoUrl(null)} />;
  }

  return (
    <div style={{ height: '100vh', display: 'flex', flexDirection: 'column', background: 'var(--bg)', fontFamily: 'var(--font-sans)' }}>
      {/* Header */}
      <div style={{
        padding: '20px 24px 26px',
        background: 'var(--brand-gradient)',
        borderBottomLeftRadius: '26px',
        borderBottomRightRadius: '26px',
        boxShadow: 'var(--shadow-brand)',
        display: 'flex',
        alignItems: 'center',
        gap: '16px',
        flexWrap: 'wrap'
      }}>
        <button
          onClick={onBackToDrills}
          style={{
            padding: '9px 16px',
            fontSize: '14px',
            background: 'rgba(255,255,255,0.18)',
            color: 'white',
            border: '1px solid rgba(255,255,255,0.55)',
            borderRadius: 'var(--r-pill)',
            cursor: 'pointer',
            fontWeight: 700,
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px',
            backdropFilter: 'blur(4px)'
          }}
        >
          ← Back to Drills
        </button>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
          <h1 style={{
            margin: 0,
            fontSize: '24px',
            fontWeight: 800,
            color: 'white',
            letterSpacing: '-0.02em'
          }}>
            Tests Dashboard
          </h1>
          <span style={{ color: 'rgba(255,255,255,0.85)', fontSize: '14px', fontWeight: 500 }}>
            Manage tests, generate demo videos and start practice
          </span>
        </div>
        <span style={{
          marginLeft: 'auto',
          color: 'white',
          fontSize: '13px',
          fontWeight: 700,
          padding: '6px 14px',
          background: 'rgba(255,255,255,0.18)',
          borderRadius: 'var(--r-pill)'
        }}>
          {tests.length} {tests.length === 1 ? 'test' : 'tests'}
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
            borderRight: isMobile ? 'none' : '1px solid var(--border)',
            overflowY: 'auto',
            padding: isMobile ? '16px' : '20px',
            background: 'var(--bg)'
          }}>
            {isMobile && (
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                <h2 style={{ margin: 0, fontSize: '20px', color: 'var(--text)', fontWeight: 800 }}>Tests</h2>
                <button
                  onClick={() => setShowTestList(false)}
                  style={{
                    padding: '8px 16px',
                    background: 'var(--surface)',
                    color: 'var(--text-soft)',
                    border: '1px solid var(--border)',
                    borderRadius: 'var(--r-pill)',
                    fontSize: '14px',
                    fontWeight: 700,
                    cursor: 'pointer',
                    boxShadow: 'var(--shadow-xs)'
                  }}
                >
                  Close
                </button>
              </div>
            )}
            {tests.length === 0 ? (
              <div style={{
                textAlign: 'center',
                padding: '48px 24px',
                color: 'var(--text-soft)',
                background: 'var(--surface)',
                border: '1px solid var(--border)',
                borderRadius: 'var(--r-xl)',
                boxShadow: 'var(--shadow-sm)'
              }}>
                <div style={{
                  width: '64px',
                  height: '64px',
                  margin: '0 auto 16px',
                  borderRadius: 'var(--r-lg)',
                  background: 'var(--brand-gradient-soft)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '30px'
                }}>📝</div>
                <p style={{ fontSize: '18px', marginBottom: '8px', fontWeight: 800, color: 'var(--text)' }}>No tests created yet</p>
                <p style={{ fontSize: '14px', margin: 0 }}>Go back to drills and select some to create a test</p>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {tests.map(test => (
                  <div
                    key={test.id}
                    onClick={() => {
                      setSelectedTest(test);
                      fetchStats(test.id);
                      if (isMobile) {
                        setShowTestList(false);
                      }
                      // Remove navigate(`/tests/${test.id}`); as it would trigger the TestTaking view
                    }}
                    style={{
                      padding: isMobile ? '18px' : '16px',
                      border: selectedTest?.id === test.id ? '2px solid var(--brand-1)' : '1px solid var(--border)',
                      borderRadius: 'var(--r-xl)',
                      cursor: 'pointer',
                      backgroundColor: 'var(--surface)',
                      boxShadow: selectedTest?.id === test.id ? 'var(--shadow-md)' : 'var(--shadow-sm)',
                      transition: 'transform var(--t-fast), box-shadow var(--t-fast), border-color var(--t-fast)'
                    }}
                    onMouseEnter={(e) => {
                      if (selectedTest?.id !== test.id) {
                        e.currentTarget.style.transform = 'translateY(-2px)';
                        e.currentTarget.style.boxShadow = 'var(--shadow-md)';
                      }
                    }}
                    onMouseLeave={(e) => {
                      if (selectedTest?.id !== test.id) {
                        e.currentTarget.style.transform = 'translateY(0)';
                        e.currentTarget.style.boxShadow = 'var(--shadow-sm)';
                      }
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '12px', gap: '8px' }}>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <h3 style={{
                          margin: '0 0 6px 0',
                          fontSize: isMobile ? '18px' : '16px',
                          color: 'var(--text)',
                          fontWeight: 800,
                          fontFamily: 'var(--font-tifinagh)'
                        }}>
                          {test.title}
                        </h3>
                        <p style={{ margin: '0 0 10px 0', fontSize: isMobile ? '14px' : '13px', color: 'var(--text-soft)', lineHeight: 1.4 }}>
                          {test.description || 'No description'}
                        </p>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                          <span style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '5px',
                            padding: '4px 11px',
                            borderRadius: 'var(--r-pill)',
                            fontSize: '12px',
                            fontWeight: 700,
                            background: 'var(--brand-gradient-soft)',
                            color: 'var(--brand-1)'
                          }}>
                            📚 {test.drill_ids.split(',').length} drills
                          </span>
                          <span style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '5px',
                            padding: '4px 11px',
                            borderRadius: 'var(--r-pill)',
                            fontSize: '12px',
                            fontWeight: 700,
                            background: 'var(--surface-2)',
                            color: 'var(--text-muted)'
                          }}>
                            📅 {new Date(test.date_created).toLocaleDateString()}
                          </span>
                          {test.video_url && (
                            <span style={{
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '5px',
                              padding: '4px 11px',
                              borderRadius: 'var(--r-pill)',
                              fontSize: '12px',
                              fontWeight: 700,
                              background: 'var(--emerald-soft)',
                              color: 'var(--emerald)'
                            }}>
                              🎬 Video ready
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                    <div style={{ display: 'flex', gap: '8px', marginTop: '12px' }}>
                      <button
                        onClick={(e) => {
                          e.stopPropagation(); // Prevent triggering handleViewTest
                          const url = `${window.location.origin}/tests/${test.id}`;
                          navigator.clipboard.writeText(url);
                          alert(`Test link copied to clipboard!\n${url}`);
                        }}
                        style={{
                          padding: isMobile ? '9px 12px' : '7px 10px',
                          fontSize: isMobile ? '14px' : '12px',
                          background: 'var(--surface)',
                          color: 'var(--brand-1)',
                          border: '1px solid var(--border)',
                          borderRadius: 'var(--r-md)',
                          cursor: 'pointer',
                          fontWeight: 700,
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          gap: '5px',
                          flexGrow: 1,
                          boxShadow: 'var(--shadow-xs)'
                        }}
                        title="Copy link to this test"
                      >
                        🔗 Copy Link
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          if (confirm(`Are you sure you want to delete test "${test.title}"? This action cannot be undone.`)) {
                            handleDeleteTest(test.id);
                          }
                        }}
                        style={{
                          padding: isMobile ? '9px 12px' : '7px 10px',
                          fontSize: isMobile ? '14px' : '12px',
                          background: 'var(--rose-soft)',
                          color: 'var(--rose)',
                          border: '1px solid var(--rose)',
                          borderRadius: 'var(--r-md)',
                          cursor: 'pointer',
                          fontWeight: 700,
                          display: 'flex',
                          alignItems: 'center',
                          gap: '5px'
                        }}
                        title="Delete test"
                      >
                        🗑️ Delete
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
            background: 'var(--bg)'
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
                  padding: '10px 18px',
                  background: 'var(--surface)',
                  color: 'var(--text-soft)',
                  border: '1px solid var(--border)',
                  borderRadius: 'var(--r-pill)',
                  fontSize: '15px',
                  fontWeight: 700,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  boxShadow: 'var(--shadow-xs)'
                }}
              >
                ← Back to Tests
              </button>
            )}
            {/* Title banner */}
            <div style={{
              background: 'var(--brand-gradient)',
              borderRadius: 'var(--r-xl)',
              boxShadow: 'var(--shadow-brand)',
              padding: isMobile ? '18px 20px' : '24px 28px',
              marginBottom: '20px'
            }}>
              <h2 style={{
                margin: 0,
                color: 'white',
                fontSize: isMobile ? '22px' : '28px',
                fontWeight: 800,
                fontFamily: 'var(--font-tifinagh)'
              }}>
                {selectedTest.title}
              </h2>
              {selectedTest.description && (
                <p style={{
                  margin: '8px 0 0',
                  color: 'rgba(255,255,255,0.9)',
                  fontSize: '15px',
                  lineHeight: 1.5
                }}>
                  {selectedTest.description}
                </p>
              )}
            </div>

            {/* Configuration - Compact */}
            <div style={{
              padding: isMobile ? '16px' : '20px',
              background: 'var(--surface)',
              border: '1px solid var(--border)',
              borderRadius: 'var(--r-xl)',
              boxShadow: 'var(--shadow-sm)',
              marginBottom: '16px'
            }}>
              <h3 style={{
                marginTop: 0,
                marginBottom: '14px',
                fontSize: '16px',
                fontWeight: 800,
                color: 'var(--text)',
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
              }}>
                <span>⚙️</span> Test Configuration
              </h3>
              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(2, 1fr)',
                gap: isMobile ? '10px' : '12px',
                fontSize: isMobile ? '13px' : '14px'
              }}>
                <div style={{ padding: '12px', background: 'var(--surface-2)', border: '1px solid var(--border)', borderRadius: 'var(--r-md)' }}>
                  <div style={{ fontWeight: 700, color: 'var(--text-muted)', marginBottom: '4px', fontSize: '12px', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Type</div>
                  <div style={{ color: 'var(--text)', fontWeight: 600 }}>{getQuestionTypeLabel(selectedTest.question_type)}</div>
                </div>
                <div style={{ padding: '12px', background: 'var(--surface-2)', border: '1px solid var(--border)', borderRadius: 'var(--r-md)' }}>
                  <div style={{ fontWeight: 700, color: 'var(--text-muted)', marginBottom: '4px', fontSize: '12px', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Hints</div>
                  <div style={{ color: 'var(--text)', fontWeight: 600 }}>
                    {getHintLevelLabel(selectedTest.hint_level)}
                    {selectedTest.hint_level === 'partial' && ` (${selectedTest.hint_percentage ?? 0}%)`}
                    {selectedTest.hint_level === 'full_after_tries' && ` (${selectedTest.hint_tries_before_reveal ?? 0})`}
                  </div>
                </div>
                <div style={{ padding: '12px', background: 'var(--surface-2)', border: '1px solid var(--border)', borderRadius: 'var(--r-md)' }}>
                  <div style={{ fontWeight: 700, color: 'var(--text-muted)', marginBottom: '4px', fontSize: '12px', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Time</div>
                  <div style={{ color: 'var(--text)', fontWeight: 600 }}>{(selectedTest.time_limit_seconds ?? 0) > 0 ? `${selectedTest.time_limit_seconds ?? 0}s` : 'No limit'}</div>
                </div>
                <div style={{ padding: '12px', background: 'var(--surface-2)', border: '1px solid var(--border)', borderRadius: 'var(--r-md)' }}>
                  <div style={{ fontWeight: 700, color: 'var(--text-muted)', marginBottom: '4px', fontSize: '12px', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Passing</div>
                  <div style={{ color: 'var(--text)', fontWeight: 600 }}>{selectedTest.passing_score}%</div>
                </div>
                <div style={{ padding: '12px', background: 'var(--surface-2)', border: '1px solid var(--border)', borderRadius: 'var(--r-md)', gridColumn: isMobile ? 'span 2' : 'span 1' }}>
                  <div style={{ fontWeight: 700, color: 'var(--text-muted)', marginBottom: '4px', fontSize: '12px', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Drills</div>
                  <div style={{ color: 'var(--text)', fontWeight: 600 }}>{selectedTest.drill_ids.split(',').length} drills</div>
                </div>
              </div>
            </div>

            {/* Statistics - Compact */}
            {stats && stats.total_attempts > 0 && (
              <div style={{
                padding: isMobile ? '16px' : '20px',
                background: 'var(--emerald-soft)',
                border: '1px solid var(--emerald)',
                borderRadius: 'var(--r-xl)',
                boxShadow: 'var(--shadow-sm)',
                marginBottom: '16px'
              }}>
                <h3 style={{
                  marginTop: 0,
                  marginBottom: '14px',
                  fontSize: '16px',
                  fontWeight: 800,
                  color: 'var(--emerald)',
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
                  <div style={{ padding: '12px', background: 'var(--surface)', borderRadius: 'var(--r-md)' }}>
                    <div style={{ fontWeight: 700, color: 'var(--emerald)', marginBottom: '4px', fontSize: '12px', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Attempts</div>
                    <div style={{ color: 'var(--text)', fontWeight: 800, fontSize: '18px' }}>{stats.total_attempts}</div>
                  </div>
                  <div style={{ padding: '12px', background: 'var(--surface)', borderRadius: 'var(--r-md)' }}>
                    <div style={{ fontWeight: 700, color: 'var(--emerald)', marginBottom: '4px', fontSize: '12px', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Avg Score</div>
                    <div style={{ color: 'var(--text)', fontWeight: 800, fontSize: '18px' }}>{stats.average_score}%</div>
                  </div>
                  <div style={{ padding: '12px', background: 'var(--surface)', borderRadius: 'var(--r-md)' }}>
                    <div style={{ fontWeight: 700, color: 'var(--emerald)', marginBottom: '4px', fontSize: '12px', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Completion</div>
                    <div style={{ color: 'var(--text)', fontWeight: 800, fontSize: '18px' }}>{stats.completion_rate}%</div>
                  </div>
                  <div style={{ padding: '12px', background: 'var(--surface)', borderRadius: 'var(--r-md)' }}>
                    <div style={{ fontWeight: 700, color: 'var(--emerald)', marginBottom: '4px', fontSize: '12px', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Passed</div>
                    <div style={{ color: 'var(--text)', fontWeight: 800, fontSize: '18px' }}>{stats.passed_attempts}/{stats.total_attempts}</div>
                  </div>
                  <div style={{ padding: '12px', background: 'var(--surface)', borderRadius: 'var(--r-md)', gridColumn: isMobile ? 'span 2' : 'span 1' }}>
                    <div style={{ fontWeight: 700, color: 'var(--emerald)', marginBottom: '4px', fontSize: '12px', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Avg Time</div>
                    <div style={{ color: 'var(--text)', fontWeight: 800, fontSize: '18px' }}>{stats.average_time}s</div>
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
                  padding: isMobile ? '14px 20px' : '13px 24px',
                  fontSize: '15px',
                  background: 'var(--brand-gradient)',
                  color: 'white',
                  border: 'none',
                  borderRadius: 'var(--r-md)',
                  cursor: 'pointer',
                  fontWeight: 700,
                  width: '100%',
                  boxShadow: 'var(--shadow-brand)'
                }}
              >
                🎯 Take Test
              </button>
              <button
                onClick={() => setEditingTestId(selectedTest.id)}
                style={{
                  padding: isMobile ? '14px 20px' : '13px 24px',
                  fontSize: '15px',
                  background: 'var(--surface)',
                  color: 'var(--text-soft)',
                  border: '1px solid var(--border)',
                  borderRadius: 'var(--r-md)',
                  cursor: 'pointer',
                  fontWeight: 700,
                  width: '100%',
                  boxShadow: 'var(--shadow-xs)'
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
                  padding: isMobile ? '14px 20px' : '13px 24px',
                  fontSize: '15px',
                  background: 'var(--sky-soft)',
                  color: 'var(--sky)',
                  border: '1px solid var(--sky)',
                  borderRadius: 'var(--r-md)',
                  cursor: 'pointer',
                  fontWeight: 700,
                  width: '100%',
                  boxShadow: 'var(--shadow-xs)'
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
                  padding: isMobile ? '14px 20px' : '13px 24px',
                  fontSize: '15px',
                  background: 'var(--amber-soft)',
                  color: 'var(--amber-strong)',
                  border: '1px solid var(--amber)',
                  borderRadius: 'var(--r-md)',
                  cursor: 'pointer',
                  fontWeight: 700,
                  width: '100%',
                  boxShadow: 'var(--shadow-xs)'
                }}
              >
                🎬 Crear Vidi
              </button>
            </div>

            {selectedTest.video_url && (
              <div style={{
                marginTop: '20px',
                padding: '20px',
                background: 'var(--emerald-soft)',
                border: '1px solid var(--emerald)',
                borderRadius: 'var(--r-xl)',
                boxShadow: 'var(--shadow-sm)',
                display: 'flex',
                flexDirection: 'column',
                gap: '12px',
                alignItems: 'flex-start'
              }}>
                <h3 style={{ margin: 0, color: 'var(--emerald)', fontSize: '18px', fontWeight: 800 }}>✅ Video Ready!</h3>
                <button
                  onClick={() => setViewingVideoUrl(selectedTest.video_url ?? null)}
                  style={{
                    padding: '11px 20px',
                    fontSize: '15px',
                    background: 'var(--emerald)',
                    color: 'white',
                    border: 'none',
                    borderRadius: 'var(--r-md)',
                    cursor: 'pointer',
                    fontWeight: 700,
                    boxShadow: 'var(--shadow-sm)'
                  }}
                >
                  ▶ View Video in Loop Player
                </button>
              </div>
            )}

            {generatingDemoVideoId === selectedTest.id && (
              <div style={{
                marginTop: '20px',
                padding: '20px',
                background: 'var(--amber-soft)',
                border: '1px solid var(--amber)',
                borderRadius: 'var(--r-xl)',
                boxShadow: 'var(--shadow-sm)',
                display: 'flex',
                alignItems: 'center',
                gap: '12px'
              }}>
                <div className="spinner" style={{ border: '4px solid var(--border)', width: '24px', height: '24px', borderRadius: '50%', borderLeftColor: 'var(--amber)', animation: 'spin 1s ease infinite', flexShrink: 0 }}></div>
                <p style={{ margin: 0, color: 'var(--amber-strong)', fontSize: '15px', fontWeight: 600 }}>Generating demo video… This may take a few minutes. Please keep this page open.</p>
              </div>
            )}
          </div>
        )}

        {/* No test selected (desktop) */}
        {!isMobile && !selectedTest && (
          <div style={{ flex: 1, padding: '30px', overflowY: 'auto', background: 'var(--bg)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <div style={{
              textAlign: 'center',
              padding: '48px',
              color: 'var(--text-soft)',
              background: 'var(--surface)',
              border: '1px solid var(--border)',
              borderRadius: 'var(--r-xl)',
              boxShadow: 'var(--shadow-sm)',
              maxWidth: '380px'
            }}>
              <div style={{
                width: '72px',
                height: '72px',
                margin: '0 auto 18px',
                borderRadius: 'var(--r-lg)',
                background: 'var(--brand-gradient-soft)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '34px'
              }}>👈</div>
              <p style={{ fontSize: '18px', margin: 0, fontWeight: 800, color: 'var(--text)' }}>Select a test to view details</p>
              <p style={{ fontSize: '14px', marginTop: '8px', marginBottom: 0 }}>Pick a test from the list to see its configuration, stats and actions.</p>
            </div>
          </div>
        )}
        {/* No test selected (mobile) - Show message if list is hidden */}
        {isMobile && !selectedTest && !showTestList && (
          <div style={{ flex: 1, padding: '30px', overflowY: 'auto', background: 'var(--bg)' }}>
            <div style={{
              textAlign: 'center',
              padding: '48px 24px',
              color: 'var(--text-soft)',
              background: 'var(--surface)',
              border: '1px solid var(--border)',
              borderRadius: 'var(--r-xl)',
              boxShadow: 'var(--shadow-sm)'
            }}>
              <p style={{ fontSize: '18px', fontWeight: 800, color: 'var(--text)' }}>No test selected</p>
              <button
                onClick={() => setShowTestList(true)}
                style={{
                  marginTop: '20px',
                  padding: '13px 24px',
                  background: 'var(--brand-gradient)',
                  color: 'white',
                  border: 'none',
                  borderRadius: 'var(--r-md)',
                  fontSize: '15px',
                  fontWeight: 700,
                  cursor: 'pointer',
                  boxShadow: 'var(--shadow-brand)'
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
