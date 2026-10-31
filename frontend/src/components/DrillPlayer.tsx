import { useState, useEffect, useMemo, useRef } from 'react';
import { duesCares } from '../utils/tifinag';
import { answerSafeFilter } from '../utils/media';
import SourceCredit from './SourceCredit';
import { getMediaUrl } from '../config';
import { preferredRecorderMime, toPlayableAudioUrl } from '../utils/media';
import { getMediaWithOfflineFallback } from '../utils/offlineCache';
import { getYouTubeVideoId, loadYouTubeApi } from '../utils/youtubeUtils';
import { FaVideo, FaPlay, FaPause, FaSync, FaTimes, FaStepBackward, FaStepForward, FaEye, FaStop, FaMicrophone } from 'react-icons/fa';
import DrillVoices from './DrillVoices';
import WordGloss from './WordGloss';
import AiAssistant from './AiAssistant';

declare global {
  interface Window {
    onYouTubeIframeAPIReady?: () => void;
    YT: any;
  }
}

import type { Drill } from '../types';
import { useIsMobileLayout } from '../utils/layout';
import { draftUsable } from '../utils/drafts';

/** The unconfirmed reading to show when a drill has no speaker-confirmed text: the
 *  subtitle/AI draft in the suggestion field unless it is a machine listening bracket. */
/** Word-by-word highlight that follows the voice. The synthetic voice has no word
 *  timings, so each word's share of the clip is proportional to its length: close
 *  enough to follow along on a short phrase. `frac` < 0 = not playing (plain text). */
const KaraokeLine = ({ text, frac, muted }: { text: string; frac: number; muted?: boolean }) => {
  const tokens = text.split(/\s+/).filter(Boolean);
  const weights = tokens.map((w) => Math.max(1, w.replace(/[^\p{L}\p{N}]/gu, '').length) + 0.6);
  const total = weights.reduce((a, b) => a + b, 0) || 1;
  let active = -1;
  if (frac >= 0 && tokens.length) {
    let acc = 0;
    active = tokens.length - 1;
    for (let i = 0; i < tokens.length; i++) {
      acc += weights[i] / total;
      if (frac < acc) { active = i; break; }
    }
  }
  return (
    <span>
      {tokens.map((w, i) => (
        <span key={i} style={{
          display: 'inline-block', padding: '0 4px', borderRadius: '8px', transition: 'background-color 0.12s, color 0.12s',
          background: i === active ? 'var(--saffron-soft)' : 'transparent',
          color: i === active ? 'var(--saffron-strong)' : (active >= 0 && i < active ? 'var(--text-soft)' : (muted ? 'var(--text-soft)' : undefined)),
        }}>{w}</span>
      ))}
    </span>
  );
};

