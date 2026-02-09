import { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { API_BASE } from '../config';

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
}

interface Drill {
  id: number;
  text_catalan: string;
  text_tachelhit: string;
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
      const testDrills = drillsResponse.data.filter((d: Drill) => drillIds.includes(d.id));

      // Shuffle drills for random order
      const shuffled = [...testDrills].sort(() => Math.random() - 0.5);
      setDrills(shuffled);

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

  const getHintText = () => {
    if (!currentDrill || !test) return '';

    const correctAnswer = currentDrill.text_tachelhit || '';

    if (test.hint_level === 'none') {
      return '';
    } else if (test.hint_level === 'full_after_tries') {
      if (attempts >= test.hint_tries_before_reveal) {
        return correctAnswer;
      }
      return '';
    } else if (test.hint_level === 'partial') {
      // Progressive hints: show more letters with each hint request
      const basePercentage = test.hint_percentage || 30;
      const progressivePercentage = Math.min(basePercentage + (hintsUsed * 15), 80);
      const numLettersToShow = Math.ceil((correctAnswer.length * progressivePercentage) / 100);

      // Always reveal first letter and spaces
      // let revealed = correctAnswer.split('').map((char, i) => {
      //   if (char === ' ') return ' ';
      //   if (i === 0) return char;
      //   return '_';
      // });

      // Reveal additional random letters
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
    return text.toLowerCase().trim().replace(/\s+/g, ' ');
  };

  const checkAnswer = () => {
    if (!currentDrill) return false;
    const correct = normalizeAnswer(currentDrill.text_tachelhit || '');
    const user = normalizeAnswer(userAnswer);
    return correct === user;
  };

  const handleSubmitAnswer = async (timeUp: boolean = false, skipQuestion: boolean = false) => {
    if (!currentDrill || !test) return;

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
      const audio = new Audio(`${API_BASE}${currentDrill.audio_url}`);
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
                        src={`${API_BASE}${drill.image_url}`}
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
                    <strong style={{ color: '#667eea' }}>Catalan:</strong>
                    <p style={{ margin: '4px 0 0 0', fontSize: '16px' }}>{drill.text_catalan}</p>
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
                        {drill.text_tachelhit}
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

  if (!currentDrill) {
    return <div>Loading question...</div>;
  }

  const hintText = getHintText();

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
                src={`${API_BASE}${currentDrill.image_url}`}
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
          <h1 style={{
            fontSize: '36px',
            textAlign: 'center',
            marginBottom: '40px',
            color: '#333'
          }}>
            {currentDrill.text_catalan}
          </h1>

          {/* Media Section */}
          {(test.question_type === 'audio' || test.question_type === 'video' || test.question_type === 'combined') && (
            <div style={{ textAlign: 'center', marginBottom: '30px' }}>
              {/* Audio playback */}
              {currentDrill.audio_url && (test.question_type === 'audio' || test.question_type === 'combined') && (
                <div style={{ marginBottom: '16px' }}>
                  <button
                    onClick={handlePlayMedia}
                    disabled={playing}
                    style={{
                      padding: '12px 24px',
                      fontSize: '16px',
                      background: playing ? '#ccc' : '#4CAF50',
                      color: 'white',
                      border: 'none',
                      borderRadius: '8px',
                      cursor: playing ? 'not-allowed' : 'pointer',
                      fontWeight: 600,
                    }}
                  >
                    {playing ? '🔊 Playing...' : '🔊 Play Audio'}
                  </button>
                </div>
              )}

              {/* Video playback */}
              {currentDrill.video_url && (test.question_type === 'video' || test.question_type === 'combined') && (
                <div>
                  <video
                    key={currentDrill.id}
                    src={`${API_BASE}${currentDrill.video_url}`}
                    controls
                    style={{
                      width: '100%',
                      maxWidth: '600px',
                      maxHeight: '300px',
                      borderRadius: '8px',
                      boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
                    }}
                  />
                </div>
              )}

              {/* Fallback message if no media available in combined mode */}
              {test.question_type === 'combined' && !currentDrill.audio_url && !currentDrill.video_url && (
                <div style={{
                  padding: '12px',
                  background: '#fff3cd',
                  borderRadius: '8px',
                  fontSize: '14px',
                  color: '#856404'
                }}>
                  💡 No audio/video available for this question
                </div>
              )}
            </div>
          )}

          {/* Answer Input */}
          <div style={{ marginBottom: '20px' }}>
            <label style={{
              display: 'block',
              marginBottom: '10px',
              fontSize: '16px',
              fontWeight: 600,
              color: '#555'
            }}>
              Your answer in Tachelhit:
            </label>
            <input
              type="text"
              value={userAnswer}
              onChange={(e) => setUserAnswer(e.target.value)}
              onKeyPress={(e) => {
                if (e.key === 'Enter') {
                  handleSubmitAnswer();
                }
              }}
              placeholder="Type your answer here..."
              autoFocus
              style={{
                width: '100%',
                padding: '16px',
                fontSize: '18px',
                border: '2px solid #ddd',
                borderRadius: '8px',
                outline: 'none',
                transition: 'border-color 0.2s'
              }}
              onFocus={(e) => e.target.style.borderColor = '#667eea'}
              onBlur={(e) => e.target.style.borderColor = '#ddd'}
            />
          </div>

          {/* Hint Display */}
          {showHint && hintText && (
            <div style={{
              padding: '16px',
              background: '#fff3cd',
              border: '1px solid #ffc107',
              borderRadius: '8px',
              marginBottom: '20px'
            }}>
              <strong>💡 Hint:</strong> {hintText}
            </div>
          )}

          {/* Correct Answer Display */}
          {showCorrectAnswer && currentDrill && (
            <div style={{
              padding: '16px',
              background: '#e8f5e9',
              border: '2px solid #4CAF50',
              borderRadius: '8px',
              marginBottom: '20px'
            }}>
              <strong style={{ color: '#2e7d32' }}>✓ Correct Answer:</strong>
              <p style={{ margin: '8px 0 0 0', fontSize: '18px', fontWeight: 600, color: '#2e7d32' }}>
                {currentDrill.text_tachelhit}
              </p>
            </div>
          )}

          {/* Feedback after wrong answer */}
          {attempts > 0 && !showCorrectAnswer && (
            <div style={{
              padding: '16px',
              background: '#ffebee',
              border: '1px solid #ff4444',
              borderRadius: '8px',
              marginBottom: '20px'
            }}>
              <div style={{ marginBottom: '8px', color: '#c62828', fontSize: '15px', fontWeight: 600 }}>
                ✗ Not quite right. Attempts: {attempts}
              </div>
              <button
                onClick={() => setShowCorrectAnswer(true)}
                style={{
                  padding: '8px 16px',
                  fontSize: '14px',
                  background: '#4CAF50',
                  color: 'white',
                  border: 'none',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  fontWeight: 600,
                  marginRight: '8px'
                }}
              >
                👁 Show Answer
              </button>
              <button
                onClick={handleNextQuestion}
                style={{
                  padding: '8px 16px',
                  fontSize: '14px',
                  background: '#2196F3',
                  color: 'white',
                  border: 'none',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  fontWeight: 600,
                }}
              >
                Next Question →
              </button>
            </div>
          )}

          {/* Action Buttons */}
          <div style={{ display: 'flex', gap: '12px' }}>
            {!showCorrectAnswer ? (
              <>
                <button
                  onClick={() => handleSubmitAnswer()}
                  disabled={!userAnswer.trim()}
                  style={{
                    flex: 1,
                    padding: '16px',
                    fontSize: '16px',
                    background: userAnswer.trim() ? '#4CAF50' : '#ccc',
                    color: 'white',
                    border: 'none',
                    borderRadius: '8px',
                    cursor: userAnswer.trim() ? 'pointer' : 'not-allowed',
                    fontWeight: 600,
                  }}
                >
                  ✓ Submit Answer
                </button>

                {test.hint_level !== 'none' && !showHint && attempts === 0 && (
                  <button
                    onClick={handleRequestHint}
                    style={{
                      padding: '16px 24px',
                      fontSize: '16px',
                      background: '#FFC107',
                      color: '#333',
                      border: 'none',
                      borderRadius: '8px',
                      cursor: 'pointer',
                      fontWeight: 600,
                    }}
                  >
                    💡 Hint
                  </button>
                )}

                {test.hint_level === 'partial' && showHint && (
                  <button
                    onClick={handleRequestHint}
                    style={{
                      padding: '16px 24px',
                      fontSize: '16px',
                      background: '#FFC107',
                      color: '#333',
                      border: 'none',
                      borderRadius: '8px',
                      cursor: 'pointer',
                      fontWeight: 600,
                    }}
                  >
                    💡 More Hint
                  </button>
                )}
              </>
            ) : (
              <button
                onClick={handleNextQuestion}
                style={{
                  flex: 1,
                  padding: '16px',
                  fontSize: '16px',
                  background: '#2196F3',
                  color: 'white',
                  border: 'none',
                  borderRadius: '8px',
                  cursor: 'pointer',
                  fontWeight: 600,
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
