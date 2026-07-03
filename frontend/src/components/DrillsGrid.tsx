import '../agGridSetup';
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
    FaPlus
} from 'react-icons/fa';

// Import CSS structural definitions
import 'ag-grid-community/styles/ag-grid.css';
import 'ag-grid-community/styles/ag-theme-alpine.css';

import type { Drill } from '../types';

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
    const [pendingMedia, setPendingMedia] = useState<Record<number, { image?: string, audio?: Blob, audioUrl?: string, video?: Blob, videoUrl?: string }>>({});
    const navigate = useNavigate();

    // Track responsive screen resize configurations
    useEffect(() => {
        const handleResize = () => setIsMobile(window.innerWidth < 768 || /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent));
        window.addEventListener('resize', handleResize);
        return () => window.removeEventListener('resize', handleResize);
    }, []);

    // 🌐 Smart Non-Destructive Translation Pipeline
    const handleTranslate = async (drill: Drill, source: 'ca' | 'shi', target: 'ca' | 'shi') => {
        console.log(`[DrillsGrid] Starting translation: ${source} -> ${target} for drill ${drill.id}`);
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

            console.log(`[DrillsGrid] API Call: ${API_BASE}/translate`);
            const res = await axios.post(`${API_BASE}/translate`, {
                text: sourceText,
                source_lang: source,
                target_lang: target
            });
            console.log('[DrillsGrid] API Success:', res.data.translated_text);

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
            // Removes from the local cache, queues/executes the server delete,
            // and waits for a sync attempt so refreshData sees the result.
            await syncManager.deleteDrill(id);

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
                {rowData.length === 0 && (
                    <div style={{ textAlign: 'center', padding: '48px 20px', background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--r-xl)', boxShadow: 'var(--shadow-sm)', color: 'var(--text-soft)' }}>
                        <div style={{ fontSize: '44px', marginBottom: '12px' }}>📭</div>
                        <div style={{ fontSize: '17px', fontWeight: 700, color: 'var(--text)', marginBottom: '4px' }}>No drills yet</div>
                        <div style={{ fontSize: '14px', color: 'var(--text-muted)' }}>Create your first drill to see it here.</div>
                    </div>
                )}
                {rowData.map((drill) => (
                    <div
                        key={drill.id}
                        style={{
                            background: 'var(--surface)',
                            borderRadius: 'var(--r-xl)',
                            padding: '18px',
                            boxShadow: 'var(--shadow-sm)',
                            border: '1px solid var(--border)',
                            display: 'flex',
                            flexDirection: 'column',
                            gap: '14px',
                            position: 'relative'
                        }}
                    >
                        {/* Header Row */}
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <span style={{ fontSize: '12px', fontWeight: 700, color: 'var(--text-muted)' }}>
                                #{drill.id >= 1000000 ? 'Offline Sync' : drill.id}
                            </span>
                            {drill.tag && (
                                <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', background: 'var(--brand-gradient-soft)', color: 'var(--brand-1)', padding: '5px 12px', borderRadius: 'var(--r-pill)', fontSize: '12px', fontWeight: 700 }}>
                                    <FaTag size={11} /> {drill.tag}
                                </span>
                            )}
                        </div>

                        {/* Content text blocks */}
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                            <div style={{ fontSize: '16px', color: 'var(--text)', fontWeight: 600, lineHeight: 1.4 }}>{drill.text_catalan || <span style={{ color: 'var(--text-muted)', fontWeight: 400 }}>No Catalan</span>}</div>
                            <div style={{ fontSize: '17px', color: 'var(--brand-1)', fontWeight: 700, fontFamily: 'var(--font-tifinagh)', lineHeight: 1.5 }}>{drill.text_tachelhit || <span style={{ color: 'var(--text-muted)', fontWeight: 400, fontFamily: 'var(--font-sans)' }}>No Tachelhit</span>}</div>
                            {drill.text_arabic && (
                                <div style={{ fontSize: '16px', color: 'var(--emerald)', direction: 'rtl', textAlign: 'right', fontWeight: 600, lineHeight: 1.5 }}>{drill.text_arabic}</div>
                            )}
                        </div>

                        {/* Thumbnail View */}
                        {(drill.image_url || pendingMedia[drill.id]?.image) && (
                            <div style={{ position: 'relative' }}>
                                <img
                                    src={pendingMedia[drill.id]?.image || getMediaUrl(drill.image_url)}
                                    alt="Media thumbnail"
                                    style={{ width: '100%', height: '160px', objectFit: 'cover', borderRadius: 'var(--r-lg)', border: '1px solid var(--border)' }}
                                />
                                <div style={{ position: 'absolute', top: '10px', right: '10px', background: 'rgba(15,23,42,0.55)', backdropFilter: 'blur(4px)', borderRadius: 'var(--r-pill)', width: '32px', height: '32px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'white', fontSize: '14px' }}>🖼️</div>
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
                                        padding: '11px',
                                        background: 'var(--brand-gradient-soft)',
                                        border: '1px solid var(--border)',
                                        borderRadius: 'var(--r-md)',
                                        fontSize: '14px',
                                        fontWeight: 700,
                                        color: 'var(--brand-1)',
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
                                        padding: '11px',
                                        background: 'var(--amber-soft)',
                                        border: '1px solid var(--amber)',
                                        borderRadius: 'var(--r-md)',
                                        fontSize: '14px',
                                        fontWeight: 700,
                                        color: 'var(--amber-strong)',
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
                                        padding: '11px',
                                        background: 'var(--brand-gradient-soft)',
                                        border: '1px solid var(--border)',
                                        borderRadius: 'var(--r-md)',
                                        fontSize: '14px',
                                        fontWeight: 700,
                                        color: 'var(--brand-2)',
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


                        <hr style={{ border: 'none', height: '1px', background: 'var(--border)', margin: '2px 0' }} />

                        {/* Quick Update Row */}
                        <div style={{ display: 'flex', gap: '8px', marginBottom: '8px' }}>
                            <button
                                onClick={() => handleQuickPhoto(drill.id)}
                                style={{ flex: 1, padding: '11px', background: 'var(--emerald-soft)', color: 'var(--emerald)', border: '1px solid var(--emerald)', borderRadius: 'var(--r-md)', fontSize: '14px', fontWeight: 700, cursor: 'pointer' }}
                            >📷 Photo</button>
                            <button
                                onClick={() => handleQuickAudio(drill.id)}
                                style={{ flex: 1, padding: '11px', background: actionLoadingId === `rec-${drill.id}` ? 'var(--rose-soft)' : 'var(--sky-soft)', color: actionLoadingId === `rec-${drill.id}` ? 'var(--rose)' : 'var(--sky)', border: `1px solid ${actionLoadingId === `rec-${drill.id}` ? 'var(--rose)' : 'var(--sky)'}`, borderRadius: 'var(--r-md)', fontSize: '14px', fontWeight: 700, cursor: 'pointer' }}
                            >
                                {actionLoadingId === `rec-${drill.id}` ? '⏹ Stop' : '🎙 Audio'}
                            </button>
                        </div>

                        {/* Previews for pending media */}
                        {pendingMedia[drill.id] && (
                            <div style={{ background: 'var(--amber-soft)', padding: '12px', borderRadius: 'var(--r-md)', border: '1px dashed var(--amber)', marginBottom: '8px' }}>
                                <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--amber-strong)', marginBottom: '6px' }}>Pending Updates:</div>
                                <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                                    {pendingMedia[drill.id].image && <img src={pendingMedia[drill.id].image} style={{ width: '40px', height: '40px', borderRadius: 'var(--r-sm)', objectFit: 'cover' }} />}
                                    {pendingMedia[drill.id].audioUrl && <button onClick={() => new Audio(pendingMedia[drill.id].audioUrl).play()} style={{ background: 'none', border: 'none', fontSize: '20px', cursor: 'pointer' }}>🔊</button>}
                                    {pendingMedia[drill.id].videoUrl && <button onClick={() => window.open(pendingMedia[drill.id].videoUrl, '_blank')} style={{ background: 'none', border: 'none', fontSize: '20px', cursor: 'pointer' }}>🎬</button>}
                                    <div style={{ flex: 1 }}></div>
                                    <button
                                        onClick={() => handleQuickSave(drill)}
                                        disabled={actionLoadingId !== null}
                                        style={{ background: 'var(--emerald)', color: 'white', border: 'none', borderRadius: 'var(--r-sm)', padding: '8px 14px', fontWeight: 700, fontSize: '13px', cursor: 'pointer' }}
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
                                        style={{ display: 'flex', alignItems: 'center', gap: '6px', background: 'var(--brand-gradient)', color: 'white', border: 'none', borderRadius: 'var(--r-md)', padding: '10px 18px', fontSize: '14px', fontWeight: 700, cursor: 'pointer', boxShadow: 'var(--shadow-brand)' }}
                                    >
                                        <FaEdit /> Edit
                                    </button>
                                )}
                                <button
                                    onClick={() => handleDeleteIntent(drill.id)}
                                    style={{ display: 'flex', alignItems: 'center', gap: '6px', background: 'var(--rose-soft)', color: 'var(--rose)', border: '1px solid var(--rose)', borderRadius: 'var(--r-md)', padding: '10px 18px', fontSize: '14px', fontWeight: 700, cursor: 'pointer' }}
                                >
                                    <FaTrash /> Delete
                                </button>
                            </div>
                        </div>
                    </div>
                ))}

                {/* Password confirmation pop-up */}
                {showPasswordModal && (
                    <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(15,23,42,0.6)', backdropFilter: 'blur(4px)', zIndex: 99999, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '20px' }}>
                        <div style={{ background: 'var(--surface)', padding: '28px', borderRadius: 'var(--r-xl)', width: '100%', maxWidth: '360px', boxShadow: 'var(--shadow-xl)', textAlign: 'center' }}>
                            <div style={{ fontSize: '40px', marginBottom: '12px' }}>🔒</div>
                            <h3 style={{ margin: '0 0 8px 0', fontSize: '19px', fontWeight: 800, color: 'var(--text)' }}>Security Verification</h3>
                            <p style={{ margin: '0 0 20px 0', fontSize: '14px', color: 'var(--text-soft)' }}>Enter the deletion password to proceed.</p>

                            <input
                                type="password"
                                placeholder="Enter password"
                                value={passwordInput}
                                onChange={(e) => setPasswordInput(e.target.value)}
                                onKeyDown={(e) => e.key === 'Enter' && verifyPasswordAndConfirm()}
                                style={{ width: '100%', padding: '12px 14px', fontSize: '16px', border: '1px solid var(--border)', background: 'var(--surface-2)', borderRadius: 'var(--r-md)', marginBottom: '18px', outline: 'none', textAlign: 'center', color: 'var(--text)' }}
                                autoFocus
                            />

                            <div style={{ display: 'flex', gap: '10px' }}>
                                <button
                                    onClick={() => { setShowPasswordModal(false); setPasswordInput(''); }}
                                    style={{ flex: 1, padding: '12px', background: 'var(--surface)', color: 'var(--text-soft)', border: '1px solid var(--border)', borderRadius: 'var(--r-md)', fontWeight: 700, cursor: 'pointer' }}
                                >
                                    Cancel
                                </button>
                                <button
                                    onClick={verifyPasswordAndConfirm}
                                    style={{ flex: 1, padding: '12px', background: 'var(--rose)', color: 'white', border: 'none', borderRadius: 'var(--r-md)', fontWeight: 700, cursor: 'pointer', boxShadow: 'var(--shadow-sm)' }}
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
            cellRenderer: (p: any) => p.value ? <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}><img src={getMediaUrl(p.value)} style={{ width: '60px', height: '60px', objectFit: 'cover', borderRadius: 'var(--r-sm)', border: '1px solid var(--border)' }} /></div> : null
        },
        { field: 'text_catalan', headerName: 'Català', flex: 2, minWidth: 150, filter: true, wrapText: true, autoHeight: true, editable: true, cellStyle: { 'line-height': '20px', 'padding-top': '10px', 'padding-bottom': '10px', 'color': 'var(--text)', 'font-weight': '600' } },
        { field: 'text_tachelhit', headerName: 'Tachelhit', flex: 2, minWidth: 150, filter: true, wrapText: true, autoHeight: true, editable: true, cellStyle: { 'line-height': '20px', 'padding-top': '10px', 'padding-bottom': '10px', 'font-family': 'var(--font-tifinagh)', 'color': 'var(--brand-1)', 'font-weight': '700' } },
        { field: 'text_arabic', headerName: 'العربية', flex: 2, minWidth: 150, filter: true, wrapText: true, autoHeight: true, editable: true, cellStyle: { 'line-height': '20px', 'padding-top': '10px', 'padding-bottom': '10px', 'direction': 'rtl', 'color': 'var(--emerald)', 'font-weight': '600' } },
        { field: 'tag', headerName: 'Etiqueta', width: 120, filter: true, editable: true },
        {
            headerName: 'Multimèdia',
            width: 120,
            cellRenderer: (params: any) => (
                <div style={{ display: 'flex', gap: '10px', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
                    {params.data.audio_url && (
                        <button onClick={() => new Audio(getMediaUrl(params.data.audio_url)).play()} style={{ background: 'var(--brand-gradient-soft)', border: '1px solid var(--border)', borderRadius: 'var(--r-sm)', padding: '8px', cursor: 'pointer', color: 'var(--brand-1)' }} title="Play Audio"><FaVolumeUp size={16} /></button>
                    )}
                    {params.data.video_url && (
                        <button onClick={() => window.open(getMediaUrl(params.data.video_url), '_blank')} style={{ background: 'var(--brand-gradient-soft)', border: '1px solid var(--border)', borderRadius: 'var(--r-sm)', padding: '8px', cursor: 'pointer', color: 'var(--brand-2)' }} title="Play Video"><FaVideo size={16} /></button>
                    )}
                </div>
            )
        },
        {
            headerName: 'Eines IA',
            width: 380,
            cellRenderer: (params: any) => (
                <div style={{ display: 'flex', gap: '6px', alignItems: 'center', height: '100%' }}>
                    <button onClick={() => handleTranslate(params.data, 'ca', 'shi')} disabled={actionLoadingId !== null} style={{ display: 'flex', alignItems: 'center', gap: '4px', padding: '7px 10px', fontSize: '11px', fontWeight: 700, background: 'var(--brand-gradient-soft)', color: 'var(--brand-1)', border: '1px solid var(--border)', borderRadius: 'var(--r-sm)', cursor: 'pointer' }}><FaLanguage /> CA➔SH</button>
                    <button onClick={() => handleTranslate(params.data, 'shi', 'ca')} disabled={actionLoadingId !== null} style={{ display: 'flex', alignItems: 'center', gap: '4px', padding: '7px 10px', fontSize: '11px', fontWeight: 700, background: 'var(--emerald-soft)', color: 'var(--emerald)', border: '1px solid var(--emerald)', borderRadius: 'var(--r-sm)', cursor: 'pointer' }}><FaLanguage /> SH➔CA</button>
                    <button onClick={() => handleTachelhitTTS(params.data)} disabled={actionLoadingId !== null} style={{ display: 'flex', alignItems: 'center', gap: '4px', padding: '7px 10px', fontSize: '11px', fontWeight: 700, background: 'var(--amber-soft)', color: 'var(--amber-strong)', border: '1px solid var(--amber)', borderRadius: 'var(--r-sm)', cursor: 'pointer' }}><FaRobot /> TTS</button>
                    {(params.data.audio_url || params.data.video_url) && (
                        <button
                            onClick={() => {
                                const hasAudio = params.data.audio_url;
                                const hasVideo = params.data.video_url;
                                if (hasAudio && hasVideo) {
                                    if (confirm('Transcripció des de VÍDEO? (Cancel·la per ÀUDIO)')) {
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
                            style={{ display: 'flex', alignItems: 'center', gap: '4px', padding: '7px 10px', fontSize: '11px', fontWeight: 700, background: 'var(--sky-soft)', color: 'var(--sky)', border: '1px solid var(--sky)', borderRadius: 'var(--r-sm)', cursor: 'pointer' }}
                        ><FaMagic /> Trans</button>
                    )}
                    <button
                        onClick={async () => {
                            const audio = params.data.audio_url;
                            const video = params.data.video_url;
                            const media = audio || video;
                            if (media) {
                                setActionLoadingId(`down-${params.data.id}`);
                                const mediaType = audio ? 'audio' : 'video';
                                await syncManager.downloadAndCacheMedia(media, mediaType);
                                setActionLoadingId(null);
                                alert('Mèdia descarregat per a ús fora de línia!');
                            }
                        }}
                        disabled={actionLoadingId !== null || !(params.data.audio_url || params.data.video_url)}
                        style={{ display: 'flex', alignItems: 'center', gap: '4px', padding: '7px 10px', fontSize: '11px', fontWeight: 700, background: 'var(--surface-2)', color: 'var(--text-soft)', border: '1px solid var(--border)', borderRadius: 'var(--r-sm)', cursor: 'pointer' }}
                    ><FaSave /> Cache</button>
                </div>
            )
        },
        {
            headerName: 'Accions',
            width: 150,
            cellRenderer: (params: any) => (
                <div style={{ display: 'flex', gap: '8px', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
                    {onEditDrill && (
                        <button
                            onClick={() => onEditDrill(params.data)}
                            style={{ background: 'var(--brand-gradient)', color: 'white', border: 'none', borderRadius: 'var(--r-sm)', padding: '8px', cursor: 'pointer', display: 'flex', alignItems: 'center', boxShadow: 'var(--shadow-brand)' }}
                            title="Edit"
                        >
                            <FaEdit size={16} />
                        </button>
                    )}
                    <button
                        onClick={() => handleDeleteIntent(params.data.id)}
                        style={{ background: 'var(--rose-soft)', color: 'var(--rose)', border: '1px solid var(--rose)', borderRadius: 'var(--r-sm)', padding: '8px', cursor: 'pointer', display: 'flex', alignItems: 'center' }}
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
            <div style={{ marginBottom: '20px', display: 'flex', gap: '12px', alignItems: 'center', background: 'var(--surface)', padding: '16px 18px', borderRadius: 'var(--r-xl)', border: '1px solid var(--border)', boxShadow: 'var(--shadow-sm)' }}>
                <span style={{ fontSize: '15px', fontWeight: 700, color: 'var(--text-soft)', marginRight: '10px' }}><FaCheckSquare style={{ verticalAlign: 'middle', marginTop: '-3px', marginRight: '5px', color: 'var(--brand-1)' }} /> {selectedRows.length} elements seleccionats</span>
                <button
                    onClick={handleBulkDelete}
                    disabled={selectedRows.length === 0}
                    style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '10px 20px', background: 'var(--rose)', color: 'white', border: 'none', borderRadius: 'var(--r-md)', cursor: 'pointer', opacity: selectedRows.length ? 1 : 0.5, fontWeight: 700, boxShadow: 'var(--shadow-sm)', transition: 'all 0.2s' }}
                >
                    <FaTrash /> Esborrar selecció
                </button>
                <button
                    onClick={handleBulkEditTags}
                    disabled={selectedRows.length === 0}
                    style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '10px 20px', background: 'var(--brand-gradient)', color: 'white', border: 'none', borderRadius: 'var(--r-md)', cursor: 'pointer', opacity: selectedRows.length ? 1 : 0.5, fontWeight: 700, boxShadow: 'var(--shadow-brand)', transition: 'all 0.2s' }}
                >
                    <FaTag /> Editar etiquetes
                </button>
                <button
                    onClick={() => setShowTestConfig(true)}
                    disabled={selectedRows.length === 0}
                    style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '10px 20px', background: 'var(--emerald)', color: 'white', border: 'none', borderRadius: 'var(--r-md)', cursor: 'pointer', opacity: selectedRows.length ? 1 : 0.5, fontWeight: 700, boxShadow: 'var(--shadow-sm)', transition: 'all 0.2s' }}
                >
                    <FaPlus /> Crear Pràctica
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
                <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(15,23,42,0.7)', backdropFilter: 'blur(4px)', zIndex: 30000, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <div style={{ background: 'var(--surface)', borderRadius: 'var(--r-xl)', width: '90%', maxWidth: '800px', maxHeight: '90vh', overflow: 'hidden', display: 'flex', flexDirection: 'column', boxShadow: 'var(--shadow-xl)' }}>
                        <TestConfigPanel
                            onClose={() => setShowTestConfig(false)}
                            onTestCreated={() => {
                                setShowTestConfig(false);
                                if (window.confirm('Pràctica creada correctament! Vols anar al panell de tests?')) {
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
