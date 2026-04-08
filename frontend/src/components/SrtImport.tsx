import React, { useState } from 'react';
import { API_BASE } from '../config';
import { useNavigate } from 'react-router-dom';

interface SrtSegment {
  sequence: number;
  start_time: string;
  end_time: string;
  text: string;
}

interface SrtImportRequest {
  srt_content: string;
  video_url: string;
  tag?: string;
  author?: string;
  create_test?: boolean;
  test_title?: string;
}

const SrtImport: React.FC = () => {
  const navigate = useNavigate();
  const [srtContent, setSrtContent] = useState('');
  const [videoUrl, setVideoUrl] = useState('');
  const [tag, setTag] = useState('youtube_srt');
  const [author, setAuthor] = useState('');
  const [createTest, setCreateTest] = useState(true);
  const [testTitle, setTestTitle] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<{ drills_created: number; test_id?: number } | null>(null);
  const [parsedSegments, setParsedSegments] = useState<SrtSegment[]>([]);
  const [previewMode, setPreviewMode] = useState(false);

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      const content = event.target?.result as string;
      setSrtContent(content);
      parseSrtContent(content);
    };
    reader.readAsText(file);
  };

  const parseSrtContent = (content: string) => {
    try {
      const lines = content.split('\n');
      const segments: SrtSegment[] = [];
      let currentSegment: Partial<SrtSegment> = {};
      
      for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim();
        
        if (!line) {
          // Empty line indicates end of segment
          if (currentSegment.sequence && currentSegment.start_time && currentSegment.end_time && currentSegment.text) {
            segments.push(currentSegment as SrtSegment);
          }
          currentSegment = {};
          continue;
        }
        
        if (!currentSegment.sequence && /^\d+$/.test(line)) {
          // Sequence number
          currentSegment.sequence = parseInt(line, 10);
        } else if (!currentSegment.start_time && line.includes('-->')) {
          // Timestamp line
          const [start, end] = line.split('-->').map(s => s.trim());
          currentSegment.start_time = start;
          currentSegment.end_time = end;
        } else if (currentSegment.start_time) {
          // Text line
          if (currentSegment.text) {
            currentSegment.text += ' ' + line;
          } else {
            currentSegment.text = line;
          }
        }
      }
      
      // Add last segment if exists
      if (currentSegment.sequence && currentSegment.start_time && currentSegment.end_time && currentSegment.text) {
        segments.push(currentSegment as SrtSegment);
      }
      
      setParsedSegments(segments);
      setPreviewMode(true);
    } catch (err) {
      console.error('Error parsing SRT:', err);
      setError('Failed to parse SRT file. Please check the format.');
    }
  };

  const handleParse = () => {
    if (!srtContent.trim()) {
      setError('Please provide SRT content');
      return;
    }
    parseSrtContent(srtContent);
  };

  const handleImport = async () => {
    if (!srtContent.trim()) {
      setError('Please provide SRT content');
      return;
    }
    if (!videoUrl.trim()) {
      setError('Please provide YouTube video URL');
      return;
    }

    setLoading(true);
    setError(null);
    setSuccess(null);

    try {
      const request: SrtImportRequest = {
        srt_content: srtContent,
        video_url: videoUrl,
        tag: tag || undefined,
        author: author || undefined,
        create_test: createTest,
        test_title: testTitle || undefined,
      };

      const response = await fetch(`${API_BASE}/srt/import`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(request),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to import SRT');
      }

      const result = await response.json();
      setSuccess({
        drills_created: result.drills_created?.length || 0,
        test_id: result.test_id,
      });

      // Reset form after successful import
      setSrtContent('');
      setVideoUrl('');
      setTestTitle('');
      setParsedSegments([]);
      setPreviewMode(false);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const formatTime = (timestamp: string) => {
    // SRT format: HH:MM:SS,mmm
    const [time, _milliseconds] = timestamp.split(',');
    return time;
  };

  return (
    <div className="srt-import" style={{ padding: '20px', maxWidth: '900px', margin: '0 auto' }}>
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
      <h2 style={{ color: '#2c3e50', marginBottom: '20px' }}>Import Drills from SRT Subtitles</h2>
      
      <div className="import-form" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        <div className="input-section" style={{ backgroundColor: '#f9f9f9', padding: '20px', borderRadius: '12px' }}>
          <h3 style={{ marginTop: 0, marginBottom: '15px' }}>1. SRT File</h3>
          
          <div style={{ marginBottom: '15px' }}>
            <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>
              Upload SRT File:
            </label>
            <input
              type="file"
              accept=".srt,.txt"
              onChange={handleFileUpload}
              style={{ padding: '8px', borderRadius: '6px', border: '1px solid #ddd' }}
            />
            <p style={{ fontSize: '12px', color: '#666', marginTop: '5px' }}>
              Or paste SRT content below
            </p>
          </div>
          
          <div>
            <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>
              SRT Content:
            </label>
            <textarea
              value={srtContent}
              onChange={(e) => setSrtContent(e.target.value)}
              placeholder={`1
00:00:01,000 --> 00:00:04,000
Hello, this is the first line.

2
00:00:05,000 --> 00:00:08,000
This is the second line.`}
              rows={10}
              style={{
                width: '100%',
                padding: '12px',
                borderRadius: '8px',
                border: '1px solid #ddd',
                fontFamily: 'monospace',
                fontSize: '14px',
                resize: 'vertical'
              }}
            />
          </div>
          
          <button
            onClick={handleParse}
            disabled={!srtContent.trim()}
            style={{
              marginTop: '15px',
              padding: '10px 20px',
              backgroundColor: '#3498db',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              cursor: srtContent.trim() ? 'pointer' : 'not-allowed',
              opacity: srtContent.trim() ? 1 : 0.7
            }}
          >
            {previewMode ? 'Update Preview' : 'Preview Segments'}
          </button>
        </div>

        <div className="input-section" style={{ backgroundColor: '#f9f9f9', padding: '20px', borderRadius: '12px' }}>
          <h3 style={{ marginTop: 0, marginBottom: '15px' }}>2. Video Configuration</h3>
          
          <div style={{ marginBottom: '15px' }}>
            <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>
              YouTube Video URL:
            </label>
            <input
              type="text"
              value={videoUrl}
              onChange={(e) => setVideoUrl(e.target.value)}
              placeholder="https://www.youtube.com/watch?v=..."
              style={{
                width: '100%',
                padding: '12px',
                borderRadius: '8px',
                border: '1px solid #ddd'
              }}
            />
            <p style={{ fontSize: '12px', color: '#666', marginTop: '5px' }}>
              Each drill will link to this video with the appropriate timestamp
            </p>
          </div>
          
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '15px' }}>
            <div>
              <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>
                Tag:
              </label>
              <input
                type="text"
                value={tag}
                onChange={(e) => setTag(e.target.value)}
                placeholder="youtube_srt"
                style={{
                  width: '100%',
                  padding: '10px',
                  borderRadius: '6px',
                  border: '1px solid #ddd'
                }}
              />
            </div>
            
            <div>
              <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>
                Author (Optional):
              </label>
              <input
                type="text"
                value={author}
                onChange={(e) => setAuthor(e.target.value)}
                placeholder="Your name"
                style={{
                  width: '100%',
                  padding: '10px',
                  borderRadius: '6px',
                  border: '1px solid #ddd'
                }}
              />
            </div>
          </div>
        </div>

        <div className="input-section" style={{ backgroundColor: '#f9f9f9', padding: '20px', borderRadius: '12px' }}>
          <h3 style={{ marginTop: 0, marginBottom: '15px' }}>3. Test Configuration</h3>
          
          <div style={{ marginBottom: '15px' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: '10px', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={createTest}
                onChange={(e) => setCreateTest(e.target.checked)}
              />
              <span style={{ fontWeight: 'bold' }}>Create a test with all drills</span>
            </label>
            <p style={{ fontSize: '12px', color: '#666', marginLeft: '30px', marginTop: '5px' }}>
              Creates a test containing all the imported drills for practice
            </p>
          </div>
          
          {createTest && (
            <div>
              <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>
                Test Title (Optional):
              </label>
              <input
                type="text"
                value={testTitle}
                onChange={(e) => setTestTitle(e.target.value)}
                placeholder="e.g., 'Episode 1 Vocabulary Practice'"
                style={{
                  width: '100%',
                  padding: '10px',
                  borderRadius: '6px',
                  border: '1px solid #ddd'
                }}
              />
            </div>
          )}
        </div>

        {error && (
          <div style={{ padding: '15px', backgroundColor: '#ffe6e6', borderRadius: '8px', border: '1px solid #ff9999' }}>
            <p style={{ color: '#cc0000', margin: 0 }}>Error: {error}</p>
          </div>
        )}

        {success && (
          <div style={{ padding: '15px', backgroundColor: '#e6ffe6', borderRadius: '8px', border: '1px solid #99cc99' }}>
            <p style={{ color: '#006600', margin: 0, fontWeight: 'bold' }}>
              ✅ Successfully created {success.drills_created} drills!
            </p>
            {success.test_id && (
              <p style={{ color: '#006600', margin: '5px 0 0 0' }}>
                Test created with ID: {success.test_id}
              </p>
            )}
            <button
              onClick={() => navigate('/tests')}
              style={{
                marginTop: '10px',
                padding: '8px 16px',
                backgroundColor: '#27ae60',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                cursor: 'pointer'
              }}
            >
              View Tests
            </button>
          </div>
        )}

        {previewMode && parsedSegments.length > 0 && (
          <div className="preview-section" style={{ backgroundColor: '#f0f7ff', padding: '20px', borderRadius: '12px' }}>
            <h3 style={{ marginTop: 0, marginBottom: '15px' }}>Preview: {parsedSegments.length} Segments Found</h3>
            
            <div style={{ maxHeight: '300px', overflowY: 'auto', border: '1px solid #cce3ff', borderRadius: '8px', backgroundColor: 'white' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead style={{ position: 'sticky', top: 0, backgroundColor: '#e6f2ff', zIndex: 1 }}>
                  <tr>
                    <th style={{ padding: '10px', textAlign: 'left', borderBottom: '1px solid #cce3ff' }}>#</th>
                    <th style={{ padding: '10px', textAlign: 'left', borderBottom: '1px solid #cce3ff' }}>Start Time</th>
                    <th style={{ padding: '10px', textAlign: 'left', borderBottom: '1px solid #cce3ff' }}>End Time</th>
                    <th style={{ padding: '10px', textAlign: 'left', borderBottom: '1px solid #cce3ff' }}>Text</th>
                  </tr>
                </thead>
                <tbody>
                  {parsedSegments.slice(0, 20).map((segment, idx) => (
                    <tr key={idx} style={{ borderBottom: '1px solid #e6f2ff' }}>
                      <td style={{ padding: '10px', fontWeight: 'bold' }}>{segment.sequence}</td>
                      <td style={{ padding: '10px', fontFamily: 'monospace' }}>{formatTime(segment.start_time)}</td>
                      <td style={{ padding: '10px', fontFamily: 'monospace' }}>{formatTime(segment.end_time)}</td>
                      <td style={{ padding: '10px', maxWidth: '300px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {segment.text}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {parsedSegments.length > 20 && (
                <div style={{ padding: '10px', textAlign: 'center', backgroundColor: '#f0f7ff', borderTop: '1px solid #cce3ff' }}>
                  <p style={{ margin: 0, color: '#666', fontSize: '14px' }}>
                    ... and {parsedSegments.length - 20} more segments
                  </p>
                </div>
              )}
            </div>
          </div>
        )}

        <div style={{ textAlign: 'center', marginTop: '20px' }}>
          <button
            onClick={handleImport}
            disabled={loading || !srtContent.trim() || !videoUrl.trim()}
            style={{
              padding: '15px 40px',
              backgroundColor: '#27ae60',
              color: 'white',
              border: 'none',
              borderRadius: '8px',
              fontSize: '16px',
              fontWeight: 'bold',
              cursor: (loading || !srtContent.trim() || !videoUrl.trim()) ? 'not-allowed' : 'pointer',
              opacity: (loading || !srtContent.trim() || !videoUrl.trim()) ? 0.7 : 1,
              boxShadow: '0 4px 6px rgba(0,0,0,0.1)'
            }}
          >
            {loading ? 'Importing...' : 'Import SRT and Create Drills'}
          </button>
          <p style={{ fontSize: '12px', color: '#666', marginTop: '10px' }}>
            This will create one drill for each SRT segment with video timestamps
          </p>
        </div>
      </div>
    </div>
  );
};

export default SrtImport;