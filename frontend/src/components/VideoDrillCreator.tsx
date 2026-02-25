import React, { useState } from 'react';
import { API_BASE } from '../config';
import { useNavigate } from 'react-router-dom';

interface VideoSegment {
  start: number;
  end: number;
  text: string;
  text_catalan?: string;
  selected?: boolean;
}

interface VideoInfo {
  title: string;
  thumbnail: string;
  duration: number;
  original_language: string;
  segments: VideoSegment[];
}

const VideoDrillCreator: React.FC = () => {
  const navigate = useNavigate();
  const [url, setUrl] = useState('');
  const [cookies, setCookies] = useState('');
  const [videoFile, setVideoFile] = useState<File | null>(null);
  const [vttFile, setVttFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [videoInfo, setVideoInfo] = useState<VideoInfo | null>(null);
  const [tempVideoPath, setTempVideoPath] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tag, setTag] = useState('video_capture');

  const handleAnalyze = async () => {
    if (!url && !videoFile) return;
    setLoading(true);
    setError(null);
    try {
      if (videoFile) {
        // Upload based analysis
        const formData = new FormData();
        formData.append('video', videoFile);
        if (vttFile) formData.append('subtitles', vttFile);

        const response = await fetch(`${API_BASE}/video-analysis/upload`, {
          method: 'POST',
          body: formData,
        });
        if (!response.ok) throw new Error('File upload failed');
        const data = await response.json();
        
        setTempVideoPath(data.video_path);

        if (data.status === 'COMPLETED') {
          // Subtitles provided or fast processing
          setVideoInfo({
            title: data.title,
            thumbnail: '', 
            duration: 0,
            original_language: 'auto',
            segments: data.segments.map((s: any) => ({ ...s, selected: false }))
          });
        } else {
          // Polling required for ASR
          const jobId = data.job_id;
          let attempts = 0;
          const maxAttempts = 200; // ~10 minutes at 3s intervals

          const pollJob = async () => {
            if (attempts >= maxAttempts) {
              setError('Analysis timed out. Try a shorter video.');
              setLoading(false);
              return;
            }
            attempts++;
            
            try {
              const pollRes = await fetch(`${API_BASE}/video-analysis/job/${jobId}`);
              const pollData = await pollRes.json();

              if (pollData.status === 'COMPLETED') {
                setVideoInfo({
                  title: data.title,
                  thumbnail: '',
                  duration: 0,
                  original_language: 'auto',
                  segments: pollData.segments.map((s: any) => ({ ...s, selected: false }))
                });
                setLoading(false);
              } else if (pollData.status === 'FAILED') {
                setError(`Analysis failed: ${pollData.error_message}`);
                setLoading(false);
              } else {
                // Still processing, wait 3s
                setTimeout(pollJob, 3000);
              }
            } catch (err) {
              console.error('Polling error:', err);
              setTimeout(pollJob, 3000);
            }
          };

          setTimeout(pollJob, 3000);
          return; // Don't turn off loading yet
        }
      } else {
        // URL based analysis (existing logic)
        const response = await fetch(`${API_BASE}/video-analysis/analyze`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ url, cookies: cookies || null }),
        });
        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || 'Failed to analyze video');
        }
        const data = await response.json();
        data.segments = data.segments.map((s: any) => ({ ...s, selected: false }));
        setVideoInfo(data);
      }
    } catch (err: any) {
      setError(err.message);
    } finally {
      // Only turn off loading if we're not polling
      // (If polling, it's handled in the pollJob function)
    }
  };

  const handleTranslateAll = async () => {
    if (!videoInfo || !videoInfo.segments.length) return;
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/video-analysis/translate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          segments: videoInfo.segments,
          source_lang: videoInfo.original_language || 'auto'
        }),
      });
      if (!response.ok) throw new Error('Translation failed');
      const translatedSegments = await response.json();
      setVideoInfo({
        ...videoInfo,
        segments: translatedSegments.map((s: any, i: number) => ({
          ...s,
          selected: videoInfo.segments[i].selected
        }))
      });
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const toggleSegmentSelection = (index: number) => {
    if (!videoInfo) return;
    const newSegments = [...videoInfo.segments];
    newSegments[index].selected = !newSegments[index].selected;
    setVideoInfo({ ...videoInfo, segments: newSegments });
  };

  const handleCreateDrills = async () => {
    if (!videoInfo || !url) return;
    const selectedSegments = videoInfo.segments.filter(s => s.selected);
    if (!selectedSegments.length) {
      alert('Please select at least one segment');
      return;
    }

    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/video-analysis/create-drills`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          url: url || null,
          video_path: tempVideoPath,
          segments: selectedSegments,
          source_lang: videoInfo.original_language,
          tag,
          cookies: cookies || null,
        }),
      });
      if (!response.ok) throw new Error('Drill creation failed');
      const result = await response.json();
      alert(`Successfully created ${result.drills_created.length} drills!`);
      // Reset after success
      setVideoInfo(null);
      setUrl('');
      setVideoFile(null);
      setVttFile(null);
      setTempVideoPath(null);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="video-drill-creator" style={{ padding: '20px', maxWidth: '900px', margin: '0 auto' }}>
      <button 
        onClick={() => navigate('/')}
        style={{ 
          marginBottom: '20px', 
          padding: '8px 16px', 
          backgroundColor: '#eee', 
          border: 'none', 
          borderRadius: '4px',
          cursor: 'pointer'
        }}
      >
        ← Back to Drills
      </button>
      <h2 style={{ color: '#2c3e50', marginBottom: '20px' }}>Create Drills from Video</h2>
      
      <div className="input-group" style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginBottom: '20px' }}>
        <input 
          type="text" 
          value={url} 
          onChange={(e) => setUrl(e.target.value)}
          placeholder="Paste YouTube URL here..."
          style={{ padding: '12px', borderRadius: '8px', border: '1px solid #ddd' }}
        />

        <div style={{ padding: '15px', background: '#f0f7ff', borderRadius: '8px', border: '1px solid #cce3ff' }}>
          <h4 style={{ margin: '0 0 10px 0', color: '#0056b3' }}>OR Upload Files (Bypass YouTube blocks)</h4>
          <div style={{ display: 'flex', gap: '15px', flexWrap: 'wrap' }}>
            <div>
              <label style={{ display: 'block', fontSize: '12px', fontWeight: 'bold' }}>Video (.mp4):</label>
              <input type="file" accept="video/mp4" onChange={(e) => setVideoFile(e.target.files?.[0] || null)} />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '12px', fontWeight: 'bold' }}>Subtitles (.vtt):</label>
              <input type="file" accept=".vtt" onChange={(e) => setVttFile(e.target.files?.[0] || null)} />
            </div>
          </div>
        </div>
        
        <div className="cookies-section" style={{ marginTop: '10px' }}>
          <label style={{ display: 'block', marginBottom: '5px', fontSize: '14px', color: '#666' }}>
            YouTube Cookies (Optional - Netscape format. Needed if blocked by bot detection):
          </label>
          <textarea 
            value={cookies}
            onChange={(e) => setCookies(e.target.value)}
            placeholder="# Netscape HTTP Cookie File..."
            style={{ 
              width: '100%', 
              height: '80px', 
              padding: '10px', 
              borderRadius: '8px', 
              border: '1px solid #ddd',
              fontFamily: 'monospace',
              fontSize: '12px'
            }}
          />
        </div>

        <button 
          onClick={handleAnalyze} 
          disabled={loading || (!url && !videoFile)}
          style={{ 
            padding: '12px 24px', 
            borderRadius: '8px', 
            backgroundColor: '#3498db', 
            color: 'white', 
            border: 'none',
            cursor: (loading || (!url && !videoFile)) ? 'not-allowed' : 'pointer',
            opacity: (loading || (!url && !videoFile)) ? 0.7 : 1,
            alignSelf: 'flex-start',
            marginTop: '10px'
          }}
        >
          {loading ? (videoFile ? 'Uploading & Analyzing...' : 'Analyzing...') : 'Analyze Video / Upload'}
        </button>
      </div>

      {error && <p style={{ color: 'red', marginBottom: '20px' }}>{error}</p>}

      {videoInfo && (
        <div className="video-info" style={{ backgroundColor: '#f9f9f9', padding: '20px', borderRadius: '12px' }}>
          <div style={{ display: 'flex', gap: '20px', marginBottom: '20px', alignItems: 'center' }}>
            <img 
              src={videoInfo.thumbnail} 
              alt={videoInfo.title} 
              style={{ width: '180px', borderRadius: '8px', boxShadow: '0 4px 6px rgba(0,0,0,0.1)' }} 
            />
            <div>
              <h3 style={{ margin: '0 0 10px 0' }}>{videoInfo.title}</h3>
              <p style={{ margin: 0, color: '#666' }}>Duration: {formatTime(videoInfo.duration)}</p>
              <p style={{ margin: '5px 0 0 0', color: '#666' }}>Captions found in: {videoInfo.original_language}</p>
              <div style={{ marginTop: '15px' }}>
                <label style={{ marginRight: '10px', fontSize: '14px', fontWeight: 'bold' }}>Tag for drills:</label>
                <input 
                  type="text" 
                  value={tag} 
                  onChange={(e) => setTag(e.target.value)}
                  style={{ padding: '5px 10px', borderRadius: '4px', border: '1px solid #ddd' }}
                />
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px' }}>
            <h4 style={{ margin: 0 }}>Video Segments ({videoInfo.segments.length})</h4>
            <button 
              onClick={handleTranslateAll}
              disabled={loading}
              style={{ padding: '8px 16px', backgroundColor: '#9b59b6', color: 'white', borderRadius: '6px', border: 'none', cursor: 'pointer' }}
            >
              Translate All to Catalan
            </button>
          </div>

          <div className="segments-list" style={{ maxHeight: '400px', overflowY: 'auto', border: '1px solid #eee', borderRadius: '8px', backgroundColor: 'white' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead style={{ position: 'sticky', top: 0, backgroundColor: '#eee', zIndex: 1 }}>
                <tr>
                  <th style={{ padding: '10px', textAlign: 'left' }}>
                    <input 
                      type="checkbox" 
                      onChange={(e) => {
                        const newSegments = videoInfo.segments.map(s => ({ ...s, selected: e.target.checked }));
                        setVideoInfo({ ...videoInfo, segments: newSegments });
                      }}
                    />
                  </th>
                  <th style={{ padding: '10px', textAlign: 'left' }}>Time & Trim</th>
                  <th style={{ padding: '10px', textAlign: 'left' }}>Original Text (Video)</th>
                  <th style={{ padding: '10px', textAlign: 'left' }}>Translation (Català)</th>
                </tr>
              </thead>
              <tbody>
                {videoInfo.segments.map((seg, idx) => (
                  <tr key={idx} style={{ borderBottom: '1px solid #eee', background: seg.selected ? '#f0f7ff' : 'white' }}>
                    <td style={{ padding: '10px' }}>
                      <input 
                        type="checkbox" 
                        checked={seg.selected} 
                        onChange={() => toggleSegmentSelection(idx)}
                      />
                    </td>
                    <td style={{ padding: '10px' }}>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                          <span style={{ fontSize: '11px', color: '#888' }}>S:</span>
                          <input 
                            type="number" 
                            value={seg.start} 
                            step="0.1"
                            onChange={(e) => {
                              const newSegments = [...videoInfo.segments];
                              newSegments[idx].start = parseFloat(e.target.value);
                              setVideoInfo({ ...videoInfo, segments: newSegments });
                            }}
                            style={{ width: '60px', padding: '2px', fontSize: '12px' }}
                          />
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                          <span style={{ fontSize: '11px', color: '#888' }}>E:</span>
                          <input 
                            type="number" 
                            value={seg.end} 
                            step="0.1"
                            onChange={(e) => {
                              const newSegments = [...videoInfo.segments];
                              newSegments[idx].end = parseFloat(e.target.value);
                              setVideoInfo({ ...videoInfo, segments: newSegments });
                            }}
                            style={{ width: '60px', padding: '2px', fontSize: '12px' }}
                          />
                        </div>
                      </div>
                    </td>
                    <td style={{ padding: '10px' }}>
                      <textarea 
                        value={seg.text} 
                        onChange={(e) => {
                          const newSegments = [...videoInfo.segments];
                          newSegments[idx].text = e.target.value;
                          setVideoInfo({ ...videoInfo, segments: newSegments });
                        }}
                        style={{ width: '100%', minHeight: '40px', padding: '4px', fontSize: '13px' }}
                      />
                    </td>
                    <td style={{ padding: '10px' }}>
                      <textarea 
                        value={seg.text_catalan || ''} 
                        onChange={(e) => {
                          const newSegments = [...videoInfo.segments];
                          newSegments[idx].text_catalan = e.target.value;
                          setVideoInfo({ ...videoInfo, segments: newSegments });
                        }}
                        placeholder="Pending..."
                        style={{ width: '100%', minHeight: '40px', padding: '4px', fontSize: '13px', color: '#27ae60' }}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div style={{ marginTop: '20px', textAlign: 'right' }}>
            <button 
              onClick={handleCreateDrills}
              disabled={loading || !videoInfo.segments.some(s => s.selected)}
              style={{ 
                padding: '12px 30px', 
                backgroundColor: '#27ae60', 
                color: 'white', 
                borderRadius: '8px', 
                border: 'none', 
                fontSize: '16px', 
                fontWeight: 'bold',
                cursor: 'pointer',
                boxShadow: '0 4px 6px rgba(0,0,0,0.1)'
              }}
            >
              {loading ? 'Creating Drills...' : 'Create Drills from Selected Segments'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default VideoDrillCreator;
