import { useState, useEffect, useRef } from 'react';
import { API_BASE, getMediaUrl } from '../config';
import { getMediaWithOfflineFallback } from '../utils/offlineCache';
import { getYouTubeVideoId, loadYouTubeApi } from '../utils/youtubeUtils';
import { FaVideo, FaVolumeUp, FaPlay, FaPause, FaSync, FaTimes, FaStepBackward, FaStepForward, FaBullseye, FaThumbsUp, FaRedo, FaExclamationTriangle, FaEye, FaStop, FaMicrophone, FaStar } from 'react-icons/fa';
import DrillVoices from './DrillVoices';

declare global {
  interface Window {
    onYouTubeIframeAPIReady?: () => void;
    YT: any;
  }
}

import type { Drill } from '../types';

interface DrillPlayerProps {
  drills: Drill[];
  onExit: () => void;
  // Spaced-repetition session: audio plays but never auto-advances; the user
  // grades each drill (0=again 1=hard 2=good 3=easy) to move on
  reviewMode?: boolean;
  onGrade?: (drillId: number, grade: number) => Promise<void> | void;
}

interface VideoControls {
  playbackRate: number;
  isLooping: boolean;
  currentSubtitleIndex: number;
  subtitleSections: Array<{start: number, end: number}>;
}

