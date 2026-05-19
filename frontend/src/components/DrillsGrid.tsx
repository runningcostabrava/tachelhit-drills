import { useState, useEffect } from 'react';
import { AgGridReact } from 'ag-grid-react';
import type { ColDef } from 'ag-grid-community';
import axios from 'axios';
import { Network } from '@capacitor/network';
import { API_BASE, getMediaUrl } from '../config';

// Import CSS structural definitions
import 'ag-grid-community/styles/ag-grid.css';
import 'ag-grid-community/styles/ag-theme-alpine.css';

interface Drill {
    id: number;
    text_catalan?: string;
    text_tachelhit?: string;
    text_arabic?: string;
    audio_url?: string;
    video_url?: string;
    image_url?: string;
    tag?: string;
    author?: string;
    date_created: string;
}

interface DrillsGridProps {
    rowData: Drill[];
    refreshData: () => Promise<void>;
    onEditDrill?: (drill: Drill) => void;
}

export default function DrillsGrid({ rowData, refreshData, onEditDrill }: DrillsGridProps) {
    const [isMobile, setIsMobile] = useState(window.innerWidth < 768 || /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent));
    const [showPasswordModal, setShowPasswordModal] = useState(false);
    const [passwordInput, setPasswordInput] = useState('');
    const [pendingDeleteId, setPendingDeleteId] = useState<number | null>(null);

    // UI states for loading actions
    const [actionLoadingId, setActionLoadingId] = useState<string | null>(null);

    // Track responsive screen resize configurations
    useEffect(() => {
        const handleResize = () => setIsMobile(window.innerWidth < 768 || /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent));
        window.addEventListener('resize', handleResize);
        return () => window.removeEventListener('resize', handleResize);
    }, []);

    // 🌐 Smart Non-Destructive Translation Pipeline
    const handleTranslate = async (drill: Drill, source: 'ca' | 'shi', target: 'ca' | 'shi') => {
        const sourceText = source === 'ca' ? drill.text_catalan : drill.text_tachelhit;
        if (!sourceText) {
            alert(`Please enter text in ${source === 'ca' ? 'Catalan' : 'Tachelhit'} first.`);
            return;
        }

        const targetField = target === 'shi' ? 'text_tachelhit' : 'text_catalan';
        const loadingKey = `trans-${drill.id}-${targetField}`;
        setActionLoadingId(loadingKey);

        try {
            const status = await Network.getStatus();
            if (!status.connected) {
                alert("⚠️ Translation requires an active internet connection.");
                return;
            }

            const res = await axios.post(`${API_BASE}/translate`, {
                text: sourceText,
                source_lang: source,
                target_lang: target
            });

            const freshTranslation = res.data.translated_text;
            const currentText = drill[targetField] || '';

            // Guard against deleting text: append in parentheses if text exists
            const preservedText = currentText.trim()
                ? `${currentText} (${freshTranslation})`
                : freshTranslation;

            // Commit the safe update to the backend DB
            await axios.put(`${API_BASE}/drills/${drill.id}`, { [targetField]: preservedText });
            await refreshData();
        } catch (err) {
            console.error('Translation workflow crashed:', err);
            alert('Failed to complete AI translation.');
        } finally {
            setActionLoadingId(null);
        }
    };

    // 🪄 Smart Non-Destructive Transcription Pipeline
    const handleTranscribe = async (drill: Drill) => {
        if (!drill.audio_url) return;

        const loadingKey = `scribe-${drill.id}`;
        setActionLoadingId(loadingKey);

        try {
            const status = await Network.getStatus();
            if (!status.connected) {
                alert("⚠️ Voice transcription requires an internet connection.");
                return;
            }

            const response = await axios.post(`${API_BASE}/transcribe/`, {
                audio_url: drill.audio_url
            });

            const freshTranscription = response.data.corrected_transcription;
            const currentTachelhit = drill.text_tachelhit || '';

            // Guard against deleting text: append text gracefully
            const preservedText = currentTachelhit.trim()
                ? `${currentTachelhit} (${freshTranscription})`
                : freshTranscription;

            await axios.put(`${API_BASE}/drills/${drill.id}`, { text_tachelhit: preservedText });
            await refreshData();
        } catch (error) {
            console.error('Transcription loop error:', error);
            alert('AI Transcription process failed.');
        } finally {
            setActionLoadingId(null);
        }
    };

    // 🗑️ Handle Deletion Security Check Sequence
    const handleDeleteIntent = (id: number) => {
        const isSessionAuthenticated = sessionStorage.getItem('drill_delete_auth') === 'true';

        if (isSessionAuthenticated) {
            executeDeletePipeline(id);
        } else {
            setPendingDeleteId(id);
            setShowPasswordModal(true);
        }
    };

    const verifyPasswordAndConfirm = () => {
        if (passwordInput === 'borrar') {
            sessionStorage.setItem('drill_delete_auth', 'true');
            setShowPasswordModal(false);
            setPasswordInput('');

            if (pendingDeleteId !== null) {
                executeDeletePipeline(pendingDeleteId);
            }
        } else {
            alert('❌ Incorrect password. Access denied.');
            setPasswordInput('');
        }
    };

    const executeDeletePipeline = async (id: number) => {
        const confirmDelete = window.confirm('Are you sure you want to permanently delete this drill?');
        if (!confirmDelete) return;

        try {
            const status = await Network.getStatus();

            const localCache = JSON.parse(localStorage.getItem('cached_drills') || '[]');
            const updatedCache = localCache.filter((d: any) => d.id !== id);
            localStorage.setItem('cached_drills', JSON.stringify(updatedCache));

            if (status.connected && id < 1000000) {
                await axios.delete(`${API_BASE}/drills/${id}`);
            } else {
                const queue = JSON.parse(localStorage.getItem('sync_queue') || '[]');
                const updatedQueue = queue.filter((d: any) => d.id !== id);
                localStorage.setItem('sync_queue', JSON.stringify(updatedQueue));
            }

            alert('🗑️ Drill removed successfully.');
            await refreshData();
        } catch (error) {
            console.error('Failed to complete delete request:', error);
            alert('Error trying to drop record entity.');
        } finally {
            setPendingDeleteId(null);
        }
    };

    // 📱 MOBILE INTERFACE: Card stream equipped with translation and transcription capabilities
    if (isMobile) {
        return (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', padding: '4px' }}>
                {rowData.map((drill) => (
                    <div
                        key={drill.id}
                        style={{
                            background: 'white',
                            borderRadius: '16px',
                            padding: '16px',
                            boxShadow: '0 4px 12px rgba(0,0,0,0.06)',
                            border: '1px solid #f0f0f0',
                            display: 'flex',
                            flexDirection: 'column',
                            gap: '12px',
                            position: 'relative'
                        }}
                    >
                        {/* Header Row */}
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <span style={{ fontSize: '12px', fontWeight: 700, color: '#aaa' }}>
                                #{drill.id >= 1000000 ? 'Offline Sync' : drill.id}
                            </span>
                            {drill.tag && (
                                <span style={{ background: '#eef2ff', color: '#4f46e5', padding: '4px 8px', borderRadius: '6px', fontSize: '11px', fontWeight: 600 }}>
                                    🏷️ {drill.tag}
                                </span>
                            )}
                        </div>

                        {/* Content text blocks */}
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                            <div style={{ fontSize: '15px', color: '#111827', fontWeight: 500 }}>{drill.text_catalan || <span style={{ color: '#ccc' }}>No Catalan</span>}</div>
                            <div style={{ fontSize: '16px', color: '#4f46e5', fontWeight: 700, fontFamily: 'monospace' }}>{drill.text_tachelhit || <span style={{ color: '#ccc' }}>No Tachelhit</span>}</div>
                            {drill.text_arabic && (
                                <div style={{ fontSize: '15px', color: '#059669', direction: 'rtl', textAlign: 'right', fontWeight: 500 }}>{drill.text_arabic}</div>
                            )}
                        </div>

                        {/* Thumbnail View */}
                        {drill.image_url && (
                            <img
                                src={getMediaUrl(drill.image_url)}
                                alt="Media thumbnail"
                                style={{ width: '100%', height: '140px', objectFit: 'cover', borderRadius: '12px', marginTop: '4px' }}
                            />
                        )}

                        {/* Interactive Audio Controls */}
                        {drill.audio_url && (
                            <button
                                onClick={() => {
                                    const audio = new Audio(getMediaUrl(drill.audio_url!));
                                    audio.play().catch(e => console.error('Playback fail:', e));
                                }}
                                style={{
                                    width: '100%',
                                    padding: '10px',
                                    background: '#f3f4f6',
                                    border: 'none',
                                    borderRadius: '10px',
                                    fontSize: '14px',
                                    fontWeight: 600,
                                    color: '#374151',
                                    cursor: 'pointer',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    gap: '6px'
                                }}
                            >
                                🔊 Play Drill Voice
                            </button>
                        )}

                        {/* 🌐 NEW COMPACT MOBILE AI OPERATION PANEL */}
                        <div style={{
                            display: 'grid',
                            gridTemplateColumns: drill.audio_url ? '1fr 1fr 1fr' : '1fr 1fr',
                            gap: '8px',
                            marginTop: '4px'
                        }}>
                            <button
                                onClick={() => handleTranslate(drill, 'ca', 'shi')}
                                disabled={actionLoadingId !== null || !drill.text_catalan}
                                style={{ padding: '8px', fontSize: '11px', fontWeight: 700, background: '#eef2ff', color: '#4f46e5', border: 'none', borderRadius: '8px', cursor: 'pointer' }}
                            >
                                {actionLoadingId === `trans-${drill.id}-text_tachelhit` ? '⏳...' : '🤖 CA➔SHI'}
                            </button>
                            <button
                                onClick={() => handleTranslate(drill, 'shi', 'ca')}
                                disabled={actionLoadingId !== null || !drill.text_tachelhit}
                                style={{ padding: '8px', fontSize: '11px', fontWeight: 700, background: '#ecfdf5', color: '#059669', border: 'none', borderRadius: '8px', cursor: 'pointer' }}
                            >
                                {actionLoadingId === `trans-${drill.id}-text_catalan` ? '⏳...' : '🤖 SHI➔CA'}
                            </button>
                            {drill.audio_url && (
                                <button
                                    onClick={() => handleTranscribe(drill)}
                                    disabled={actionLoadingId !== null}
                                    style={{ padding: '8px', fontSize: '11px', fontWeight: 700, background: '#fff7ed', color: '#ea580c', border: 'none', borderRadius: '8px', cursor: 'pointer' }}
                                >
                                    {actionLoadingId === `scribe-${drill.id}` ? '⏳...' : '🪄 Transcribe'}
                                </button>
                            )}
                        </div>

                        <hr style={{ border: 'none', height: '1px', background: '#f3f4f6', margin: '4px 0' }} />

                        {/* Action Footer */}
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <span style={{ fontSize: '12px', color: '#9ca3af' }}>By: {drill.author || 'System'}</span>

                            <div style={{ display: 'flex', gap: '8px' }}>
                                {onEditDrill && (
                                    <button
                                        onClick={() => onEditDrill(drill)}
                                        style={{ background: '#4f46e5', color: 'white', border: 'none', borderRadius: '8px', padding: '8px 14px', fontSize: '13px', fontWeight: 600, cursor: 'pointer' }}
                                    >
                                        ✏️ Edit
                                    </button>
                                )}
                                <button
                                    onClick={() => handleDeleteIntent(drill.id)}
                                    style={{ background: '#fee2e2', color: '#ef4444', border: 'none', borderRadius: '8px', padding: '8px 12px', fontSize: '13px', fontWeight: 600, cursor: 'pointer' }}
                                >
                                    🗑️ Delete
                                </button>
                            </div>
                        </div>
                    </div>
                ))}

                {/* Password confirmation pop-up */}
                {showPasswordModal && (
                    <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.6)', zIndex: 99999, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '20px' }}>
                        <div style={{ background: 'white', padding: '24px', borderRadius: '16px', width: '100%', maxWidth: '340px', boxShadow: '0 10px 25px rgba(0,0,0,0.2)', textAlign: 'center' }}>
                            <div style={{ fontSize: '40px', marginBottom: '12px' }}>🔒</div>
                            <h3 style={{ margin: '0 0 8px 0', fontSize: '18px', fontWeight: 700 }}>Security Verification</h3>
                            <p style={{ margin: '0 0 20px 0', fontSize: '14px', color: '#666' }}>Enter the deletion password to proceed.</p>

                            <input
                                type="password"
                                placeholder="Enter password"
                                value={passwordInput}
                                onChange={(e) => setPasswordInput(e.target.value)}
                                onKeyDown={(e) => e.key === 'Enter' && verifyPasswordAndConfirm()}
                                style={{ width: '100%', padding: '12px', fontSize: '16px', border: '2px solid #e5e7eb', borderRadius: '8px', marginBottom: '16px', outline: 'none', textAlign: 'center' }}
                                autoFocus
                            />

                            <div style={{ display: 'flex', gap: '10px' }}>
                                <button
                                    onClick={() => { setShowPasswordModal(false); setPasswordInput(''); }}
                                    style={{ flex: 1, padding: '12px', background: '#f3f4f6', color: '#4b5563', border: 'none', borderRadius: '8px', fontWeight: 600, cursor: 'pointer' }}
                                >
                                    Cancel
                                </button>
                                <button
                                    onClick={verifyPasswordAndConfirm}
                                    style={{ flex: 1, padding: '12px', background: '#ef4444', color: 'white', border: 'none', borderRadius: '8px', fontWeight: 600, cursor: 'pointer' }}
                                >
                                    Confirm
                                </button>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        );
    }

    // 🖥️ DESKTOP INTERFACE: Standard High-Performance spreadsheet view
    const columnDefs: ColDef<Drill>[] = [
        { field: 'id', headerName: 'ID', width: 70 },
        { field: 'text_catalan', headerName: 'Català', flex: 1, filter: true },
        { field: 'text_tachelhit', headerName: 'Tachelhit', flex: 1, filter: true },
        { field: 'text_arabic', headerName: 'العربية', flex: 1, filter: true },
        { field: 'tag', headerName: 'Tag', width: 110, filter: true },
        { field: 'author', headerName: 'Author', width: 110, filter: true },
        {
            headerName: 'Actions',
            width: 160,
            cellRenderer: (params: any) => (
                <div style={{ display: 'flex', gap: '6px', alignItems: 'center', height: '100%' }}>
                    {onEditDrill && (
                        <button
                            onClick={() => onEditDrill(params.data)}
                            style={{ background: '#4f46e5', color: 'white', border: 'none', borderRadius: '4px', padding: '4px 8px', cursor: 'pointer', fontSize: '12px' }}
                        >
                            ✏️
                        </button>
                    )}
                    <button
                        onClick={() => handleDeleteIntent(params.data.id)}
                        style={{ background: '#fee2e2', color: '#ef4444', border: 'none', borderRadius: '4px', padding: '4px 8px', cursor: 'pointer', fontSize: '12px', fontWeight: 'bold' }}
                    >
                        🗑️ Delete
                    </button>
                </div>
            )
        }
    ];

    return (
        <div className="ag-theme-alpine" style={{ width: '100%', height: 'calc(100vh - 180px)' }}>
            <AgGridReact
                rowData={rowData}
                columnDefs={columnDefs}
                animateRows={true}
                pagination={true}
                paginationPageSize={20}
            />
        </div>
    );
}