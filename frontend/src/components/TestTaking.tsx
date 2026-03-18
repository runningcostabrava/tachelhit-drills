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
      const testDrills = drillIds.map((id: number) => drillsResponse.data.find((d: Drill) => d.id === id)).filter((d): d is Drill => d !== undefined);
      
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
    return text.toLowerCase().trim().replace(/\s+/g, ' ');
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
                      {result.correct ? '✓ Correct' : '✗ Incorrect'}శ్వత్The user is still encountering a Vercel deployment error in `frontend/src/components/TestTaking.tsx` at line 495. The error `TS1109: Expression expected.` indicates an incomplete or invalid JSX expression. This is due to an incomplete `return` statement in the `if (testCompleted)` block. The previous `write_to_file` command for `TestTaking.tsx` resulted in a corrupted file. I need to fully reconstruct and rewrite the file. I have already read the file to ensure I have its current (erroneous) content. I will now use `write_to_file` again to provide the *complete and corrected content* for `frontend/src/components/TestTaking.tsx`. This corrected content includes the full JSX for the test results summary within the `if (testCompleted)` block, which was previously truncated. I will also incorporate RTL text direction for Arabic questions and answers where appropriate. This is a crucial step to correctly implement the user's requested features.   <execute_command>   print(default_api.execute_command(command = 