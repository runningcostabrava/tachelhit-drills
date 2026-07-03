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
      const tachelhitVoices = voices.filter(voice => voice.lang.startsWith('shi') || (voice.name?.toLowerCase() || '').includes('tachelhit'));
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
      const voice = supportedVoices.find(v => v.lang === lang) || supportedVoices.find(v => v.lang.startsWith(lang.substring(0, 2)));
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
    <div style={{ minHeight: '100vh', background: 'var(--bg)', padding: '32px', fontFamily: 'var(--font-sans)' }}>
      <div style={{ maxWidth: '720px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '20px' }}>
        <h2 style={{ margin: 0 }}>Media Recorder Test</h2>

        <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--r-xl)', boxShadow: 'var(--shadow-sm)', padding: '20px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
          {!recording ? (
            <button onClick={startRecording} style={{ alignSelf: 'flex-start', background: 'var(--rose)', color: 'white', borderRadius: 'var(--r-md)', padding: '11px 18px', fontWeight: 700 }}>● Start Recording</button>
          ) : (
            <button onClick={stopRecording} style={{ alignSelf: 'flex-start', background: 'var(--surface-2)', color: 'var(--text)', border: '1px solid var(--border)', borderRadius: 'var(--r-md)', padding: '11px 18px', fontWeight: 700 }}>■ Stop Recording</button>
          )}
          {audioURL && <audio src={audioURL} controls style={{ width: '100%' }} />}
        </div>

        <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--r-xl)', boxShadow: 'var(--shadow-sm)', padding: '20px' }}>
          <h3 style={{ marginTop: 0, marginBottom: '14px' }}>Speech Synthesis Test</h3>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px' }}>
            <button onClick={() => speakText('Hello in Catalan', 'ca-ES', 1.5)} style={{ background: 'var(--brand-gradient)', color: 'white', borderRadius: 'var(--r-md)', padding: '10px 16px', fontWeight: 700, boxShadow: 'var(--shadow-brand)' }}>
              Speak Catalan (Fast)
            </button>
            <button onClick={() => speakText('Hello in Tachelhit', 'shi', 1)} style={{ background: 'var(--brand-gradient)', color: 'white', borderRadius: 'var(--r-md)', padding: '10px 16px', fontWeight: 700, boxShadow: 'var(--shadow-brand)', fontFamily: 'var(--font-tifinagh)' }}>
              Speak Tachelhit (shi)
            </button>
            <button onClick={() => speakText('Hello in Arabic', 'ar-SA', 1)} style={{ background: 'var(--brand-gradient)', color: 'white', borderRadius: 'var(--r-md)', padding: '10px 16px', fontWeight: 700, boxShadow: 'var(--shadow-brand)' }}>
              Speak Arabic (ar-SA)
            </button>
          </div>
        </div>

        <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--r-xl)', boxShadow: 'var(--shadow-sm)', padding: '20px' }}>
          <h3 style={{ marginTop: 0, marginBottom: '14px' }}>Available Voices ({supportedVoices.length})</h3>
          <ul style={{ margin: 0, paddingLeft: '18px', color: 'var(--text-soft)', display: 'flex', flexDirection: 'column', gap: '6px' }}>
            {supportedVoices.map(voice => (
              <li key={voice.name}>
                {voice.name} ({voice.lang}) - Default: {voice.default ? 'Yes' : 'No'}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
