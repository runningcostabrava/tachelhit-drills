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
  const [sessionStarted, setSessionStarted] = useState(false);
  const [autoPlayEnabled, setAutoPlayEnabled] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const speechSynthRef = useRef<SpeechSynthesisUtterance | null>(null);

  const currentDrill = drills[currentIndex];
  const isMobile = window.innerWidth < 768;

  // Limpiar al cambiar de drill
  useEffect(() => {
    setPlayCount(0);
    setIsPlaying(false);
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
    if (speechSynthRef.current) {
      speechSynthesis.cancel();
      speechSynthRef.current = null;
    }
  }, [currentIndex]);

  // Efecto para reproducción automática cuando autoPlayEnabled es true
  useEffect(() => {
    if (!autoPlayEnabled || !sessionStarted) return;
    if (!currentDrill?.audio_url) {
      // Si no hay audio, avanzar después de un tiempo
      const timer = setTimeout(() => {
        goToNextDrill();
      }, 1500);
      return () => clearTimeout(timer);
    }
    
    if (playCount < 2) {
      // Esperar un momento antes de reproducir
      const timer = setTimeout(() => {
        playCurrentAudio();
      }, 300);
      return () => clearTimeout(timer);
    } else if (playCount >= 2) {
      // Después de 2 reproducciones, avanzar
      const timer = setTimeout(() => {
        goToNextDrill();
      }, 800);
      return () => clearTimeout(timer);
    }
  }, [currentIndex, playCount, autoPlayEnabled, sessionStarted, currentDrill]);

  const playCurrentAudio = () => {
    if (!currentDrill?.audio_url) {
      setPlayCount(2);
      return;
    }
    
    // Limpiar audio anterior
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
    
    const audio = new Audio(getMediaUrl(currentDrill.audio_url));
    audioRef.current = audio;
    setIsPlaying(true);
    
    // Configurar eventos antes de reproducir
    const handleEnded = () => {
      setIsPlaying(false);
      setPlayCount(prev => prev + 1);
      audio.removeEventListener('ended', handleEnded);
      audio.removeEventListener('error', handleError);
    };
    
    const handleError = () => {
      setIsPlaying(false);
      setPlayCount(prev => prev + 1);
      audio.removeEventListener('ended', handleEnded);
      audio.removeEventListener('error', handleError);
    };
    
    audio.addEventListener('ended', handleEnded);
    audio.addEventListener('error', handleError);
    
    const playPromise = audio.play();
    if (playPromise !== undefined) {
      playPromise.catch(error => {
        console.error('Error al reproducir audio:', error);
        setIsPlaying(false);
        // Si falla, desactivar autoPlay y pedir interacción manual
        setAutoPlayEnabled(false);
        if (/iPad|iPhone|iPod/.test(navigator.userAgent)) {
          alert('La reproducción automática no está disponible en iOS. Usa los botones manuales.');
        }
        // Aún así, contar como reproducido para no bloquear el flujo
        setPlayCount(prev => prev + 1);
      });
    }
  };

  const goToNextDrill = () => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
    if (speechSynthRef.current) {
      speechSynthesis.cancel();
      speechSynthRef.current = null;
    }
    
    if (currentIndex < drills.length - 1) {
      setCurrentIndex(currentIndex + 1);
    } else {
      onExit();
    }
  };

  const handleStartSession = () => {
    // En iOS, necesitamos una interacción de usuario para activar el audio
    // Creamos un audio silencioso y lo reproducimos para desbloquear la API de audio
    const unlockAudio = () => {
      const silentAudio = new Audio('data:audio/wav;base64,UklGRigAAABXQVZFZm10IBIAAAABAAEARKwAAIhYAQACABAAZGF0YQQ=');
      silentAudio.volume = 0.01;
      silentAudio.play().then(() => {
        silentAudio.pause();
        silentAudio.remove();
        // Ahora iniciamos la sesión
        setSessionStarted(true);
        setAutoPlayEnabled(true);
        // Reproducir el primer audio inmediatamente
        if (currentDrill?.audio_url) {
          playCurrentAudio();
        }
      }).catch(error => {
        console.error('No se pudo desbloquear audio:', error);
        // Si falla, iniciamos de todos modos pero con autoPlay desactivado
        setSessionStarted(true);
        setAutoPlayEnabled(false);
        alert('No se pudo activar la reproducción automática. Usa los botones manuales.');
      });
    };
    
    unlockAudio();
  };

  const handlePlayAudio = () => {
    playCurrentAudio();
  };

  const handleSpeakCatalan = () => {
    if (!currentDrill?.text_catalan) return;
    
    if ('speechSynthesis' in window) {
      speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(currentDrill.text_catalan);
      utterance.lang = 'ca-ES';
      utterance.rate = 1.0;
      utterance.volume = 1.0;
      speechSynthRef.current = utterance;
      speechSynthesis.speak(utterance);
      
      utterance.onend = () => {
        speechSynthRef.current = null;
      };
    } else {
      alert('La síntesis de voz no está disponible en este dispositivo.');
    }
  };

  const handleNext = () => {
    goToNextDrill();
  };

  const handlePrev = () => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
    if (speechSynthRef.current) {
      speechSynthesis.cancel();
      speechSynthRef.current = null;
    }
    
    if (currentIndex > 0) {
      setCurrentIndex(currentIndex - 1);
    }
  };

  const handleReplay = () => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
    if (speechSynthRef.current) {
      speechSynthesis.cancel();
      speechSynthRef.current = null;
    }
    setPlayCount(0);
    setIsPlaying(false);
  };

  // Si la sesión no ha comenzado, mostrar pantalla de inicio
  if (!sessionStarted) {
    return (
      <div style={{
        height: '100vh',
        display: 'flex',
        flexDirection: 'column',
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        overflow: 'hidden',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '20px',
        textAlign: 'center'
      }}>
        <div style={{
          background: 'white',
          padding: '30px',
          borderRadius: '16px',
          maxWidth: '500px',
          width: '100%',
          boxShadow: '0 10px 40px rgba(0,0,0,0.2)'
        }}>
          <h2 style={{ color: '#333', marginBottom: '15px' }}>Sesión de Práctica</h2>
          <p style={{ color: '#666', marginBottom: '25px' }}>
            Esta sesión reproducirá cada drill dos veces y pasará automáticamente al siguiente.
            Para iOS, es posible que necesites permitir la reproducción de audio al hacer clic en "Iniciar Sesión Automática".
            Si la reproducción automática no funciona, usa el "Control Manual".
          </p>
          <button
            onClick={handleStartSession}
            style={{
              padding: '15px 30px',
              fontSize: '18px',
              background: '#4CAF50',
              color: 'white',
              border: 'none',
              borderRadius: '8px',
              cursor: 'pointer',
              fontWeight: 600,
              marginBottom: '15px',
              width: '100%'
            }}
          >
            🎵 Iniciar Sesión Automática
          </button>
          <button
            onClick={() => setSessionStarted(true)}
            style={{
              padding: '12px 24px',
              fontSize: '16px',
              background: '#2196F3',
              color: 'white',
              border: 'none',
              borderRadius: '8px',
              cursor: 'pointer',
              fontWeight: 600,
              width: '100%'
            }}
          >
            ▶️ Control Manual
          </button>
          <button
            onClick={onExit}
            style={{
              padding: '10px 20px',
              fontSize: '14px',
              background: 'transparent',
              color: '#666',
              border: '1px solid #ccc',
              borderRadius: '8px',
              cursor: 'pointer',
              marginTop: '15px',
              width: '100%'
            }}
          >
            Volver
          </button>
        </div>
      </div>
    );
  }

  // Resto del componente (igual que antes pero con los nuevos estados)
  return (
    <div style={{
      height: '100vh',
      display: 'flex',
      flexDirection: 'column',
      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      overflow: 'hidden'
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
            {currentIndex + 1} de {drills.length} • Reproducciones {playCount}/2
            {autoPlayEnabled && ' • Auto'}
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
          Salir
        </button>
      </div>

      {/* Controles de navegación */}
      <div style={{
        padding: isMobile ? '8px 12px' : '12px 20px',
        background: 'rgba(255,255,255,0.1)',
        backdropFilter: 'blur(10px)',
        display: 'flex',
        justifyContent: 'center',
        gap: isMobile ? '6px' : '10px',
        flexWrap: 'nowrap',
        overflowX: 'auto',
        whiteSpace: 'nowrap'
      }}>
        <button
          onClick={handlePrev}
          disabled={currentIndex === 0}
          style={{
            padding: isMobile ? '6px 10px' : '8px 16px',
            fontSize: isMobile ? '12px' : '14px',
            background: currentIndex === 0 ? '#ccc' : '#2196F3',
            color: 'white',
            border: 'none',
            borderRadius: '6px',
            cursor: currentIndex === 0 ? 'not-allowed' : 'pointer',
            fontWeight: 600,
            flexShrink: 0
          }}
        >
          ← Anterior
        </button>
        <button
          onClick={handleReplay}
          style={{
            padding: isMobile ? '6px 10px' : '8px 16px',
            fontSize: isMobile ? '12px' : '14px',
            background: '#FFC107',
            color: '#333',
            border: 'none',
            borderRadius: '6px',
            cursor: 'pointer',
            fontWeight: 600,
            flexShrink: 0
          }}
        >
          🔄 Reiniciar
        </button>
        <button
          onClick={handleNext}
          style={{
            padding: isMobile ? '6px 10px' : '8px 16px',
            fontSize: isMobile ? '12px' : '14px',
            background: '#4CAF50',
            color: 'white',
            border: 'none',
            borderRadius: '6px',
            cursor: 'pointer',
            fontWeight: 600,
            flexShrink: 0
          }}
        >
          {currentIndex < drills.length - 1 ? 'Siguiente →' : 'Finalizar'}
        </button>
        {!autoPlayEnabled && (
          <button
            onClick={() => setAutoPlayEnabled(true)}
            style={{
              padding: isMobile ? '6px 10px' : '8px 16px',
              fontSize: isMobile ? '12px' : '14px',
              background: '#9C27B0',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer',
              fontWeight: 600,
              flexShrink: 0
            }}
          >
            🔄 Activar Auto
          </button>
        )}
      </div>

      {/* Contenido principal */}
      <div style={{
        flex: 1,
        overflowY: 'auto',
        padding: isMobile ? '10px' : '20px',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center'
      }}>
        <div style={{
          background: 'white',
          padding: isMobile ? '16px' : '30px',
          borderRadius: '16px',
          maxWidth: '600px',
          width: '100%',
          boxShadow: '0 10px 40px rgba(0,0,0,0.2)',
          textAlign: 'center',
          marginBottom: '20px'
        }}>
          {/* Imagen */}
          {currentDrill.image_url && (
            <div style={{ marginBottom: isMobile ? '20px' : '30px' }}>
              <img
                src={getMediaUrl(currentDrill.image_url)}
                alt="Visual del drill"
                style={{
                  maxWidth: '100%',
                  maxHeight: isMobile ? '150px' : '200px',
                  borderRadius: '12px',
                  objectFit: 'contain'
                }}
              />
            </div>
          )}

          {/* Català */}
          <div style={{ marginBottom: isMobile ? '12px' : '16px' }}>
            <div style={{ 
              fontSize: isMobile ? '10px' : '12px', 
              color: '#667eea', 
              fontWeight: 600, 
              marginBottom: '4px',
              opacity: 0.8
            }}>
              Català
            </div>
            <div style={{ 
              fontSize: isMobile ? '16px' : '20px', 
              fontWeight: 600, 
              color: '#333',
              lineHeight: 1.3
            }}>
              {currentDrill.text_catalan || 'Sin texto'}
            </div>
          </div>

          {/* Tachelhit */}
          <div style={{ marginBottom: isMobile ? '16px' : '20px' }}>
            <div style={{ 
              fontSize: isMobile ? '12px' : '14px', 
              color: '#4CAF50', 
              fontWeight: 600, 
              marginBottom: '6px' 
            }}>
              Tachelhit
            </div>
            <div style={{ 
              fontSize: isMobile ? '18px' : '22px', 
              fontWeight: 600, 
              color: '#2e7d32',
              lineHeight: 1.3
            }}>
              {currentDrill.text_tachelhit || 'Sin texto'}
            </div>
          </div>

          {/* Arabic - Smaller and less prominent */}
          {currentDrill.text_arabic && (
            <div style={{ 
              marginBottom: isMobile ? '12px' : '20px',
              padding: isMobile ? '8px' : '12px',
              background: '#f8f9fa',
              borderRadius: '8px'
            }}>
              <div style={{ 
                fontSize: isMobile ? '10px' : '12px', 
                color: '#9C27B0', 
                fontWeight: 600, 
                marginBottom: '4px',
                opacity: 0.8
              }}>
                العربية
              </div>
              <div style={{ 
                fontSize: isMobile ? '14px' : '18px', 
                fontWeight: 500, 
                color: '#7b1fa2', 
                direction: 'rtl',
                lineHeight: 1.4
              }}>
                {currentDrill.text_arabic}
              </div>
            </div>
          )}

          {/* Audio Status - Clearer */}
          <div style={{
            padding: isMobile ? '14px' : '16px',
            background: isPlaying ? '#e8f5e9' : '#fff3cd',
            border: `2px solid ${isPlaying ? '#4CAF50' : '#FFC107'}`,
            borderRadius: '12px',
            marginBottom: isMobile ? '16px' : '24px'
          }}>
            <div style={{ 
              fontSize: isMobile ? '15px' : '16px', 
              fontWeight: 700, 
              color: isPlaying ? '#2e7d32' : '#856404',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '10px',
              marginBottom: '8px'
            }}>
              <span style={{ fontSize: '20px' }}>{isPlaying ? '🔊' : '⏸'}</span>
              <span>{isPlaying ? 'Reproduciendo audio...' : 'Listo para reproducir'}</span>
            </div>
            <div style={{ 
              fontSize: isMobile ? '13px' : '14px', 
              color: '#666', 
              marginBottom: '10px'
            }}>
              {currentDrill.audio_url ? 
                `Reproducción ${playCount + 1} de 2` 
                : 'No hay audio disponible'}
            </div>
            
            {/* Botones de control */}
            <div style={{ 
              display: 'flex', 
              gap: '10px', 
              marginTop: '10px',
              flexDirection: isMobile ? 'column' : 'row'
            }}>
              {/* Síntesis de voz para catalán */}
              {currentDrill.text_catalan && (
                <button
                  onClick={handleSpeakCatalan}
                  style={{
                    flex: 1,
                    padding: isMobile ? '12px' : '10px 16px',
                    fontSize: isMobile ? '15px' : '14px',
                    background: '#9C27B0',
                    color: 'white',
                    border: 'none',
                    borderRadius: '8px',
                    cursor: 'pointer',
                    fontWeight: 600,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '8px'
                  }}
                >
                  <span>🗣️</span>
                  <span>Escuchar Català</span>
                </button>
              )}
              
              {/* Reproducir audio original */}
              {currentDrill.audio_url && (
                <button
                  onClick={handlePlayAudio}
                  style={{
                    flex: 1,
                    padding: isMobile ? '12px' : '10px 16px',
                    fontSize: isMobile ? '15px' : '14px',
                    background: '#4CAF50',
                    color: 'white',
                    border: 'none',
                    borderRadius: '8px',
                    cursor: 'pointer',
                    fontWeight: 600,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '8px'
                  }}
                >
                  <span>▶️</span>
                  <span>Reproducir Audio</span>
                </button>
              )}
            </div>
            
            {/* Indicador de progreso */}
            {playCount > 0 && (
              <div style={{ 
                marginTop: '15px', 
                padding: '8px',
                background: '#e3f2fd',
                borderRadius: '8px',
                fontSize: isMobile ? '13px' : '14px',
                color: '#1976d2'
              }}>
                {playCount === 1 ? 'Una reproducción completada. Reproduce de nuevo para continuar.' :
                 playCount >= 2 ? 'Dos reproducciones completadas. Pasando al siguiente drill...' : ''}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
