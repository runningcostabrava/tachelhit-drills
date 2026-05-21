import { useState, useEffect } from 'react';
import { AgGridReact } from 'ag-grid-react';
import type { ColDef } from 'ag-grid-community';
import axios from 'axios';
import TestConfigPanel from './TestConfigPanel';
import { useNavigate } from 'react-router-dom';
import { syncManager } from '../services/OfflineSyncManager';
import { Network } from '@capacitor/network';
import { Camera, CameraResultType, CameraSource } from '@capacitor/camera';
import { VoiceRecorder } from 'capacitor-voice-recorder';
import { API_BASE, getMediaUrl } from '../config';
import { 
  FaVolumeUp, 
  FaVideo, 
  FaRobot, 
  FaLanguage, 
  FaMagic, 
  FaSave, 
  FaEdit, 
  FaTrash, 
  FaCheckSquare, 
  FaTag, 
  FaPlus,
  FaFileAudio,
  FaSearch
} from 'react-icons/fa';

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
    const [selectedRows, setSelectedRows] = useState<Drill[]>([]);
    const [actionLoadingId, setActionLoadingId] = useState<string | null>(null);
    const [showTestConfig, setShowTestConfig] = useState(false);
    const [pendingMedia, setPendingMedia] = useState<Record<number, {image?: string, audio?: Blob, audioUrl?: string, video?: Blob, videoUrl?: string}>>({});
    const navigate = useNavigate();

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
            const currentText = (drill as any)[targetField] || '';

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
    const handleTranscribe = async (drill: Drill, sourceType?: 'audio' | 'video') => {
        let mediaSource = '';
        if (sourceType === 'audio') mediaSource = drill.audio_url || '';
        else if (sourceType === 'video') mediaSource = drill.video_url || '';
        else mediaSource = drill.audio_url || drill.video_url || '';

        console.log(`[Transcribe] Starting for drill ${drill.id}, source type: ${sourceType || 'auto'}, url: ${mediaSource}`);

        if (!mediaSource) {
            alert('No media available to transcribe.');
            return;
        }

        const loadingKey = `scribe-${drill.id}`;
        setActionLoadingId(loadingKey);

        try {
            const status = await Network.getStatus();
            if (!status.connected) {
                console.warn('[Transcribe] Offline. Aborting.');
                alert("⚠️ Voice transcription requires an internet connection.");
                return;
            }

            // Ensure we use the proper media URL for transcription
            const fullMediaUrl = getMediaUrl(mediaSource);
            console.log(`[Transcribe] Posting to backend with URL: ${fullMediaUrl}`);

            const response = await axios.post(`${API_BASE}/transcribe/`, {
                audio_url: fullMediaUrl
            });

            console.log('[Transcribe] Backend response received:', response.data);

            let freshTranscription = response.data.corrected_transcription;
            
            // Add mention if it's from video
            if (sourceType === 'video' || (!sourceType && mediaSource === drill.video_url)) {
                freshTranscription = `[Video] ${freshTranscription}`;
            }

            const currentTachelhit = drill.text_tachelhit || '';

            // Guard against deleting text: append text gracefully
            const preservedText = currentTachelhit.trim()
                ? `${currentTachelhit} (${freshTranscription})`
                : freshTranscription;

            console.log(`[Transcribe] Saving updated Tachelhit text: ${preservedText}`);
            await axios.put(`${API_BASE}/drills/${drill.id}`, { text_tachelhit: preservedText });
            await refreshData();
            console.log('[Transcribe] Success.');
        } catch (error) {
            console.error('[Transcribe] Transcription loop error:', error);
            alert('AI Transcription process failed.');
        } finally {
            setActionLoadingId(null);
        }
    };

    // 🔊 Smart Tachelhit TTS Pipeline
    const handleTachelhitTTS = async (drill: Drill) => {
        const text = drill.text_tachelhit;
        if (!text) {
            alert('Tachelhit field is empty.');
            return;
        }

        const loadingKey = `tts-${drill.id}`;
        setActionLoadingId(loadingKey);

        try {
            const status = await Network.getStatus();
            if (!status.connected) {
                alert("⚠️ TTS requires an active internet connection.");
                return;
            }

            const res = await axios.post(`${API_BASE}/tts/tachelhit`, { 
                text, 
                drill_id: drill.id 
            });

            if (res.data.url) {
                new Audio(getMediaUrl(res.data.url)).play();
                await refreshData();
            }
        } catch (err) {
            console.error('TTS workflow crashed:', err);
            alert('Failed to generate TTS audio.');
        } finally {
            setActionLoadingId(null);
        }
    };

    const onCellValueChanged = async (params: any) => {
        const { data, colDef, newValue } = params;
        const field = colDef.field;
        try {
            await axios.put(`${API_BASE}/drills/${data.id}`, { [field]: newValue });
        } catch (err) {
            console.error('Failed to save inline edit:', err);
            refreshData(); 
        }
    };

    const handleBulkDelete = async () => {
        if (selectedRows.length === 0) return;
        if (!window.confirm(`Are you sure you want to delete ${selectedRows.length} drills?`)) return;

        try {
            const status = await Network.getStatus();
            for (const drill of selectedRows) {
                if (status.connected && drill.id < 1000000) {
                    await axios.delete(`${API_BASE}/drills/${drill.id}`);
                }
            }
            alert('Bulk delete complete.');
            await refreshData();
        } catch (error) {
            alert('One or more deletes failed.');
        }
    };

    const handleBulkEditTags = async () => {
        if (selectedRows.length === 0) return;
        const newTag = prompt('Enter new tag for selected drills (prefix with + to append, - to remove):');
        if (newTag === null) return;

        try {
            for (const drill of selectedRows) {
                await axios.put(`${API_BASE}/drills/${drill.id}`, { tag: newTag });
            }
            alert('Bulk tag update complete.');
            await refreshData();
        } catch (error) {
            alert('Tag update failed.');
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

    const handleQuickPhoto = async (drillId: number) => {
        try {
            const image = await Camera.getPhoto({
                quality: 50,
                width: 640,
                height: 480,
                resultType: CameraResultType.Base64,
                source: CameraSource.Prompt
            });
            if (image && image.base64String) {
                const base64Data = `data:image/${image.format};base64,${image.base64String}`;
                setPendingMedia(prev => ({
                    ...prev,
                    [drillId]: { ...prev[drillId], image: base64Data }
                }));
            }
        } catch (e) {
            console.error('Quick photo failed', e);
        }
    };

    const handleQuickAudio = async (drillId: number) => {
        try {
            const isRecording = actionLoadingId === `rec-${drillId}`;
            if (isRecording) {
                const result = await VoiceRecorder.stopRecording();
                setActionLoadingId(null);
                if (result.value && result.value.recordDataBase64) {
                    const base64Response = await fetch(`data:${result.value.mimeType};base64,${result.value.recordDataBase64}`);
                    const blob = await base64Response.blob();
                    setPendingMedia(prev => ({
                        ...prev,
                        [drillId]: { ...prev[drillId], audio: blob, audioUrl: URL.createObjectURL(blob) }
                    }));
                }
            } else {
                await VoiceRecorder.requestAudioRecordingPermission();
                await VoiceRecorder.startRecording();
                setActionLoadingId(`rec-${drillId}`);
            }
        } catch (e) {
            console.error('Quick audio failed', e);
            setActionLoadingId(null);
        }
    };

    const handleQuickSave = async (drill: Drill) => {
        const pending = pendingMedia[drill.id];
        if (!pending) return;

        setActionLoadingId(`save-${drill.id}`);
        try {
            if (pending.image) {
                const response = await fetch(pending.image);
                const blob = await response.blob();
                const fileName = `photo_${drill.id}_${Date.now()}.jpg`;
                await syncManager.saveMediaLocally(blob, fileName);
                await syncManager.queueAction({
                    type: 'UPLOAD_MEDIA',
                    drillId: drill.id,
                    mediaType: 'image',
                    localPath: fileName,
                    fileName: fileName
                });
            }

            if (pending.audio) {
                const fileName = `audio_${drill.id}_${Date.now()}.m4a`;
                await syncManager.saveMediaLocally(pending.audio, fileName);
                await syncManager.queueAction({
                    type: 'UPLOAD_MEDIA',
                    drillId: drill.id,
                    mediaType: 'audio',
                    localPath: fileName,
                    fileName: fileName
                });
            }

            if (pending.video) {
                const fileName = `video_${drill.id}_${Date.now()}.mp4`;
                await syncManager.saveMediaLocally(pending.video, fileName);
                await syncManager.queueAction({
                    type: 'UPLOAD_MEDIA',
                    drillId: drill.id,
                    mediaType: 'video',
                    localPath: fileName,
                    fileName: fileName
                });
            }

            // Trigger sync (background) and refresh UI immediately
            syncManager.sync(); 
            setPendingMedia(prev => {
                const next = { ...prev };
                delete next[drill.id];
                return next;
            });
            
            // Artificial delay to allow Preferences to settle before refresh
            setTimeout(() => refreshData(), 100);
        } catch (err) {
            alert('Failed to save media');
        } finally {
            setActionLoadingId(null);
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
                        {(drill.image_url || pendingMedia[drill.id]?.image) && (
                            <div style={{ position: 'relative' }}>
                                <img
                                    src={pendingMedia[drill.id]?.image || getMediaUrl(drill.image_url)}
                                    alt="Media thumbnail"
                                    style={{ width: '100%', height: '140px', objectFit: 'cover', borderRadius: '12px', marginTop: '4px' }}
                                />
                                <div style={{ position: 'absolute', top: '10px', right: '10px', background: 'rgba(0,0,0,0.5)', borderRadius: '50%', width: '30px', height: '30px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'white', fontSize: '14px' }}>🖼️</div>
                            </div>
                        )}

                        {/* Interactive Audio Controls */}
                        <div style={{ display: 'flex', gap: '8px' }}>
                            {drill.audio_url && (
                                <button
                                    onClick={() => {
                                        const audio = new Audio(getMediaUrl(drill.audio_url!));
                                        audio.play().catch(e => console.error('Playback fail:', e));
                                    }}
                                    style={{
                                        flex: 1,
                                        padding: '10px',
                                        background: '#EEF2FF',
                                        border: '1px solid #C3DAFE',
                                        borderRadius: '12px',
                                        fontSize: '14px',
                                        fontWeight: 600,
                                        color: '#4338CA',
                                        cursor: 'pointer',
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'center',
                                        gap: '8px'
                                    }}
                                >
                                    <FaVolumeUp /> Audio
                                </button>
                            )}
                            {drill.text_tachelhit && (
                                <button
                                    onClick={() => handleTachelhitTTS(drill)}
                                    disabled={actionLoadingId === `tts-${drill.id}`}
                                    style={{
                                        flex: 1,
                                        padding: '10px',
                                        background: '#FEF3C7',
                                        border: '1px solid #FDE68A',
                                        borderRadius: '12px',
                                        fontSize: '14px',
                                        fontWeight: 600,
                                        color: '#92400E',
                                        cursor: 'pointer',
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'center',
                                        gap: '8px'
                                    }}
                                >
                                    <FaRobot /> {actionLoadingId === `tts-${drill.id}` ? '...' : 'TTS'}
                                </button>
                            )}
                            {drill.video_url && (
                                <button
                                    onClick={() => {
                                        window.open(getMediaUrl(drill.video_url!), '_blank');
                                    }}
                                    style={{
                                        flex: 1,
                                        padding: '10px',
                                        background: '#F3E8FF',
                                        border: '1px solid #E9D5FF',
                                        borderRadius: '12px',
                                        fontSize: '14px',
                                        fontWeight: 600,
                                        color: '#7E22CE',
                                        cursor: 'pointer',
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'center',
                                        gap: '8px'
                                    }}
                                >
                                    <FaVideo /> Video
                                </button>
                            )}
                        </div>


                        <hr style={{ border: 'none', height: '1px', background: '#f3f4f6', margin: '4px 0' }} />

                        {/* Quick Update Row */}
                        <div style={{ display: 'flex', gap: '8px', marginBottom: '8px' }}>
                            <button 
                                onClick={() => handleQuickPhoto(drill.id)}
                                style={{ flex: 1, padding: '10px', background: '#f0fdf4', color: '#166534', border: '1px solid #bbf7d0', borderRadius: '8px', fontSize: '14px', fontWeight: 'bold' }}
                            >📷 Photo</button>
                            <button 
                                onClick={() => handleQuickAudio(drill.id)}
                                style={{ flex: 1, padding: '10px', background: actionLoadingId === `rec-${drill.id}` ? '#fef2f2' : '#eff6ff', color: actionLoadingId === `rec-${drill.id}` ? '#991b1b' : '#1e40af', border: '1px solid #bfdbfe', borderRadius: '8px', fontSize: '14px', fontWeight: 'bold' }}
                            >
                                {actionLoadingId === `rec-${drill.id}` ? '⏹ Stop' : '🎙 Audio'}
                            </button>
                        </div>

                        {/* Previews for pending media */}
                        {pendingMedia[drill.id] && (
                            <div style={{ background: '#fffbeb', padding: '10px', borderRadius: '10px', border: '1px dashed #fbbf24', marginBottom: '8px' }}>
                                <div style={{ fontSize: '12px', fontWeight: 'bold', color: '#92400e', marginBottom: '4px' }}>Pending Updates:</div>
                                <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                                    {pendingMedia[drill.id].image && <img src={pendingMedia[drill.id].image} style={{ width: '40px', height: '40px', borderRadius: '4px', objectFit: 'cover' }} />}
                                    {pendingMedia[drill.id].audioUrl && <button onClick={() => new Audio(pendingMedia[drill.id].audioUrl).play()} style={{ background: 'none', border: 'none', fontSize: '20px' }}>🔊</button>}
                                    {pendingMedia[drill.id].videoUrl && <button onClick={() => window.open(pendingMedia[drill.id].videoUrl, '_blank')} style={{ background: 'none', border: 'none', fontSize: '20px' }}>🎬</button>}
                                    <div style={{ flex: 1 }}></div>
                                    <button 
                                        onClick={() => handleQuickSave(drill)}
                                        disabled={actionLoadingId !== null}
                                        style={{ background: '#4CAF50', color: 'white', border: 'none', borderRadius: '6px', padding: '6px 12px', fontWeight: 'bold', fontSize: '13px' }}
                                    >
                                        {actionLoadingId === `save-${drill.id}` ? '...' : '💾 Save Now'}
                                    </button>
                                </div>
                            </div>
                        )}

                        {/* Action Footer */}
                        <div style={{ display: 'flex', justifyContent: 'flex-end', alignItems: 'center' }}>
                            <div style={{ display: 'flex', gap: '8px' }}>
                                {onEditDrill && (
                                    <button
                                        onClick={() => onEditDrill(drill)}
                                        style={{ display: 'flex', alignItems: 'center', gap: '6px', background: '#4f46e5', color: 'white', border: 'none', borderRadius: '10px', padding: '10px 18px', fontSize: '14px', fontWeight: 600, cursor: 'pointer', boxShadow: '0 2px 4px rgba(79, 70, 229, 0.2)' }}
                                    >
                                        <FaEdit /> Edit
                                    </button>
                                )}
                                <button
                                    onClick={() => handleDeleteIntent(drill.id)}
                                    style={{ display: 'flex', alignItems: 'center', gap: '6px', background: '#FFF1F2', color: '#E11D48', border: '1px solid #FECDD3', borderRadius: '10px', padding: '10px 18px', fontSize: '14px', fontWeight: 600, cursor: 'pointer' }}
                                >
                                    <FaTrash /> Delete
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
        { field: 'id', headerName: 'ID', width: 80, sortable: true, editable: true },
        { 
            field: 'image_url', 
            headerName: 'Preview', 
            width: 90, 
            cellRenderer: (p: any) => p.value ? <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}><img src={getMediaUrl(p.value)} style={{ width: '60px', height: '60px', objectFit: 'cover', borderRadius: '8px', border: '1px solid #e5e7eb' }} /></div> : null 
        },
        { field: 'text_catalan', headerName: 'Català', flex: 2, minWidth: 150, filter: true, wrapText: true, autoHeight: true, editable: true, cellStyle: { 'line-height': '20px', 'padding-top': '10px', 'padding-bottom': '10px' } },
        { field: 'text_tachelhit', headerName: 'Tachelhit', flex: 2, minWidth: 150, filter: true, wrapText: true, autoHeight: true, editable: true, cellStyle: { 'line-height': '20px', 'padding-top': '10px', 'padding-bottom': '10px' } },
        { field: 'text_arabic', headerName: 'العربية', flex: 2, minWidth: 150, filter: true, wrapText: true, autoHeight: true, editable: true, cellStyle: { 'line-height': '20px', 'padding-top': '10px', 'padding-bottom': '10px', 'direction': 'rtl' } },
        { field: 'tag', headerName: 'Tag', width: 120, filter: true, editable: true },
        {
            headerName: 'Media',
            width: 120,
            cellRenderer: (params: any) => (
                <div style={{ display: 'flex', gap: '10px', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
                    {params.data.audio_url && (
                        <button onClick={() => new Audio(getMediaUrl(params.data.audio_url)).play()} style={{ background: '#EEF2FF', border: 'none', borderRadius: '8px', padding: '8px', cursor: 'pointer', color: '#4338CA' }} title="Play Audio"><FaVolumeUp size={16} /></button>
                    )}
                    {params.data.video_url && (
                        <button onClick={() => window.open(getMediaUrl(params.data.video_url), '_blank')} style={{ background: '#F3E8FF', border: 'none', borderRadius: '8px', padding: '8px', cursor: 'pointer', color: '#7E22CE' }} title="Play Video"><FaVideo size={16} /></button>
                    )}
                </div>
            )
        },
        {
            headerName: 'AI Tools',
            width: 380,
            cellRenderer: (params: any) => (
                <div style={{ display: 'flex', gap: '6px', alignItems: 'center', height: '100%' }}>
                    <button onClick={() => handleTranslate(params.data, 'ca', 'shi')} disabled={actionLoadingId !== null} style={{ display: 'flex', alignItems: 'center', gap: '4px', padding: '6px 10px', fontSize: '11px', fontWeight: 600, background: '#E0E7FF', color: '#4338CA', border: 'none', borderRadius: '8px', cursor: 'pointer' }}><FaLanguage /> CA➔SH</button>
                    <button onClick={() => handleTranslate(params.data, 'shi', 'ca')} disabled={actionLoadingId !== null} style={{ display: 'flex', alignItems: 'center', gap: '4px', padding: '6px 10px', fontSize: '11px', fontWeight: 600, background: '#D1FAE5', color: '#059669', border: 'none', borderRadius: '8px', cursor: 'pointer' }}><FaLanguage /> SH➔CA</button>
                    <button onClick={() => handleTachelhitTTS(params.data)} disabled={actionLoadingId !== null} style={{ display: 'flex', alignItems: 'center', gap: '4px', padding: '6px 10px', fontSize: '11px', fontWeight: 600, background: '#FEF3C7', color: '#D97706', border: 'none', borderRadius: '8px', cursor: 'pointer' }}><FaRobot /> TTS</button>
                    {(params.data.audio_url || params.data.video_url) && (
                        <button 
                            onClick={() => {
                                const hasAudio = params.data.audio_url;
                                const hasVideo = params.data.video_url;
                                if (hasAudio && hasVideo) {
                                    if (confirm('Transcribe from VIDEO? (Cancel for AUDIO)')) {
                                        handleTranscribe(params.data, 'video');
                                    } else {
                                        handleTranscribe(params.data, 'audio');
                                    }
                                } else if (hasVideo) {
                                    handleTranscribe(params.data, 'video');
                                } else {
                                    handleTranscribe(params.data, 'audio');
                                }
                            }} 
                            disabled={actionLoadingId !== null} 
                            style={{ display: 'flex', alignItems: 'center', gap: '4px', padding: '6px 10px', fontSize: '11px', fontWeight: 600, background: '#FFEDD5', color: '#EA580C', border: 'none', borderRadius: '8px', cursor: 'pointer' }}
                        ><FaMagic /> Trans</button>
                    )}
                    <button 
                        onClick={async () => {
                            const media = params.data.audio_url || params.data.video_url;
                            if (media) {
                                setActionLoadingId(`down-${params.data.id}`);
                                await syncManager.downloadAndCacheMedia(media);
                                setActionLoadingId(null);
                                alert('Media downloaded for offline use!');
                            }
                        }}
                        disabled={actionLoadingId !== null || !(params.data.audio_url || params.data.video_url)}
                        style={{ display: 'flex', alignItems: 'center', gap: '4px', padding: '6px 10px', fontSize: '11px', fontWeight: 600, background: '#F3F4F6', color: '#4B5563', border: 'none', borderRadius: '8px', cursor: 'pointer' }}
                    ><FaSave /> Cache</button>
                </div>
            )
        },
        {
            headerName: 'Actions',
            width: 150,
            cellRenderer: (params: any) => (
                <div style={{ display: 'flex', gap: '8px', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
                    {onEditDrill && (
                        <button
                            onClick={() => onEditDrill(params.data)}
                            style={{ background: '#4f46e5', color: 'white', border: 'none', borderRadius: '8px', padding: '8px', cursor: 'pointer', display: 'flex', alignItems: 'center' }}
                            title="Edit"
                        >
                            <FaEdit size={16} />
                        </button>
                    )}
                    <button
                        onClick={() => handleDeleteIntent(params.data.id)}
                        style={{ background: '#FFF1F2', color: '#E11D48', border: 'none', borderRadius: '8px', padding: '8px', cursor: 'pointer', display: 'flex', alignItems: 'center' }}
                        title="Delete"
                    >
                        <FaTrash size={16} />
                    </button>
                </div>
            )
        }
    ];

    return (
        <div style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 120px)', padding: '20px' }}>
            <div style={{ marginBottom: '20px', display: 'flex', gap: '12px', alignItems: 'center', background: '#F9FAFB', padding: '15px', borderRadius: '12px', border: '1px solid #E5E7EB' }}>
                <span style={{ fontSize: '15px', fontWeight: 600, color: '#374151', marginRight: '10px' }}><FaCheckSquare style={{ verticalAlign: 'middle', marginTop: '-3px', marginRight: '5px' }} /> {selectedRows.length} items selected</span>
                <button 
                    onClick={handleBulkDelete} 
                    disabled={selectedRows.length === 0} 
                    style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '10px 20px', background: '#EF4444', color: 'white', border: 'none', borderRadius: '10px', cursor: 'pointer', opacity: selectedRows.length ? 1 : 0.5, fontWeight: 600, transition: 'all 0.2s' }}
                >
                    <FaTrash /> Bulk Delete
                </button>
                <button 
                    onClick={handleBulkEditTags} 
                    disabled={selectedRows.length === 0} 
                    style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '10px 20px', background: '#4F46E5', color: 'white', border: 'none', borderRadius: '10px', cursor: 'pointer', opacity: selectedRows.length ? 1 : 0.5, fontWeight: 600, transition: 'all 0.2s' }}
                >
                    <FaTag /> Bulk Edit Tags
                </button>
                <button 
                    onClick={() => setShowTestConfig(true)} 
                    disabled={selectedRows.length === 0} 
                    style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '10px 20px', background: '#10B981', color: 'white', border: 'none', borderRadius: '10px', cursor: 'pointer', opacity: selectedRows.length ? 1 : 0.5, fontWeight: 600, transition: 'all 0.2s' }}
                >
                    <FaPlus /> Create Practica
                </button>
            </div>
            <div className="ag-theme-alpine" style={{ flex: 1 }}>
                <AgGridReact
                    rowData={rowData}
                    columnDefs={columnDefs}
                    animateRows={true}
                    pagination={true}
                    paginationPageSize={50}
                    rowHeight={70}
                    theme="legacy"
                    rowSelection={{
                        mode: 'multiRow',
                        checkboxes: true,
                        headerCheckbox: true
                    }}
                    onSelectionChanged={(event) => {
                        setSelectedRows(event.api.getSelectedRows());
                    }}
                    onCellValueChanged={onCellValueChanged}
                    defaultColDef={{
                        resizable: true,
                        sortable: true,
                        suppressNavigable: false,
                        cellStyle: { display: 'flex', alignItems: 'center' }
                    }}
                />
            </div>

            {showTestConfig && (
                <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0,0,0,0.8)', zIndex: 30000, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <div style={{ background: 'white', borderRadius: '12px', width: '90%', maxWidth: '800px', maxHeight: '90vh', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
                        <TestConfigPanel 
                            onClose={() => setShowTestConfig(false)}
                            onTestCreated={() => {
                                setShowTestConfig(false);
                                if (window.confirm('Practica created successfully! Go to Tests Dashboard?')) {
                                    navigate('/tests');
                                }
                            }}
                            initialSelectedDrillIds={selectedRows.map(r => r.id)}
                        />
                    </div>
                </div>
            )}
        </div>
    );
}
