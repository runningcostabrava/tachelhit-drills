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
    // Cleanup previous audio
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
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
        // Step 1: Speech synthesis for Catalan text (if available)
        if (currentDrill.text_catalan && 'speechSynthesis' in window) {
          const utterance = new SpeechSynthesisUtterance(currentDrill.text_catalan);
          utterance.lang = 'ca-ES'; // Catalan
          utterance.rate = 1.2; // Slightly faster
          utterance.volume = 0.8;
          
          await new Promise<void>((resolve) => {
            utterance.onend = () => resolve();
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

        // Update play count
        setPlayCount(prev => {
          const newCount = prev + 1;
          if (newCount >= 2) {
            // Move to next drill after 2 plays
            setTimeout(() => {
              if (currentIndex < drills.length - 1) {
                setCurrentIndex(currentIndex + 1);
              } else {
                onExit();
              }
            }, 1000);
          } else {
            // Play again after a short delay (without speech synthesis)
            setTimeout(() => {
              const audio2 = new Audio(getMediaUrl(currentDrill.audio_url));
              audioRef.current = audio2;
              setIsPlaying(true);
              audio2.play();
              audio2.onended = () => {
                setIsPlaying(false);
                setPlayCount(prev => prev + 1);
              };
              audio2.onerror = () => {
                setIsPlaying(false);
                setPlayCount(prev => prev + 1);
              };
            }, 500);
          }
          return newCount;
        });
      };

      playSequence();
    }
  }, [currentDrill, playCount, currentIndex, drills.length, onExit]);

  const handleNext = () => {
    if (currentIndex < drills.length - 1) {
      setCurrentIndex(currentIndex + 1);
    } else {
      onExit();
    }
  };

  const handlePrev = () => {
    if (currentIndex > 0) {
      setCurrentIndex(currentIndex - 1);
    }
  };

  const handleReplay = () => {
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
        padding: '20px'
      }}>
        <div style={{
          background: 'white',
          padding: '30px',
          borderRadius: '16px',
          maxWidth: '600px',
          width: '100%',
          boxShadow: '0 10px 40px rgba(0,0,0,0.2)',
          textAlign: 'center'
        }}>
          {/* Image */}
          {currentDrill.image_url && (
            <div style={{ marginBottom: '30px' }}>
              <img
                src={getMediaUrl(currentDrill.image_url)}
                alt="Drill visual"
                style={{
                  maxWidth: '100%',
                  maxHeight: '200px',
                  borderRadius: '12px',
                  objectFit: 'contain'
                }}
              />
            </div>
          )}

          {/* Catalan */}
          <div style={{ marginBottom: '20px' }}>
            <div style={{ fontSize: '14px', color: '#667eea', fontWeight: 600, marginBottom: '8px' }}>
              Català
            </div>
            <div style={{ fontSize: '24px', fontWeight: 700, color: '#333' }}>
              {currentDrill.text_catalan || 'No text'}
            </div>
          </div>

          {/* Tachelhit */}
          <div style={{ marginBottom: '20px' }}>
            <div style={{ fontSize: '14px', color: '#4CAF50', fontWeight: 600, marginBottom: '8px' }}>
              Tachelhit
            </div>
            <div style={{ fontSize: '22px', fontWeight: 600, color: '#2e7d32' }}>
              {currentDrill.text_tachelhit || 'No text'}
            </div>
          </div>

          {/* Arabic */}
          {currentDrill.text_arabic && (
            <div style={{ marginBottom: '30px' }}>
              <div style={{ fontSize: '14px', color: '#9C27B0', fontWeight: 600, marginBottom: '8px' }}>
                العربية
              </div>
              <div style={{ fontSize: '22px', fontWeight: 600, color: '#7b1fa2', direction: 'rtl' }}>
                {currentDrill.text_arabic}
              </div>
            </div>
          )}

          {/* Audio Status */}
          <div style={{
            padding: '16px',
            background: isPlaying ? '#e8f5e9' : '#fff3cd',
            border: `2px solid ${isPlaying ? '#4CAF50' : '#FFC107'}`,
            borderRadius: '12px',
            marginBottom: '30px'
          }}>
            <div style={{ fontSize: '16px', fontWeight: 600, color: isPlaying ? '#2e7d32' : '#856404' }}>
              {isPlaying ? '🔊 Playing audio...' : '⏸ Ready'}
            </div>
            <div style={{ fontSize: '14px', color: '#666', marginTop: '8px' }}>
              {currentDrill.audio_url ? 
                (playCount === 0 ? 'First: Catalan speech + audio' : `Second: audio only (${playCount}/2)`) 
                : 'No audio available'}
            </div>
          </div>

          {/* Controls */}
          <div style={{ display: 'flex', gap: '12px', justifyContent: 'center' }}>
            <button
              onClick={handlePrev}
              disabled={currentIndex === 0}
              style={{
                padding: '12px 24px',
                fontSize: '16px',
                background: currentIndex === 0 ? '#ccc' : '#2196F3',
                color: 'white',
                border: 'none',
                borderRadius: '8px',
                cursor: currentIndex === 0 ? 'not-allowed' : 'pointer',
                fontWeight: 600,
              }}
            >
              ← Previous
            </button>
            <button
              onClick={handleReplay}
              style={{
                padding: '12px 24px',
                fontSize: '16px',
                background: '#FFC107',
                color: '#333',
                border: 'none',
                borderRadius: '8px',
                cursor: 'pointer',
                fontWeight: 600,
              }}
            >
              🔄 Replay
            </button>
            <button
              onClick={handleNext}
              style={{
                padding: '12px 24px',
                fontSize: '16px',
                background: '#4CAF50',
                color: 'white',
                border: 'none',
                borderRadius: '8px',
                cursor: 'pointer',
                fontWeight: 600,
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
