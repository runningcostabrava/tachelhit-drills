import { useState, useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import { getYouTubeVideoId, loadYouTubeApi } from '../utils/youtubeUtils';

let libPlayerCounter = 0;

export default function VideoLibraryPlayer({ videoUrl, drills, onClose }: { videoUrl: string, drills: any[], onClose: () => void }) {
    const [playing, setPlaying] = useState(false);
    const [playbackRate, setPlaybackRate] = useState(1);
    const [currentTime, setCurrentTime] = useState(0);

    const ytPlayerRef = useRef<any>(null);
    // Stable for the component's lifetime — a per-render id would detach the
    // rendered div from the element the YT player was bound to
    const containerIdRef = useRef(`lib-player-${++libPlayerCounter}`);
    const containerId = containerIdRef.current;

    useEffect(() => {
        const videoId = getYouTubeVideoId(videoUrl);
        if (!videoId) return;

        const initPlayer = () => {
            if (!(window as any).YT || !(window as any).YT.Player) return;
            
            if (ytPlayerRef.current) {
                try { ytPlayerRef.current.destroy(); } catch (e) { }
            }

            ytPlayerRef.current = new (window as any).YT.Player(containerId, {
                videoId: videoId,
                playerVars: { 
                    autoplay: 1, 
                    controls: 1, // Let user use YT controls as well
                    rel: 0, 
                    modestbranding: 1,
                    enablejsapi: 1,
                    origin: window.location.origin
                },
                events: {
                    onReady: (event: any) => {
                        event.target.setPlaybackRate(playbackRate);
                        setPlaying(true);
                    },
                    onStateChange: (event: any) => {
                        if (event.data === (window as any).YT.PlayerState.PLAYING) setPlaying(true);
                        if (event.data === (window as any).YT.PlayerState.PAUSED) setPlaying(false);
                    }
                }
            });
        };

        let cancelled = false;
        loadYouTubeApi().then(() => { if (!cancelled) initPlayer(); });

        const interval = setInterval(() => {
            if (ytPlayerRef.current && typeof ytPlayerRef.current.getCurrentTime === 'function') {
                // React skips the re-render when the value hasn't changed
                setCurrentTime(ytPlayerRef.current.getCurrentTime());
            }
        }, 200); // 5 updates per second is enough for subtitles

        return () => {
            cancelled = true;
            clearInterval(interval);
            if (ytPlayerRef.current) {
                try { ytPlayerRef.current.destroy(); } catch (e) { }
            }
        };
    }, [videoUrl]); // Only recreate if URL changes

    // Controls
    const togglePlayPause = () => {
        if (!ytPlayerRef.current || typeof ytPlayerRef.current.pauseVideo !== 'function') return;
        playing ? ytPlayerRef.current.pauseVideo() : ytPlayerRef.current.playVideo();
    };
    
    const goBack2Seconds = () => {
        if (!ytPlayerRef.current || typeof ytPlayerRef.current.seekTo !== 'function') return;
        ytPlayerRef.current.seekTo(Math.max(0, currentTime - 2));
    };

    const togglePlaybackRate = () => {
        const rates = [0.5, 0.75, 1, 1.25, 1.5];
        const nextRate = rates[(rates.indexOf(playbackRate) + 1) % rates.length];
        setPlaybackRate(nextRate);
        if (ytPlayerRef.current && typeof ytPlayerRef.current.setPlaybackRate === 'function') {
            ytPlayerRef.current.setPlaybackRate(nextRate);
        }
    };

    // Subtitle sync logic
    const activeDrill = drills.find(d => {
        const start = Number(d.video_start_time);
        if (isNaN(start)) return false;
        
        // Use video_end_time or default to 5s duration
        const end = !isNaN(Number(d.video_end_time)) && d.video_end_time !== null
            ? Number(d.video_end_time) 
            : start + 5;
            
        return currentTime >= start && currentTime <= end;
    });

    return createPortal(
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'black', zIndex: 10000, display: 'flex', flexDirection: 'column' }}>
            <div style={{ flex: 1, position: 'relative', display: 'flex', justifyContent: 'center', alignItems: 'center', overflow: 'hidden' }}>
                <div id={containerId} style={{ width: '100%', height: '100%' }} />
                
                {activeDrill && (
                    <div style={{
                        position: 'absolute', bottom: '15%', left: '50%', transform: 'translateX(-50%)',
                        padding: '18px 32px', backgroundColor: 'rgba(15, 23, 42, 0.78)', textAlign: 'center',
                        borderRadius: 'var(--r-lg)', backdropFilter: 'blur(10px)', minWidth: '80%', maxWidth: '90%',
                        pointerEvents: 'none', border: '1px solid rgba(255,255,255,0.12)'
                    }}>
                        {activeDrill.text_arabic && (
                            <div style={{ fontSize: '32px', direction: 'rtl', fontWeight: 'bold', marginBottom: '8px', color: '#f472b6' }}>
                                {activeDrill.text_arabic}
                            </div>
                        )}
                        {activeDrill.text_tachelhit && (
                            <div style={{ fontSize: '26px', fontWeight: 'bold', marginBottom: '6px', color: 'var(--amber)', fontFamily: 'var(--font-tifinagh)' }}>
                                {activeDrill.text_tachelhit}
                            </div>
                        )}
                        {activeDrill.text_catalan && (
                            <div style={{ fontSize: '22px', color: 'var(--emerald)', fontWeight: '500' }}>
                                {activeDrill.text_catalan}
                            </div>
                        )}
                    </div>
                )}
            </div>
            
            <div style={{ height: '100px', backgroundColor: '#0f172a', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '20px', borderTop: '1px solid rgba(255,255,255,0.08)' }}>
                <button onClick={goBack2Seconds} style={btnStyle}>↺ 2s</button>
                <button onClick={togglePlayPause} style={{...btnStyle, background: playing ? 'var(--rose)' : 'var(--emerald)', border: 'none', minWidth: '120px'}}>
                    {playing ? '⏸ Pause' : '▶ Play'}
                </button>
                <button onClick={togglePlaybackRate} style={btnStyle}>{playbackRate}x</button>
                <button onClick={onClose} style={{...btnStyle, marginLeft: '40px'}}>✕ Close</button>
            </div>
        </div>,
        document.body
    );
}

const btnStyle: React.CSSProperties = {
    padding: '14px 28px',
    background: 'rgba(255,255,255,0.08)',
    color: 'white',
    border: '1px solid rgba(255,255,255,0.16)',
    borderRadius: 'var(--r-md)',
    cursor: 'pointer',
    fontSize: '18px',
    fontWeight: 'bold',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    transition: 'all 0.2s'
};