export default function DrillPlayer({ drills, onExit, reviewMode, onGrade }: DrillPlayerProps) {
  // Style definitions (moved to top to avoid "used before declaration" errors)
  const cleanButtonStyle = {
    background: 'rgba(255,255,255,0.15)',
    border: '1px solid rgba(255,255,255,0.25)',
    color: 'white',
    fontSize: '18px',
    lineHeight: 1,
    cursor: 'pointer',
    width: '38px',
    height: '38px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 'var(--r-pill)',
    transition: 'all 0.2s'
  };

  const pillButtonStyle = {
    padding: '8px 14px',
    border: 'none',
    borderRadius: 'var(--r-pill)',
    fontSize: '12px',
    fontWeight: 700,
    letterSpacing: '0.02em',
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
  // Refs read inside long-lived callbacks (YT event handlers, audio promise
  // chains) so they always see current values instead of stale closures.
  const isLoopingRef = useRef(videoControls.isLooping);
  const currentIndexRef = useRef(currentIndex);
  const audioTimersRef = useRef<number[]>([]);

  useEffect(() => { isLoopingRef.current = videoControls.isLooping; }, [videoControls.isLooping]);
  useEffect(() => { currentIndexRef.current = currentIndex; }, [currentIndex]);

  // Recall-first (review mode): the answer stays hidden and only the Catalan
  // prompt plays until the user reveals — recall practice, not recognition
  const [answerRevealed, setAnswerRevealed] = useState(false);
  const answerRevealedRef = useRef(false);
  const hideAnswer = !!reviewMode && !answerRevealed;

  // Session-finished state (review mode): shown once the last due card is graded
  const [finished, setFinished] = useState(false);
  const [reviewedCount, setReviewedCount] = useState(0);

  const revealAnswer = () => {
    setAnswerRevealed(true);
    answerRevealedRef.current = true;
    stopAllAudio();
    setIsPlaying(true);
    playTachelhitAudio().catch(() => setIsPlaying(false));
  };

  // Synthetic-voice scaffold state (marks TTS fallback playback)
  const [usingSyntheticVoice, setUsingSyntheticVoice] = useState(false);
  const [synthesizingVoice, setSynthesizingVoice] = useState(false);

  // Pronunciation check (review mode): record -> ASR -> similarity score
  const pronunciationRecorderRef = useRef<MediaRecorder | null>(null);
  const [isCheckingRecording, setIsCheckingRecording] = useState(false);
  const [pronunciationBusy, setPronunciationBusy] = useState(false);
  const [pronunciationResult, setPronunciationResult] = useState<{ heard: string; score: number } | null>(null);

  // Voice understanding guides scheduling: the score suggests a self-grade
  // (learner still decides — the highlight is advice, not automation)
  const suggestedGrade = pronunciationResult && pronunciationResult.score >= 0
    ? (pronunciationResult.score >= 0.85 ? 3
      : pronunciationResult.score >= 0.65 ? 2
      : pronunciationResult.score >= 0.4 ? 1 : 0)
    : null;

  const togglePronunciationRecording = async () => {
    if (isCheckingRecording) {
      pronunciationRecorderRef.current?.stop();
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      const chunks: Blob[] = [];
      recorder.ondataavailable = (e) => { if (e.data.size) chunks.push(e.data); };
      recorder.onstop = async () => {
        stream.getTracks().forEach(t => t.stop());
        setIsCheckingRecording(false);
        const drillId = drills[currentIndexRef.current]?.id;
        if (!drillId || !chunks.length) return;
        setPronunciationBusy(true);
        try {
          const blob = new Blob(chunks, { type: recorder.mimeType || 'audio/webm' });
          const fd = new FormData();
          fd.append('drill_id', String(drillId));
          fd.append('audio', blob, 'pronunciation.webm');
          const res = await fetch(`${API_BASE}/pronunciation/check`, { method: 'POST', body: fd });
          if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || 'Pronunciation check failed');
          }
          const data = await res.json();
          setPronunciationResult({ heard: data.heard, score: data.score });
        } catch (e: any) {
          console.error('Pronunciation check failed:', e);
          setPronunciationResult({ heard: e.message || 'Error', score: -1 });
        } finally {
          setPronunciationBusy(false);
        }
      };
      recorder.start();
      pronunciationRecorderRef.current = recorder;
      setPronunciationResult(null);
      setIsCheckingRecording(true);
    } catch (e) {
      console.error('Microphone access failed:', e);
    }
  };

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
    } else {
      setVideoControls(prev => ({ ...prev, subtitleSections: [], currentSubtitleIndex: 0 }));
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
    // Cancel any pending replay/advance timers from the previous drill so its
    // audio can't restart over the new drill
    audioTimersRef.current.forEach(t => window.clearTimeout(t));
    audioTimersRef.current = [];
    // Reset pronunciation feedback for the new card
    setPronunciationResult(null);
    if (pronunciationRecorderRef.current?.state === 'recording') {
      try { pronunciationRecorderRef.current.stop(); } catch { /* already stopped */ }
    }
    // New card starts hidden again (recall-first)
    setAnswerRevealed(false);
    answerRevealedRef.current = false;
    setUsingSyntheticVoice(false);
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

    // Reset playback controls (subtitle sections are owned by the init effect above)
    setVideoControls(prev => ({
      ...prev,
      playbackRate: 1.0,
      isLooping: true
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

  // Load YouTube IFrame API script (shared, non-clobbering loader)
  useEffect(() => {
    let cancelled = false;
    loadYouTubeApi().then(() => { if (!cancelled) setPlayerReady(true); });
    return () => { cancelled = true; };
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
          const startTime = Number(currentDrill.video_start_time) || 0;
          event.target.seekTo(startTime, true);
          event.target.playVideo();
        },
        'onStateChange': (event: any) => {
          const player = event.target;
          const startTime = Number(currentDrill.video_start_time) || 0;
          const endTime = Number(currentDrill.video_end_time);

          if (event.data === window.YT.PlayerState.PAUSED && isLoopingRef.current) {
            // 2. Loop Logic: Check if it paused because it reached the 'end' limit
            const currentTime = player.getCurrentTime();
            if (endTime && currentTime >= endTime - 0.5) {
              console.log('🔄 Reached end of segment, looping back to:', startTime);
              player.seekTo(startTime, true);
              player.playVideo();
            }
          }

          if (event.data === window.YT.PlayerState.ENDED && isLoopingRef.current) {
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

    return () => {
      if (playerRef.current) {
        playerRef.current.destroy();
        playerRef.current = null;
      }
    };
  }, [playerReady, currentDrill?.id, showVideo]);





  // Handle playback rate separately
  useEffect(() => {
    if (playerRef.current && typeof playerRef.current.setPlaybackRate === 'function') {
      playerRef.current.setPlaybackRate(videoControls.playbackRate);
    }
  }, [videoControls.playbackRate]);

  const playCurrentAudio = async () => {
    stopAllAudio();
    setIsPlaying(true);
    const startedAtIndex = currentIndexRef.current;

    try {
      // 1. Catalan (1x)
      await handleSpeakCatalan();

      // Recall-first: stop after the prompt until the user reveals the answer
      if (reviewMode && !answerRevealedRef.current) {
        setIsPlaying(false);
        return;
      }

      // 2. Tachelhit (2x)
      await playTachelhitAudio();
    } catch (error) {
      console.error('Playback sequence error:', error);
      setIsPlaying(false);
      // Only auto-advance if the user hasn't already navigated away — an
      // interrupted play() also rejects, and advancing then would skip a drill
      if (autoPlayEnabled && !reviewMode && currentIndexRef.current === startedAtIndex) goToNextDrill();
    }
  };

  const stopAllAudio = () => {
    if (audioRef.current) { audioRef.current.pause(); audioRef.current = null; }
    if (ttsAudioRef.current) { ttsAudioRef.current.pause(); ttsAudioRef.current = null; }
    if (speechSynthRef.current) { speechSynthesis.cancel(); speechSynthRef.current = null; }
  };

  const playTachelhitAudio = async (): Promise<void> => {
    // Voice-source chain: native recording (gold) -> stored synthetic voice
    // (scaffold) -> synthesize on demand for text-only cards (the backend
    // stores the result so this only happens once per drill)
    let sourceUrl = currentDrill?.audio_url || currentDrill?.audio_tts_shi_url || '';
    let synthetic = !currentDrill?.audio_url && !!sourceUrl;

    if (!sourceUrl && currentDrill?.text_tachelhit) {
      try {
        setSynthesizingVoice(true);
        const res = await fetch(`${API_BASE}/tts/tachelhit`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text: currentDrill.text_tachelhit, drill_id: currentDrill.id }),
        });
        if (res.ok) {
          sourceUrl = (await res.json()).url || '';
          synthetic = !!sourceUrl;
        }
      } catch (e) {
        console.warn('Tachelhit TTS synthesis failed:', e);
      } finally {
        setSynthesizingVoice(false);
      }
    }

    if (!sourceUrl) {
      if (autoPlayEnabled && !reviewMode) goToNextDrill();
      return;
    }
    setUsingSyntheticVoice(synthetic);

    try {
      // Get audio URL with offline fallback
      const audioUrl = await getMediaWithOfflineFallback(sourceUrl, getMediaUrl);
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
              // Tracked so navigating away cancels the pending replay
              audioTimersRef.current.push(window.setTimeout(playInstance, 600));
            } else {
              setIsPlaying(false);
              audioTimersRef.current.push(window.setTimeout(() => {
                if (autoPlayEnabled && !reviewMode) goToNextDrill();
                resolve();
              }, 1000));
            }
          };

          const handleError = (error: any) => {
            audio.removeEventListener('ended', handleEnded);
            audio.removeEventListener('error', handleError);
            setIsPlaying(false);
            // Advancing on failure is handled once, in playCurrentAudio's catch
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
      // Advancing on failure is handled once, in playCurrentAudio's catch
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
    // Read the index from a ref: this runs at the end of multi-second audio
    // chains, so the closure's currentIndex may be stale after manual navigation
    const idx = currentIndexRef.current;
    if (idx < drills.length - 1) {
      setCurrentIndex(idx + 1);
    } else if (loopEnabled) {
      setCurrentIndex(0);
    } else if (reviewMode) {
      // Recap the session before leaving instead of dropping straight out
      setFinished(true);
    } else {
      onExit();
    }
  };

  const handlePrev = () => {
    if (currentIndex > 0) setCurrentIndex(currentIndex - 1);
  };

  // Shared grade action so the on-screen buttons and keyboard shortcuts stay in
  // sync (does not alter grade integers or the grading call)
  const gradeAndAdvance = async (g: number) => {
    if (!currentDrill || !onGrade) return;
    const drillId = currentDrill.id;
    try {
      await onGrade(drillId, g);
    } catch (e) {
      console.error('Failed to record grade', e);
    }
    // "Again" replays the same card; any other grade moves on
    if (g === 0) {
      playCurrentAudio();
    } else {
      setReviewedCount(c => c + 1);
      goToNextDrill();
    }
  };

  // Keyboard operability (review mode only): reveal with Space/Enter, then grade
  // with 1-4. Ignored while typing in a field.
  useEffect(() => {
    if (!reviewMode || finished) return;
    const onKey = (e: KeyboardEvent) => {
      const el = document.activeElement as HTMLElement | null;
      if (el && (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA' || el.isContentEditable)) return;
      if (hideAnswer) {
        if (e.key === ' ' || e.key === 'Enter') {
          e.preventDefault();
          revealAnswer();
        }
      } else if (onGrade) {
        // Same order as the on-screen grade buttons: 0=again 1=hard 2=good 3=easy
        const map: Record<string, number> = { '1': 0, '2': 1, '3': 2, '4': 3 };
        if (e.key in map) {
          e.preventDefault();
          gradeAndAdvance(map[e.key]);
        }
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [reviewMode, finished, hideAnswer, onGrade, currentDrill]);

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

  // Session-finished recap (review mode) — mirrors the empty-state card styling
  if (finished) {
    return (
      <div style={{
        height: '100vh',
        width: '100vw',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'var(--bg)',
        padding: '20px',
        textAlign: 'center',
        fontFamily: 'var(--font-sans)',
        position: 'fixed',
        top: 0, left: 0, right: 0, bottom: 0,
        zIndex: 1000
      }}>
        <div style={{
          background: 'var(--surface)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--r-2xl)',
          boxShadow: 'var(--shadow-lg)',
          padding: '40px 36px',
          maxWidth: '420px'
        }}>
          <div style={{
            width: '72px',
            height: '72px',
            margin: '0 auto 22px',
            borderRadius: 'var(--r-xl)',
            background: 'var(--brand-gradient-soft)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '36px'
          }}>🎉</div>
          <h2 style={{ margin: '0 0 10px', fontSize: '22px', fontWeight: 800, color: 'var(--text)', fontFamily: 'var(--font-display)' }}>Repàs completat!</h2>
          <p style={{ color: 'var(--text-soft)', margin: '0 0 24px', fontSize: '15px', lineHeight: 1.5 }}>Has repassat {reviewedCount} drills.</p>
          <button
            onClick={onExit}
            style={{
              padding: '12px 28px',
              background: 'var(--brand-1)',
              color: 'white',
              border: 'none',
              borderRadius: 'var(--r-pill)',
              fontWeight: 700,
              fontSize: '15px',
              cursor: 'pointer',
              boxShadow: 'var(--shadow-brand)'
            }}
          >
            Torna a l'inici
          </button>
        </div>
      </div>
    );
  }

  return (
    <div style={{
      height: '100vh',
      width: '100vw',
      display: 'flex',
      flexDirection: 'column',
      background: 'var(--bg)',
      fontFamily: 'var(--font-sans)',
      overflow: 'hidden',
      position: 'fixed',
      top: 0, left: 0, right: 0, bottom: 0,
      zIndex: 1000
    }}>
      {/* Header */}
      <div style={{
        padding: '12px 18px',
        background: 'var(--brand-1)',
        color: 'white',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        boxShadow: 'var(--shadow-brand)',
        flexWrap: 'wrap',
        gap: '8px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <button onClick={onExit} style={cleanButtonStyle} aria-label="Tanca"><FaTimes /></button>
          <span style={{
            fontWeight: 800,
            fontSize: '14px',
            letterSpacing: '0.02em',
            background: 'rgba(255,255,255,0.15)',
            padding: '6px 14px',
            borderRadius: 'var(--r-pill)'
          }}>{currentIndex + 1} / {drills.length}</span>
        </div>

        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            onClick={() => setAutoPlayEnabled(!autoPlayEnabled)}
            style={{ ...pillButtonStyle, background: autoPlayEnabled ? 'var(--saffron)' : 'rgba(255,255,255,0.18)', color: autoPlayEnabled ? '#3a2a00' : 'white' }}
          >
            AUTO {autoPlayEnabled ? 'ON' : 'OFF'}
          </button>
          <button
            onClick={() => setLoopEnabled(!loopEnabled)}
            style={{ ...pillButtonStyle, background: loopEnabled ? 'var(--saffron)' : 'rgba(255,255,255,0.18)', color: loopEnabled ? '#3a2a00' : 'white' }}
          >
            LOOP {loopEnabled ? 'ON' : 'OFF'}
          </button>

          {/* Video Library Button */}
          {videoDrills.length > 0 && (
            <button
              onClick={() => setShowVideoLibrary(true)}
              style={{ ...pillButtonStyle, background: 'rgba(255,255,255,0.18)', color: 'white' }}
            >
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}><FaVideo /> BIBLIOTECA</span>
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
        alignItems: 'center',
        padding: '24px 16px 132px'
      }}>
        <div style={{
          width: '100%',
          maxWidth: '560px',
          display: 'flex',
          flexDirection: 'column',
          background: 'var(--surface)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--r-2xl)',
          boxShadow: 'var(--shadow-lg)',
          overflow: 'hidden'
        }}>
          {/* Catalan (primary) */}
          {currentDrill?.text_catalan && (
            <div style={{
              padding: '28px 24px 8px',
              textAlign: 'center',
              fontSize: '26px',
              fontWeight: 800,
              color: 'var(--text)',
              lineHeight: 1.35,
              fontFamily: 'var(--font-display)'
            }}>
              {currentDrill.text_catalan}
            </div>
          )}

          {/* Tachelhit Text (Tifinagh) */}
          <div style={{
            padding: '12px 24px 20px',
            textAlign: 'center',
            fontSize: '30px',
            fontWeight: 700,
            color: 'var(--brand-1)',
            fontFamily: 'var(--font-tifinagh)',
            lineHeight: 1.5,
            minHeight: '64px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}>
            {hideAnswer ? (
              <span style={{ letterSpacing: '8px', opacity: 0.35 }}>· · ·</span>
            ) : (
              currentDrill?.text_tachelhit || 'Sense text tachelhit'
            )}
          </div>

          {/* Latin romanization (shown with the answer) */}
          {!hideAnswer && currentDrill?.text_tachelhit_latin && (
            <div style={{
              padding: '0 24px 14px',
              textAlign: 'center',
              fontSize: '17px',
              fontStyle: 'italic',
              color: 'var(--text-soft)'
            }}>
              {currentDrill.text_tachelhit_latin}
            </div>
          )}

          {/* Different speakers' takes, each with its variety — hear the phrase across varieties */}
          {!hideAnswer && currentDrill && <DrillVoices drillId={currentDrill.id} />}

          {/* Synthetic-voice scaffold marker: learners must know sketch from gold */}
          {(synthesizingVoice || usingSyntheticVoice) && (
            <div style={{ textAlign: 'center', paddingBottom: '10px' }}>
              <span style={{
                fontSize: '11px', fontWeight: 700, padding: '3px 10px',
                borderRadius: 'var(--r-pill)', background: 'var(--sky-soft)', color: 'var(--sky)'
              }}>
                {synthesizingVoice
                  ? <span style={{ display: 'inline-flex', alignItems: 'center', gap: '5px' }}><FaVolumeUp /> Sintetitzant la veu…</span>
                  : <span style={{ display: 'inline-flex', alignItems: 'center', gap: '5px' }}><FaVolumeUp /> Veu sintètica — encara sense gravació nativa</span>}
              </span>
            </div>
          )}

          {/* Image */}
          {imageUrl && (
            <div style={{ padding: '0 24px 20px', display: 'flex', justifyContent: 'center' }}>
              <img
                src={imageUrl}
                alt="Drill"
                style={{
                  maxWidth: '100%',
                  maxHeight: '320px',
                  borderRadius: 'var(--r-lg)',
                  boxShadow: 'var(--shadow-md)'
                }}
                onError={(e) => {
                  (e.target as HTMLImageElement).style.display = 'none';
                }}
              />
            </div>
          )}

          {/* Translations */}
          <div style={{ padding: '0 24px 8px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {/* Arabic */}
            {!hideAnswer && currentDrill?.text_arabic && (
              <div style={{
                padding: '14px 16px',
                background: 'var(--emerald-soft)',
                borderRadius: 'var(--r-md)',
                borderLeft: '4px solid var(--emerald)',
                fontSize: '20px',
                color: 'var(--text)',
                textAlign: 'right',
                direction: 'rtl'
              }}>
                {currentDrill.text_arabic}
              </div>
            )}
          </div>

          {/* Video Button (if video exists) */}
          {currentDrill?.video_url && (
            <div style={{ padding: '16px 24px 24px', display: 'flex', justifyContent: 'center' }}>
              <button
                onClick={() => setShowVideo(true)}
                style={{
                  padding: '13px 26px',
                  background: 'var(--brand-gradient)',
                  color: 'white',
                  border: 'none',
                  borderRadius: 'var(--r-pill)',
                  fontSize: '15px',
                  fontWeight: 700,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  boxShadow: 'var(--shadow-brand)'
                }}
              >
                <FaPlay />
                Mira el vídeo amb subtítols
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Navigation Footer */}
      <div style={{
        padding: '16px 20px',
        background: 'var(--surface)',
        borderTop: '1px solid var(--border)',
        boxShadow: '0 -4px 16px rgba(15,23,42,0.04)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        gap: '14px',
        flexWrap: 'wrap'
      }}>
        <button
          onClick={handlePrev}
          disabled={currentIndex === 0}
          aria-label="Anterior"
          style={{
            width: '48px',
            height: '48px',
            borderRadius: 'var(--r-pill)',
            border: '1px solid var(--border)',
            background: 'var(--surface-2)',
            color: 'var(--text-soft)',
            fontSize: '20px',
            cursor: currentIndex === 0 ? 'not-allowed' : 'pointer',
            opacity: currentIndex === 0 ? 0.4 : 1,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            transition: 'all 0.2s',
            flexShrink: 0
          }}
        >
          <FaStepBackward />
        </button>

        {/* Audio Progress Bar */}
        <div style={{ flex: 1, minWidth: '160px', display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-muted)', minWidth: '38px' }}>
            {formatTime(audioProgress)}
          </span>
          <div
            role="slider"
            tabIndex={0}
            aria-label="Progrés de l'àudio"
            aria-valuemin={0}
            aria-valuemax={Math.round(audioDuration)}
            aria-valuenow={Math.round(audioProgress)}
            style={{
              flex: 1,
              height: '8px',
              background: 'var(--border)',
              borderRadius: 'var(--r-pill)',
              overflow: 'hidden',
              cursor: 'pointer'
            }}
            onClick={(e) => {
              const rect = e.currentTarget.getBoundingClientRect();
              const percent = (e.clientX - rect.left) / rect.width;
              const time = percent * audioDuration;
              handleSeek(time);
            }}
            onKeyDown={(e) => {
              const step = 1; // seconds
              const clamp = (t: number) => Math.max(0, Math.min(audioDuration, t));
              if (e.key === 'ArrowLeft') {
                e.preventDefault();
                handleSeek(clamp(audioProgress - step));
              } else if (e.key === 'ArrowRight') {
                e.preventDefault();
                handleSeek(clamp(audioProgress + step));
              } else if (e.key === 'Home') {
                e.preventDefault();
                handleSeek(0);
              } else if (e.key === 'End') {
                e.preventDefault();
                handleSeek(audioDuration);
              }
            }}
          >
            <div
              style={{
                width: `${audioDuration ? (audioProgress / audioDuration) * 100 : 0}%`,
                height: '100%',
                background: 'var(--brand-1)',
                borderRadius: 'var(--r-pill)',
                transition: 'width 0.1s'
              }}
            />
          </div>
          <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-muted)', minWidth: '38px' }}>
            {formatTime(audioDuration)}
          </span>
        </div>

        <div style={{ display: 'flex', gap: '10px', alignItems: 'center', flexShrink: 0 }}>
          <button
            onClick={playCurrentAudio}
            disabled={isPlaying}
            aria-label={isPlaying ? 'Reproduint' : 'Reprodueix l\'àudio'}
            style={{
              width: '60px',
              height: '60px',
              borderRadius: 'var(--r-pill)',
              background: 'var(--brand-1)',
              color: 'white',
              border: 'none',
              fontSize: '24px',
              cursor: isPlaying ? 'default' : 'pointer',
              boxShadow: 'var(--shadow-brand)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              opacity: isPlaying ? 0.9 : 1,
              transition: 'all 0.2s'
            }}
          >
            {isPlaying ? <FaPause /> : <FaPlay />}
          </button>

          <button
            onClick={goToNextDrill}
            aria-label="Següent"
            style={{
              width: '48px',
              height: '48px',
              borderRadius: 'var(--r-pill)',
              border: '1px solid var(--border)',
              background: 'var(--surface-2)',
              color: 'var(--text-soft)',
              fontSize: '20px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              transition: 'all 0.2s'
            }}
          >
            <FaStepForward />
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
            background: '#0f1220',
            borderRadius: 'var(--r-xl)',
            overflow: 'hidden',
            boxShadow: 'var(--shadow-xl)',
            display: 'flex',
            flexDirection: 'column'
          }}>
            {/* Video Modal Header */}
            <div style={{
              padding: '14px 18px',
              background: '#171a2b',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              gap: '12px',
              flexWrap: 'wrap',
              borderBottom: '1px solid rgba(255,255,255,0.08)'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <button
                  onClick={() => setShowVideo(false)}
                  aria-label="Tanca"
                  style={{
                    background: 'rgba(255,255,255,0.1)',
                    border: '1px solid rgba(255,255,255,0.18)',
                    color: 'white',
                    fontSize: '16px',
                    cursor: 'pointer',
                    width: '34px',
                    height: '34px',
                    borderRadius: 'var(--r-pill)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center'
                  }}
                >
                  <FaTimes />
                </button>
                <span style={{ color: 'white', fontWeight: 700, fontFamily: 'var(--font-tifinagh)', fontSize: '15px' }}>
                  {currentDrill.text_tachelhit?.substring(0, 50)}…
                </span>
              </div>

              {/* Video Controls */}
              <div style={{ display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
                {/* Playback Speed */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                  <span style={{ color: 'rgba(255,255,255,0.72)', fontSize: '12px', fontWeight: 600 }}>Velocitat</span>
                  {[0.5, 0.75, 1.0, 1.25, 1.5].map(rate => (
                    <button
                      key={rate}
                      onClick={() => handlePlaybackRateChange(rate)}
                      style={{
                        padding: '5px 10px',
                        background: videoControls.playbackRate === rate ? 'var(--brand-gradient)' : 'rgba(255,255,255,0.08)',
                        color: 'white',
                        border: 'none',
                        borderRadius: 'var(--r-pill)',
                        fontSize: '12px',
                        fontWeight: 700,
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
                    padding: '7px 14px',
                    background: videoControls.isLooping ? 'var(--saffron)' : 'rgba(255,255,255,0.08)',
                    color: videoControls.isLooping ? '#3a2a00' : 'white',
                    border: 'none',
                    borderRadius: 'var(--r-pill)',
                    fontSize: '12px',
                    fontWeight: 700,
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '5px'
                  }}
                >
                  <FaSync /> {videoControls.isLooping ? 'Bucle ACTIU' : 'Bucle'}
                </button>
              </div>
            </div>

            {/* Video Player */}
            <div style={{ position: 'relative', width: '100%', aspectRatio: '16/9' }}>
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
                    borderRadius: 'var(--r-md)',
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
                    background: 'var(--brand-1)',
                    color: 'white',
                    padding: '10px 16px',
                    borderRadius: 'var(--r-md)',
                    fontSize: '20px',
                    fontWeight: 600,
                    fontFamily: 'var(--font-tifinagh)',
                    lineHeight: 1.5
                  }}>
                    {currentDrill.text_tachelhit}
                  </div>
                )}

                {/* Catalan Subtitle */}
                {currentDrill?.text_catalan && (
                  <div style={{
                    background: 'var(--sky)',
                    color: 'white',
                    padding: '8px 16px',
                    borderRadius: 'var(--r-md)',
                    fontSize: '16px',
                    fontWeight: 600,
                    opacity: 0.95,
                    lineHeight: 1.4
                  }}>
                    {currentDrill.text_catalan}
                  </div>
                )}
              </div>
            </div>

            {/* Subtitle Navigation Controls */}
            <div style={{
              padding: '14px 18px',
              background: '#171a2b',
              borderTop: '1px solid rgba(255,255,255,0.08)',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              gap: '12px',
              flexWrap: 'wrap'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <button
                  onClick={handlePreviousSubtitle}
                  disabled={videoControls.currentSubtitleIndex === 0}
                  style={{
                    padding: '8px 16px',
                    background: videoControls.currentSubtitleIndex === 0 ? 'rgba(255,255,255,0.06)' : 'var(--brand-gradient)',
                    color: 'white',
                    border: 'none',
                    borderRadius: 'var(--r-pill)',
                    fontWeight: 700,
                    fontSize: '13px',
                    cursor: videoControls.currentSubtitleIndex === 0 ? 'not-allowed' : 'pointer',
                    opacity: videoControls.currentSubtitleIndex === 0 ? 0.5 : 1,
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px'
                  }}
                >
                  ← Anterior
                </button>

                <div style={{ color: 'rgba(255,255,255,0.72)', fontSize: '13px', fontWeight: 600 }}>
                  Subtítol {videoControls.currentSubtitleIndex + 1} de {videoControls.subtitleSections.length}
                </div>

                <button
                  onClick={handleNextSubtitle}
                  disabled={videoControls.currentSubtitleIndex >= videoControls.subtitleSections.length - 1}
                  style={{
                    padding: '8px 16px',
                    background: videoControls.currentSubtitleIndex >= videoControls.subtitleSections.length - 1 ? 'rgba(255,255,255,0.06)' : 'var(--brand-gradient)',
                    color: 'white',
                    border: 'none',
                    borderRadius: 'var(--r-pill)',
                    fontWeight: 700,
                    fontSize: '13px',
                    cursor: videoControls.currentSubtitleIndex >= videoControls.subtitleSections.length - 1 ? 'not-allowed' : 'pointer',
                    opacity: videoControls.currentSubtitleIndex >= videoControls.subtitleSections.length - 1 ? 0.5 : 1,
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px'
                  }}
                >
                  Següent →
                </button>
              </div>

              {/* Subtitle Timeline */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ color: 'rgba(255,255,255,0.72)', fontSize: '12px', fontWeight: 600 }}>Línia de temps</span>
                <div style={{ display: 'flex', gap: '5px' }}>
                  {videoControls.subtitleSections.map((section, index) => (
                    <button
                      key={index}
                      onClick={() => handleJumpToSubtitle(index)}
                      style={{
                        padding: '5px 10px',
                        background: videoControls.currentSubtitleIndex === index ? 'var(--saffron)' : 'rgba(255,255,255,0.08)',
                        color: videoControls.currentSubtitleIndex === index ? '#3a2a00' : 'white',
                        border: 'none',
                        borderRadius: 'var(--r-pill)',
                        fontSize: '12px',
                        fontWeight: 700,
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
            background: '#0f1220',
            borderRadius: 'var(--r-xl)',
            overflow: 'hidden',
            boxShadow: 'var(--shadow-xl)',
            display: 'flex',
            flexDirection: 'column'
          }}>
            {/* Library Header */}
            <div style={{
              padding: '16px 24px',
              background: '#171a2b',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              gap: '12px',
              flexWrap: 'wrap',
              borderBottom: '1px solid rgba(255,255,255,0.08)'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <button
                  onClick={() => setShowVideoLibrary(false)}
                  aria-label="Tanca"
                  style={{
                    background: 'rgba(255,255,255,0.1)',
                    border: '1px solid rgba(255,255,255,0.18)',
                    color: 'white',
                    fontSize: '16px',
                    cursor: 'pointer',
                    width: '34px',
                    height: '34px',
                    borderRadius: 'var(--r-pill)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center'
                  }}
                >
                  <FaTimes />
                </button>
                <span style={{ color: 'white', fontWeight: 800, fontSize: '18px', fontFamily: 'var(--font-display)', display: 'inline-flex', alignItems: 'center', gap: '8px' }}>
                  <FaVideo /> Biblioteca de vídeos ({videoDrills.length} vídeos)
                </span>
              </div>
              <div style={{ color: 'rgba(255,255,255,0.72)', fontSize: '14px', fontWeight: 600 }}>
                Fes clic a qualsevol vídeo per reproduir-lo amb subtítols
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
                    background: 'rgba(255,255,255,0.04)',
                    borderRadius: 'var(--r-lg)',
                    overflow: 'hidden',
                    cursor: 'pointer',
                    transition: 'transform 0.2s, background 0.2s, border-color 0.2s',
                    border: '1px solid rgba(255,255,255,0.08)'
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.transform = 'translateY(-4px)';
                    e.currentTarget.style.background = 'rgba(255,255,255,0.08)';
                    e.currentTarget.style.borderColor = 'var(--brand-1)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.transform = '';
                    e.currentTarget.style.background = 'rgba(255,255,255,0.04)';
                    e.currentTarget.style.borderColor = 'rgba(255,255,255,0.08)';
                  }}
                >
                  {/* Video Thumbnail */}
                  <div style={{
                    position: 'relative',
                    paddingTop: '56.25%' /* 16:9 aspect ratio */,
                    background: '#0f1220'
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
                      background: 'var(--brand-gradient)'
                    }}>
                      <span style={{ color: 'white', fontSize: '28px', display: 'inline-flex' }}><FaPlay /></span>
                    </div>
                    <div style={{
                      position: 'absolute',
                      bottom: '8px',
                      right: '8px',
                      background: 'rgba(0,0,0,0.7)',
                      color: 'white',
                      padding: '4px 8px',
                      borderRadius: 'var(--r-sm)',
                      fontSize: '12px'
                    }}>
                      {drill.video_start_time !== undefined && drill.video_end_time !== undefined
                        ? `${formatTime(drill.video_start_time)}-${formatTime(drill.video_end_time)}`
                        : 'Vídeo complet'
                      }
                    </div>
                  </div>

                  {/* Video Info */}
                  <div style={{ padding: '16px' }}>
                    <div style={{
                      color: 'white',
                      fontSize: '17px',
                      fontWeight: 700,
                      fontFamily: 'var(--font-tifinagh)',
                      marginBottom: '8px',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      display: '-webkit-box',
                      WebkitLineClamp: 2,
                      WebkitBoxOrient: 'vertical',
                      lineHeight: 1.4,
                      height: '48px'
                    }}>
                      {drill.text_tachelhit || 'Sense títol'}
                    </div>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                      {drill.text_arabic && (
                        <div style={{
                          color: 'rgba(255,255,255,0.72)',
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
                          color: 'rgba(255,255,255,0.72)',
                          fontSize: '12px',
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

      {/* Pronunciation feedback chip */}
      {reviewMode && (pronunciationResult || pronunciationBusy) && (
        <div style={{
          position: 'fixed', bottom: '80px', left: '50%', transform: 'translateX(-50%)',
          zIndex: 10001, maxWidth: '90vw',
          background: 'rgba(15, 23, 42, 0.9)', color: 'white',
          padding: '10px 18px', borderRadius: 'var(--r-lg)',
          backdropFilter: 'blur(8px)', boxShadow: 'var(--shadow-lg)',
          fontSize: '14px', textAlign: 'center'
        }}>
          {pronunciationBusy ? (
            <span>👂 Escoltant la teva pronunciació…</span>
          ) : pronunciationResult && pronunciationResult.score >= 0 ? (
            <>
              <span style={{
                fontWeight: 800,
                display: 'inline-flex',
                alignItems: 'center',
                gap: '5px',
                color: pronunciationResult.score >= 0.8 ? 'var(--emerald)'
                  : pronunciationResult.score >= 0.5 ? 'var(--saffron)' : 'var(--rose)'
              }}>
                {pronunciationResult.score >= 0.8 ? <FaBullseye /> : pronunciationResult.score >= 0.5 ? <FaThumbsUp /> : <FaRedo />}
                {Math.round(pronunciationResult.score * 100)}%
              </span>
              <span style={{ margin: '0 8px', opacity: 0.5 }}>·</span>
              <span style={{ fontFamily: 'var(--font-tifinagh)' }}>He sentit: “{pronunciationResult.heard}”</span>
            </>
          ) : (
            <span style={{ color: 'var(--rose)', display: 'inline-flex', alignItems: 'center', gap: '6px' }}><FaExclamationTriangle /> {pronunciationResult?.heard}</span>
          )}
        </div>
      )}

      {/* Spaced-repetition grading bar */}
      {reviewMode && onGrade && currentDrill && (
        <div style={{
          position: 'fixed', bottom: '18px', left: '50%', transform: 'translateX(-50%)',
          display: 'flex', gap: '10px', zIndex: 10001,
          flexWrap: 'wrap', justifyContent: 'center', maxWidth: '96vw',
          background: 'rgba(15, 23, 42, 0.85)', padding: '10px 14px',
          borderRadius: 'var(--r-pill)', backdropFilter: 'blur(8px)', boxShadow: 'var(--shadow-lg)'
        }}>
          {hideAnswer ? (
            <button
              onClick={revealAnswer}
              aria-label="Mostra la resposta"
              style={{
                padding: '12px 28px', background: 'var(--brand-1)', color: 'white',
                border: 'none', borderRadius: 'var(--r-pill)', fontWeight: 800,
                fontSize: '15px', cursor: 'pointer',
                display: 'inline-flex', alignItems: 'center', gap: '8px'
              }}
            >
              <FaEye /> Mostra la resposta (Espai)
            </button>
          ) : (
          <>
          <button
            onClick={togglePronunciationRecording}
            disabled={pronunciationBusy}
            aria-label={isCheckingRecording ? 'Atura i comprova la pronunciació' : 'Comprova la teva pronunciació'}
            title={isCheckingRecording ? 'Atura i comprova' : 'Comprova la teva pronunciació'}
            style={{
              padding: '10px 14px',
              background: isCheckingRecording ? 'var(--rose)' : 'rgba(255,255,255,0.15)',
              color: 'white', border: '1px solid rgba(255,255,255,0.3)',
              borderRadius: 'var(--r-pill)', fontWeight: 700, fontSize: '15px',
              cursor: pronunciationBusy ? 'wait' : 'pointer',
              animation: isCheckingRecording ? 'pulse 1s infinite' : undefined,
              display: 'inline-flex', alignItems: 'center', justifyContent: 'center'
            }}
          >
            {isCheckingRecording ? <FaStop /> : <FaMicrophone />}
          </button>
          {[
            { g: 0, label: 'Un altre cop', bg: 'var(--rose)' },
            { g: 1, label: 'Difícil', bg: 'var(--saffron)' },
            { g: 2, label: 'Bé', bg: 'var(--emerald)' },
            { g: 3, label: 'Fàcil', bg: 'var(--sky)' },
          ].map(({ g, label, bg }, i) => (
            <button
              key={g}
              onClick={() => gradeAndAdvance(g)}
              aria-label={`${label} (tecla ${i + 1})`}
              title={suggestedGrade === g ? 'Suggerit per la teva pronunciació' : undefined}
              style={{
                padding: '10px 16px', background: bg, color: 'white', border: 'none',
                borderRadius: 'var(--r-pill)', fontWeight: 700, fontSize: '14px', cursor: 'pointer',
                display: 'inline-flex', alignItems: 'center', gap: '6px',
                boxShadow: suggestedGrade === g ? '0 0 0 3px rgba(255,255,255,0.85)' : undefined,
                transform: suggestedGrade === g ? 'scale(1.08)' : undefined
              }}
            >
              <span style={{ fontSize: '10px', fontWeight: 700, color: 'var(--text-muted)', background: 'rgba(255,255,255,0.85)', borderRadius: 'var(--r-sm)', padding: '1px 5px', lineHeight: 1.4 }}>{i + 1}</span>
              {suggestedGrade === g ? <FaStar /> : null}{label}
            </button>
          ))}
          </>
          )}
        </div>
      )}
    </div>
  );
}
