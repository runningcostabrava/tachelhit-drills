import { useState, useRef, useEffect } from 'react';

export default function MediaRecorderTest() {
  const [recording, setRecording] = useState(false);
  const [audioURL, setAudioURL] = useState('');
  const [supportedVoices, setSupportedVoices] = useState<SpeechSynthesisVoice[]>([]);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  useEffect(() => {
    // Function to load voices
    const loadVoices = () => {
      const voices = speechSynthesis.getVoices();
      setSupportedVoices(voices);
      console.log('Available voices:', voices);
      // Check for Tachelhit specific voices
      const tachelhitVoices = voices.filter(voice => voice.lang.startsWith('shi') || voice.name.toLowerCase().includes('tachelhit'));
      console.log('Tachelhit-like voices found:', tachelhitVoices);
    };

    // Load voices immediately if they are already available
    if (speechSynthesis.getVoices().length > 0) {
      loadVoices();
    } else {
      // Otherwise, wait for the 'voiceschanged' event
      speechSynthesis.onvoiceschanged = loadVoices;
    }

    return () => {
      speechSynthesis.onvoiceschanged = null;
    };
  }, []);

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorderRef.current = new MediaRecorder(stream);
      mediaRecorderRef.current.ondataavailable = (e) => {
        if (e.data.size > 0) {
          chunksRef.current.push(e.data);
        }
      };
      mediaRecorderRef.current.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' });
        const url = URL.createObjectURL(blob);
        setAudioURL(url);
        chunksRef.current = [];
      };
      mediaRecorderRef.current.start();
      setRecording(true);
    } catch (error) {
      console.error('Error starting recording:', error);
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current) {
      mediaRecorderRef.current.stop();
      setRecording(false);
    }
  };

  const speakText = (text: string, lang: string, rate: number = 1) => {
    if ('speechSynthesis' in window) {
      speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = lang;
      utterance.rate = rate;
      utterance.volume = 1.0;
      
      // Try to find a specific voice if needed, otherwise use default
      const voice = supportedVoices.find(v => v.lang === lang) || supportedVoices.find(v => v.lang.startsWith(lang.substring(0,2)));
      if (voice) {
        utterance.voice = voice;
      }

      speechSynthesis.speak(utterance);
      
      utterance.onend = () => {
        console.log('Speech finished for:', text);
      };
      
      utterance.onerror = (event) => {
        console.error('Error speaking:', event);
        alert(`Error al reproducir la voz para "${text}". Asegúrate de que el volumen esté activado y el idioma (${lang}) sea compatible.`);
      };
    } else {
      alert('La síntesis de voz no está disponible en este dispositivo.');
    }
  };

  return (
    <div>
      <h2>Media Recorder Test</h2>
      {!recording ? (
        <button onClick={startRecording}>Start Recording</button>
      ) : (
        <button onClick={stopRecording}>Stop Recording</button>
      )}
      {audioURL && <audio src={audioURL} controls />}

      <h3>Speech Synthesis Test</h3>
      <button onClick={() => speakText('Hello in Catalan', 'ca-ES', 1.5)}>
        Speak Catalan (Fast)
      </button>
      <button onClick={() => speakText('Hello in Tachelhit', 'shi', 1)}>
        Speak Tachelhit (shi)
      </button>
      <button onClick={() => speakText('Hello in Arabic', 'ar-SA', 1)}>
        Speak Arabic (ar-SA)
      </button>

      <h3>Available Voices ({supportedVoices.length})</h3>
      <ul>
        {supportedVoices.map(voice => (
          <li key={voice.name}>
            {voice.name} ({voice.lang}) - Default: {voice.default ? 'Yes' : 'No'}
          </li>
        ))}
      </ul>
    </div>
  );
}
