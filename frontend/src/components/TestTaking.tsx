import { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { API_BASE, getMediaUrl } from '../config';

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
  text_catalan: string;
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

      // Load drills
      const drillIds = testResponse.data.drill_ids.split(',').map((id: string) => parseInt(id));
      const drillsResponse = await axios.get(`${API_BASE}/drills/`);
      // Filter drills based on IDs and maintain order
      const testDrills = drillIds.map((id: number) => drillsResponse.data.find((d: Drill) => d.id === id)).filter((d: Drill | undefined): d is Drill => d !== undefined);

      // Removed shuffling to respect the order from drill_ids
      setDrills(testDrills);

      // Initialize timer if needed
      if (testResponse.data.time_limit_seconds > 0) {
        setTimeRemaining(testResponse.data.time_limit_seconds);
      }

      setTestStartTime(Date.now());
      setQuestionStartTime(Date.now());
    } catch (error) {
      console.error('Error loading test:', error);
      alert('Failed to load test');
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

      const indices = new Set<number>([0]); // First letter already revealed
      while (indices.size < numLettersToShow && indices.size < correctAnswer.length) {
        const randomIndex = Math.floor(Math.random() * correctAnswer.length);
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
    let normalized = text.toLowerCase();
    normalized = normalized.trim();
    normalized = normalized.split(' ').filter(s => s !== '').join(' ');
    return normalized;
  };

  const checkAnswer = () => {
    if (!correctAnswer) return false;
    const correct = normalizeAnswer(correctAnswer);
    const user = normalizeAnswer(userAnswer);
    return correct === user;
  };

  const handleSubmitAnswer = async (timeUp: boolean = false, skipQuestion: boolean = false) => {
    if (!currentDrill || !test || !correctAnswer) return;

    const isCorrect = checkAnswer();
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
        user_name: null,
        score: score,
        time_taken_seconds: totalTime,
        total_questions: results.length,
        correct_answers: correctAnswers,
        question_results: JSON.stringify(results)
      });

      setTestCompleted(true);
    } catch (error) {
      console.error('Error submitting test attempt:', error);
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
      // Create new audio element each time for reliability
      const audio = new Audio(getMediaUrl(currentDrill.audio_url));
      audioRef.current = audio;

      setPlaying(true);

      audio.onended = () => {
        setPlaying(false);
      };

      audio.onerror = (e) => {
        console.error('Audio playback error:', e);
        setPlaying(false);
        alert('Failed to play audio. Please check if the audio file exists.');
      };

      await audio.play();
      console.log('Audio playing:', currentDrill.audio_url);
    } catch (error) {
      console.error('Error playing audio:', error);
      setPlaying(false);
      alert('Failed to play audio');
    }
  };

  if (!test || drills.length === 0) {
    return (
      <div style={{ padding: '40px', textAlign: 'center' }}>
        <p>Loading test...</p>
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
          height: '100vh',
          display: 'flex',
          flexDirection: 'column',
          background: '#f5f5f5'
        }}>
          {/* Header */}
          <div style={{
            padding: '20px',
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            color: 'white'
          }}>
            <h2 style={{ margin: 0 }}>Review Your Answers</h2>
            <p style={{ margin: '5px 0 0 0', opacity: 0.9 }}>
              Score: {Math.round(score)}% ({correctAnswers}/{questionResults.length} correct)
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

              return (
                <div key={index} style={{
                  background: 'white',
                  padding: '24px',
                  borderRadius: '12px',
                  marginBottom: '16px',
                  border: result.correct ? '2px solid #4CAF50' : '2px solid #ff4444',
                  boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '16px' }}>
                    <h3 style={{ margin: 0, fontSize: '18px', color: '#333' }}>
                      Question {index + 1}
                    </h3>
                    <span style={{
                      padding: '4px 12px',
                      borderRadius: '12px',
                      fontSize: '14px',
                      fontWeight: 'bold',
                      background: result.correct ? '#4CAF50' : '#ff4444',
                      color: 'white'
                    }}>
                      {result.correct ? '✓ Correct' : '✗ Incorrect'}
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
                          borderRadius: '8px',
                          objectFit: 'contain'
                        }}
                      />
                    </div>
                  )}

                  <div style={{ marginBottom: '12px' }}>
                    <strong style={{ color: '#667eea' }}>Question:</strong>
                    <p style={{ margin: '4px 0 0 0', fontSize: '16px' }}>{reviewQuestionText}</p>
                  </div>

                  <div style={{ marginBottom: '12px' }}>
                    <strong style={{ color: result.correct ? '#4CAF50' : '#ff4444' }}>Your Answer:</strong>
                    <p style={{ margin: '4px 0 0 0', fontSize: '16px', fontWeight: 500 }}>
                      {result.user_answer || '(no answer)'}
                    </p>
                  </div>

                  {!result.correct && (
                    <div style={{
                      background: '#e8f5e9',
                      padding: '12px',
                      borderRadius: '8px',
                      marginBottom: '12px'
                    }}>
                      <strong style={{ color: '#2e7d32' }}>Correct Answer:</strong>
                      <p style={{ margin: '4px 0 0 0', fontSize: '16px', fontWeight: 500, color: '#2e7d32' }}>
                        {reviewCorrectAnswerText}
                      </p>
                    </div>
                  )}

                  <div style={{ fontSize: '13px', color: '#999', marginTop: '12px' }}>
                    Attempts: {result.attempts} • Time: {result.time_spent}s
                  </div>
                </div>
              );
            })}
          </div>

          {/* Footer Buttons */}
          <div style={{
            padding: '20px',
            background: 'white',
            borderTop: '1px solid #e0e0e0',
            display: 'flex',
            gap: '12px',
            justifyContent: 'center'
          }}>
            <button
              onClick={() => setReviewMode(false)}
              style={{
                padding: '12px 24px',
                fontSize: '15px',
                background: '#667eea',
                color: 'white',
                border: 'none',
                borderRadius: '8px',
                cursor: 'pointer',
                fontWeight: 600,
              }}
            >
              Back to Results
            </button>
            <button
              onClick={onExit}
              style={{
                padding: '12px 24px',
                fontSize: '15px',
                background: '#999',
                color: 'white',
                border: 'none',
                borderRadius: '8px',
                cursor: 'pointer',
                fontWeight: 600,
              }}
            >
              Exit
            </button>
          </div>
        </div>
      );
    }

    return (
      <div style={{
        height: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
      }}>
        <div style={{
          background: 'white',
          padding: '40px',
          borderRadius: '16px',
          maxWidth: '600px',
          textAlign: 'center',
          boxShadow: '0 10px 40px rgba(0,0,0,0.2)'
        }}>
          <h1 style={{
            fontSize: '48px',
            margin: '0 0 20px 0',
            color: passed ? '#4CAF50' : '#ff4444'
          }}>
            {passed ? '🎉 Passed!' : '📚 Keep Practicing'}
          </h1>

          <h2 style={{ fontSize: '64px', margin: '20px 0', color: '#333' }}>
            {Math.round(score)}%
          </h2>

          <p style={{ fontSize: '18px', color: '#666', marginBottom: '30px' }}>
            {correctAnswers} out of {questionResults.length} correct
          </p>

          <div style={{
            background: '#f8f9fa',
            padding: '20px',
            borderRadius: '8px',
            marginBottom: '30px'
          }}>
            <div style={{ marginBottom: '10px' }}>
              <strong>Time Taken:</strong> {Math.floor((Date.now() - testStartTime) / 1000)}s
            </div>
            <div>
              <strong>Passing Score:</strong> {test.passing_score}%
            </div>
          </div>

          <div style={{ display: 'flex', gap: '12px', justifyContent: 'center' }}>
            <button
              onClick={() => setReviewMode(true)}
              style={{
                padding: '14px 32px',
                fontSize: '16px',
                background: '#4CAF50',
                color: 'white',
                border: 'none',
                borderRadius: '8px',
                cursor: 'pointer',
                fontWeight: 600,
              }}
            >
              📝 Review Answers
            </button>
            <button
              onClick={onExit}
              style={{
                padding: '14px 32px',
                fontSize: '16px',
                background: '#667eea',
                color: 'white',
                border: 'none',
                borderRadius: '8px',
                cursor: 'pointer',
                fontWeight: 600,
              }}
            >
              Back to Tests
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (!currentDrill || !questionText || !correctAnswer) {
    return <div>Loading question...</div>;
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
          <h2 style={{ margin: 0, fontSize: '20px' }}>{test.title}</h2>
          <p style={{ margin: '5px 0 0 0', fontSize: '14px', opacity: 0.9 }}>
            Question {currentQuestionIndex + 1} of {drills.length}
          </p>
        </div>
        <div style={{ textAlign: 'right' }}>
          {timeRemaining !== null && (
            <div style={{
              fontSize: '24px',
              fontWeight: 'bold',
              color: timeRemaining < 10 ? '#ff4444' : 'white'
            }}>
              ⏱ {timeRemaining}s
            </div>
          )}
          <button
            onClick={() => {
              if (confirm('Are you sure you want to exit? Your progress will be lost.')) {
                onExit();
              }
            }}
            style={{
              marginTop: '10px',
              padding: '6px 12px',
              background: 'rgba(255,255,255,0.2)',
              color: 'white',
              border: '1px solid white',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '12px'
            }}
          >
            Exit Test
          </button>
        </div>
      </div>

      {/* Question Area */}
      <div style={{
        flex: 1,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '40px'
      }}>
        <div style={{
          background: 'white',
          padding: '50px',
          borderRadius: '16px',
          maxWidth: '800px',
          width: '100%',
          boxShadow: '0 10px 40px rgba(0,0,0,0.2)'
        }}>
          {/* Image if available */}
          {currentDrill.image_url && (
            <div style={{ marginBottom: '30px', textAlign: 'center' }}>
              <img
                src={getMediaUrl(currentDrill.image_url)}
                alt="Visual hint"
                style={{
                  maxWidth: '100%',
                  maxHeight: '200px',
                  borderRadius: '8px',
                  objectFit: 'contain'
                }}
              />
            </div>
          )}

          {/* Question */}
          <div style={{ marginBottom: '20px' }}>
            <div style={{
              fontSize: window.innerWidth < 768 ? '24px' : '36px',
              textAlign: 'center',
              color: '#333',
              fontWeight: 600,
              lineHeight: 1.3,
              direction: isArabicQuestion ? 'rtl' : 'ltr'
            }}>
              {mainQuestionDisplay}
            </div>
            {secondaryQuestionDisplay && (
              <div style={{
                fontSize: window.innerWidth < 768 ? '14px' : '16px',
                textAlign: 'center',
                color: '#666',
                marginTop: '8px',
                padding: '8px',
                background: '#f8f9fa',
                borderRadius: '6px',
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
                <button
                  onClick={handlePlayMedia}
                  disabled={playing}
                  style={{
                    padding: window.innerWidth < 768 ? '10px 16px' : '12px 24px',
                    fontSize: window.innerWidth < 768 ? '14px' : '16px',
                    background: playing ? '#ccc' : '#4CAF50',
                    color: 'white',
                    border: 'none',
                    borderRadius: '8px',
                    cursor: playing ? 'not-allowed' : 'pointer',
                    fontWeight: 600,
                    flex: window.innerWidth < 768 ? '1' : 'none',
                    width: window.innerWidth < 768 ? '100%' : 'auto',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '8px'
                  }}
                >
                  <span>{playing ? '🔊' : '🔊'}</span>
                  <span>{playing ? 'Playing...' : 'Play Audio'}</span>
                </button>
              )}

              {/* Video playback */}
              {currentDrill.video_url && (test.question_type === 'video' || test.question_type === 'combined') && (
                <button
                  onClick={() => {
                    const videoUrl = getMediaUrl(currentDrill.video_url);
                    window.open(videoUrl, '_blank');
                  }}
                  style={{
                    padding: window.innerWidth < 768 ? '10px 16px' : '12px 24px',
                    fontSize: window.innerWidth < 768 ? '14px' : '16px',
                    background: '#2196F3',
                    color: 'white',
                    border: 'none',
                    borderRadius: '8px',
                    cursor: 'pointer',
                    fontWeight: 600,
                    flex: window.innerWidth < 768 ? '1' : 'none',
                    width: window.innerWidth < 768 ? '100%' : 'auto',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '8px'
                  }}
                >
                  <span>🎥</span>
                  <span>Open Video</span>
                </button>
              )}

              {/* Fallback message if no media available in combined mode */}
              {test.question_type === 'combined' && !currentDrill.audio_url && !currentDrill.video_url && (
                <div style={{
                  padding: '10px',
                  background: '#fff3cd',
                  borderRadius: '8px',
                  fontSize: window.innerWidth < 768 ? '12px' : '14px',
                  color: '#856404',
                  width: '100%'
                }}>
                  💡 No audio/video available
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
                fontWeight: 600,
                color: '#555',
                direction: (test.playback_direction === 'ar-tash' || test.playback_direction === 'tash-ar') ? 'rtl' : 'ltr' // Apply direction to label
              }}>
                Your answer in {correctAnswer === currentDrill.text_tachelhit ? 'Tachelhit' : correctAnswer === currentDrill.text_catalan ? 'Catalan' : 'Arabic'}:
              </label>
              {timeRemaining !== null && (
                <div style={{
                  fontSize: window.innerWidth < 768 ? '14px' : '16px',
                  fontWeight: 'bold',
                  color: timeRemaining < 10 ? '#ff4444' : '#667eea',
                  background: '#f0f4ff',
                  padding: '4px 10px',
                  borderRadius: '12px'
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
              placeholder='Type here...'
              autoFocus
              style={{
                width: '100%',
                padding: window.innerWidth < 768 ? '12px' : '16px',
                fontSize: window.innerWidth < 768 ? '16px' : '18px',
                border: '2px solid #ddd',
                borderRadius: '8px',
                outline: 'none',
                transition: 'border-color 0.2s',
                direction: (test.playback_direction === 'ar-tash' || test.playback_direction === 'tash-ar') ? 'rtl' : 'ltr' // Apply direction to input
              }}
              onFocus={(e) => e.target.style.borderColor = '#667eea'}
              onBlur={(e) => e.target.style.borderColor = '#ddd'}
            />
          </div>

          {/* Hint Display - Compact */}
          {showHint && hintText && (
            <div style={{
              padding: window.innerWidth < 768 ? '12px' : '16px',
              background: '#fff3cd',
              border: '1px solid #ffc107',
              borderRadius: '8px',
              marginBottom: window.innerWidth < 768 ? '16px' : '20px',
              fontSize: window.innerWidth < 768 ? '14px' : '15px'
            }}>
              <strong>💡 Hint:</strong> {hintText}
            </div>
          )}

          {/* Correct Answer Display - Compact */}
          {showCorrectAnswer && currentDrill && (
            <div style={{
              padding: window.innerWidth < 768 ? '12px' : '16px',
              background: '#e8f5e9',
              border: '2px solid #4CAF50',
              borderRadius: '8px',
              marginBottom: window.innerWidth < 768 ? '16px' : '20px'
            }}>
              <div style={{
                fontSize: window.innerWidth < 768 ? '14px' : '16px',
                fontWeight: 600,
                color: '#2e7d32',
                marginBottom: '6px'
              }}>
                ✓ Correct Answer:
              </div>
              <div style={{
                fontSize: window.innerWidth < 768 ? '16px' : '18px',
                fontWeight: 600,
                color: '#2e7d32',
                direction: (correctAnswer === currentDrill.text_arabic) ? 'rtl' : 'ltr'
              }}>
                {correctAnswer}
              </div>
            </div>
          )}

          {/* Feedback after wrong answer - Compact */}
          {attempts > 0 && !showCorrectAnswer && (
            <div style={{
              padding: window.innerWidth < 768 ? '12px' : '16px',
              background: '#ffebee',
              border: '1px solid #ff4444',
              borderRadius: '8px',
              marginBottom: window.innerWidth < 768 ? '16px' : '20px'
            }}>
              <div style={{
                color: '#c62828',
                fontSize: window.innerWidth < 768 ? '14px' : '15px',
                fontWeight: 600,
                marginBottom: '8px'
              }}>
                ✗ Not quite right. Attempts: {attempts}
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
                    background: '#4CAF50',
                    color: 'white',
                    border: 'none',
                    borderRadius: '6px',
                    cursor: 'pointer',
                    fontWeight: 600,
                  }}
                >
                  👁 Show Answer
                </button>
                <button
                  onClick={handleNextQuestion}
                  style={{
                    flex: window.innerWidth < 768 ? '1 1 calc(50% - 4px)' : 'none',
                    padding: window.innerWidth < 768 ? '8px 12px' : '8px 16px',
                    fontSize: window.innerWidth < 768 ? '13px' : '14px',
                    background: '#2196F3',
                    color: 'white',
                    border: 'none',
                    borderRadius: '6px',
                    cursor: 'pointer',
                    fontWeight: 600,
                  }}
                >
                  Next →
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
                    background: userAnswer.trim() ? '#4CAF50' : '#ccc',
                    color: 'white',
                    border: 'none',
                    borderRadius: '8px',
                    cursor: userAnswer.trim() ? 'pointer' : 'not-allowed',
                    fontWeight: 600,
                    minWidth: window.innerWidth < 768 ? '100%' : 'auto'
                  }}
                >
                  ✓ Submit Answer
                </button>

                {test.hint_level !== 'none' && !showHint && attempts === 0 && (
                  <button
                    onClick={handleRequestHint}
                    style={{
                      flex: window.innerWidth < 768 ? '1 1 calc(50% - 4px)' : 'none',
                      padding: window.innerWidth < 768 ? '12px' : '16px 24px',
                      fontSize: window.innerWidth < 768 ? '14px' : '16px',
                      background: '#FFC107',
                      color: '#333',
                      border: 'none',
                      borderRadius: '8px',
                      cursor: 'pointer',
                      fontWeight: 600,
                      minWidth: window.innerWidth < 768 ? 'calc(50% - 4px)' : 'auto'
                    }}
                  >
                    💡 Hint
                  </button>
                )}

                {test.hint_level === 'partial' && showHint && (
                  <button
                    onClick={handleRequestHint}
                    style={{
                      flex: window.innerWidth < 768 ? '1 1 calc(50% - 4px)' : 'none',
                      padding: window.innerWidth < 768 ? '12px' : '16px 24px',
                      fontSize: window.innerWidth < 768 ? '14px' : '16px',
                      background: '#FFC107',
                      color: '#333',
                      border: 'none',
                      borderRadius: '8px',
                      cursor: 'pointer',
                      fontWeight: 600,
                      minWidth: window.innerWidth < 768 ? 'calc(50% - 4px)' : 'auto'
                    }}
                  >
                    💡 More Hint
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
                      background: '#9C27B0',
                      color: 'white',
                      border: 'none',
                      borderRadius: '8px',
                      cursor: 'pointer',
                      fontWeight: 600,
                      minWidth: window.innerWidth < 768 ? 'calc(50% - 4px)' : 'auto'
                    }}
                  >
                    👁 Show Answer
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
                      background: '#666',
                      color: 'white',
                      border: 'none',
                      borderRadius: '8px',
                      cursor: 'pointer',
                      fontWeight: 600,
                    }}
                  >
                    Skip →
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
                  background: '#2196F3',
                  color: 'white',
                  border: 'none',
                  borderRadius: '8px',
                  cursor: 'pointer',
                  fontWeight: 600,
                  minWidth: window.innerWidth < 768 ? '100%' : 'auto'
                }}
              >
                Continue to Next Question →
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
