import { useState, useEffect, useRef } from 'react';
import { getMediaUrl } from '../config';

interface Drill {
  id: number;
  text_catalan?: string;
  text_tachelhit?: string;
  text_arabic?: string;
  audio_url?: string;
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
  const [playCount, setPlayCount] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const speechSynthRef = useRef<SpeechSynthesisUtterance | null>(null);

  const currentDrill = drills[currentIndex];

  useEffect(() => {
    // Reset play count when drill changes
    setPlayCount(0);
    setIsPlaying(false);
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
    // Cancel any ongoing speech synthesis
    if (speechSynthRef.current) {
      speechSynthesis.cancel();
      speechSynthRef.current = null;
    }
  }, [currentIndex]);

  useEffect(() => {
    // Cleanup previous audio and speech
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
    if (speechSynthRef.current) {
      speechSynthesis.cancel();
      speechSynthRef.current = null;
    }

    // If no audio URL, move on after a delay
    if (!currentDrill?.audio_url) {
      const timer = setTimeout(() => {
        if (currentIndex < drills.length - 1) {
          setCurrentIndex(currentIndex + 1);
        } else {
          onExit();
        }
      }, 2000);
      return () => clearTimeout(timer);
    }

    // If we have audio and haven't played twice yet
    if (currentDrill?.audio_url && playCount < 2) {
      const playSequence = async () => {
        // Step 1: Speech synthesis for Catalan text (only on first play)
        if (playCount === 0 && currentDrill.text_catalan && 'speechSynthesis' in window) {
          const utterance = new SpeechSynthesisUtterance(currentDrill.text_catalan);
          utterance.lang = 'ca-ES'; // Catalan
          utterance.rate = 1.2; // Slightly faster
          utterance.volume = 0.8;
          speechSynthRef.current = utterance;
          
          await new Promise<void>((resolve) => {
            utterance.onend = () => resolve();
            utterance.onerror = () => resolve();
            speechSynthesis.speak(utterance);
          });
          // Small pause between speech and audio
          await new Promise(resolve => setTimeout(resolve, 300));
        }

        // Step 2: Play recorded audio
        const audio = new Audio(getMediaUrl(currentDrill.audio_url));
        audioRef.current = audio;
        setIsPlaying(true);
        
        await new Promise<void>((resolve) => {
          audio.onended = () => {
            setIsPlaying(false);
            resolve();
          };
          audio.onerror = () => {
            setIsPlaying(false);
            resolve();
          };
          audio.play();
        });

        // Update play count after audio finishes
        const newCount = playCount + 1;
        setPlayCount(newCount);
        
        // If we've played twice, move to next drill after a delay
        if (newCount >= 2) {
          setTimeout(() => {
            if (currentIndex < drills.length - 1) {
              setCurrentIndex(currentIndex + 1);
            } else {
              onExit();
            }
          }, 1000);
        } else {
          // If we've only played once, play again without speech synthesis
          // We'll trigger another play by using a timeout to allow state to update
          setTimeout(() => {
            // This will cause the effect to run again because playCount changed
          }, 100);
        }
      };

      playSequence();
    }
  }, [currentDrill, playCount, currentIndex, drills.length, onExit]);

  const handleNext = () => {
    // Clean up current audio
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
    if (speechSynthRef.current) {
      speechSynthesis.cancel();
      speechSynthRef.current = null;
    }
    
    if (currentIndex < drills.length - 1) {
      setCurrentIndex(currentIndex + 1);
    } else {
      onExit();
    }
  };

  const handlePrev = () => {
    // Clean up current audio
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
    if (speechSynthRef.current) {
      speechSynthesis.cancel();
      speechSynthRef.current = null;
    }
    
    if (currentIndex > 0) {
      setCurrentIndex(currentIndex - 1);
    }
  };

  const handleReplay = () => {
    // Clean up current audio
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
    if (speechSynthRef.current) {
      speechSynthesis.cancel();
      speechSynthRef.current = null;
    }
    setPlayCount(0);
  };

