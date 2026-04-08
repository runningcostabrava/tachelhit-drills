import { useState, useEffect, useRef } from 'react';
import { getMediaUrl } from '../config';
import { getMediaWithOfflineFallback } from '../utils/offlineCache';
import { getYouTubeVideoId } from '../utils/youtubeUtils';

declare global {
  interface Window {
    onYouTubeIframeAPIReady?: () => void;
    YT: any;
  }
}

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
  video_start_time?: number;
  video_end_time?: number;
}

interface DrillPlayerProps {
  drills: Drill[];
  onExit: () => void;
}

interface VideoControls {
  playbackRate: number;
  isLooping: boolean;
  currentSubtitleIndex: number;
  subtitleSections: Array<{start: number, end: number}>;
}

export default function DrillPlayer({ drills, onExit }: DrillPlayerProps) {
  // Style definitions (moved to top to avoid "used before declaration" errors)
  const cleanButtonStyle = {
    background: 'none',
    border: 'none',
    color: 'white',
    fontSize: '20px',
    cursor: 'pointer',
    padding: '4px 8px',
    borderRadius: '4px'
  };

  const pillButtonStyle = {
    padding: '6px 12px',
    border: 'none',
    borderRadius: '20px',
    fontSize: '12px',
    fontWeight: 600,
    cursor: 'pointer',
    transition: 'all 0.2s'
  };

  const navButtonStyle = {
    padding: '10px 20px',
    background: '#f0f0f0',
    border: '1px solid #ddd',
    borderRadius: '6px',
    fontSize: '14px',
    fontWeight: 600,
    cursor: 'pointer',
    transition: 'all 0.2s'
  };

  const [currentIndex, setCurrentIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [autoPlayEnabled, setAutoPlayEnabled] = useState(false);
  const [loopEnabled, setLoopEnabled] = useState(false);
  const [audioProgress, setAudioProgress] = useState(0);
  const [audioDuration, setAudioDuration] = useState(0);
  const [imageUrl, setImageUrl] = useState<string>('');
  const [showVideo, setShowVideo] = useState(false);
  const [showVideoLibrary, setShowVideoLibrary] = useState(false);
  const [videoControls, setVideoControls] = useState<VideoControls>({
    playbackRate: 1.0,
    isLooping: true,
    currentSubtitleIndex: 0,
    subtitleSections: []
  });
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const ttsAudioRef = useRef<HTMLAudioElement | null>(null);
  const speechSynthRef = useRef<SpeechSynthesisUtterance | null>(null);
  const progressIntervalRef = useRef<number | null>(null);
  const videoIframeRef = useRef<HTMLIFrameElement | null>(null);
  const playerRef = useRef<any>(null); // YouTube Player instance
  const [playerReady, setPlayerReady] = useState(false);

  const currentDrill = drills[currentIndex];
  // Note: isMobile is declared for potential future mobile-specific logic
  // const isMobile = window.innerWidth < 768;

  // Initialize subtitle sections when drill changes
  useEffect(() => {
    if (currentDrill?.video_start_time !== undefined && currentDrill?.video_end_time !== undefined) {
      setVideoControls(prev => ({
        ...prev,
        subtitleSections: [{
          start: currentDrill.video_start_time || 0,
          end: currentDrill.video_end_time || 0
        }],
        currentSubtitleIndex: 0
      }));
    }
  }, [currentDrill]);

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
    
    // Reset video controls
    setVideoControls(prev => ({
      ...prev,
      playbackRate: 1.0,
      isLooping: true,
      currentSubtitleIndex: 0,
      subtitleSections: []
    }));
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

  // Load YouTube IFrame API script
  useEffect(() => {
    if (!window.YT) {
      const tag = document.createElement('script');
      tag.src = "https://www.youtube.com/iframe_api";
      const firstScriptTag = document.getElementsByTagName('script')[0];
      firstScriptTag.parentNode?.insertBefore(tag, firstScriptTag);

      window.onYouTubeIframeAPIReady = () => {
        console.log("YouTube IFrame API is Ready");
        setPlayerReady(true);
      };
    } else {
      setPlayerReady(true);
    }
  }, []);

  // Initialize YouTube Player
  useEffect(() => {
    if (!playerReady || !currentDrill?.video_url || !showVideo) return;

    const videoId = getYouTubeVideoId(currentDrill.video_url);
    if (!videoId) {
      console.error("Invalid YouTube URL or video ID not found:", currentDrill.video_url);
      return;
    }

    if (playerRef.current) {
      playerRef.current.destroy();
    }

    playerRef.current = new window.YT.Player('youtube-player', {
      videoId: videoId,
      playerVars: {
        autoplay: 1,
        controls: 1,
        modestbranding: 1,
        start: Math.floor(currentDrill.video_start_time || 0),
        end: Math.ceil(currentDrill.video_end_time || 0) || undefined,
        rel: 0,
      },
      events: {
        'onReady': (event: any) => {
          console.log('✅ YT Player Ready (DrillPlayer)');
          if (videoControls.playbackRate !== 1.0) {
            event.target.setPlaybackRate(videoControls.playbackRate);
          }
          // 1. Force explicit seek to the exact start time on load
          const startTime = currentDrill.video_start_time || 0;
          event.target.seekTo(startTime, true);
          event.target.playVideo();
        },
        'onStateChange': (event: any) => {
          const player = event.target;
          const startTime = currentDrill.video_start_time || 0;
          const endTime = currentDrill.video_end_time;

          if (event.data === window.YT.PlayerState.PAUSED && videoControls.isLooping) {
            // 2. Loop Logic: Check if it paused because it reached the 'end' limit
            const currentTime = player.getCurrentTime();
            if (endTime && currentTime >= endTime - 0.5) {
              console.log('🔄 Reached end of segment, looping back to:', startTime);
              player.seekTo(startTime, true);
              player.playVideo();
            }
          }

          if (event.data === window.YT.PlayerState.ENDED && videoControls.isLooping) {
            // 3. Loop Logic: If the whole video ended, jump back to start
            console.log('🔄 Video ended, looping back to:', startTime);
            player.seekTo(startTime, true);
            player.playVideo();
          }
        },
        'onError': (error: any) => {
          console.error('❌ YouTube player error:', error);
        }
      },
    });
>>>>+++ REPLACE


    return () => {
      if (playerRef.current) {
        playerRef.current.destroy();
        playerRef.current = null;
      }
    };
  }, [playerReady, currentDrill?.id, showVideo]);

  // Handle precise video looping without destroying player
>>>>+++ REPLACE


  // Handle playback rate separately
  useEffect(() => {
    if (playerRef.current && typeof playerRef.current.setPlaybackRate === 'function') {
      playerRef.current.setPlaybackRate(videoControls.playbackRate);
    }
  }, [videoControls.playbackRate]);

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

  // Helper function to format time in seconds to MM:SS format
  const formatTime = (seconds: number) => {
    if (!seconds) return '0:00';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  // Video control functions
  const handlePlaybackRateChange = (rate: number) => {
    setVideoControls(prev => ({ ...prev, playbackRate: rate }));
    if (playerRef.current) {
      playerRef.current.setPlaybackRate(rate);
    }
  };

  const handleToggleLoop = () => {
    setVideoControls(prev => ({ ...prev, isLooping: !prev.isLooping }));
    // Looping logic is handled in the onStateChange event and a time interval check
  };

  const seekToSubtitle = (index: number) => {
    if (index >= 0 && index < videoControls.subtitleSections.length) {
      const targetSection = videoControls.subtitleSections[index];
      setVideoControls(prev => ({ ...prev, currentSubtitleIndex: index }));
      if (playerRef.current) {
        playerRef.current.seekTo(targetSection.start, true);
        playerRef.current.playVideo();
      }
    }
  };

  const handlePreviousSubtitle = () => {
    if (videoControls.currentSubtitleIndex > 0) {
      seekToSubtitle(videoControls.currentSubtitleIndex - 1);
    }
  };

  const handleNextSubtitle = () => {
    if (videoControls.currentSubtitleIndex < videoControls.subtitleSections.length - 1) {
      seekToSubtitle(videoControls.currentSubtitleIndex + 1);
    }
  };

  const handleJumpToSubtitle = (index: number) => {
    seekToSubtitle(index);
  };


  // Get video drills (drills with video URLs)
  const videoDrills = drills.filter(drill => drill.video_url);

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
          
          {/* Video Library Button */}
          {videoDrills.length > 0 && (
            <button
              onClick={() => setShowVideoLibrary(true)}
              style={{ ...pillButtonStyle, background: 'rgba(255,255,255,0.2)', color: 'white' }}
            >
              📹 LIBRARY
            </button>
          )}
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
          {/* Tachelhit Text */}
          <div style={{
            padding: '24px 16px 16px',
            textAlign: 'center',
            fontSize: '28px',
            fontWeight: 700,
            color: '#333',
            lineHeight: 1.4,
            minHeight: '120px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}>
            {currentDrill?.text_tachelhit || 'No Tachelhit text'}
          </div>

          {/* Image */}
          {imageUrl && (
            <div style={{ padding: '0 16px 16px', display: 'flex', justifyContent: 'center' }}>
              <img
                src={imageUrl}
                alt="Drill"
                style={{
                  maxWidth: '100%',
                  maxHeight: '300px',
                  borderRadius: '12px',
                  boxShadow: '0 4px 12px rgba(0,0,0,0.1)'
                }}
                onError={(e) => {
                  (e.target as HTMLImageElement).style.display = 'none';
                }}
              />
            </div>
          )}

          {/* Translations */}
          <div style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {/* Arabic */}
            {currentDrill?.text_arabic && (
              <div style={{
                padding: '12px',
                background: '#f8f9fa',
                borderRadius: '8px',
                borderLeft: '4px solid #4CAF50',
                fontSize: '18px',
                color: '#333',
                textAlign: 'right',
                direction: 'rtl'
              }}>
                {currentDrill.text_arabic}
              </div>
            )}

            {/* Catalan */}
            {currentDrill?.text_catalan && (
              <div style={{
                padding: '12px',
                background: '#f0f7ff',
                borderRadius: '8px',
                borderLeft: '4px solid #2196F3',
                fontSize: '16px',
                color: '#333',
                fontStyle: 'italic'
              }}>
                {currentDrill.text_catalan}
              </div>
            )}
          </div>

          {/* Video Button (if video exists) */}
          {currentDrill?.video_url && (
            <div style={{ padding: '16px', display: 'flex', justifyContent: 'center' }}>
              <button
                onClick={() => setShowVideo(true)}
                style={{
                  padding: '12px 24px',
                  background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                  color: 'white',
                  border: 'none',
                  borderRadius: '8px',
                  fontSize: '16px',
                  fontWeight: 600,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  boxShadow: '0 4px 12px rgba(102, 126, 234, 0.3)'
                }}
              >
                <span>▶️</span>
                Watch Video with Subtitles
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Navigation Footer */}
      <div style={{
        padding: '16px',
        background: '#f8f9fa',
        borderTop: '1px solid #e0e0e0',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center'
      }}>
        <button
          onClick={handlePrev}
          disabled={currentIndex === 0}
          style={{
            ...navButtonStyle,
            opacity: currentIndex === 0 ? 0.5 : 1,
            cursor: currentIndex === 0 ? 'not-allowed' : 'pointer'
          }}
        >
          ← Previous
        </button>

        {/* Audio Progress Bar */}
        <div style={{ flex: 1, margin: '0 16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '12px', color: '#666', minWidth: '40px' }}>
            {formatTime(audioProgress)}
          </span>
          <div
            style={{
              flex: 1,
              height: '6px',
              background: '#e0e0e0',
              borderRadius: '3px',
              overflow: 'hidden',
              cursor: 'pointer'
            }}
            onClick={(e) => {
              const rect = e.currentTarget.getBoundingClientRect();
              const percent = (e.clientX - rect.left) / rect.width;
              const time = percent * audioDuration;
              handleSeek(time);
            }}
          >
            <div
              style={{
                width: `${audioDuration ? (audioProgress / audioDuration) * 100 : 0}%`,
                height: '100%',
                background: '#4CAF50',
                transition: 'width 0.1s'
              }}
            />
          </div>
          <span style={{ fontSize: '12px', color: '#666', minWidth: '40px' }}>
            {formatTime(audioDuration)}
          </span>
        </div>

        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            onClick={playCurrentAudio}
            disabled={isPlaying}
            style={{
              ...navButtonStyle,
              background: isPlaying ? '#4CAF50' : '#2196F3',
              color: 'white',
              minWidth: '100px'
            }}
          >
            {isPlaying ? 'Playing...' : 'Play Audio'}
          </button>

          <button
            onClick={goToNextDrill}
            style={navButtonStyle}
          >
            Next →
          </button>
        </div>
      </div>

      {/* Enhanced Video Modal */}
      {showVideo && currentDrill?.video_url && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0,0,0,0.9)',
          zIndex: 2000,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center'
        }}>
          <div style={{
            width: '90%',
            maxWidth: '1000px',
            background: '#1a1a1a',
            borderRadius: '12px',
            overflow: 'hidden',
            display: 'flex',
            flexDirection: 'column'
          }}>
            {/* Video Modal Header */}
            <div style={{
              padding: '16px',
              background: '#2a2a2a',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              borderBottom: '1px solid #444'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <button
                  onClick={() => setShowVideo(false)}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: 'white',
                    fontSize: '20px',
                    cursor: 'pointer',
                    padding: '4px 8px'
                  }}
                >
                  ✕
                </button>
                <span style={{ color: 'white', fontWeight: 600 }}>
                  Video Player - {currentDrill.text_tachelhit?.substring(0, 50)}...
                </span>
              </div>
              
              {/* Video Controls */}
              <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                {/* Playback Speed */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <span style={{ color: '#aaa', fontSize: '12px' }}>Speed:</span>
                  {[0.5, 0.75, 1.0, 1.25, 1.5].map(rate => (
                    <button
                      key={rate}
                      onClick={() => handlePlaybackRateChange(rate)}
                      style={{
                        padding: '4px 8px',
                        background: videoControls.playbackRate === rate ? '#667eea' : '#444',
                        color: 'white',
                        border: 'none',
                        borderRadius: '4px',
                        fontSize: '12px',
                        cursor: 'pointer'
                      }}
                    >
                      {rate}x
                    </button>
                  ))}
                </div>

                {/* Loop Toggle */}
                <button
                  onClick={handleToggleLoop}
                  style={{
                    padding: '6px 12px',
                    background: videoControls.isLooping ? '#FFD700' : '#444',
                    color: videoControls.isLooping ? '#333' : 'white',
                    border: 'none',
                    borderRadius: '4px',
                    fontSize: '12px',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px'
                  }}
                >
                  🔁 {videoControls.isLooping ? 'Looping ON' : 'Loop'}
                </button>
              </div>
            </div>

            {/* Video Player */}
            <div style={{ position: 'relative', paddingTop: '56.25%' /* 16:9 aspect ratio */ }}>
              <div
                id="youtube-player"
                style={{
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  width: '100%',
                  height: '100%',
                  border: 'none'
                }}
              />

              <iframe
                ref={videoIframeRef}
                src="" // Controlled by YouTube Player API
                style={{
                  display: 'none', // Hide the original iframe once YT player is loaded
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  width: '100%',
                  height: '100%',
                  border: 'none'
                }}
                title="YouTube video player"
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                allowFullScreen
              />
              
              {/* Subtitle Overlay */}
              <div style={{
                position: 'absolute',
                bottom: '60px',
                left: 0,
                right: 0,
                padding: '0 20px',
                display: 'flex',
                flexDirection: 'column',
                gap: '4px',
                pointerEvents: 'none'
              }}>
                {/* Arabic Subtitle */}
                {currentDrill?.text_arabic && (
                  <div style={{
                    background: 'rgba(0, 0, 0, 0.7)',
                    color: 'white',
                    padding: '12px 16px',
                    borderRadius: '8px',
                    fontSize: '20px',
                    textAlign: 'right',
                    direction: 'rtl',
                    lineHeight: 1.4
                  }}>
                    {currentDrill.text_arabic}
                  </div>
                )}
                
                {/* Tachelhit Subtitle */}
                {currentDrill?.text_tachelhit && (
                  <div style={{
                    background: 'rgba(76, 175, 80, 0.8)',
                    color: 'white',
                    padding: '10px 16px',
                    borderRadius: '8px',
                    fontSize: '18px',
                    fontWeight: 600,
                    lineHeight: 1.4
                  }}>
                    {currentDrill.text_tachelhit}
                  </div>
                )}
                
                {/* Catalan Subtitle */}
                {currentDrill?.text_catalan && (
                  <div style={{
                    background: 'rgba(33, 150, 243, 0.9)',
                    color: 'white',
                    padding: '8px 16px',
                    borderRadius: '8px',
                    fontSize: '16px',
                    fontStyle: 'italic',
                    opacity: 0.9,
                    lineHeight: 1.4
                  }}>
                    {currentDrill.text_catalan}
                  </div>
                )}
              </div>
            </div>

            {/* Subtitle Navigation Controls */}
            <div style={{
              padding: '16px',
              background: '#2a2a2a',
              borderTop: '1px solid #444',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <button
                  onClick={handlePreviousSubtitle}
                  disabled={videoControls.currentSubtitleIndex === 0}
                  style={{
                    padding: '8px 16px',
                    background: videoControls.currentSubtitleIndex === 0 ? '#555' : '#667eea',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: videoControls.currentSubtitleIndex === 0 ? 'not-allowed' : 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px'
                  }}
                >
                  ← Previous Subtitle
                </button>

                <div style={{ color: '#aaa', fontSize: '14px' }}>
                  Subtitle {videoControls.currentSubtitleIndex + 1} of {videoControls.subtitleSections.length}
                </div>

                <button
                  onClick={handleNextSubtitle}
                  disabled={videoControls.currentSubtitleIndex >= videoControls.subtitleSections.length - 1}
                  style={{
                    padding: '8px 16px',
                    background: videoControls.currentSubtitleIndex >= videoControls.subtitleSections.length - 1 ? '#555' : '#667eea',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: videoControls.currentSubtitleIndex >= videoControls.subtitleSections.length - 1 ? 'not-allowed' : 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px'
                  }}
                >
                  Next Subtitle →
                </button>
              </div>

              {/* Subtitle Timeline */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ color: '#aaa', fontSize: '12px' }}>Timeline:</span>
                <div style={{ display: 'flex', gap: '4px' }}>
                  {videoControls.subtitleSections.map((section, index) => (
                    <button
                      key={index}
                      onClick={() => handleJumpToSubtitle(index)}
                      style={{
                        padding: '4px 8px',
                        background: videoControls.currentSubtitleIndex === index ? '#FFD700' : '#444',
                        color: videoControls.currentSubtitleIndex === index ? '#333' : 'white',
                        border: 'none',
                        borderRadius: '4px',
                        fontSize: '12px',
                        cursor: 'pointer',
                        minWidth: '60px'
                      }}
                    >
                      {formatTime(section.start)}-{formatTime(section.end)}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Video Library Modal */}
      {showVideoLibrary && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0,0,0,0.9)',
          zIndex: 2000,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center'
        }}>
          <div style={{
            width: '90%',
            maxWidth: '1200px',
            maxHeight: '90vh',
            background: '#1a1a1a',
            borderRadius: '12px',
            overflow: 'hidden',
            display: 'flex',
            flexDirection: 'column'
          }}>
            {/* Library Header */}
            <div style={{
              padding: '16px 24px',
              background: '#2a2a2a',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              borderBottom: '1px solid #444'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <button
                  onClick={() => setShowVideoLibrary(false)}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: 'white',
                    fontSize: '20px',
                    cursor: 'pointer',
                    padding: '4px 8px'
                  }}
                >
                  ✕
                </button>
                <span style={{ color: 'white', fontWeight: 600, fontSize: '18px' }}>
                  📹 Video Library ({videoDrills.length} videos)
                </span>
              </div>
              <div style={{ color: '#aaa', fontSize: '14px' }}>
                Click any video to play with subtitles
              </div>
            </div>

            {/* Video Grid */}
            <div style={{
              flex: 1,
              overflowY: 'auto',
              padding: '24px',
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))',
              gap: '20px'
            }}>
              {videoDrills.map((drill) => (
                <div
                  key={drill.id}
                  onClick={() => {
                    const drillIndex = drills.findIndex(d => d.id === drill.id);
                    if (drillIndex !== -1) {
                      setCurrentIndex(drillIndex);
                      setShowVideoLibrary(false);
                      setShowVideo(true);
                    }
                  }}
                  style={{
                    background: '#2a2a2a',
                    borderRadius: '8px',
                    overflow: 'hidden',
                    cursor: 'pointer',
                    transition: 'transform 0.2s, background 0.2s, border-color 0.2s',
                    border: '1px solid #444'
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.transform = 'translateY(-4px)';
                    e.currentTarget.style.background = '#333';
                    e.currentTarget.style.borderColor = '#667eea';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.transform = '';
                    e.currentTarget.style.background = '#2a2a2a';
                    e.currentTarget.style.borderColor = '#444';
                  }}
                >
                  {/* Video Thumbnail */}
                  <div style={{
                    position: 'relative',
                    paddingTop: '56.25%' /* 16:9 aspect ratio */,
                    background: '#1a1a1a'
                  }}>
                    <div style={{
                      position: 'absolute',
                      top: 0,
                      left: 0,
                      right: 0,
                      bottom: 0,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
                    }}>
                      <span style={{ color: 'white', fontSize: '24px' }}>▶️</span>
                    </div>
                    <div style={{
                      position: 'absolute',
                      bottom: '8px',
                      right: '8px',
                      background: 'rgba(0,0,0,0.7)',
                      color: 'white',
                      padding: '4px 8px',
                      borderRadius: '4px',
                      fontSize: '12px'
                    }}>
                      {drill.video_start_time !== undefined && drill.video_end_time !== undefined 
                        ? `${formatTime(drill.video_start_time)}-${formatTime(drill.video_end_time)}`
                        : 'Full video'
                      }
                    </div>
                  </div>

                  {/* Video Info */}
                  <div style={{ padding: '16px' }}>
                    <div style={{
                      color: 'white',
                      fontSize: '16px',
                      fontWeight: 600,
                      marginBottom: '8px',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      display: '-webkit-box',
                      WebkitLineClamp: 2,
                      WebkitBoxOrient: 'vertical',
                      lineHeight: 1.4,
                      height: '44px'
                    }}>
                      {drill.text_tachelhit || 'No title'}
                    </div>
                    
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                      {drill.text_arabic && (
                        <div style={{
                          color: '#aaa',
                          fontSize: '14px',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap',
                          textAlign: 'right',
                          direction: 'rtl'
                        }}>
                          {drill.text_arabic}
                        </div>
                      )}
                      
                      {drill.text_catalan && (
                        <div style={{
                          color: '#aaa',
                          fontSize: '12px',
                          fontStyle: 'italic',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap'
                        }}>
                          {drill.text_catalan}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
