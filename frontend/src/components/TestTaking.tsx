import { useState, useEffect, useRef } from 'react';
import SourceCredit from './SourceCredit';
import axios from 'axios';
import { API_BASE, getMediaUrl, getUserName } from '../config';
import AmbSo from './AmbSo';
import { answerSafeFilter } from '../utils/media';
import { api } from '../api';
import { toast } from '../toast';
import { syncManager } from '../services/OfflineSyncManager';

interface Test {
  id: number;
  title: string;
  description: string;
  question_type: string;
  hint_level: string;
  hint_percentage: number;
  hint_tries_before_reveal: number;
  time_limit_seconds: number;
  passing_score: number;
  drill_ids: string;
  playback_direction: string; // New field
}

interface Drill {
  id: number;
  text_tachelhit_latin?: string;
  text_catalan: string;
  source_url?: string;
  source_title?: string;
  source_channel?: string;
  video_start_time?: number;
  text_tachelhit: string;
  text_arabic?: string;
  audio_url: string;
  video_url: string;
  image_url: string;
}

interface QuestionResult {
  drill_id: number;
  correct: boolean;
  attempts: number;
  time_spent: number;
  user_answer: string;
}

export default function TestTaking({ testId, onExit }: { testId: number; onExit: () => void }) {
  const [test, setTest] = useState<Test | null>(null);
  const [drills, setDrills] = useState<Drill[]>([]);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [userAnswer, setUserAnswer] = useState('');
  const [attempts, setAttempts] = useState(0);
  const [hintsUsed, setHintsUsed] = useState(0);
  const [showHint, setShowHint] = useState(false);
  const [questionResults, setQuestionResults] = useState<QuestionResult[]>([]);
  const [questionStartTime, setQuestionStartTime] = useState(Date.now());
  const [testStartTime, setTestStartTime] = useState(Date.now());
  const [testCompleted, setTestCompleted] = useState(false);
  const [timeRemaining, setTimeRemaining] = useState<number | null>(null);
  const [playing, setPlaying] = useState(false);
  const [showCorrectAnswer, setShowCorrectAnswer] = useState(false);
  const [reviewMode, setReviewMode] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  // const videoRef = useRef<HTMLVideoElement | null>(null); // Unused

  useEffect(() => {
    loadTest();
  }, [testId]);

  useEffect(() => {
    // Timer countdown
    if (test && test.time_limit_seconds > 0 && timeRemaining !== null && timeRemaining > 0 && !testCompleted) {
      const timer = setTimeout(() => {
        setTimeRemaining(timeRemaining - 1);
      }, 1000);
      return () => clearTimeout(timer);
    } else if (timeRemaining === 0) {
      // Time's up, submit current answer
      handleSubmitAnswer(true);
    }
  }, [timeRemaining, testCompleted]);

  const loadTest = async () => {
    try {
      // Load test
      const testResponse = await axios.get(`${API_BASE}/tests/${testId}`);
      setTest(testResponse.data);

      // Load only this test's drills (server keeps the given order; older
      // backends ignore ?ids= and return everything, so we still map by id).
      const drillIds: number[] = String(testResponse.data.drill_ids || '').split(',').map((id: string) => parseInt(id)).filter((n: number) => !isNaN(n));
      const drillsResponse = await axios.get(`${API_BASE}/drills/`, { params: { ids: drillIds.join(',') } });
      const byId = new Map<number, Drill>((drillsResponse.data as Drill[]).map(d => [d.id, d]));
      const direction = testResponse.data.playback_direction || 'cat-tash';
      const askable = (d: Drill) => {
        const q = direction === 'ar-tash' ? d.text_arabic : direction.startsWith('tash') ? d.text_tachelhit : d.text_catalan;
        const a = direction === 'tash-cat' ? d.text_catalan : direction === 'tash-ar' ? d.text_arabic : d.text_tachelhit;
        return !!(q && q.trim() && a && a.trim());
      };
      const found = drillIds.map(id => byId.get(id)).filter((d): d is Drill => !!d);
      const testDrills = found.filter(askable);
      const missing = drillIds.length - found.length;
      const skipped = found.length - testDrills.length;
      if (missing > 0 || skipped > 0) {
        toast.info(`S'han omès ${missing + skipped} preguntes (${missing} drills esborrats, ${skipped} sense text en aquesta direcció).`);
      }
      if (testDrills.length === 0) {
        toast.error('Aquest test no té cap pregunta vàlida.');
        onExit();
        return;
      }
      setDrills(testDrills);

      // Initialize timer if needed
      if (testResponse.data.time_limit_seconds > 0) {
        setTimeRemaining(testResponse.data.time_limit_seconds);
      }

      setTestStartTime(Date.now());
      setQuestionStartTime(Date.now());
    } catch (error) {
      console.error('Error loading test:', error);
      toast.error('No s\'ha pogut carregar el test');
      onExit();
    }
  };

  const currentDrill = drills[currentQuestionIndex];

  // Determine question and answer fields based on playback_direction
  const getQuestionAndAnswerFields = () => {
    if (!test || !currentDrill) return { questionText: null, correctAnswer: null };

    let questionText = null;
    let correctAnswer = null;

    switch (test.playback_direction) {
      case 'cat-tash':
        questionText = currentDrill.text_catalan;
        correctAnswer = currentDrill.text_tachelhit;
        break;
      case 'tash-cat':
        questionText = currentDrill.text_tachelhit;
        correctAnswer = currentDrill.text_catalan;
        break;
      case 'ar-tash':
        questionText = currentDrill.text_arabic;
        correctAnswer = currentDrill.text_tachelhit;
        break;
      case 'tash-ar':
        questionText = currentDrill.text_tachelhit;
        correctAnswer = currentDrill.text_arabic;
        break;
      default:
        questionText = currentDrill.text_catalan; // Default to Catalan to Tachelhit
        correctAnswer = currentDrill.text_tachelhit;
        break;
    }
    return { questionText, correctAnswer };
  };

  const { questionText, correctAnswer } = getQuestionAndAnswerFields();

  const getHintText = () => {
    if (!correctAnswer || !test) return '';

    if (test.hint_level === 'none') {
      return '';
    } else if (test.hint_level === 'full_after_tries') {
      if (attempts >= test.hint_tries_before_reveal) {
        return correctAnswer;
      }
      return '';
    } else if (test.hint_level === 'partial') {
      const basePercentage = test.hint_percentage || 30;
      const progressivePercentage = Math.min(basePercentage + (hintsUsed * 15), 80);
      const numLettersToShow = Math.ceil((correctAnswer.length * progressivePercentage) / 100);

      // Deterministic pseudo-random letters so the hint is stable while the
      // learner types; it only changes when they ask for "more hint".
      let seed = (currentDrill?.id || 1) * 7919 + hintsUsed * 104729 + correctAnswer.length;
      const rand = () => { seed = (seed * 1103515245 + 12345) & 0x7fffffff; return seed / 0x7fffffff; };
      const indices = new Set<number>([0]); // First letter already revealed
      const nonSpace = correctAnswer.split('').filter(c => c !== ' ').length;
      let guard = 0;
      while (indices.size < numLettersToShow && indices.size < nonSpace && guard++ < 10000) {
        const randomIndex = Math.floor(rand() * correctAnswer.length);
        if (correctAnswer[randomIndex] !== ' ') {
          indices.add(randomIndex);
        }
      }

      return correctAnswer.split('').map((char, i) =>
        char === ' ' || indices.has(i) ? char : '_'
      ).join('');
    }

    return '';
  };

  const normalizeAnswer = (text: string) => {
    if (!text) return '';
    let normalized = text.toLowerCase();
    normalized = normalized.trim();
    normalized = normalized.split(' ').filter(s => s !== '').join(' ');
    return normalized;
  };

  const stripDiacritics = (t: string) => t.normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/[.,;:!?¿¡'"«»]/g, '');

  // Tachelhit answers may be typed in phone-Latin (aghrum, ta7anut) or in
  // Tifinagh. Accept: exact match, the drill's own Latin form, or the same
  // phonemic key as computed by the backend transliterator.
  const checkAnswer = async (): Promise<boolean> => {
    if (!correctAnswer || !currentDrill) return false;
    const correct = normalizeAnswer(correctAnswer);
    const user = normalizeAnswer(userAnswer);
    if (!user) return false;
    if (correct === user) return true;
    if (stripDiacritics(correct) === stripDiacritics(user)) return true;
    const answerIsTachelhit = correctAnswer === currentDrill.text_tachelhit;
    if (!answerIsTachelhit) return false;
    const latin = normalizeAnswer(currentDrill.text_tachelhit_latin || '');
    if (latin && (latin === user || stripDiacritics(latin) === stripDiacritics(user))) return true;
    try {
      const [a, b] = await Promise.all([api.transliterate(userAnswer), api.transliterate(correctAnswer)]);
      if (a.key && b.key && a.key === b.key) return true;
      if (a.tifinagh && normalizeAnswer(a.tifinagh) === correct) return true;
      if (latin && a.clean_latin && normalizeAnswer(a.clean_latin) === latin) return true;
    } catch {
      /* transliteration service down: exact matching only */
    }
    return false;
  };

  const handleSubmitAnswer = async (timeUp: boolean = false, skipQuestion: boolean = false) => {
    if (!currentDrill || !test || !correctAnswer) return;

    const isCorrect = (timeUp || skipQuestion) && !userAnswer.trim() ? false : await checkAnswer();
    const timeSpent = Math.floor((Date.now() - questionStartTime) / 1000);

    if (!isCorrect && !timeUp && !skipQuestion) {
      // Wrong answer - increment attempts and show feedback
      setAttempts(attempts + 1);

      // Show hint if configured
      if (test.hint_level === 'full_after_tries' && attempts + 1 >= test.hint_tries_before_reveal) {
        setShowHint(true);
      }
      return; // Don't move to next question yet
    }

    // Record the result
    const result: QuestionResult = {
      drill_id: currentDrill.id,
      correct: isCorrect,
      attempts: attempts + 1,
      time_spent: timeSpent,
      user_answer: userAnswer
    };

    const newResults = [...questionResults, result];
    setQuestionResults(newResults);

    // Move to next question or complete test
    if (currentQuestionIndex < drills.length - 1) {
      // Stop any playing audio
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current = null;
      }
      setPlaying(false);

      setCurrentQuestionIndex(currentQuestionIndex + 1);
      setUserAnswer('');
      setAttempts(0);
      setHintsUsed(0);
      setShowHint(false);
      setShowCorrectAnswer(false);
      setQuestionStartTime(Date.now());

      // Reset timer for next question
      if (test.time_limit_seconds > 0) {
        setTimeRemaining(test.time_limit_seconds);
      }
    } else {
      // Test completed
      // Stop any playing audio
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current = null;
      }
      setPlaying(false);

      await submitTestAttempt(newResults);
    }
  };

  const handleNextQuestion = () => {
    handleSubmitAnswer(false, true);
  };

  const submitTestAttempt = async (results: QuestionResult[]) => {
    if (!test) return;

    const correctAnswers = results.filter(r => r.correct).length;
    const score = (correctAnswers / results.length) * 100;
    const totalTime = Math.floor((Date.now() - testStartTime) / 1000);

    try {
      await axios.post(`${API_BASE}/test-attempts/`, {
        test_id: test.id,
        user_name: getUserName() || null,
        score: score,
        time_taken_seconds: totalTime,
        total_questions: results.length,
        correct_answers: correctAnswers,
        question_results: JSON.stringify(results)
      });

      setTestCompleted(true);
    } catch (error) {
      console.error('Error submitting test attempt:', error);
      toast.error("El resultat no s'ha pogut desar al servidor (es mostra igualment).");
      setTestCompleted(true);
    }
  };

  const handleRequestHint = () => {
    setShowHint(true);
    setHintsUsed(hintsUsed + 1);
  };

  const handlePlayMedia = async () => {
    if (!currentDrill?.audio_url) {
      console.error('No audio URL available');
      return;
    }

    try {
      const localUrl = await syncManager.getLocalMediaUrl(currentDrill.audio_url);

      // Create new audio element each time for reliability
      const audio = new Audio(localUrl);
      audioRef.current = audio;

      setPlaying(true);

      audio.onended = () => {
        setPlaying(false);
      };

      audio.onerror = (e) => {
        console.error('Audio playback error:', e);
        setPlaying(false);
        toast.error("No s'ha pogut reproduir l'àudio.");
      };

      await audio.play();
      console.log('Audio playing:', currentDrill.audio_url);
    } catch (error) {
      console.error('Error playing audio:', error);
      setPlaying(false);
      toast.error("No s'ha pogut reproduir l'àudio.");
    }
  };

  if (!test || drills.length === 0) {
    return (
      <div style={{ padding: '40px', textAlign: 'center', fontFamily: 'var(--font-sans)', color: 'var(--text-soft)' }}>
        <p>Carregant el test…</p>
      </div>
    );
  }

  if (testCompleted) {
    const correctAnswers = questionResults.filter(r => r.correct).length;
    const score = (correctAnswers / questionResults.length) * 100;
    const passed = score >= test.passing_score;

    if (reviewMode) {
      // Review Mode - Show all questions and answers
      return (
        <div style={{
          position: 'fixed', inset: 0, zIndex: 5000,
          display: 'flex',
          flexDirection: 'column',
          background: 'var(--bg)',
          fontFamily: 'var(--font-sans)'
        }}>
          {/* Header */}
          <div style={{
            padding: 'calc(18px + env(safe-area-inset-top, 0px)) 24px 24px',
            background: 'var(--brand-gradient)',
            color: '#fff',
            borderBottomLeftRadius: '26px',
            borderBottomRightRadius: '26px',
            boxShadow: 'var(--shadow-md)'
          }}>
            <h2 style={{ margin: 0, color: '#fff', fontWeight: 800 }}>Revisa les teves respostes</h2>
            <p style={{ margin: '8px 0 0 0', opacity: 0.92 }}>
              Puntuació: {Math.round(score)}% ({correctAnswers}/{questionResults.length} correctes)
            </p>
          </div>

          {/* Questions Review */}
          <div style={{ flex: 1, overflowY: 'auto', padding: '20px' }}>
            {questionResults.map((result, index) => {
              const drill = drills.find(d => d.id === result.drill_id);
              if (!drill) return null;

              // Determine question and answer text for review mode based on playback_direction
              let reviewQuestionText = '';
              let reviewCorrectAnswerText = '';

              switch (test.playback_direction) {
                case 'cat-tash':
                  reviewQuestionText = drill.text_catalan;
                  reviewCorrectAnswerText = drill.text_tachelhit;
                  break;
                case 'tash-cat':
                  reviewQuestionText = drill.text_tachelhit;
                  reviewCorrectAnswerText = drill.text_catalan;
                  break;
                case 'ar-tash':
                  reviewQuestionText = drill.text_arabic || '';
                  reviewCorrectAnswerText = drill.text_tachelhit;
                  break;
                case 'tash-ar':
                  reviewQuestionText = drill.text_tachelhit;
                  reviewCorrectAnswerText = drill.text_arabic || '';
                  break;
                default:
                  reviewQuestionText = drill.text_catalan;
                  reviewCorrectAnswerText = drill.text_tachelhit;
                  break;
              }

              const reviewQuestionIsTashelhit = test.playback_direction === 'tash-cat' || test.playback_direction === 'tash-ar';
              const reviewAnswerIsTashelhit = test.playback_direction === 'cat-tash' || test.playback_direction === 'ar-tash' || (!test.playback_direction);
              const reviewAnswerIsArabic = test.playback_direction === 'tash-ar';

              return (
                <div key={index} style={{
                  background: 'var(--surface)',
                  padding: '24px',
                  borderRadius: 'var(--r-xl)',
                  marginBottom: '16px',
                  border: result.correct ? '1px solid var(--emerald)' : '1px solid var(--rose)',
                  boxShadow: 'var(--shadow-sm)'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '16px' }}>
                    <h3 style={{ margin: 0, fontSize: '18px', color: 'var(--text)', fontWeight: 800 }}>
                      Pregunta {index + 1}
                    </h3>
                    <span style={{
                      padding: '5px 14px',
                      borderRadius: 'var(--r-pill)',
                      fontSize: '13px',
                      fontWeight: 700,
                      background: result.correct ? 'var(--emerald-soft)' : 'var(--rose-soft)',
                      color: result.correct ? 'var(--emerald)' : 'var(--rose)'
                    }}>
                      {result.correct ? '✓ Correcta' : '✗ Incorrecta'}
                    </span>
                  </div>

                  {/* Image if available */}
                  {drill.image_url && (
                    <div style={{ marginBottom: '16px', textAlign: 'center' }}>
                      <img
                        src={getMediaUrl(drill.image_url)}
                        alt="Visual"
                        style={{
                          maxWidth: '100%',
                          maxHeight: '150px',
                          borderRadius: 'var(--r-md)',
                          objectFit: 'contain'
                        }}
                      />
                    </div>
                  )}

                  <div style={{ marginBottom: '12px' }}>
                    <strong style={{ color: 'var(--brand-1)' }}>Pregunta:</strong>
                    <p style={{ margin: '4px 0 0 0', fontSize: '16px', color: 'var(--text)', fontFamily: reviewQuestionIsTashelhit ? 'var(--font-tifinagh)' : 'var(--font-sans)' }}>{reviewQuestionText}</p>
                  </div>

                  <div style={{ marginBottom: '12px' }}>
                    <strong style={{ color: result.correct ? 'var(--emerald)' : 'var(--rose)' }}>La teva resposta:</strong>
                    <p style={{ margin: '4px 0 0 0', fontSize: '16px', fontWeight: 500, color: 'var(--text)', fontFamily: reviewAnswerIsTashelhit ? 'var(--font-tifinagh)' : 'var(--font-sans)', direction: reviewAnswerIsArabic ? 'rtl' : 'ltr' }}>
                      {result.user_answer || '(sense resposta)'}
                    </p>
                  </div>

                  {!result.correct && (
                    <div style={{
                      background: 'var(--emerald-soft)',
                      padding: '12px 14px',
                      borderRadius: 'var(--r-md)',
                      marginBottom: '12px',
                      border: '1px solid var(--emerald)'
                    }}>
                      <strong style={{ color: 'var(--emerald)' }}>Resposta correcta:</strong>
                      <p style={{ margin: '4px 0 0 0', fontSize: '16px', fontWeight: 600, color: 'var(--emerald)', fontFamily: reviewAnswerIsTashelhit ? 'var(--font-tifinagh)' : 'var(--font-sans)', direction: reviewAnswerIsArabic ? 'rtl' : 'ltr' }}>
                        {reviewCorrectAnswerText}
                      </p>
                    </div>
                  )}

                  <div style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '12px' }}>
                    Intents: {result.attempts} · Temps: {result.time_spent}s
                  </div>
                </div>
              );
            })}
          </div>

          {/* Footer Buttons */}
          <div style={{
            padding: '18px 20px',
            background: 'var(--surface)',
            borderTop: '1px solid var(--border)',
            display: 'flex',
            gap: '12px',
            justifyContent: 'center'
          }}>
            <button
              onClick={() => setReviewMode(false)}
              style={{
                padding: '12px 24px',
                fontSize: '15px',
                background: 'var(--brand-gradient)',
                color: '#fff',
                border: 'none',
                borderRadius: 'var(--r-md)',
                cursor: 'pointer',
                fontWeight: 700,
                boxShadow: 'var(--shadow-brand)'
              }}
            >
              Torna als resultats
            </button>
            <button
              onClick={onExit}
              style={{
                padding: '12px 24px',
                fontSize: '15px',
                background: 'var(--surface)',
                color: 'var(--text-soft)',
                border: '1px solid var(--border)',
                borderRadius: 'var(--r-md)',
                cursor: 'pointer',
                fontWeight: 700,
                boxShadow: 'var(--shadow-xs)'
              }}
            >
              Surt
            </button>
          </div>
        </div>
      );
    }

    return (
      <div style={{
        position: 'fixed', inset: 0, zIndex: 5000, overflowY: 'auto',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 'calc(24px + env(safe-area-inset-top, 0px)) 24px calc(24px + env(safe-area-inset-bottom, 0px))',
        background: 'var(--brand-gradient)',
        fontFamily: 'var(--font-sans)'
      }}>
        <div style={{
          background: 'var(--surface)',
          padding: '44px 40px',
          borderRadius: 'var(--r-2xl)',
          maxWidth: '600px',
          width: '100%',
          textAlign: 'center',
          boxShadow: 'var(--shadow-xl)'
        }}>
          <div style={{
            width: '96px',
            height: '96px',
            margin: '0 auto 18px',
            borderRadius: 'var(--r-pill)',
            background: passed ? 'var(--emerald-soft)' : 'var(--amber-soft)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '48px'
          }}>{passed ? '🎉' : '📚'}</div>
          <h1 style={{
            fontSize: '32px',
            margin: '0 0 14px 0',
            fontWeight: 800,
            color: passed ? 'var(--emerald)' : 'var(--amber)'
          }}>
            {passed ? 'Aprovat!' : 'Continua practicant'}
          </h1>

          <h2 style={{ fontSize: '64px', margin: '12px 0', color: 'var(--text)', fontWeight: 800 }}>
            {Math.round(score)}%
          </h2>

          <p style={{ fontSize: '18px', color: 'var(--text-soft)', marginBottom: '28px' }}>
            {correctAnswers} de {questionResults.length} correctes
          </p>

          <div style={{
            background: 'var(--surface-2)',
            border: '1px solid var(--border)',
            padding: '20px',
            borderRadius: 'var(--r-lg)',
            marginBottom: '30px',
            color: 'var(--text-soft)'
          }}>
            <div style={{ marginBottom: '10px' }}>
              <strong style={{ color: 'var(--text)' }}>Temps:</strong> {Math.floor((Date.now() - testStartTime) / 1000)}s
            </div>
            <div>
              <strong style={{ color: 'var(--text)' }}>Nota per aprovar:</strong> {test.passing_score}%
            </div>
          </div>

          <div style={{ display: 'flex', gap: '12px', justifyContent: 'center', flexWrap: 'wrap' }}>
            <button
              onClick={() => setReviewMode(true)}
              style={{
                padding: '14px 30px',
                fontSize: '16px',
                background: 'var(--brand-gradient)',
                color: '#fff',
                border: 'none',
                borderRadius: 'var(--r-md)',
                cursor: 'pointer',
                fontWeight: 700,
                boxShadow: 'var(--shadow-brand)'
              }}
            >
              📝 Revisa les respostes
            </button>
            <button
              onClick={onExit}
              style={{
                padding: '14px 30px',
                fontSize: '16px',
                background: 'var(--surface)',
                color: 'var(--brand-1)',
                border: '1px solid var(--border)',
                borderRadius: 'var(--r-md)',
                cursor: 'pointer',
                fontWeight: 700,
                boxShadow: 'var(--shadow-xs)'
              }}
            >
              Torna als tests
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (!currentDrill || !questionText || !correctAnswer) {
    return <div style={{ padding: '40px', textAlign: 'center', fontFamily: 'var(--font-sans)', color: 'var(--text-soft)' }}>Carregant la pregunta…</div>;
  }

  const hintText = getHintText();

  // Determine question and secondary text display based on playback_direction
  let mainQuestionDisplay = questionText;
  let secondaryQuestionDisplay = '';
  let isArabicQuestion = false;

  switch (test.playback_direction) {
    case 'cat-tash':
      mainQuestionDisplay = currentDrill.text_catalan;
      secondaryQuestionDisplay = currentDrill.text_arabic || '';
      break;
    case 'tash-cat':
      mainQuestionDisplay = currentDrill.text_tachelhit;
      secondaryQuestionDisplay = currentDrill.text_arabic || ''; // Still show Arabic if available
      break;
    case 'ar-tash':
      mainQuestionDisplay = currentDrill.text_arabic || '';
      secondaryQuestionDisplay = currentDrill.text_catalan;
      isArabicQuestion = true;
      break;
    case 'tash-ar':
      mainQuestionDisplay = currentDrill.text_tachelhit;
      secondaryQuestionDisplay = currentDrill.text_catalan; // Show Catalan as secondary
      break;
    default:
      mainQuestionDisplay = currentDrill.text_catalan;
      secondaryQuestionDisplay = currentDrill.text_arabic || '';
      break;
  }

  const mainQuestionIsTashelhit = test.playback_direction === 'tash-cat' || test.playback_direction === 'tash-ar';
  const answerIsTashelhit = correctAnswer === currentDrill.text_tachelhit;
  const progressPct = ((currentQuestionIndex + 1) / drills.length) * 100;

  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 5000,
      display: 'flex',
      flexDirection: 'column',
      background: 'var(--bg)',
      fontFamily: 'var(--font-sans)'
    }}>
      {/* Header */}
      <div style={{
        padding: 'calc(16px + env(safe-area-inset-top, 0px)) 24px 22px',
        background: 'var(--brand-gradient)',
        color: '#fff',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        borderBottomLeftRadius: '26px',
        borderBottomRightRadius: '26px',
        boxShadow: 'var(--shadow-md)'
      }}>
        <div>
          <h2 style={{ margin: 0, fontSize: '20px', color: '#fff', fontWeight: 800 }}>{test.title}</h2>
          <p style={{ margin: '6px 0 0 0', fontSize: '14px', opacity: 0.92 }}>
            Pregunta {currentQuestionIndex + 1} de {drills.length}
          </p>
        </div>
        <div style={{ textAlign: 'right' }}>
          {timeRemaining !== null && (
            <div style={{
              fontSize: '24px',
              fontWeight: 800,
              color: timeRemaining < 10 ? '#fecaca' : '#fff'
            }}>
              ⏱ {timeRemaining}s
            </div>
          )}
          <button
            onClick={() => {
              if (confirm('Segur que vols sortir? Perdràs el progrés.')) {
                onExit();
              }
            }}
            style={{
              marginTop: '10px',
              padding: '7px 14px',
              background: 'rgba(255,255,255,0.18)',
              color: '#fff',
              border: '1px solid rgba(255,255,255,0.45)',
              borderRadius: 'var(--r-pill)',
              cursor: 'pointer',
              fontSize: '12px',
              fontWeight: 600
            }}
          >
            Surt del test
          </button>
        </div>
      </div>

      {/* Progress bar */}
      <div style={{ height: '6px', background: 'var(--border)', flexShrink: 0 }}>
        <div style={{
          height: '100%',
          width: `${progressPct}%`,
          background: 'var(--brand-gradient)',
          transition: 'width 0.3s var(--ease)'
        }} />
      </div>

      {/* Question Area */}
      <div style={{
        flex: 1,
        minHeight: 0,
        overflowY: 'auto',
        display: 'flex',
        alignItems: 'flex-start',
        justifyContent: 'center',
        padding: window.innerWidth < 768 ? '16px 12px calc(24px + env(safe-area-inset-bottom, 0px))' : '40px'
      }}>
        <div style={{
          background: 'var(--surface)',
          border: '1px solid var(--border)',
          padding: window.innerWidth < 768 ? '28px' : '48px',
          borderRadius: 'var(--r-xl)',
          maxWidth: '800px',
          width: '100%',
          boxShadow: 'var(--shadow-lg)'
        }}>
          {/* Credit for captured content: author, title, link to the original second */}
          <div style={{ marginBottom: '10px', textAlign: 'right' }}><SourceCredit drill={currentDrill} compact /></div>
          {/* Image if available */}
          {currentDrill.image_url && (
            <div style={{ marginBottom: '30px', textAlign: 'center' }}>
              <img
                src={getMediaUrl(currentDrill.image_url)}
                alt="Pista visual"
                style={{
                  maxWidth: '100%',
                  maxHeight: '200px',
                  borderRadius: 'var(--r-md)',
                  objectFit: 'contain',
                  // a video frame can carry the subtitle with the answer: blur it until answered
                  filter: answerSafeFilter(currentDrill.image_url, !showCorrectAnswer)
                }}
              />
            </div>
          )}

          {/* Question */}
          <div style={{ marginBottom: '20px' }}>
            <div style={{
              fontSize: window.innerWidth < 768 ? '24px' : '36px',
              textAlign: 'center',
              color: 'var(--text)',
              fontWeight: 700,
              lineHeight: 1.3,
              direction: isArabicQuestion ? 'rtl' : 'ltr',
              fontFamily: mainQuestionIsTashelhit ? 'var(--font-tifinagh)' : 'var(--font-sans)'
            }}>
              {mainQuestionDisplay}
            </div>
            {secondaryQuestionDisplay && (
              <div style={{
                fontSize: window.innerWidth < 768 ? '14px' : '16px',
                textAlign: 'center',
                color: 'var(--text-soft)',
                marginTop: '10px',
                padding: '8px 12px',
                background: 'var(--surface-2)',
                border: '1px solid var(--border)',
                borderRadius: 'var(--r-md)',
                direction: secondaryQuestionDisplay === currentDrill.text_arabic ? 'rtl' : 'ltr'
              }}>
                {secondaryQuestionDisplay}
              </div>
            )}
          </div>

          {/* Media Section - Compact */}
          {(test.question_type === 'audio' || test.question_type === 'video' || test.question_type === 'combined') && (
            <div style={{
              textAlign: 'center',
              marginBottom: window.innerWidth < 768 ? '20px' : '30px',
              display: 'flex',
              flexDirection: window.innerWidth < 768 ? 'column' : 'row',
              gap: '10px',
              justifyContent: 'center',
              alignItems: 'center'
            }}>
              {/* Audio playback */}
              {currentDrill.audio_url && (test.question_type === 'audio' || test.question_type === 'combined') && (
                <AmbSo url={currentDrill.audio_url} dins><button
                  onClick={handlePlayMedia}
                  disabled={playing}
                  style={{
                    padding: window.innerWidth < 768 ? '10px 16px' : '12px 24px',
                    fontSize: window.innerWidth < 768 ? '14px' : '16px',
                    background: playing ? 'var(--surface-2)' : 'var(--emerald)',
                    color: playing ? 'var(--text-muted)' : '#fff',
                    border: 'none',
                    borderRadius: 'var(--r-md)',
                    cursor: playing ? 'not-allowed' : 'pointer',
                    fontWeight: 700,
                    flex: window.innerWidth < 768 ? '1' : 'none',
                    width: window.innerWidth < 768 ? '100%' : 'auto',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '8px',
                    boxShadow: playing ? 'none' : 'var(--shadow-sm)'
                  }}
                >
                  <span>{playing ? '🔊' : '🔊'}</span>
                  <span>{playing ? 'Reproduint…' : 'Escolta l\'àudio'}</span>
                </button></AmbSo>
              )}

              {/* Video playback */}
              {currentDrill.video_url && (test.question_type === 'video' || test.question_type === 'combined') && (
                <video
                  key={currentDrill.id}
                  src={getMediaUrl(currentDrill.video_url)}
                  controls
                  playsInline
                  preload="metadata"
                  style={{ width: '100%', maxWidth: '420px', maxHeight: '240px', borderRadius: 'var(--r-md)', background: '#000' }}
                />
              )}

              {/* Fallback message if no media available in combined mode */}
              {test.question_type === 'combined' && !currentDrill.audio_url && !currentDrill.video_url && (
                <div style={{
                  padding: '10px 14px',
                  background: 'var(--amber-soft)',
                  border: '1px solid var(--amber)',
                  borderRadius: 'var(--r-md)',
                  fontSize: window.innerWidth < 768 ? '12px' : '14px',
                  color: 'var(--amber-strong)',
                  fontWeight: 600,
                  width: '100%'
                }}>
                  💡 Aquest drill no té àudio ni vídeo
                </div>
              )}
            </div>
          )}

          {/* Answer Input - Compact */}
          <div style={{ marginBottom: window.innerWidth < 768 ? '16px' : '20px' }}>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              marginBottom: '8px'
            }}>
              <label style={{
                fontSize: window.innerWidth < 768 ? '14px' : '16px',
                fontWeight: 700,
                color: 'var(--text-soft)',
                direction: (test.playback_direction === 'ar-tash' || test.playback_direction === 'tash-ar') ? 'rtl' : 'ltr' // Apply direction to label
              }}>
                La teva resposta en {correctAnswer === currentDrill.text_tachelhit ? 'tachelhit' : correctAnswer === currentDrill.text_catalan ? 'català' : 'àrab'}:
              </label>
              {timeRemaining !== null && (
                <div style={{
                  fontSize: window.innerWidth < 768 ? '14px' : '16px',
                  fontWeight: 700,
                  color: timeRemaining < 10 ? 'var(--rose)' : 'var(--brand-1)',
                  background: timeRemaining < 10 ? 'var(--rose-soft)' : 'var(--brand-gradient-soft)',
                  padding: '5px 12px',
                  borderRadius: 'var(--r-pill)'
                }}>
                  ⏱ {timeRemaining}s
                </div>
              )}
            </div>
            <input
              type='text'
              value={userAnswer}
              onChange={(e) => setUserAnswer(e.target.value)}
              onKeyPress={(e) => {
                if (e.key === 'Enter') {
                  handleSubmitAnswer();
                }
              }}
              placeholder={answerIsTashelhit ? 'Escriu en llatí (aghrum) o en tifinagh…' : 'Escriu aquí…'}
              autoFocus
              autoCapitalize="off"
              autoCorrect="off"
              autoComplete="off"
              spellCheck={false}
              enterKeyHint="done"
              lang={answerIsTashelhit ? 'shi' : correctAnswer === currentDrill.text_arabic ? 'ar' : 'ca'}
              style={{
                width: '100%',
                padding: window.innerWidth < 768 ? '12px 14px' : '15px 16px',
                fontSize: window.innerWidth < 768 ? '16px' : '18px',
                border: '1px solid var(--border)',
                background: 'var(--surface-2)',
                color: 'var(--text)',
                borderRadius: 'var(--r-md)',
                outline: 'none',
                transition: 'border-color 0.2s, box-shadow 0.2s',
                direction: (test.playback_direction === 'ar-tash' || test.playback_direction === 'tash-ar') ? 'rtl' : 'ltr', // Apply direction to input
                fontFamily: answerIsTashelhit ? 'var(--font-tifinagh)' : 'var(--font-sans)'
              }}
              onFocus={(e) => { e.target.style.borderColor = 'var(--brand-1)'; e.target.style.boxShadow = '0 0 0 3px rgba(99, 102, 241, 0.12)'; e.target.style.background = 'var(--surface)'; }}
              onBlur={(e) => { e.target.style.borderColor = 'var(--border)'; e.target.style.boxShadow = 'none'; e.target.style.background = 'var(--surface-2)'; }}
            />
          </div>

          {/* Hint Display - Compact */}
          {showHint && hintText && (
            <div style={{
              padding: window.innerWidth < 768 ? '12px 14px' : '16px',
              background: 'var(--amber-soft)',
              border: '1px solid var(--amber)',
              borderRadius: 'var(--r-md)',
              marginBottom: window.innerWidth < 768 ? '16px' : '20px',
              fontSize: window.innerWidth < 768 ? '14px' : '15px',
              color: 'var(--text)'
            }}>
              <strong style={{ color: 'var(--amber-strong)' }}>💡 Pista:</strong>{' '}
              <span style={{ fontFamily: answerIsTashelhit ? 'var(--font-tifinagh)' : 'var(--font-sans)' }}>{hintText}</span>
            </div>
          )}

          {/* Correct Answer Display - Compact */}
          {showCorrectAnswer && currentDrill && (
            <div style={{
              padding: window.innerWidth < 768 ? '12px 14px' : '16px',
              background: 'var(--emerald-soft)',
              border: '1px solid var(--emerald)',
              borderRadius: 'var(--r-md)',
              marginBottom: window.innerWidth < 768 ? '16px' : '20px'
            }}>
              <div style={{
                fontSize: window.innerWidth < 768 ? '14px' : '16px',
                fontWeight: 700,
                color: 'var(--emerald)',
                marginBottom: '6px'
              }}>
                ✓ Resposta correcta:
              </div>
              <div style={{
                fontSize: window.innerWidth < 768 ? '16px' : '18px',
                fontWeight: 700,
                color: 'var(--emerald)',
                direction: (correctAnswer === currentDrill.text_arabic) ? 'rtl' : 'ltr',
                fontFamily: answerIsTashelhit ? 'var(--font-tifinagh)' : 'var(--font-sans)'
              }}>
                {correctAnswer}
              </div>
            </div>
          )}

          {/* Feedback after wrong answer - Compact */}
          {attempts > 0 && !showCorrectAnswer && (
            <div style={{
              padding: window.innerWidth < 768 ? '12px 14px' : '16px',
              background: 'var(--rose-soft)',
              border: '1px solid var(--rose)',
              borderRadius: 'var(--r-md)',
              marginBottom: window.innerWidth < 768 ? '16px' : '20px'
            }}>
              <div style={{
                color: 'var(--rose)',
                fontSize: window.innerWidth < 768 ? '14px' : '15px',
                fontWeight: 700,
                marginBottom: '8px'
              }}>
                ✗ No és ben bé això. Intents: {attempts}
              </div>
              <div style={{
                display: 'flex',
                gap: '8px',
                flexWrap: window.innerWidth < 768 ? 'wrap' : 'nowrap'
              }}>
                <button
                  onClick={() => setShowCorrectAnswer(true)}
                  style={{
                    flex: window.innerWidth < 768 ? '1 1 calc(50% - 4px)' : 'none',
                    padding: window.innerWidth < 768 ? '8px 12px' : '8px 16px',
                    fontSize: window.innerWidth < 768 ? '13px' : '14px',
                    background: 'var(--emerald)',
                    color: '#fff',
                    border: 'none',
                    borderRadius: 'var(--r-sm)',
                    cursor: 'pointer',
                    fontWeight: 700,
                  }}
                >
                  👁 Mostra la resposta
                </button>
                <button
                  onClick={handleNextQuestion}
                  style={{
                    flex: window.innerWidth < 768 ? '1 1 calc(50% - 4px)' : 'none',
                    padding: window.innerWidth < 768 ? '8px 12px' : '8px 16px',
                    fontSize: window.innerWidth < 768 ? '13px' : '14px',
                    background: 'var(--sky)',
                    color: '#fff',
                    border: 'none',
                    borderRadius: 'var(--r-sm)',
                    cursor: 'pointer',
                    fontWeight: 700,
                  }}
                >
                  Següent →
                </button>
              </div>
            </div>
          )}

          {/* Action Buttons - Always visible and responsive */}
          <div style={{
            display: 'flex',
            gap: window.innerWidth < 768 ? '8px' : '12px',
            flexWrap: 'wrap'
          }}>
            {!showCorrectAnswer ? (
              <>
                <button
                  onClick={() => handleSubmitAnswer()}
                  disabled={!userAnswer.trim()}
                  style={{
                    flex: window.innerWidth < 768 ? '1 1 100%' : 1,
                    padding: window.innerWidth < 768 ? '14px' : '16px',
                    fontSize: window.innerWidth < 768 ? '15px' : '16px',
                    background: userAnswer.trim() ? 'var(--brand-gradient)' : 'var(--surface-2)',
                    color: userAnswer.trim() ? '#fff' : 'var(--text-muted)',
                    border: userAnswer.trim() ? 'none' : '1px solid var(--border)',
                    borderRadius: 'var(--r-md)',
                    cursor: userAnswer.trim() ? 'pointer' : 'not-allowed',
                    fontWeight: 700,
                    boxShadow: userAnswer.trim() ? 'var(--shadow-brand)' : 'none',
                    minWidth: window.innerWidth < 768 ? '100%' : 'auto'
                  }}
                >
                  ✓ Envia la resposta
                </button>

                {test.hint_level !== 'none' && !showHint && attempts === 0 && (
                  <button
                    onClick={handleRequestHint}
                    style={{
                      flex: window.innerWidth < 768 ? '1 1 calc(50% - 4px)' : 'none',
                      padding: window.innerWidth < 768 ? '12px' : '16px 24px',
                      fontSize: window.innerWidth < 768 ? '14px' : '16px',
                      background: 'var(--amber-soft)',
                      color: 'var(--amber-strong)',
                      border: '1px solid var(--amber)',
                      borderRadius: 'var(--r-md)',
                      cursor: 'pointer',
                      fontWeight: 700,
                      minWidth: window.innerWidth < 768 ? 'calc(50% - 4px)' : 'auto'
                    }}
                  >
                    💡 Pista
                  </button>
                )}

                {test.hint_level === 'partial' && showHint && (
                  <button
                    onClick={handleRequestHint}
                    style={{
                      flex: window.innerWidth < 768 ? '1 1 calc(50% - 4px)' : 'none',
                      padding: window.innerWidth < 768 ? '12px' : '16px 24px',
                      fontSize: window.innerWidth < 768 ? '14px' : '16px',
                      background: 'var(--amber-soft)',
                      color: 'var(--amber-strong)',
                      border: '1px solid var(--amber)',
                      borderRadius: 'var(--r-md)',
                      cursor: 'pointer',
                      fontWeight: 700,
                      minWidth: window.innerWidth < 768 ? 'calc(50% - 4px)' : 'auto'
                    }}
                  >
                    💡 Més pista
                  </button>
                )}

                {/* Show Answer button for wrong attempts */}
                {attempts > 0 && !showCorrectAnswer && (
                  <button
                    onClick={() => setShowCorrectAnswer(true)}
                    style={{
                      flex: window.innerWidth < 768 ? '1 1 calc(50% - 4px)' : 'none',
                      padding: window.innerWidth < 768 ? '12px' : '8px 16px',
                      fontSize: window.innerWidth < 768 ? '13px' : '14px',
                      background: 'var(--brand-2)',
                      color: '#fff',
                      border: 'none',
                      borderRadius: 'var(--r-md)',
                      cursor: 'pointer',
                      fontWeight: 700,
                      minWidth: window.innerWidth < 768 ? 'calc(50% - 4px)' : 'auto'
                    }}
                  >
                    👁 Mostra la resposta
                  </button>
                )}

                {/* Skip button for mobile */}
                {window.innerWidth < 768 && (
                  <button
                    onClick={handleNextQuestion}
                    style={{
                      flex: '1 1 calc(50% - 4px)',
                      padding: '12px',
                      fontSize: '14px',
                      background: 'var(--surface)',
                      color: 'var(--text-soft)',
                      border: '1px solid var(--border)',
                      borderRadius: 'var(--r-md)',
                      cursor: 'pointer',
                      fontWeight: 700,
                    }}
                  >
                    Salta →
                  </button>
                )}
              </>
            ) : (
              <button
                onClick={handleNextQuestion}
                style={{
                  flex: 1,
                  padding: window.innerWidth < 768 ? '14px' : '16px',
                  fontSize: window.innerWidth < 768 ? '15px' : '16px',
                  background: 'var(--brand-gradient)',
                  color: '#fff',
                  border: 'none',
                  borderRadius: 'var(--r-md)',
                  cursor: 'pointer',
                  fontWeight: 700,
                  boxShadow: 'var(--shadow-brand)',
                  minWidth: window.innerWidth < 768 ? '100%' : 'auto'
                }}
              >
                Següent pregunta →
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
