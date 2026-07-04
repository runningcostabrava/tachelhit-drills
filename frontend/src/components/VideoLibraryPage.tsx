import '../agGridSetup';
import { useState, useEffect, useMemo } from 'react';
import { AgGridReact } from 'ag-grid-react';
import type { ColDef } from 'ag-grid-community';
import 'ag-grid-community/styles/ag-theme-alpine.css';
import axios from 'axios';
import { API_BASE } from '../config';
import { isYouTubeUrl, getYouTubeVideoId } from '../utils/youtubeUtils';
import VideoLibraryPlayer from './VideoLibraryPlayer';

export default function VideoLibraryPage() {
    const [drills, setDrills] = useState<any[]>([]);
    const [activeLibraryVideo, setActiveLibraryVideo] = useState<{url: string, drills: any[]} | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(false);

    useEffect(() => {
        setLoading(true);
        setError(false);
        axios.get(`${API_BASE}/drills/`)
            .then(res => { setDrills(res.data); setLoading(false); })
            .catch(err => { console.error('Failed to load drills:', err); setError(true); setLoading(false); });
    }, []);

    const libraryVideos = useMemo(() => {
        const grouped: Record<string, { url: string; drills: any[] }> = {};

        drills.forEach(drill => {
            if (drill.video_url && isYouTubeUrl(drill.video_url)) {
                const videoId = getYouTubeVideoId(drill.video_url); 
                
                if (videoId) {
                    if (!grouped[videoId]) {
                        grouped[videoId] = { url: drill.video_url, drills: [] };
                    }
                    if (drill.video_start_time !== null && drill.video_start_time !== undefined) {
                        grouped[videoId].drills.push(drill);
                    }
                }
            }
        });
        
        return Object.entries(grouped).map(([videoId, data]) => {
            // Sort chronologically so subtitles appear in order
            const sortedDrills = data.drills.sort((a, b) => Number(a.video_start_time) - Number(b.video_start_time));
            
            return {
                id: videoId,
                url: data.url,
                drillCount: sortedDrills.length,
                title: sortedDrills[0]?.tag || sortedDrills[0]?.author || `Vídeo: ${videoId}`,
                drills: sortedDrills
            };
        }).filter(video => video.drillCount > 0);
    }, [drills]);

    const columnDefs: ColDef[] = [
        { field: 'title', headerName: 'Perfil del vídeo', flex: 1 },
        { field: 'drillCount', headerName: 'Nombre de drills (subtítols)', width: 250 },
        {
            headerName: 'Acció',
            width: 150,
            cellRenderer: (params: any) => (
                <button
                    onClick={() => setActiveLibraryVideo(params.data)}
                    aria-label={`Reprodueix el vídeo sencer: ${params.data.title}`}
                    style={{ padding: '8px 16px', background: 'var(--brand-gradient)', color: 'white', border: 'none', borderRadius: 'var(--r-pill)', cursor: 'pointer', fontWeight: 700, fontSize: '13px', boxShadow: 'var(--shadow-brand)' }}
                >
                    <span aria-hidden="true">▶</span> Reprodueix el vídeo sencer
                </button>
            )
        }
    ];

    return (
        <div style={{ height: '100vh', display: 'flex', flexDirection: 'column', background: 'var(--bg)' }}>
            <div style={{ padding: 'clamp(12px, 4vw, 24px)', background: 'var(--surface)', borderBottom: '1px solid var(--border)' }}>
                <h1 id="library-title" style={{ margin: 0, fontFamily: 'var(--font-display)', fontSize: 'clamp(20px, 5vw, 24px)', fontWeight: 700, color: 'var(--text)', letterSpacing: '-0.02em' }}>Biblioteca de vídeos</h1>
                <p style={{ margin: '4px 0 0 0', color: 'var(--text-soft)', fontSize: '14px' }}>Vídeos complets sincronitzats amb les traduccions dels teus drills.</p>
            </div>

            {error && (
                <div style={{ margin: 'clamp(12px, 4vw, 32px)', marginBottom: 0, padding: '12px 16px', background: 'var(--surface)', border: '1px solid var(--rose)', borderRadius: 'var(--r-md)', color: 'var(--rose)', fontSize: '14px' }}>
                    No s'han pogut carregar els vídeos. Torna-ho a provar més tard.
                </div>
            )}

            <div
                className="ag-theme-alpine"
                role="region"
                aria-labelledby="library-title"
                style={{ flex: 1, width: '100%', padding: 'clamp(12px, 4vw, 32px)' }}
            >
                <AgGridReact
                    rowData={libraryVideos}
                    columnDefs={columnDefs}
                    rowHeight={60}
                    theme="legacy"
                    loading={loading}
                    overlayLoadingTemplate="<span style='padding:16px;color:var(--text-soft)'>S'estan carregant els vídeos…</span>"
                    overlayNoRowsTemplate="<span style='padding:16px;color:var(--text-soft)'>Encara no hi ha vídeos sincronitzats amb els teus drills. Afegeix marques de temps als drills per veure'ls aquí.</span>"
                    defaultColDef={{ resizable: true, sortable: true, filter: true }}
                />
            </div>
            
            {activeLibraryVideo && (
                <VideoLibraryPlayer 
                    videoUrl={activeLibraryVideo.url} 
                    drills={activeLibraryVideo.drills} 
                    onClose={() => setActiveLibraryVideo(null)} 
                />
            )}
        </div>
    );
}
