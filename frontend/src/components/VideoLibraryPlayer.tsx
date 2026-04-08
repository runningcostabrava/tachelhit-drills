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
            setTimeout(() => {
                const targetDiv = document.getElementById(containerId);
                if (!targetDiv) return;

                if (ytPlayerRef.current) {
                    try { ytPlayerRef.current.destroy(); } catch (e) { }
                }

                ytPlayerRef.current = new (window as any).YT.Player(containerId, {
                    videoId: videoId,
                    playerVars: { autoplay: 1, controls: 0, rel: 0, modestbranding: 1 },
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
            }, 50);
        };

        if (!(window as any).YT || !(window as any).YT.Player) {
            if (!document.getElementById('youtube-iframe-api')) {
                const tag = document.createElement('script');
                tag.id = 'youtube-iframe-api';
                tag.src = "https://www.youtube.com/iframe_api";
                document.head.appendChild(tag);
            }
            const prevOnReady = (window as any).onYouTubeIframeAPIReady;
            (window as any).onYouTubeIframeAPIReady = () => {
                if (prevOnReady) prevOnReady();
                initPlayer();
            };
        } else {
            initPlayer();
        }

        const interval = setInterval(() => {
            if (ytPlayerRef.current && typeof ytPlayerRef.current.getCurrentTime === 'function') {
                setCurrentTime(ytPlayerRef.current.getCurrentTime());
            }
        }, 100);

        return () => {
            clearInterval(interval);
            if (ytPlayerRef.current) {
                try { ytPlayerRef.current.destroy(); } catch (e) { }
            }
        };
    }, [videoUrl, containerId]);

    // Controls
    const togglePlayPause = () => {
        if (!ytPlayerRef.current) return;
        playing ? ytPlayerRef.current.pauseVideo() : ytPlayerRef.current.playVideo();
    };
    const goBack2Seconds = () => {
        if (!ytPlayerRef.current) return;
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

    // Find the drill acting as the current subtitle. 
    // Falls back to a 5-second window if video_end_time is null.
    const activeDrill = drills.find(d => {
        const start = Number(d.video_start_time) || 0;
        const end = Number(d.video_end_time) || (start + 5);
        return currentTime >= start && currentTime <= end;
    });

    return createPortal(
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'black', zIndex: 10000, display: 'flex', flexDirection: 'column' }}>
            <div style={{ flex: 1, position: 'relative', display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
                <div id={containerId} style={{ width: '100%', height: '100%', pointerEvents: 'none' }} />
                
                {activeDrill && (activeDrill.text_catalan || activeDrill.text_tachelhit || activeDrill.text_arabic) && (
                    <div style={{
                        position: 'absolute', bottom: '10%', left: '50%', transform: 'translateX(-50%)',
                        padding: '15px 30px', backgroundColor: 'rgba(0, 0, 0, 0.8)', textAlign: 'center',
                        borderRadius: '12px', backdropFilter: 'blur(4px)', minWidth: '300px'
                    }}>
                        {activeDrill.text_arabic && (
                            <div style={{ fontSize: '28px', direction: 'rtl', fontWeight: 'bold', marginBottom: '8px', color: '#9C27B0' }}>
                                {activeDrill.text_arabic}
                            </div>
                        )}
                        {activeDrill.text_tachelhit && (
                            <div style={{ fontSize: '24px', fontWeight: 'bold', marginBottom: '5px', color: '#FFD700' }}>
                                {activeDrill.text_tachelhit}
                            </div>
                        )}
                        {activeDrill.text_catalan && (
                            <div style={{ fontSize: '20px', color: '#4CAF50', opacity: 0.9 }}>
                                {activeDrill.text_catalan}
                            </div>
                        )}
                    </div>
                )}
            </div>
            <div style={{ height: '80px', backgroundColor: '#1a1a1a', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '15px' }}>
                <button onClick={goBack2Seconds} style={btnStyle}>↺ 2s</button>
                <button onClick={togglePlayPause} style={{...btnStyle, background: '#4CAF50'}}>{playing ? '⏸ Pause' : '▶ Play'}</button>
                <button onClick={togglePlaybackRate} style={btnStyle}>{playbackRate}x</button>
                <button onClick={onClose} style={{...btnStyle, background: '#ff4444'}}>✕ Close</button>
            </div>
        </div>,
        document.body
    );
}

const btnStyle = { padding: '12px 24px', background: '#333', color: 'white', border: 'none', borderRadius: '8px', cursor: 'pointer', fontSize: '16px', fontWeight: 'bold' };