  return (
    <div style={{
      height: '100vh',
      display: 'flex',
      flexDirection: 'column',
      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
    }}>
      {/* Header */}
      <div style={{
        padding: '20px',
        background: 'rgba(255,255,255,0.1)',
        backdropFilter: 'blur(10px)',
        color: 'white',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center'
      }}>
        <div>
          <h2 style={{ margin: 0, fontSize: '20px' }}>Drill Player</h2>
          <p style={{ margin: '5px 0 0 0', fontSize: '14px', opacity: 0.9 }}>
            {currentIndex + 1} of {drills.length} • Play {playCount}/2
          </p>
        </div>
        <button
          onClick={onExit}
          style={{
            padding: '8px 16px',
            background: 'rgba(255,255,255,0.2)',
            color: 'white',
            border: '1px solid white',
            borderRadius: '6px',
            cursor: 'pointer',
            fontSize: '14px'
          }}
        >
          Exit
        </button>
      </div>

      {/* Content */}
      <div style={{
        flex: 1,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: window.innerWidth < 768 ? '10px' : '20px'
      }}>
        <div style={{
          background: 'white',
          padding: window.innerWidth < 768 ? '20px' : '30px',
          borderRadius: '16px',
          maxWidth: '600px',
          width: '100%',
          boxShadow: '0 10px 40px rgba(0,0,0,0.2)',
          textAlign: 'center'
        }}>
          {/* Image */}
          {currentDrill.image_url && (
            <div style={{ marginBottom: window.innerWidth < 768 ? '20px' : '30px' }}>
              <img
                src={getMediaUrl(currentDrill.image_url)}
                alt="Drill visual"
                style={{
                  maxWidth: '100%',
                  maxHeight: window.innerWidth < 768 ? '150px' : '200px',
                  borderRadius: '12px',
                  objectFit: 'contain'
                }}
              />
            </div>
          )}

          {/* Catalan */}
          <div style={{ marginBottom: window.innerWidth < 768 ? '16px' : '20px' }}>
            <div style={{ 
              fontSize: window.innerWidth < 768 ? '12px' : '14px', 
              color: '#667eea', 
              fontWeight: 600, 
              marginBottom: '6px' 
            }}>
              Català
            </div>
            <div style={{ 
              fontSize: window.innerWidth < 768 ? '20px' : '24px', 
              fontWeight: 700, 
              color: '#333',
              lineHeight: 1.3
            }}>
              {currentDrill.text_catalan || 'No text'}
            </div>
          </div>

          {/* Tachelhit */}
          <div style={{ marginBottom: window.innerWidth < 768 ? '16px' : '20px' }}>
            <div style={{ 
              fontSize: window.innerWidth < 768 ? '12px' : '14px', 
              color: '#4CAF50', 
              fontWeight: 600, 
              marginBottom: '6px' 
            }}>
              Tachelhit
            </div>
            <div style={{ 
              fontSize: window.innerWidth < 768 ? '18px' : '22px', 
              fontWeight: 600, 
              color: '#2e7d32',
              lineHeight: 1.3
            }}>
              {currentDrill.text_tachelhit || 'No text'}
            </div>
          </div>

          {/* Arabic */}
          {currentDrill.text_arabic && (
            <div style={{ marginBottom: window.innerWidth < 768 ? '20px' : '30px' }}>
              <div style={{ 
                fontSize: window.innerWidth < 768 ? '11px' : '14px', 
                color: '#9C27B0', 
                fontWeight: 600, 
                marginBottom: '6px' 
              }}>
                العربية
              </div>
              <div style={{ 
                fontSize: window.innerWidth < 768 ? '16px' : '22px', 
                fontWeight: 600, 
                color: '#7b1fa2', 
                direction: 'rtl',
                lineHeight: 1.4
              }}>
                {currentDrill.text_arabic}
              </div>
            </div>
          )}

          {/* Audio Status */}
          <div style={{
            padding: window.innerWidth < 768 ? '12px' : '16px',
            background: isPlaying ? '#e8f5e9' : '#fff3cd',
            border: `2px solid ${isPlaying ? '#4CAF50' : '#FFC107'}`,
            borderRadius: '12px',
            marginBottom: window.innerWidth < 768 ? '20px' : '30px'
          }}>
            <div style={{ 
              fontSize: window.innerWidth < 768 ? '14px' : '16px', 
              fontWeight: 600, 
              color: isPlaying ? '#2e7d32' : '#856404',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '8px'
            }}>
              <span>{isPlaying ? '🔊' : '⏸'}</span>
              <span>{isPlaying ? 'Playing audio...' : 'Ready'}</span>
            </div>
            <div style={{ 
              fontSize: window.innerWidth < 768 ? '12px' : '14px', 
              color: '#666', 
              marginTop: '6px' 
            }}>
              {currentDrill.audio_url ? 
                (playCount === 0 ? 'First: Catalan speech + audio' : `Second: audio only (${playCount}/2)`) 
                : 'No audio available'}
            </div>
            {/* Manual speech synthesis button for mobile */}
            {playCount === 0 && currentDrill.text_catalan && window.innerWidth < 768 && (
              <button
                onClick={() => {
                  if ('speechSynthesis' in window) {
                    const utterance = new SpeechSynthesisUtterance(currentDrill.text_catalan);
                    utterance.lang = 'ca-ES';
                    utterance.rate = 1.2;
                    utterance.volume = 0.8;
                    speechSynthesis.speak(utterance);
                  } else {
                    alert('Speech synthesis not supported on this device');
                  }
                }}
                style={{
                  marginTop: '10px',
                  padding: '6px 12px',
                  fontSize: '12px',
                  background: '#667eea',
                  color: 'white',
                  border: 'none',
                  borderRadius: '6px',
                  cursor: 'pointer'
                }}
              >
                🔊 Speak Catalan Text
              </button>
            )}
          </div>

          {/* Controls */}
          <div style={{ 
            display: 'flex', 
            gap: window.innerWidth < 768 ? '8px' : '12px', 
            justifyContent: 'center',
            flexWrap: window.innerWidth < 768 ? 'wrap' : 'nowrap'
          }}>
            <button
              onClick={handlePrev}
              disabled={currentIndex === 0}
              style={{
                padding: window.innerWidth < 768 ? '10px 16px' : '12px 24px',
                fontSize: window.innerWidth < 768 ? '14px' : '16px',
                background: currentIndex === 0 ? '#ccc' : '#2196F3',
                color: 'white',
                border: 'none',
                borderRadius: '8px',
                cursor: currentIndex === 0 ? 'not-allowed' : 'pointer',
                fontWeight: 600,
                flex: window.innerWidth < 768 ? '1 1 calc(33% - 6px)' : 'none',
                minWidth: window.innerWidth < 768 ? 'calc(33% - 6px)' : 'auto'
              }}
            >
              ← Prev
            </button>
            <button
              onClick={handleReplay}
              style={{
                padding: window.innerWidth < 768 ? '10px 16px' : '12px 24px',
                fontSize: window.innerWidth < 768 ? '14px' : '16px',
                background: '#FFC107',
                color: '#333',
                border: 'none',
                borderRadius: '8px',
                cursor: 'pointer',
                fontWeight: 600,
                flex: window.innerWidth < 768 ? '1 1 calc(34% - 6px)' : 'none',
                minWidth: window.innerWidth < 768 ? 'calc(34% - 6px)' : 'auto'
              }}
            >
              🔄 Replay
            </button>
            <button
              onClick={handleNext}
              style={{
                padding: window.innerWidth < 768 ? '10px 16px' : '12px 24px',
                fontSize: window.innerWidth < 768 ? '14px' : '16px',
                background: '#4CAF50',
                color: 'white',
                border: 'none',
                borderRadius: '8px',
                cursor: 'pointer',
                fontWeight: 600,
                flex: window.innerWidth < 768 ? '1 1 calc(33% - 6px)' : 'none',
                minWidth: window.innerWidth < 768 ? 'calc(33% - 6px)' : 'auto'
              }}
            >
              {currentIndex < drills.length - 1 ? 'Next →' : 'Finish'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
