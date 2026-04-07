import { useState, useEffect, useRef } from 'react';
import { getMediaUrl } from '../config';
import { getMediaWithOfflineFallback } from '../utils/offlineCache';

interface Drill {
  id: number;
  text_catalan?: string;
  text_tachelhit?: string;
  text_arabic?: string;
  audio_url?: string;
  audio_tts_url?: string;
  video_url?: string;
  image_url?: string;
  tag?: string;
  date_created: string;
}

interface DrillPlayerProps {
  drills: Drill[];
  onExit: () => void;
}

export default function DrillPlayer({ drills, onExit }: DrillPlayerProps) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [autoPlayEnabled, setAutoPlayEnabled] = useState(false);
  const [loopEnabled, setLoopEnabled] = useState(false);
  const [audioProgress, setAudioProgress] = useState(0);
  const [audioDuration, setAudioDuration] = useState(0);
  const [imageUrl, setImageUrl] = useState<string>('');
  const [showVideo, setShowVideo] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const ttsAudioRef = useRef<HTMLAudioElement | null>(null);
  const speechSynthRef = useRef<SpeechSynthesisUtterance | null>(null);
  const progressIntervalRef = useRef<number | null>(null);

  const currentDrill = drills[currentIndex];
  const isMobile = window.innerWidth < 768;

  // Track progress of whichever audio is playing
  useEffect(() => {
    if (progressIntervalRef.current) window.clearInterval(progressIntervalRef.current);

    if (isPlaying) {
      progressIntervalRef.current = window.setInterval(() => {
        const activeAudio = audioRef.current || ttsAudioRef.current;
        if (activeAudio) {
          setAudioProgress(activeAudio.currentTime);
          setAudioDuration(activeAudio.duration || 0);
        }
      }, 100);
    } else {
      setAudioProgress(0);
    }

    return () => {
      if (progressIntervalRef.current) window.clearInterval(progressIntervalRef.current);
    };
  }, [isPlaying]);

  const handleSeek = (time: number) => {
    const activeAudio = audioRef.current || ttsAudioRef.current;
    if (activeAudio) {
      activeAudio.currentTime = time;
      setAudioProgress(time);
    }
  };

  // Update image URL when drill changes
  useEffect(() => {
    const updateImageUrl = async () => {
      if (currentDrill?.image_url) {
        try {
          const url = await getMediaWithOfflineFallback(currentDrill.image_url, getMediaUrl);
          setImageUrl(url);
        } catch (error) {
          console.error('Failed to load image:', error);
          setImageUrl(getMediaUrl(currentDrill.image_url));
        }
      } else {
        setImageUrl('');
      }
    };
    updateImageUrl();
  }, [currentDrill]);

  // Cleanup on drill change
  useEffect(() => {
    setIsPlaying(false);
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
    if (ttsAudioRef.current) {
      ttsAudioRef.current.pause();
      ttsAudioRef.current = null;
    }
    if (speechSynthRef.current) {
      speechSynthesis.cancel();
      speechSynthRef.current = null;
    }
  }, [currentIndex]);

  // Autoplay effect
  useEffect(() => {
    if (!autoPlayEnabled || !currentDrill) return;
    const timer = setTimeout(() => {
      playCurrentAudio();
    }, 500);
    return () => clearTimeout(timer);
  }, [currentIndex, autoPlayEnabled]);

  // Initial autoplay (except iOS)
  useEffect(() => {
    const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent);
    if (!isIOS) {
      setAutoPlayEnabled(true);
    }
  }, []);

  const playCurrentAudio = async () => {
    stopAllAudio();
    setIsPlaying(true);

    try {
      // 1. Catalan (1x)
      await handleSpeakCatalan();

      // 2. Tachelhit (2x)
      await playTachelhitAudio();
    } catch (error) {
      console.error('Playback sequence error:', error);
      setIsPlaying(false);
      if (autoPlayEnabled) goToNextDrill();
    }
  };

  const stopAllAudio = () => {
    if (audioRef.current) { audioRef.current.pause(); audioRef.current = null; }
    if (ttsAudioRef.current) { ttsAudioRef.current.pause(); ttsAudioRef.current = null; }
    if (speechSynthRef.current) { speechSynthesis.cancel(); speechSynthRef.current = null; }
  };

  const playTachelhitAudio = async (): Promise<void> => {
    if (!currentDrill?.audio_url) {
      if (autoPlayEnabled) goToNextDrill();
      return;
    }

    try {
      // Get audio URL with offline fallback
      const audioUrl = await getMediaWithOfflineFallback(currentDrill.audio_url, getMediaUrl);
      const audio = new Audio(audioUrl);
      audioRef.current = audio;
      let internalCount = 0;

      return new Promise((resolve, reject) => {
        const playInstance = () => {
          internalCount++;
          setIsPlaying(true);

          const handleEnded = () => {
            audio.removeEventListener('ended', handleEnded);
            audio.removeEventListener('error', handleError);

            if (internalCount < 2) {
              setTimeout(playInstance, 600);
            } else {
              setIsPlaying(false);
              setTimeout(() => {
                if (autoPlayEnabled) goToNextDrill();
                resolve();
              }, 1000);
            }
          };

          const handleError = (error: any) => {
            audio.removeEventListener('ended', handleEnded);
            audio.removeEventListener('error', handleError);
            setIsPlaying(false);
            if (autoPlayEnabled) goToNextDrill();
            reject(error);
          };

          audio.addEventListener('ended', handleEnded);
          audio.addEventListener('error', handleError);
          audio.play().catch(handleError);
        };
        playInstance();
      });
    } catch (error) {
      console.error('Failed to load audio:', error);
      setIsPlaying(false);
      if (autoPlayEnabled) goToNextDrill();
      throw error;
    }
  };

  const handleSpeakCatalan = async (): Promise<void> => {
    if (currentDrill?.audio_tts_url) {
      try {
        const audioUrl = await getMediaWithOfflineFallback(currentDrill.audio_tts_url, getMediaUrl);
        const audio = new Audio(audioUrl);
        ttsAudioRef.current = audio;

        return new Promise((resolve, reject) => {
          audio.onended = () => { ttsAudioRef.current = null; resolve(); };
          audio.onerror = () => {
            ttsAudioRef.current = null;
            handleSpeechSynthesis().then(resolve).catch(reject);
          };
          audio.play().catch(() => handleSpeechSynthesis().then(resolve).catch(reject));
        });
      } catch (error) {
        console.error('Failed to load TTS audio:', error);
        return handleSpeechSynthesis();
      }
    } else {
      return handleSpeechSynthesis();
    }
  };

  const handleSpeechSynthesis = (): Promise<void> => {
    return new Promise((resolve) => {
      if (!currentDrill?.text_catalan) return resolve();
      if (!('speechSynthesis' in window)) return resolve();

      speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(currentDrill.text_catalan);
      utterance.lang = 'ca-ES';
      utterance.rate = 0.9;
      speechSynthRef.current = utterance;
      utterance.onend = () => { speechSynthRef.current = null; resolve(); };
      utterance.onerror = () => { speechSynthRef.current = null; resolve(); };
      speechSynthesis.speak(utterance);
    });
  };

  const goToNextDrill = () => {
    if (currentIndex < drills.length - 1) {
      setCurrentIndex(currentIndex + 1);
    } else if (loopEnabled) {
      setCurrentIndex(0);
    } else {
      onExit();
    }
  };

  const handlePrev = () => {
    if (currentIndex > 0) setCurrentIndex(currentIndex - 1);
  };

  return (
    <div style={{
      height: '100vh',
      width: '100vw',
      display: 'flex',
      flexDirection: 'column',
      background: 'white',
      overflow: 'hidden',
      position: 'fixed',
      top: 0, left: 0, right: 0, bottom: 0,
      zIndex: 1000
    }}>
      {/* Header */}
      <div style={{
        padding: '10px 16px',
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        color: 'white',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <button onClick={onExit} style={cleanButtonStyle}>✕</button>
          <span style={{ fontWeight: 700 }}>{currentIndex + 1} / {drills.length}</span>
        </div>

        <div style={{ display: 'flex', gap: '6px' }}>
          <button
            onClick={() => setAutoPlayEnabled(!autoPlayEnabled)}
            style={{ ...pillButtonStyle, background: autoPlayEnabled ? '#FFD700' : 'rgba(255,255,255,0.2)', color: autoPlayEnabled ? '#333' : 'white' }}
          >
            AUTO {autoPlayEnabled ? 'ON' : 'OFF'}
          </button>
          <button
            onClick={() => setLoopEnabled(!loopEnabled)}
            style={{ ...pillButtonStyle, background: loopEnabled ? '#FFD700' : 'rgba(255,255,255,0.2)', color: loopEnabled ? '#333' : 'white' }}
          >
            LOOP {loopEnabled ? 'ON' : 'OFF'}
          </button>
        </div>
      </div>

      {/* Main Content Area */}
      <div style={{
        flex: 1,
        overflowY: 'auto',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center'
      }}>
        <div style={{ width: '100%', maxWidth: '500px', display: 'flex', flexDirection: 'column' }}>

          {/* 1. Tachelhit (Prominent) */}
          <div style={{ padding: '20px 16px', textAlign: 'center' }}>
            <div style={{ fontSize: isMobile ? '26px' : '32px', fontWeight: 800, color: '#2e7d32', lineHeight: 1.2 }}>
              {currentDrill.text_tachelhit || '---'}
            </div>
          </div>

          {/* 2. Image (Full Width Square) */}
          <div style={{ width: '100%', aspectRatio: '1/1', background: '#f0f0f0', overflow: 'hidden' }}>
            {imageUrl ? (
              <img src={imageUrl} alt="Visual" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
            ) : currentDrill.image_url ? (
              <img src={getMediaUrl(currentDrill.image_url)} alt="Visual" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
            ) : (
              <div style={{ width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '40px', opacity: 0.1 }}>📷</div>
            )}
          </div>

          {/* 3. Translations (Subtle) */}
          <div style={{ padding: '16px', textAlign: 'center', display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <div style={{ fontSize: '14px', color: '#666', fontWeight: 500 }}>{currentDrill.text_catalan}</div>
            {currentDrill.text_arabic && (
              <div style={{ fontSize: '14px', color: '#9C27B0', direction: 'rtl', opacity: 0.8 }}>{currentDrill.text_arabic}</div>
            )}
          </div>
        </div>
      </div>

      {/* Navigation Footer - Enhanced for mobile */}
      <div style={{
        padding: isMobile ? '12px 16px' : '8px 12px',
        background: 'white',
        borderTop: '1px solid #eee',
        display: 'flex',
        flexDirection: 'column',
        gap: isMobile ? '12px' : '4px',
        paddingBottom: isMobile ? 'calc(20px + env(safe-area-inset-bottom, 0px))' : '8px',
        flexShrink: 0
      }}>
        {/* Progress Slider */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '0 4px' }}>
          <span style={{ fontSize: isMobile ? '12px' : '10px', color: '#999', minWidth: '30px', textAlign: 'right' }}>
            {Math.floor(audioProgress / 60)}:{(audioProgress % 60).toFixed(0).padStart(2, '0')}
          </span>
          <input
            type="range"
            min="0"
            max={audioDuration || 100}
            step="0.1"
            value={audioProgress}
            onChange={(e) => handleSeek(parseFloat(e.target.value))}
            style={{
              flex: 1,
              cursor: 'pointer',
              accentColor: '#667eea',
              height: isMobile ? '6px' : '3px',
              borderRadius: '3px'
            }}
          />
          <span style={{ fontSize: isMobile ? '12px' : '10px', color: '#999', minWidth: '30px' }}>
            {Math.floor(audioDuration / 60)}:{(audioDuration % 60).toFixed(0).padStart(2, '0')}
          </span>
        </div>

        {/* Main Controls - Enhanced for mobile */}
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          width: '100%',
          gap: isMobile ? '8px' : '4px'
        }}>
          {/* Previous Button */}
          <button
            onClick={handlePrev}
            disabled={currentIndex === 0}
            style={{
              ...iconButtonStyle,
              background: currentIndex === 0 ? '#f5f5f5' : '#667eea',
              color: currentIndex === 0 ? '#999' : 'white',
              borderRadius: isMobile ? '12px' : '8px',
              width: isMobile ? '60px' : '44px',
              height: isMobile ? '60px' : '44px',
              fontSize: isMobile ? '24px' : '18px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              opacity: currentIndex === 0 ? 0.5 : 1
            }}
            title="Previous drill"
          >
            ⏮️
          </button>

          {/* Catalan Speak Button */}
          <button
            onClick={() => handleSpeakCatalan()}
            style={{
              ...iconButtonStyle,
              background: '#4CAF50',
              color: 'white',
              borderRadius: isMobile ? '12px' : '8px',
              width: isMobile ? '60px' : '44px',
              height: isMobile ? '60px' : '44px',
              fontSize: isMobile ? '24px' : '18px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}
            title="Speak Catalan"
          >
            🗣️
          </button>

          {/* Main Play Button - More prominent on mobile */}
          <button
            onClick={() => playCurrentAudio()}
            style={{
              ...iconButtonStyle,
              background: isPlaying ? '#ff4444' : '#667eea',
              color: 'white',
              borderRadius: '50%',
              width: isMobile ? '80px' : '60px',
              height: isMobile ? '80px' : '60px',
              fontSize: isMobile ? '32px' : '24px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 4px 12px rgba(102, 126, 234, 0.3)',
              border: isMobile ? '3px solid white' : '2px solid white'
            }}
            title={isPlaying ? 'Stop' : 'Play'}
          >
            {isPlaying ? '⏸️' : '▶️'}
          </button>

          {/* Tachelhit Audio Button */}
          <button
            onClick={() => playTachelhitAudio()}
            style={{
              ...iconButtonStyle,
              background: '#9C27B0',
              color: 'white',
              borderRadius: isMobile ? '12px' : '8px',
              width: isMobile ? '60px' : '44px',
              height: isMobile ? '60px' : '44px',
              fontSize: isMobile ? '24px' : '18px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}
            title="Play Tachelhit audio"
          >
            🎙️
          </button>

          {/* Video Play Button */}
          {currentDrill.video_url && (
            <button
              onClick={() => setShowVideo(true)}
              style={{
                ...iconButtonStyle,
                background: '#FF6B6B',
                color: 'white',
                borderRadius: isMobile ? '12px' : '8px',
                width: isMobile ? '60px' : '44px',
                height: isMobile ? '60px' : '44px',
                fontSize: isMobile ? '24px' : '18px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}
              title="Play video"
            >
              🎥
            </button>
          )}

          {/* Next Button */}
          <button
            onClick={goToNextDrill}
            style={{
              ...iconButtonStyle,
              background: currentIndex < drills.length - 1 ? '#667eea' : (loopEnabled ? '#4CAF50' : '#FFD700'),
              color: 'white',
              borderRadius: isMobile ? '12px' : '8px',
              width: isMobile ? '60px' : '44px',
              height: isMobile ? '60px' : '44px',
              fontSize: isMobile ? '24px' : '18px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}
            title={currentIndex < drills.length - 1 ? 'Next drill' : (loopEnabled ? 'Restart from beginning' : 'Finish')}
          >
            {currentIndex < drills.length - 1 ? '⏭️' : (loopEnabled ? '🔄' : '🏁')}
          </button>
        </div>

        {/* Drill Preview Section - Shows upcoming drills */}
        {isMobile && drills.length > 1 && (
          <div style={{
            marginTop: '12px',
            padding: '8px',
            background: '#f8f9fa',
            borderRadius: '8px',
            border: '1px solid #e9ecef'
          }}>
            <div style={{
              fontSize: '12px',
              fontWeight: 600,
              color: '#666',
              marginBottom: '6px',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center'
            }}>
              <span>Upcoming Drills ({drills.length - currentIndex - 1} remaining)</span>
              <span style={{ fontSize: '11px', color: '#999' }}>
                {currentIndex + 1}/{drills.length}
              </span>
            </div>
            <div style={{
              display: 'flex',
              gap: '8px',
              overflowX: 'auto',
              paddingBottom: '4px'
            }}>
              {drills.slice(currentIndex + 1, Math.min(currentIndex + 4, drills.length)).map((drill, idx) => (
                <div
                  key={drill.id}
                  style={{
                    minWidth: '80px',
                    padding: '6px',
                    background: 'white',
                    borderRadius: '6px',
                    border: '1px solid #dee2e6',
                    fontSize: '11px',
                    color: '#495057',
                    textAlign: 'center',
                    cursor: 'pointer',
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    gap: '4px'
                  }}
                  onClick={() => setCurrentIndex(currentIndex + idx + 1)}
                  title={`Jump to drill ${currentIndex + idx + 2}: ${drill.text_catalan || 'No text'}`}
                >
                  <div style={{
                    width: '24px',
                    height: '24px',
                    borderRadius: '50%',
                    background: '#667eea',
                    color: 'white',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '10px',
                    fontWeight: 'bold'
                  }}>
                    {currentIndex + idx + 2}
                  </div>
                  <div style={{
                    whiteSpace: 'nowrap',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    maxWidth: '70px'
                  }}>
                    {drill.text_catalan ? (drill.text_catalan.length > 10 ? drill.text_catalan.substring(0, 10) + '...' : drill.text_catalan) : '---'}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Video Player Modal */}
      {showVideo && currentDrill.video_url && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.9)',
            zIndex: 2000,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center'
          }}
          onClick={() => setShowVideo(false)}
        >
          <div
            style={{
              width: '100%',
              maxWidth: '800px',
              maxHeight: '90vh',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center'
            }}
            onClick={(e) => e.stopPropagation()}
          >
            {/* Close button */}
            <button
              onClick={() => setShowVideo(false)}
              style={{
                position: 'absolute',
                top: '20px',
                right: '20px',
                background: 'rgba(255, 255, 255, 0.2)',
                border: 'none',
                color: 'white',
                fontSize: '24px',
                width: '40px',
                height: '40px',
                borderRadius: '50%',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                zIndex: 2001
              }}
            >
              ✕
            </button>

            {/* Video player */}
            <div style={{ width: '100%', aspectRatio: '16/9', position: 'relative' }}>
              {currentDrill.video_url.includes('youtube.com') || currentDrill.video_url.includes('youtu.be') ? (
                // YouTube embed
                <iframe
                  src={currentDrill.video_url.replace('watch?v=', 'embed/').replace('youtu.be/', 'youtube.com/embed/')}
                  style={{
                    width: '100%',
                    height: '100%',
                    border: 'none',
                    borderRadius: '8px'
                  }}
                  allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                  allowFullScreen
                  title="YouTube video player"
                />
              ) : (
                // Regular video player for non-YouTube URLs
                <video
                  src={getMediaUrl(currentDrill.video_url)}
                  controls
                  autoPlay
                  style={{
                    width: '100%',
                    height: '100%',
                    objectFit: 'contain',
                    borderRadius: '8px'
                  }}
                />
              )}
            </div>

            {/* Video caption */}
            <div style={{
              marginTop: '16px',
              padding: '12px',
              backgroundColor: 'rgba(255, 255, 255, 0.1)',
              borderRadius: '8px',
              maxWidth: '600px',
              textAlign: 'center'
            }}>
              <div style={{ color: 'white', fontSize: '16px', fontWeight: 'bold', marginBottom: '4px' }}>
                {currentDrill.text_tachelhit || currentDrill.text_catalan || 'Video'}
              </div>
              {currentDrill.text_catalan && (
                <div style={{ color: 'rgba(255, 255, 255, 0.8)', fontSize: '14px' }}>
                  {currentDrill.text_catalan}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

const cleanButtonStyle: React.CSSProperties = {
  background: 'none', border: 'none', color: 'white', fontSize: '24px', cursor: 'pointer', padding: 0
};

const pillButtonStyle: React.CSSProperties = {
  padding: '5px 10px', border: 'none', borderRadius: '15px', fontSize: '10px', fontWeight: 800, cursor: 'pointer'
};

const iconButtonStyle: React.CSSProperties = {
  background: 'none', border: 'none', cursor: 'pointer', padding: '4px', display: 'flex', alignItems: 'center', justifyContent: 'center'
};
