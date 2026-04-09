import { useState, useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import { getYouTubeVideoId } from '../utils/youtubeUtils';

export default function VideoLibraryPlayer({ videoUrl, drills, onClose }: { videoUrl: string, drills: any[], onClose: () => void }) {
    const [playing, setPlaying] = useState(false);
    const [playbackRate, setPlaybackRate] = useState(1);
    const [currentTime, setCurrentTime] = useState(0);
    
    const ytPlayerRef = useRef<any>(null);
    const containerId = `lib-player-${Date.now()}`;

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

        if (!(window as any).YT || !(window as any).YT.Player) {
            if (!document.getElementById('youtube-iframe-api')) {
                const tag = document.createElement('script');
                tag.id = 'youtube-iframe-api';
                tag.src = "https://www.youtube.com/iframe_api";
                document.head.appendChild(tag);
            }
            // Overwrite or hook into global ready callback
            const prevOnReady = (window as any).onYouTubeIframeAPIReady;
            (window as any).onYouTubeIframeAPIReady = () => {
                if (prevOnReady) prevOnReady();
                initPlayer();
            };
        } else {
            // Already loaded
            initPlayer();
        }

        const interval = setInterval(() => {
            if (ytPlayerRef.current && typeof ytPlayerRef.current.getCurrentTime === 'function') {
                const time = ytPlayerRef.current.getCurrentTime();
                if (time !== currentTime) {
                    setCurrentTime(time);
                }
            }
        }, 200); // 5 updates per second is enough for subtitles

        return () => {
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
                        padding: '15px 30px', backgroundColor: 'rgba(0, 0, 0, 0.75)', textAlign: 'center',
                        borderRadius: '12px', backdropFilter: 'blur(8px)', minWidth: '80%', maxWidth: '90%',
                        pointerEvents: 'none', border: '1px solid rgba(255,255,255,0.1)'
                    }}>
                        {activeDrill.text_arabic && (
                            <div style={{ fontSize: '32px', direction: 'rtl', fontWeight: 'bold', marginBottom: '8px', color: '#E91E63' }}>
                                {activeDrill.text_arabic}
                            </div>
                        )}
                        {activeDrill.text_tachelhit && (
                            <div style={{ fontSize: '26px', fontWeight: 'bold', marginBottom: '5px', color: '#FFD700' }}>
                                {activeDrill.text_tachelhit}
                            </div>
                        )}
                        {activeDrill.text_catalan && (
                            <div style={{ fontSize: '22px', color: '#4CAF50', fontWeight: '500' }}>
                                {activeDrill.text_catalan}
                            </div>
                        )}
                    </div>
                )}
            </div>
            
            <div style={{ height: '100px', backgroundColor: '#111', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '20px', borderTop: '1px solid #333' }}>
                <button onClick={goBack2Seconds} style={btnStyle}>↺ 2s</button>
                <button onClick={togglePlayPause} style={{...btnStyle, background: playing ? '#f44336' : '#4CAF50', minWidth: '120px'}}>
                    {playing ? '⏸ Pause' : '▶ Play'}
                </button>
                <button onClick={togglePlaybackRate} style={btnStyle}>{playbackRate}x</button>
                <button onClick={onClose} style={{...btnStyle, background: '#333', marginLeft: '40px'}}>✕ Close</button>
            </div>
        </div>,
        document.body
    );
}

const btnStyle: React.CSSProperties = { 
    padding: '14px 28px', 
    background: '#222', 
    color: 'white', 
    border: '1px solid #444', 
    borderRadius: '10px', 
    cursor: 'pointer', 
    fontSize: '18px', 
    fontWeight: 'bold',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    transition: 'all 0.2s'
};