const draftText = (d?: Drill | null): string => {
  if (!d) return '';
  if (!draftUsable(d)) return '';  // the meaning check rejected it: not for learners
  const sug = (d.text_tachelhit_suggested || '').trim();
  if (sug && !sug.startsWith('[')) return sug;
  return (d.text_tachelhit_latin || '').trim();
};

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
  // Phones: the grading bar docks full-width at the bottom and keyboard hints are dropped
  const compactUi = useIsMobileLayout();
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
  // Say the Catalan meaning (synthetic voice) before the Tachelhit; remembered on this device
  const [catalanFirst, setCatalanFirst] = useState<boolean>(() => { try { return localStorage.getItem('player_catalan_first') !== 'off'; } catch { return true; } });
  const toggleCatalanFirst = () => setCatalanFirst((v) => { try { localStorage.setItem('player_catalan_first', v ? 'off' : 'on'); } catch { /* private mode */ } return !v; });
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
  // Captured drills carry a Cloudinary clip (mp4), not a YouTube id: those play in a plain <video>.
  const clipVideoRef = useRef<HTMLVideoElement | null>(null);
  const isClipUrl = (u?: string | null) => !!u && !getYouTubeVideoId(u);
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
  const [explainOpen, setExplainOpen] = useState(false);

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

  // Say it yourself, then hear the two takes one after the other (review mode).
  //
  // Until 2026-10-22 this sent the recording away to be transcribed and turned into a percentage,
  // and that percentage even suggested the review grade. We measured the transcriber: CER 0.78 on
  // our own recordings, 0.87 on Aït Mraw (docs/ASR_EVAL_NOSTRA_2026-10-22.md). It was guessing,
  // and the guess was steering the schedule. Nothing is analysed now: the take stays in the page,
  // you compare it with the speaker, and you grade yourself.
  const pronunciationRecorderRef = useRef<MediaRecorder | null>(null);
  const [isCheckingRecording, setIsCheckingRecording] = useState(false);
  const [myTake, setMyTake] = useState<Blob | null>(null);
  const myTakeUrl = useMemo(() => (myTake ? URL.createObjectURL(myTake) : ''), [myTake]);
  useEffect(() => () => { if (myTakeUrl) URL.revokeObjectURL(myTakeUrl); }, [myTakeUrl]);

  const togglePronunciationRecording = async () => {
    if (isCheckingRecording) {
      pronunciationRecorderRef.current?.stop();
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mime = preferredRecorderMime('audio');
      const recorder = mime ? new MediaRecorder(stream, { mimeType: mime }) : new MediaRecorder(stream);
      const chunks: Blob[] = [];
      recorder.ondataavailable = (e) => { if (e.data.size) chunks.push(e.data); };
      recorder.onstop = () => {
        stream.getTracks().forEach(t => t.stop());
        setIsCheckingRecording(false);
        // Stays here: never uploaded, never transcribed, dropped when you move on.
        if (chunks.length) setMyTake(new Blob(chunks, { type: recorder.mimeType || mime || 'audio/webm' }));
      };
      recorder.start();
      pronunciationRecorderRef.current = recorder;
      setMyTake(null);
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

  // The big button: pause while playing, resume from the same point when paused, start otherwise.
  const [isPaused, setIsPaused] = useState(false);
  const togglePlayback = () => {
    const activeAudio = audioRef.current || ttsAudioRef.current;
    if (isPlaying && activeAudio) {
      activeAudio.pause();
      setIsPaused(true);
      setIsPlaying(false);
      return;
    }
    if (isPaused && activeAudio && !activeAudio.ended) {
      setIsPaused(false);
      setIsPlaying(true);
      activeAudio.play().catch(() => { setIsPlaying(false); setIsPaused(false); });
      return;
    }
    setIsPaused(false);
    playCurrentAudio();
  };

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
    // The take belongs to the card you just left
    setMyTake(null);
    if (pronunciationRecorderRef.current?.state === 'recording') {
      try { pronunciationRecorderRef.current.stop(); } catch { /* already stopped */ }
    }
    // New card starts hidden again (recall-first)
    setAnswerRevealed(false);
    answerRevealedRef.current = false;
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
      return; // a direct clip URL: rendered by the <video> element in the modal
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
      // 1. Catalan (1x), unless the learner turned it off
      if (catalanFirst) await handleSpeakCatalan();

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
    // Només veus de persona: la gravació o el so del vídeo. Una frase sense veu queda muda (#532).
    const sourceUrl = currentDrill?.audio_url || currentDrill?.video_url || '';


    if (!sourceUrl) {
      if (autoPlayEnabled && !reviewMode) goToNextDrill();
      return;
    }

    try {
      // Get audio URL with offline fallback
      const audioUrl = await getMediaWithOfflineFallback(sourceUrl, (u) => toPlayableAudioUrl(getMediaUrl(u)));
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
        const audioUrl = await getMediaWithOfflineFallback(currentDrill.audio_tts_url, (u) => toPlayableAudioUrl(getMediaUrl(u)));
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
    if (clipVideoRef.current) {
      clipVideoRef.current.playbackRate = rate;
    }
  };

  const handleToggleLoop = () => {
    setVideoControls(prev => {
      const isLooping = !prev.isLooping;
      if (clipVideoRef.current) clipVideoRef.current.loop = isLooping;
      return { ...prev, isLooping };
    });
    // YouTube looping is handled in the onStateChange event and a time interval check
  };

  const seekToSubtitle = (index: number) => {
    if (index >= 0 && index < videoControls.subtitleSections.length) {
      const targetSection = videoControls.subtitleSections[index];
      setVideoControls(prev => ({ ...prev, currentSubtitleIndex: index }));
      if (playerRef.current) {
        playerRef.current.seekTo(targetSection.start, true);
        playerRef.current.playVideo();
      } else if (clipVideoRef.current) {
        // a clip starts at the drill's own start time
        clipVideoRef.current.currentTime = Math.max(0, targetSection.start - (Number(currentDrill?.video_start_time) || 0));
        clipVideoRef.current.play().catch(() => {});
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
        padding: 'calc(12px + env(safe-area-inset-top, 0px)) 18px 12px',
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
          <button
            onClick={toggleCatalanFirst}
            title={catalanFirst ? 'Primer sona el significat en català, després el tamazight' : 'Només el tamazight'}
            style={{ ...pillButtonStyle, background: catalanFirst ? 'var(--saffron)' : 'rgba(255,255,255,0.18)', color: catalanFirst ? '#3a2a00' : 'white' }}
          >
            CAT {catalanFirst ? 'ON' : 'OFF'}
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
          flexShrink: 0, // never squeeze into the scroll area: that clipped the card and stacked its texts on phones
          display: 'flex',
          flexDirection: 'column',
          background: 'var(--surface)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--r-2xl)',
          boxShadow: 'var(--shadow-lg)',
          overflow: 'hidden'
        }}>
          {/* Picture first, like a flashcard: the learner sees the scene, then the sentence.
              Illustrations are square on a plain light ground, so they sit on the sand band
              uncropped; video frames and photos get the same band. */}
          {imageUrl && (
            <div style={{ background: 'var(--surface-2)', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'center', position: 'relative' }}>
              <img
                src={imageUrl}
                alt=""
                style={{ width: '100%', height: 'clamp(180px, 34vh, 300px)', objectFit: 'contain', display: 'block', filter: answerSafeFilter(currentDrill?.image_url, hideAnswer), transition: 'filter 0.3s' }}
                onError={(e) => {
                  ((e.target as HTMLImageElement).parentElement as HTMLElement).style.display = 'none';
                }}
              />
              {currentDrill?.image_credit && (
                <div style={{ position: 'absolute', right: 6, bottom: 4, fontSize: '9px', color: 'var(--text-muted)', background: 'rgba(255,255,255,0.75)', padding: '1px 5px', borderRadius: '4px', maxWidth: '70%', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={currentDrill.image_credit}>
                  {currentDrill.image_credit}
                </div>
              )}
            </div>
          )}

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
            ) : currentDrill?.text_tachelhit ? (
              // La frase EN TIFINAG (#339). Fins ara aquí hi anava el text tal com el va escriure
              // el parlant, pintat amb la lletra tifinag: qui havia escrit en llatí es veia en
              // llatí amb tipografia tifinag, i de tifinag no n'hi havia enlloc.
              <KaraokeLine text={duesCares(currentDrill.text_tachelhit, currentDrill.text_tachelhit_latin).tif} frac={isPlaying && audioDuration > 0 ? Math.min(1, audioProgress / audioDuration) : -1} />
            ) : draftText(currentDrill) ? (
              // Captured from subtitles / drafted by a machine and not yet confirmed by a speaker:
              // still worth seeing while learning, but visibly not gold
              <span style={{ color: 'var(--text-soft)', fontWeight: 600 }} title="Esborrany no verificat per cap parlant">
                <KaraokeLine text={draftText(currentDrill)} frac={isPlaying && audioDuration > 0 ? Math.min(1, audioProgress / audioDuration) : -1} muted />
                <span style={{ display: 'block', fontSize: '11px', fontFamily: 'inherit', letterSpacing: '0.04em', textTransform: 'uppercase', opacity: 0.7, marginTop: '4px' }}>esborrany · no verificat</span>
              </span>
            ) : (
              'Sense text tachelhit'
            )}
          </div>

          {/* I el llatí a sota. Abans només sortia per als 90 drills que tenien la forma llatina
              DESADA; ara surt sempre, perquè es calcula, i una frase amaziga ha de portar sempre
              els dos alfabets (#339). */}
          {!hideAnswer && currentDrill?.text_tachelhit && (
            <div style={{
              padding: '0 24px 14px',
              textAlign: 'center',
              fontSize: '17px',
              fontStyle: 'italic',
              color: 'var(--text-soft)'
            }}>
              <KaraokeLine text={duesCares(currentDrill.text_tachelhit, currentDrill.text_tachelhit_latin).lat} frac={isPlaying && audioDuration > 0 ? Math.min(1, audioProgress / audioDuration) : -1} muted />
            </div>
          )}

          {/* Word by word: each word as written, its Tifinagh and the Catalan it answers to */}
          {!hideAnswer && currentDrill && <div style={{ padding: '0 24px 10px' }}><WordGloss drill={currentDrill} align="center" /></div>}
          {/* Different speakers' takes, each with its variety — hear the phrase across varieties */}
          {!hideAnswer && currentDrill && <DrillVoices drillId={currentDrill.id} />}
          {/* Credit: the author and the original video, always, as content authors require */}
          {currentDrill?.source_url && (
            <div style={{ textAlign: 'center', padding: '0 24px 6px', fontSize: '12px', color: 'var(--text-muted)' }}>
              Font: {currentDrill.source_channel || 'vídeo original'}{currentDrill.source_title ? ` · «${currentDrill.source_title}»` : ''} ·{' '}
              <a href={currentDrill.source_url} target="_blank" rel="noopener noreferrer" style={{ color: 'var(--brand-1)', fontWeight: 700 }}>vídeo original ↗</a>
              {currentDrill.license ? <span> · {currentDrill.license}</span> : null}
            </div>
          )}
          {!hideAnswer && currentDrill && (currentDrill.text_tachelhit || currentDrill.text_tachelhit_suggested || currentDrill.text_tachelhit_latin) && (
            <div style={{ textAlign: 'center', padding: '4px 24px 16px' }}>
              <button onClick={() => setExplainOpen(true)} style={{ padding: '9px 16px', borderRadius: 'var(--r-pill)', border: '1px solid var(--border)', background: 'var(--surface-2)', color: 'var(--text)', fontWeight: 700, fontSize: '13px', cursor: 'pointer' }}>
                💡 Explica'm la frase
              </button>
            </div>
          )}
          {explainOpen && currentDrill && <AiAssistant drillId={currentDrill.id} drillLabel={currentDrill.text_catalan || currentDrill.text_tachelhit || `#${currentDrill.id}`} autoAction="explain" onClose={() => setExplainOpen(false)} />}

          {/* Synthetic-voice scaffold marker: learners must know sketch from gold */}

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
              <div style={{ marginTop: '8px' }}><SourceCredit drill={currentDrill || {}} /></div>
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

      {/* Navigation Footer — leaves room for the grading bar in review mode */}
      <div style={{
        padding: reviewMode && onGrade ? `16px 20px calc(${compactUi ? 136 : 92}px + env(safe-area-inset-bottom, 0px))` : '16px 20px calc(16px + env(safe-area-inset-bottom, 0px))',
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
            onClick={togglePlayback}
            aria-label={isPlaying ? 'Pausa' : (isPaused ? 'Continua' : 'Reprodueix l\'àudio')}
            title={isPlaying ? 'Pausa' : (isPaused ? 'Continua' : 'Reprodueix')}
            style={{
              width: '60px',
              height: '60px',
              borderRadius: 'var(--r-pill)',
              background: 'var(--brand-1)',
              color: 'white',
              border: 'none',
              fontSize: '24px',
              cursor: 'pointer',
              boxShadow: 'var(--shadow-brand)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
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
              {isClipUrl(currentDrill.video_url) && (
                <video
                  ref={clipVideoRef}
                  key={currentDrill.id}
                  src={getMediaUrl(currentDrill.video_url)}
                  controls
                  autoPlay
                  playsInline
                  loop={videoControls.isLooping}
                  onLoadedMetadata={(e) => { e.currentTarget.playbackRate = videoControls.playbackRate; }}
                  style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', background: '#000' }}
                />
              )}
              {!isClipUrl(currentDrill.video_url) && (<>
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
              </>)}

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

      {/* Your own take, to hear next to the speaker's. Nothing is measured. */}
      {reviewMode && (myTake || isCheckingRecording) && (
        <div style={{
          position: 'fixed', bottom: '80px', left: '50%', transform: 'translateX(-50%)',
          zIndex: 10001, maxWidth: '90vw',
          background: 'rgba(15, 23, 42, 0.9)', color: 'white',
          padding: '10px 18px', borderRadius: 'var(--r-lg)',
          backdropFilter: 'blur(8px)', boxShadow: 'var(--shadow-lg)',
          fontSize: '14px', textAlign: 'center',
          display: 'inline-flex', alignItems: 'center', gap: '10px'
        }}>
          {isCheckingRecording ? (
            <span>Parla… torna a prémer quan acabis</span>
          ) : (
            <>
              <button
                onClick={() => { if (myTakeUrl) new Audio(myTakeUrl).play().catch(() => {}); }}
                style={{ padding: '7px 14px', background: 'rgba(255,255,255,0.15)', color: 'white', border: '1px solid rgba(255,255,255,0.3)', borderRadius: 'var(--r-pill)', fontWeight: 700, fontSize: '13px', cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: '6px' }}
              >
                <FaPlay size={11} /> El que has dit
              </button>
              <span style={{ opacity: 0.6, fontSize: '12.5px' }}>compara-ho amb la veu de dalt</span>
            </>
          )}
        </div>
      )}

      {/* Spaced-repetition grading bar */}
      {reviewMode && onGrade && currentDrill && (
        <div style={{
          position: 'fixed', zIndex: 10001, display: 'flex', gap: compactUi ? '8px' : '10px',
          flexWrap: 'wrap', justifyContent: 'center',
          background: 'rgba(15, 23, 42, 0.85)', backdropFilter: 'blur(8px)', boxShadow: 'var(--shadow-lg)',
          ...(compactUi
            ? { left: 0, right: 0, bottom: 0, padding: '10px 10px calc(12px + env(safe-area-inset-bottom, 0px))', borderRadius: 'var(--r-xl) var(--r-xl) 0 0' }
            : { bottom: 'calc(18px + env(safe-area-inset-bottom, 0px))', left: '50%', transform: 'translateX(-50%)', maxWidth: '96vw', padding: '10px 14px', borderRadius: 'var(--r-pill)' })
        }}>
          {hideAnswer ? (
            <button
              onClick={revealAnswer}
              aria-label="Mostra la resposta"
              style={{
                padding: '12px 28px', background: 'var(--brand-1)', color: 'white',
                border: 'none', borderRadius: 'var(--r-pill)', fontWeight: 800,
                fontSize: '15px', cursor: 'pointer', whiteSpace: 'nowrap',
                display: 'inline-flex', alignItems: 'center', gap: '8px'
              }}
            >
              <FaEye /> Mostra la resposta{!compactUi && ' (Espai)'}
            </button>
          ) : (
          <>
          <button
            onClick={togglePronunciationRecording}
            aria-label={isCheckingRecording ? 'Atura la gravació' : 'Grava’t i compara’t amb la veu'}
            title={isCheckingRecording ? 'Atura' : 'Grava’t i compara’t amb la veu'}
            style={{
              padding: '10px 14px',
              background: isCheckingRecording ? 'var(--rose)' : 'rgba(255,255,255,0.15)',
              color: 'white', border: '1px solid rgba(255,255,255,0.3)',
              borderRadius: 'var(--r-pill)', fontWeight: 700, fontSize: '15px',
              cursor: 'pointer',
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
              style={{
                padding: compactUi ? '10px 12px' : '10px 16px', background: bg, color: 'white', border: 'none',
                borderRadius: 'var(--r-pill)', fontWeight: 700, fontSize: '14px', cursor: 'pointer',
                display: 'inline-flex', alignItems: 'center', gap: '6px'
              }}
            >
              {!compactUi && <span style={{ fontSize: '10px', fontWeight: 700, color: 'var(--text-muted)', background: 'rgba(255,255,255,0.85)', borderRadius: 'var(--r-sm)', padding: '1px 5px', lineHeight: 1.4 }}>{i + 1}</span>}
              {label}
            </button>
          ))}
          </>
          )}
        </div>
      )}
    </div>
  );
}
