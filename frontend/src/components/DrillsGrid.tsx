import type React from 'react';
import '../agGridSetup';
import { useState, useEffect, useRef, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { AgGridReact } from 'ag-grid-react';
import type { ColDef } from 'ag-grid-community';
import axios from 'axios';
import TestConfigPanel from './TestConfigPanel';
import { useNavigate } from 'react-router-dom';
import { syncManager } from '../services/OfflineSyncManager';
import { Network } from '@capacitor/network';
import { Camera, CameraResultType, CameraSource } from '@capacitor/camera';
import { API_BASE, getMediaUrl } from '../config';
import AmbSo, { BaixaAudio } from './AmbSo';
import { audioSrc, baixaAudio } from '../services/audioLocal';
import { parseTopics, topicLabel } from '../utils/topics';
import { answerSafeFilter } from '../utils/media';
import { setSelectedDrillIds } from '../selection';
import SourceCredit from './SourceCredit';
import LaMaquina from './LaMaquina';
import {
    FaVolumeUp,
    FaVideo,
    FaLanguage,
    FaMagic,
    FaSave,
    FaEdit,
    FaTrash,
    FaCheckSquare,
    FaTag,
    FaPlus,
    FaMicrophone,
    FaCamera,
    FaPlay,
    FaLightbulb
} from 'react-icons/fa';
import RecordAudioModal from './RecordAudioModal';
import MicrofonMantingut, { type PerfilVeu } from './MicrofonMantingut';
// `api` dins d'aquest fitxer ja és el de la graella d'AG Grid; el nostre entra amb un altre nom.
import { api as servidor } from '../api';
import WordGloss from './WordGloss';
import { varietyShort, varietyLabel } from '../varieties';

// Import CSS structural definitions
import 'ag-grid-community/styles/ag-grid.css';
import 'ag-grid-community/styles/ag-theme-alpine.css';

import type { Drill } from '../types';
import { toast } from '../toast';
import { isMobileLayout } from '../utils/layout';
import AiAssistant from './AiAssistant';
import AiToolsMenu from './AiToolsMenu';
import { draftUsable, DRAFT_REJECTED_LABEL } from '../utils/drafts';

interface DrillsGridProps {
    rowData: Drill[];
    refreshData: () => Promise<void>;
    onEditDrill?: (drill: Drill) => void;
    /** 'error' = server unreachable and no local copy; 'cached' = showing the local copy */
    loadError?: 'error' | 'cached' | null;
    /** What is ticked right now, so the screen above can play just those (#201). */
    onSelectionChange?: (rows: Drill[]) => void;
}

export default function DrillsGrid({ rowData, refreshData, onEditDrill, loadError, onSelectionChange }: DrillsGridProps) {
    const [isMobile, setIsMobile] = useState(isMobileLayout);
    const [pendingDeleteId, setPendingDeleteId] = useState<number | null>(null);
    // Inline media preview (video/audio) opened from the grid or the cards.
    const [preview, setPreview] = useState<{ url: string; kind: 'video' | 'audio'; title?: string; drillId?: number } | null>(null);
    const [explainDrill, setExplainDrill] = useState<Drill | null>(null);
    // Card: Tifinagh face of a Latin-only reading (machine transliteration, labelled)
    const [cardTifinagh, setCardTifinagh] = useState<{ id: number; text: string } | null>(null);
    // Synthetic Tamazight voice on the card: an extra way to hear the phrase or one word,
    // never a replacement for the recording or the clip (those keep their own player).
    useEffect(() => {
        const d = preview?.drillId != null ? rowData.find((x) => x.id === preview.drillId) : undefined;
        if (!d) { setCardTifinagh(null); return; }
        const hasTifinagh = /[ⴰ-⵿]/.test(d.text_tachelhit || '');
        const source = hasTifinagh ? '' : (d.text_tachelhit_latin || d.text_tachelhit || d.text_tachelhit_suggested || '');
        if (!source.trim()) { setCardTifinagh(null); return; }
        let alive = true;
        axios.get(`${API_BASE}/transliterate`, { params: { text: source } })
            .then((r) => { if (alive && r.data?.tifinagh) setCardTifinagh({ id: d.id, text: r.data.tifinagh }); })
            .catch(() => { if (alive) setCardTifinagh(null); });
        return () => { alive = false; };
    }, [preview?.drillId, rowData]);
    const [askDrill, setAskDrill] = useState<Drill | null>(null);
    // Phone list: render the cards in slices of 40 as the learner scrolls. A thousand cards
    // with a picture each made the page crawl.
    const MOBILE_PAGE = 40;
    const [mobileLimit, setMobileLimit] = useState(MOBILE_PAGE);
    const moreRef = useRef<HTMLDivElement>(null);
    useEffect(() => { setMobileLimit(MOBILE_PAGE); }, [rowData]);
    useEffect(() => {
        const el = moreRef.current;
        if (!el || typeof IntersectionObserver === 'undefined') return;
        const io = new IntersectionObserver((entries) => {
            if (entries.some((e) => e.isIntersecting)) setMobileLimit((n) => Math.min(n + MOBILE_PAGE, rowData.length));
        }, { rootMargin: '600px 0px' });
        io.observe(el);
        return () => io.disconnect();
    }, [rowData.length, mobileLimit]);
    const [autoNext, setAutoNext] = useState(true); // keep playing the next clip when one ends
    const [reveal, setReveal] = useState(false); // meaning shown for the current clip (study mode hides it first)
    const [alwaysReveal, setAlwaysReveal] = useState(() => { try { return localStorage.getItem('preview.alwaysReveal') === '1'; } catch { return false; } });
    const autoNextTimer = useRef<number | null>(null);
    const setAlwaysRevealPersist = (v: boolean) => { setAlwaysReveal(v); try { localStorage.setItem('preview.alwaysReveal', v ? '1' : '0'); } catch { /* private mode */ } };
    const [selectedRows, setSelectedRows] = useState<Drill[]>([]);
    const [actionLoadingId, setActionLoadingId] = useState<string | null>(null);
    const gridApiRef = useRef<any>(null);
    const busyDrillId = actionLoadingId ? Number((actionLoadingId.match(/-(\d+)$/) || [])[1]) || null : null;
    // Highlight only the rows that change (the one that got busy, the one that stopped):
    // redrawing every row on each change froze the page.
    const lastBusyRef = useRef<number | null>(null);
    useEffect(() => {
        const api = gridApiRef.current;
        if (!api) return;
        const ids = new Set([busyDrillId, lastBusyRef.current].filter((x): x is number => x != null));
        lastBusyRef.current = busyDrillId;
        const nodes: any[] = [];
        api.forEachNode?.((n: any) => { if (n.data && ids.has(n.data.id)) nodes.push(n); });
        if (nodes.length) api.redrawRows?.({ rowNodes: nodes });
    }, [busyDrillId]);
    const getRowStyle = useCallback((p: { data?: Drill }) => (busyDrillId != null && p.data?.id === busyDrillId ? { background: 'var(--brand-gradient-soft)', boxShadow: 'inset 4px 0 0 var(--brand-1)' } : undefined), [busyDrillId]);
    // A refresh after an AI tool replaces the rows; keep the list where the person was reading.
    const refreshKeepingScroll = async () => {
        const viewport = document.querySelector('.ag-body-viewport') as HTMLElement | null;
        const top = viewport?.scrollTop ?? 0;
        await refreshData();
        requestAnimationFrame(() => { const v = document.querySelector('.ag-body-viewport') as HTMLElement | null; if (v && top) v.scrollTop = top; });
    };
    const [recordDrill, setRecordDrill] = useState<Drill | null>(null);
    // Qui grava: la seva varietat i el seu poble. Es demana UNA vegada i val per a totes les
    // targetes; sense això, cada frase tornaria a preguntar el que ja s'ha contestat (#370).
    const [perfilVeu, setPerfilVeu] = useState<PerfilVeu | null | undefined>(undefined);
    useEffect(() => {
        servidor.me()
            .then((m) => setPerfilVeu(m ? { variety: m.variety ?? null, region: m.region ?? null, is_native: m.is_native ?? null } : null))
            .catch(() => setPerfilVeu(null));
    }, []);
    const [showTestConfig, setShowTestConfig] = useState(false);
    const [mobileTestIds, setMobileTestIds] = useState<number[]>([]);
    const [pendingMedia, setPendingMedia] = useState<Record<number, { image?: string, audio?: Blob, audioUrl?: string, video?: Blob, videoUrl?: string }>>({});
    const navigate = useNavigate();

    // Track responsive screen resize configurations
    useEffect(() => {
        const handleResize = () => setIsMobile(isMobileLayout());
        window.addEventListener('resize', handleResize);
        return () => window.removeEventListener('resize', handleResize);
    }, []);

    // 🌐 Smart Non-Destructive Translation Pipeline
    const handleTranslate = async (drill: Drill, source: 'ca' | 'shi', target: 'ca' | 'shi') => {
        console.log(`[DrillsGrid] Starting translation: ${source} -> ${target} for drill ${drill.id}`);
        const sourceText = source === 'ca' ? drill.text_catalan : drill.text_tachelhit;
        if (!sourceText) {
            toast.error(`Introdueix primer el text en ${source === 'ca' ? 'català' : 'amazic'}.`);
            return;
        }

        const targetField = target === 'shi' ? 'text_tachelhit' : 'text_catalan';
        const loadingKey = `trans-${drill.id}-${targetField}`;
        setActionLoadingId(loadingKey);

        try {
            const status = await Network.getStatus();
            if (!status.connected) {
                toast.error("⚠️ La traducció requereix una connexió a internet activa.");
                return;
            }

            console.log(`[DrillsGrid] API Call: ${API_BASE}/translate`);
            const res = await axios.post(`${API_BASE}/translate`, {
                text: sourceText,
                source_lang: source,
                target_lang: target
            });
            console.log('[DrillsGrid] API Success:', res.data.translated_text);

            const preservedText = (res.data.translated_text || '').trim();
            if (!preservedText) { toast.error('La traducció ha retornat un text buit.'); return; }

            // Commit the safe update to the backend DB
            // Never overwrite text that is already there (it may be attested or captured
            // from a source): the machine output goes to the suggestion field instead.
            const existing = (target === 'shi' ? drill.text_tachelhit : drill.text_catalan)?.trim();
            const field = existing ? `${targetField}_suggested` : targetField;
            await axios.put(`${API_BASE}/drills/${drill.id}`, { [field]: preservedText });
            if (existing) toast.success(`Suggeriment IA desat, el text «${existing}» es manté: ${preservedText}`);
            else toast.success(`Traducció: ${preservedText}`);
            await refreshKeepingScroll();
        } catch (err) {
            console.error('Translation workflow crashed:', err);
            toast.error("No s'ha pogut completar la traducció amb IA.");
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
            toast.error('No hi ha cap mèdia per transcriure.');
            return;
        }

        const loadingKey = `scribe-${drill.id}`;
        setActionLoadingId(loadingKey);

        try {
            const status = await Network.getStatus();
            if (!status.connected) {
                console.warn('[Transcribe] Offline. Aborting.');
                toast.error("⚠️ La transcripció de veu requereix una connexió a internet.");
                return;
            }

            // Ensure we use the proper media URL for transcription
            const fullMediaUrl = getMediaUrl(mediaSource);
            console.log(`[Transcribe] Posting to backend with URL: ${fullMediaUrl}`);

            const response = await axios.post(`${API_BASE}/transcribe/`, {
                audio_url: fullMediaUrl,
                drill_id: drill.id, // its variety picks the listener; its meaning and speaker text guide it
            });

            console.log('[Transcribe] Backend response received:', response.data);

            let freshTranscription = response.data.corrected_transcription;

            const fromVideo = sourceType === 'video' || (!sourceType && mediaSource === drill.video_url);
            const heard = (freshTranscription || '').trim();
            // one or two letters is noise, not a reading: do not save it
            if (heard.replace(/[^\p{L}]/gu, '').length < 3) { toast.error(fromVideo ? "No s'ha entès res del so del vídeo. Prova amb la gravació." : "No s'ha entès res de la gravació."); return; }
            const preservedText = fromVideo ? `${heard} · (del vídeo)` : heard;

            console.log(`[Transcribe] Saving updated Tachelhit text: ${preservedText}`);
            // Same rule as translation: keep what is there, store ASR as a suggestion.
            const existingTa = (drill.text_tachelhit || '').trim();
            await axios.put(`${API_BASE}/drills/${drill.id}`, existingTa ? { text_tachelhit_suggested: preservedText } : { text_tachelhit: preservedText });
            if (existingTa) toast.success(`Transcripció desada com a suggeriment (es manté «${existingTa}»): ${preservedText}`);
            await refreshKeepingScroll();
            console.log('[Transcribe] Success.');
        } catch (error) {
            console.error('[Transcribe] Transcription loop error:', error);
            toast.error('El procés de transcripció amb IA ha fallat.');
        } finally {
            setActionLoadingId(null);
        }
    };


    const onCellValueChanged = async (params: any) => {
        const { data, colDef, newValue } = params;
        const field = colDef.field;
        try {
            await axios.put(`${API_BASE}/drills/${data.id}`, { [field]: newValue });
        } catch (err: any) {
            toast.error(`No s'ha pogut desar el canvi: ${err?.response?.data?.detail || err?.message || 'error'}`);
            refreshData();
        }
    };

    const handleBulkDelete = async () => {
        if (selectedRows.length === 0) return;
        if (!window.confirm(`Segur que vols eliminar ${selectedRows.length} drills?`)) return;

        try {
            const status = await Network.getStatus();
            for (const drill of selectedRows) {
                if (status.connected && drill.id < 1000000) {
                    await axios.delete(`${API_BASE}/drills/${drill.id}`);
                }
            }
            toast.success('Eliminació massiva completada.');
            await refreshKeepingScroll();
        } catch (error) {
            toast.error('Una o més eliminacions han fallat.');
        }
    };

    // Bulk tags: a dialog instead of a prompt. Adding is the default and never touches the
    // other tags (the API's '+tag' / '-tag' forms); replacing them all is a separate, explicit
    // action. Tags are stored comma-separated in `tag`.
    const [showTagEditor, setShowTagEditor] = useState(false);
    const [tagInput, setTagInput] = useState('');
    const [tagBusy, setTagBusy] = useState(false);
    // The drills the dialog works on: fixed when it opens, because refreshing the list after
    // a change clears the grid selection (the dialog must survive its own refresh).
    const [tagTargets, setTagTargets] = useState<number[]>([]);
    const splitTags = (t?: string | null) => (t || '').split(',').map((x) => x.trim()).filter(Boolean);
    const handleBulkEditTags = () => {
        if (selectedRows.length === 0) return;
        setTagTargets(selectedRows.map((d) => d.id));
        setTagInput('');
        setShowTagEditor(true);
    };
    const applyTagChange = async (op: '+' | '-' | '=', tag: string) => {
        const t = tag.trim();
        if (!t && op !== '=') return;
        setTagBusy(true);
        try {
            for (const id of tagTargets) {
                await axios.put(`${API_BASE}/drills/${id}`, { tag: op === '=' ? (t || '') : `${op}${t}` });
            }
            toast.success(op === '+' ? `Etiqueta «${t}» afegida a ${tagTargets.length} drills.` : op === '-' ? `Etiqueta «${t}» treta de ${tagTargets.length} drills.` : `Etiquetes substituïdes a ${tagTargets.length} drills.`);
            setTagInput('');
            await refreshKeepingScroll();
            if (op === '=') setShowTagEditor(false);
        } catch (error) {
            toast.error("L'actualització d'etiquetes ha fallat.");
        } finally {
            setTagBusy(false);
        }
    };

    // 🗑️ Handle Deletion Security Check Sequence
    // The trash button used to open a "password" dialog ('borrar', hard-coded
    // client-side) that was only rendered in the mobile layout, so on desktop
    // nothing happened. One in-app confirmation now, in both layouts.
    const handleDeleteIntent = (id: number) => setPendingDeleteId(id);

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
            toast.error("No s'ha pogut desar el mèdia.");
        } finally {
            setActionLoadingId(null);
        }
    };

    const executeDeletePipeline = async (id: number) => {
        setPendingDeleteId(null);
        try {
            // Removes from the local cache, queues/executes the server delete,
            // and waits for a sync attempt so refreshData sees the result.
            await syncManager.deleteDrill(id);

            toast.success('🗑️ Drill eliminat correctament.');
            await refreshKeepingScroll();
        } catch (error) {
            console.error('Failed to complete delete request:', error);
            toast.error("S'ha produït un error en intentar eliminar el registre.");
        } finally {
            setPendingDeleteId(null);
        }
    };

    const overlayStyle = { position: 'fixed' as const, inset: 0, background: 'rgba(15,23,42,0.6)', backdropFilter: 'blur(4px)', zIndex: 99999, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '20px' };

    const deleteDialog = pendingDeleteId !== null && (
        <div style={overlayStyle} onClick={() => setPendingDeleteId(null)}>
            <div onClick={(e) => e.stopPropagation()} style={{ background: 'var(--surface)', padding: '28px', borderRadius: 'var(--r-xl)', width: '100%', maxWidth: '360px', boxShadow: 'var(--shadow-xl)', textAlign: 'center' }}>
                <div style={{ fontSize: '40px', marginBottom: '12px' }}>🗑️</div>
                <h3 style={{ margin: '0 0 8px 0', fontSize: '19px', fontWeight: 800, color: 'var(--text)', fontFamily: 'var(--font-display)' }}>Eliminar el drill #{pendingDeleteId}?</h3>
                <p style={{ margin: '0 0 20px 0', fontSize: '14px', color: 'var(--text-soft)' }}>S'esborra de manera permanent, amb el seu àudio i vídeo.</p>
                <div style={{ display: 'flex', gap: '10px' }}>
                    <button onClick={() => setPendingDeleteId(null)} style={{ flex: 1, padding: '12px', background: 'var(--surface)', color: 'var(--text-soft)', border: '1px solid var(--border)', borderRadius: 'var(--r-md)', fontWeight: 700, cursor: 'pointer' }}>Cancel·la</button>
                    <button autoFocus onClick={() => executeDeletePipeline(pendingDeleteId)} style={{ flex: 1, padding: '12px', background: 'var(--rose)', color: 'white', border: 'none', borderRadius: 'var(--r-md)', fontWeight: 700, cursor: 'pointer', boxShadow: 'var(--shadow-sm)' }}>Elimina</button>
                </div>
            </div>
        </div>
    );

    // Tags present on the selection (with how many of the selected drills carry each) and
    // every tag in the list, for the suggestions.
    const targetRows = rowData.filter((d) => tagTargets.includes(d.id));
    const selectionTags = (() => {
        const m = new Map<string, number>();
        for (const d of targetRows) for (const t of splitTags(d.tag)) m.set(t, (m.get(t) || 0) + 1);
        return [...m.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));
    })();
    const allTags = [...new Set(rowData.flatMap((d) => splitTags(d.tag)))].sort((a, b) => a.localeCompare(b));
    const tagDialog = showTagEditor && (
        <div style={overlayStyle} onClick={() => !tagBusy && setShowTagEditor(false)}>
            <div onClick={(e) => e.stopPropagation()} style={{ background: 'var(--surface)', padding: '24px', borderRadius: 'var(--r-xl)', width: '100%', maxWidth: '420px', boxShadow: 'var(--shadow-xl)', display: 'flex', flexDirection: 'column', maxHeight: '85vh' }}>
                <h3 style={{ margin: '0 0 4px 0', fontSize: '19px', fontWeight: 800, color: 'var(--text)', fontFamily: 'var(--font-display)', flexShrink: 0 }}>Etiquetes de {tagTargets.length} drills</h3>
                <p style={{ margin: '0 0 14px 0', fontSize: '13px', color: 'var(--text-soft)', flexShrink: 0 }}>Afegir una etiqueta no toca les que ja hi són. Treu-ne una amb la ✕.</p>
                {/* many drills selected = many tags: this list scrolls so the field below stays reachable */}
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginBottom: '14px', minHeight: '28px', overflowY: 'auto', maxHeight: '38vh', flexShrink: 1 }}>
                    {selectionTags.length === 0 && <span style={{ fontSize: '13px', color: 'var(--text-muted)' }}>Cap etiqueta encara.</span>}
                    {selectionTags.map(([t, n]) => (
                        <span key={t} style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', padding: '4px 6px 4px 10px', borderRadius: 'var(--r-pill)', border: '1px solid var(--border)', background: 'var(--surface-2)', fontSize: '12.5px', fontWeight: 700, color: 'var(--text)' }}>
                            {t}{n < tagTargets.length && <span style={{ fontWeight: 600, color: 'var(--text-muted)' }}>{n}/{tagTargets.length}</span>}
                            <button type="button" onClick={() => applyTagChange('-', t)} disabled={tagBusy} aria-label={`Treu l'etiqueta ${t}`} title={`Treu «${t}» dels drills seleccionats`} style={{ border: 'none', background: 'transparent', color: 'var(--rose)', cursor: 'pointer', fontWeight: 800, padding: '0 4px', lineHeight: 1 }}>✕</button>
                        </span>
                    ))}
                </div>
                <form onSubmit={(e) => { e.preventDefault(); applyTagChange('+', tagInput); }} style={{ display: 'flex', gap: '8px', flexShrink: 0 }}>
                    <input
                        autoFocus
                        list="bulk-tag-options"
                        value={tagInput}
                        onChange={(e) => setTagInput(e.target.value)}
                        placeholder="Etiqueta nova o existent…"
                        aria-label="Etiqueta a afegir"
                        disabled={tagBusy}
                        style={{ flex: 1, minWidth: 0, padding: '10px 12px', borderRadius: 'var(--r-md)', border: '1px solid var(--border)', background: 'var(--surface-2)', color: 'var(--text)', fontSize: '14px' }}
                    />
                    <datalist id="bulk-tag-options">{allTags.map((t) => <option key={t} value={t} />)}</datalist>
                    <button type="submit" disabled={tagBusy || !tagInput.trim()} style={{ padding: '10px 16px', background: 'var(--brand-1)', color: '#fff', border: 'none', borderRadius: 'var(--r-md)', fontWeight: 700, cursor: 'pointer', opacity: tagBusy || !tagInput.trim() ? 0.6 : 1 }}>{tagBusy ? '…' : 'Afegeix'}</button>
                </form>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '16px', gap: '8px', flexShrink: 0 }}>
                    <button type="button" disabled={tagBusy || !tagInput.trim()} onClick={() => { if (window.confirm(`Substituir TOTES les etiquetes dels ${tagTargets.length} drills per «${tagInput.trim()}»?`)) applyTagChange('=', tagInput); }} style={{ padding: '8px 10px', background: 'transparent', color: 'var(--text-muted)', border: 'none', fontSize: '12.5px', cursor: 'pointer', textDecoration: 'underline', opacity: tagBusy || !tagInput.trim() ? 0.5 : 1 }}>Substitueix-les totes per aquesta</button>
                    <button type="button" onClick={() => setShowTagEditor(false)} disabled={tagBusy} style={{ padding: '10px 16px', background: 'var(--surface)', color: 'var(--text-soft)', border: '1px solid var(--border)', borderRadius: 'var(--r-md)', fontWeight: 700, cursor: 'pointer' }}>Tanca</button>
                </div>
            </div>
        </div>
    );

    // Walk the current (filtered, ordered) list: a story or lesson plays in video order.
    const playable = rowData.filter((d) => d.video_url || d.audio_url);
    const previewIndex = preview?.drillId != null ? playable.findIndex((d) => d.id === preview.drillId) : -1;
    const openPreviewOf = (d: Drill) => {
        const url = d.video_url ? getMediaUrl(d.video_url) : audioSrc(d.audio_url!);
        setPreview({ url, kind: d.video_url ? 'video' : 'audio', title: d.text_catalan || d.text_tachelhit || `Drill #${d.id}`, drillId: d.id });
        setReveal(false);
        if (autoNextTimer.current) { window.clearTimeout(autoNextTimer.current); autoNextTimer.current = null; }
    };
    // Clip finished: listen -> read -> meaning -> next. With the meaning already on
    // screen we move on at once; otherwise reveal it and give three seconds to read.
    const onClipEnded = () => {
        if (!autoNext || explainDrill || askDrill) return;  // the tutor is open: stay on this drill
        if (alwaysReveal || reveal) { previewStep(1); return; }
        setReveal(true);
        autoNextTimer.current = window.setTimeout(() => previewStep(1), 3000);
    };
    const previewDrill = preview?.drillId != null ? playable.find((d) => d.id === preview.drillId) : undefined;
    // The study card under the player: what you hear, in letters, while you listen;
    // the meaning only when you ask for it (or always, for review sessions).
    const previewCard = previewDrill && (() => {
        const d = previewDrill;
        const latin = d.text_tachelhit_latin || d.text_tachelhit;
        const tifinagh = d.text_tachelhit && d.text_tachelhit !== latin ? d.text_tachelhit : null;
        const draft = !latin && draftUsable(d) ? d.text_tachelhit_suggested : '';
        const shown = reveal || alwaysReveal;
        const timeSpan = d.video_start_time != null && d.video_end_time != null ? `${Math.round(d.video_start_time)}s–${Math.round(d.video_end_time)}s` : null;
        return (
            <div style={{ padding: '12px 14px 4px', background: 'var(--surface)', borderTop: '1px solid var(--border)' }}>
                <div style={{ fontSize: '19px', fontWeight: 700, color: 'var(--text)', lineHeight: 1.3, display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
                    {latin ? (
                        <span>
                            {latin}
                        </span>
                    ) : null}
                    {!latin && (draft ? <span style={{ fontStyle: 'italic', color: 'var(--text-muted)' }}>{draft} <span style={{ fontSize: '11px' }}>(esborrany IA)</span></span> : <span style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>{d.text_tachelhit_suggested ? DRAFT_REJECTED_LABEL : 'sense transcripció'}</span>)}
                </div>
                {tifinagh && <div style={{ fontSize: '15px', color: 'var(--text-soft)', marginTop: '2px' }}>{tifinagh}</div>}
                {!tifinagh && cardTifinagh?.id === d.id && (
                    <div style={{ fontSize: '15px', color: 'var(--text-soft)', marginTop: '2px', fontFamily: 'var(--font-tifinagh)' }}>
                        {cardTifinagh.text} <span style={{ fontSize: '11px', color: 'var(--text-muted)', fontFamily: 'var(--font-body)' }}>(transliteració automàtica)</span>
                    </div>
                )}
                {shown ? (
                    <div style={{ marginTop: '8px', display: 'flex', flexDirection: 'column', gap: '2px' }}>
                        {d.text_catalan && <div style={{ fontSize: '15px', color: 'var(--text)' }}>{d.text_catalan}</div>}
                        <WordGloss drill={d} size="sm" />
                        {d.text_arabic && <div dir="rtl" style={{ fontSize: '15px', color: 'var(--text-soft)', textAlign: 'right' }}>{d.text_arabic}</div>}
                        {!d.text_catalan && !d.text_arabic && <div style={{ fontSize: '13px', color: 'var(--text-muted)', fontStyle: 'italic' }}>sense traducció</div>}
                        <LaMaquina drill={d} />
                    </div>
                ) : (
                    <button onClick={() => setReveal(true)} style={{ marginTop: '8px', padding: '7px 12px', background: 'var(--surface-2)', border: '1px solid var(--border)', borderRadius: 'var(--r-md)', fontWeight: 700, cursor: 'pointer', color: 'var(--text)', fontSize: '13px' }}>
                        Mostra el significat
                    </button>
                )}
                <div style={{ marginTop: '8px', display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap', fontSize: '11.5px', color: 'var(--text-muted)' }}>
                    <span>#{d.id}</span>
                    {d.variety && <span>{varietyShort(d.variety)}</span>}
                    {timeSpan && <span>{timeSpan}</span>}
                    {d.tag && <span>{d.tag}</span>}
                    {parseTopics(d.topics).map((t) => <span key={t} style={{ padding: '1px 7px', borderRadius: 'var(--r-pill)', background: 'var(--surface-2)', border: '1px solid var(--border)' }}>{topicLabel(t)}</span>)}
                    <SourceCredit drill={d} compact />
                    <button
                      onClick={async () => {
                        try {
                          await axios.put(`${API_BASE}/drills/${d.id}`, { verified: !d.verified });
                          toast.success(d.verified ? 'Marca de verificat treta' : 'Drill verificat');
                          await refreshKeepingScroll();
                        } catch { toast.error('No s\'ha pogut desar'); }
                      }}
                      title={d.verified ? 'Verificat per un parlant · clica per treure la marca' : 'Marca aquest drill com a verificat (text i so correctes)'}
                      style={{ marginLeft: 'auto', padding: '2px 9px', borderRadius: 'var(--r-pill)', fontSize: '11.5px', fontWeight: 700, cursor: 'pointer',
                        border: `1px solid ${d.verified ? 'var(--emerald)' : 'var(--border)'}`, background: d.verified ? 'var(--emerald-soft)' : 'var(--surface)', color: d.verified ? 'var(--emerald)' : 'var(--text-soft)' }}
                    >
                      {d.verified ? '✓ Verificat' : 'Verifica'}
                    </button>
                </div>
            </div>
        );
    })();
    const previewStep = (delta: number) => {
        if (previewIndex < 0) return;
        const next = playable[previewIndex + delta];
        if (next) openPreviewOf(next);
    };

    useEffect(() => {
        if (!preview) return;
        const onKey = (e: KeyboardEvent) => {
            if (e.key === 'ArrowRight') previewStep(1);
            else if (e.key === 'ArrowLeft') previewStep(-1);
            else if (e.key === 'Escape') setPreview(null);
            else if (e.key === ' ' && !(e.target instanceof HTMLInputElement)) { /* space = reveal */ if (!reveal) { e.preventDefault(); setReveal(true); } }
        };
        window.addEventListener('keydown', onKey);
        return () => window.removeEventListener('keydown', onKey);
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [preview, previewIndex]);

    const previewDialog = preview && (
        <div style={overlayStyle} onClick={() => setPreview(null)}>
            <div onClick={(e) => e.stopPropagation()} style={{ background: '#000', borderRadius: 'var(--r-xl)', width: '100%', maxWidth: preview.kind === 'video' ? '720px' : '420px', boxShadow: 'var(--shadow-xl)', overflow: 'hidden' }}>
                {preview.kind === 'video' ? (
                    <video key={preview.url} src={preview.url} controls autoPlay playsInline onEnded={onClipEnded} style={{ display: 'block', width: '100%', maxHeight: '75vh', background: '#000' }} />
                ) : (
                    <>
                        {previewDrill?.image_url && (
                            <img src={getMediaUrl(previewDrill.image_url)} alt="" draggable={false}
                                style={{ display: 'block', width: '100%', maxHeight: '260px', objectFit: 'contain', background: '#000',
                                         filter: answerSafeFilter(previewDrill.image_url, !(reveal || alwaysReveal)), transition: 'filter 0.3s' }} />
                        )}
                        <audio key={preview.url} src={preview.url} controls autoPlay onEnded={onClipEnded} style={{ display: 'block', width: '100%', padding: '16px', background: 'var(--surface)' }} />
                    </>
                )}
                {previewCard}
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', padding: '10px 14px', background: 'var(--surface)', flexWrap: 'wrap' }}>
                    <button onClick={() => previewStep(-1)} disabled={previewIndex <= 0} aria-label="Drill anterior" title="Anterior (←)"
                        style={{ padding: '8px 12px', background: 'var(--surface-2)', border: '1px solid var(--border)', borderRadius: 'var(--r-md)', fontWeight: 700, cursor: previewIndex <= 0 ? 'not-allowed' : 'pointer', opacity: previewIndex <= 0 ? 0.5 : 1, color: 'var(--text)' }}>◀</button>
                    <button onClick={() => previewStep(1)} disabled={previewIndex < 0 || previewIndex >= playable.length - 1} aria-label="Drill següent" title="Següent (→)"
                        style={{ padding: '8px 12px', background: 'var(--surface-2)', border: '1px solid var(--border)', borderRadius: 'var(--r-md)', fontWeight: 700, cursor: 'pointer', opacity: (previewIndex < 0 || previewIndex >= playable.length - 1) ? 0.5 : 1, color: 'var(--text)' }}>▶</button>
                    <span style={{ flex: 1, fontSize: '13px', color: 'var(--text-soft)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {previewIndex >= 0 ? `${previewIndex + 1}/${playable.length}` : (preview.title || '')}
                    </span>
                    <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12.5px', color: 'var(--text-soft)', cursor: 'pointer' }}>
                        <input type="checkbox" checked={autoNext} onChange={(e) => setAutoNext(e.target.checked)} /> Seguit
                    </label>
                    <label title="Mostra la traducció sense haver de tocar" style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12.5px', color: 'var(--text-soft)', cursor: 'pointer' }}>
                        <input type="checkbox" checked={alwaysReveal} onChange={(e) => setAlwaysRevealPersist(e.target.checked)} /> Significat sempre
                    </label>
                    {(() => {
                        const d = rowData.find((x) => x.id === preview.drillId);
                        if (!d) return null;
                        const btn: React.CSSProperties = { padding: '8px 12px', background: 'var(--surface-2)', border: '1px solid var(--border)', borderRadius: 'var(--r-md)', fontWeight: 700, fontSize: '13px', cursor: 'pointer', color: 'var(--text)' };
                        return (
                            <>
                                {(d.text_tachelhit || d.text_tachelhit_suggested || d.text_tachelhit_latin) && (
                                    <button onClick={() => setExplainDrill(d)} title="Paraula per paraula, construcció i drills semblants" style={btn}>💡 Explica'm</button>
                                )}
                                <button onClick={() => setAskDrill(d)} title="Pregunta a l'assistent sobre aquest drill: paraules, conjugació, pronunciació" style={btn}>💬 Pregunta</button>
                            </>
                        );
                    })()}
                    <a href={preview.url} target="_blank" rel="noreferrer" style={{ fontSize: '13px', color: 'var(--brand-1)', fontWeight: 700 }}>Obre en una pestanya</a>
                    <button onClick={() => setPreview(null)} style={{ padding: '8px 14px', background: 'var(--surface-2)', border: '1px solid var(--border)', borderRadius: 'var(--r-md)', fontWeight: 700, cursor: 'pointer', color: 'var(--text)' }}>Tanca</button>
                </div>
            </div>
        </div>
    );

    // 📱 MOBILE INTERFACE: Card stream equipped with translation and transcription capabilities
    if (isMobile) {
        return (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', padding: '4px' }}>
                {explainDrill && <AiAssistant drillId={explainDrill.id} drillLabel={explainDrill.text_catalan || explainDrill.text_tachelhit || `#${explainDrill.id}`} autoAction="explain" onClose={() => setExplainDrill(null)} />}
                {rowData.length > 0 && rowData.length <= 60 && (
                    <button onClick={() => { setMobileTestIds(rowData.map((d) => d.id)); setShowTestConfig(true); }}
                        style={{ alignSelf: 'flex-start', padding: '9px 14px', background: 'var(--brand-gradient-soft)', color: 'var(--brand-1)', border: '1px solid var(--border)', borderRadius: 'var(--r-pill)', fontWeight: 700, fontSize: '13px', cursor: 'pointer' }}>
                        <FaPlus style={{ marginRight: '6px' }} />Crea pràctica amb aquests {rowData.length} drills
                    </button>
                )}
                {showTestConfig && createPortal(
                    <div style={{ position: 'fixed', inset: 0, backgroundColor: 'rgba(15,23,42,0.7)', zIndex: 30000, display: 'flex', alignItems: 'stretch', justifyContent: 'center' }}>
                        <div style={{ background: 'var(--surface)', width: '100%', maxHeight: '100dvh', overflow: 'auto' }}>
                            <TestConfigPanel
                                onClose={() => setShowTestConfig(false)}
                                onTestCreated={(id) => { setShowTestConfig(false); navigate(`/tests/${id}`); }}
                                initialSelectedDrillIds={mobileTestIds}
                            />
                        </div>
                    </div>, document.body)}
                {rowData.length === 0 && (
                    <div style={{ textAlign: 'center', padding: '48px 20px', background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--r-xl)', boxShadow: 'var(--shadow-sm)', color: 'var(--text-soft)' }}>
                        <div style={{ fontSize: '44px', marginBottom: '12px' }}>{loadError === 'error' ? '📡' : '📭'}</div>
                        <div style={{ fontSize: '17px', fontWeight: 700, color: 'var(--text)', marginBottom: '4px', fontFamily: 'var(--font-display)' }}>{loadError === 'error' ? "No s'han pogut carregar els drills" : 'Encara no hi ha cap drill'}</div>
                        <div style={{ fontSize: '14px', color: 'var(--text-muted)' }}>{loadError === 'error' ? "El servidor no respon (pot estar despertant-se). Torna-ho a provar d'aquí a uns segons." : "Crea el teu primer drill per veure'l aquí."}</div>
                        {loadError === 'error' && <button onClick={() => refreshData()} style={{ marginTop: '14px', padding: '10px 18px', borderRadius: 'var(--r-pill)', border: 'none', background: 'var(--brand-gradient)', color: '#fff', fontWeight: 700, cursor: 'pointer' }}>Torna-ho a provar</button>}
                    </div>
                )}
                {rowData.slice(0, mobileLimit).map((drill) => (
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
                                #{drill.id >= 1000000 ? 'Sinc. pendent' : drill.id}
                            </span>
                            {drill.tag && (
                                <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', background: 'var(--brand-gradient-soft)', color: 'var(--brand-1)', padding: '5px 12px', borderRadius: 'var(--r-pill)', fontSize: '12px', fontWeight: 700 }}>
                                    <FaTag size={11} /> {drill.tag}
                                </span>
                            )}
                            {drill.variety && (
                                <span title={varietyLabel(drill.variety)} style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', background: 'var(--saffron-soft)', color: 'var(--saffron-strong)', padding: '5px 10px', borderRadius: 'var(--r-pill)', fontSize: '11px', fontWeight: 800, letterSpacing: '0.03em' }}>
                                    {varietyShort(drill.variety)}{drill.region ? ` · ${drill.region}` : ''}
                                </span>
                            )}
                        </div>

                        {/* Content text blocks */}
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                            <div style={{ fontSize: '16px', color: 'var(--text)', fontWeight: 600, lineHeight: 1.4 }}>{drill.text_catalan || <span style={{ color: 'var(--text-muted)', fontWeight: 400 }}>Sense català</span>}</div>
                            <div style={{ fontSize: '17px', color: 'var(--brand-1)', fontWeight: 700, fontFamily: 'var(--font-tifinagh)', lineHeight: 1.5 }}>{drill.text_tachelhit || (drill.text_tachelhit_suggested && draftUsable(drill)
                              ? <span title="Esborrany automàtic (no verificat)" style={{ color: 'var(--text-muted)', fontWeight: 500, fontStyle: 'italic' }}>{drill.text_tachelhit_suggested}<span style={{ display: 'block', fontSize: 10, letterSpacing: '0.04em', textTransform: 'uppercase', fontStyle: 'normal', fontFamily: 'var(--font-sans)' }}>esborrany</span></span>
                              : <span style={{ color: 'var(--text-muted)', fontWeight: 400, fontFamily: 'var(--font-sans)' }}>{drill.text_tachelhit_suggested ? DRAFT_REJECTED_LABEL : 'Sense amazic'}</span>)}</div>
                            {drill.text_arabic && (
                                <div style={{ fontSize: '16px', color: 'var(--emerald)', direction: 'rtl', textAlign: 'right', fontWeight: 600, lineHeight: 1.5 }}>{drill.text_arabic}</div>
                            )}
                        </div>

                        {/* La foto, amb la veu a sobre.
                            La mida d'un botó ha de dir què val. El que més es prem d'una targeta
                            és sentir com sona la frase, i estava en una fila de cinc botons del
                            mateix pes, al costat d'una veu de màquina i d'un botó per mirar una
                            foto. Ara va gran, a sobre de la imatge, i no comparteix fila amb res. */}
                        {(drill.image_url || pendingMedia[drill.id]?.image) && (
                            <div style={{ position: 'relative' }}>
                                <img
                                    src={pendingMedia[drill.id]?.image || getMediaUrl(drill.image_url)}
                                    alt="Imatge del drill"
                                    loading="lazy"
                                    decoding="async"
                                    onError={(e) => { e.currentTarget.style.display = 'none'; }}
                                    style={{ width: '100%', height: '180px', objectFit: 'contain', background: 'var(--surface-2)', borderRadius: 'var(--r-lg)', border: '1px solid var(--border)' }}
                                />
                                {drill.audio_url && (
                                    <AmbSo url={drill.audio_url} dins><button
                                        onClick={() => {
                                            const audio = new Audio(audioSrc(drill.audio_url!));
                                            audio.play().catch(e => console.error('Playback fail:', e));
                                        }}
                                        aria-label="Escolta com sona"
                                        style={{
                                            position: 'absolute', left: '50%', top: '50%', transform: 'translate(-50%,-50%)',
                                            width: '64px', height: '64px', borderRadius: '50%', border: 'none',
                                            background: 'var(--brand-gradient)', color: '#fff', cursor: 'pointer',
                                            display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                                            boxShadow: '0 4px 16px rgba(15,23,42,0.35)', padding: 0
                                        }}
                                    >
                                        <FaPlay size={22} style={{ marginLeft: 4 }} />
                                    </button></AmbSo>
                                )}
                            </div>
                        )}

                        {/* La resta, petita i sense text.
                            Cinc botons amb text i el mateix pes no deien quin importava. El que
                            porta text ara és el que la gent no endevinaria d'una icona. */}
                        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                            {/* Sense foto, la veu no té on anar a sobre: es queda gran aquí. */}
                            {drill.audio_url && !(drill.image_url || pendingMedia[drill.id]?.image) && (
                                <AmbSo url={drill.audio_url} dins><button
                                    onClick={() => {
                                        const audio = new Audio(audioSrc(drill.audio_url!));
                                        audio.play().catch(e => console.error('Playback fail:', e));
                                    }}
                                    style={{
                                        flex: 1,
                                        padding: '14px',
                                        background: 'var(--brand-gradient)',
                                        border: 'none',
                                        borderRadius: 'var(--r-md)',
                                        fontSize: '15px',
                                        fontWeight: 800,
                                        color: '#fff',
                                        cursor: 'pointer',
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'center',
                                        gap: '10px'
                                    }}
                                >
                                    <FaPlay /> Escolta com sona
                                </button></AmbSo>
                            )}
                            {(drill.text_tachelhit || drill.text_tachelhit_suggested || drill.text_tachelhit_latin) && (
                                <button
                                    onClick={() => setExplainDrill(drill)}
                                    aria-label="Explica'm la frase paraula per paraula"
                                    title="Explica'm la frase paraula per paraula"
                                    style={{ width: '38px', height: '38px', flexShrink: 0, padding: 0, background: 'var(--surface-2)', border: '1px solid var(--border)', borderRadius: 'var(--r-pill)', color: 'var(--text)', cursor: 'pointer', display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}
                                >
                                    <FaLightbulb size={15} />
                                </button>
                            )}
                            {drill.video_url && (
                                <button
                                    onClick={() => openPreviewOf(drill)}
                                    aria-label="Mira el vídeo d'on surt"
                                    title="Mira el vídeo d'on surt"
                                    style={{ width: '38px', height: '38px', flexShrink: 0, padding: 0, background: 'var(--brand-gradient-soft)', border: '1px solid var(--border)', borderRadius: 'var(--r-pill)', color: 'var(--brand-2)', cursor: 'pointer', display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}
                                >
                                    <FaVideo size={15} />
                                </button>
                            )}
                            {/* Afegir-hi una foto és una feina d'edició, no una cosa que es faci
                                mentre s'estudia: icona i prou, i a la punta. */}
                            <BaixaAudio drill={drill} style={{ width: '38px', height: '38px', flexShrink: 0, padding: 0, background: 'var(--surface-2)', border: '1px solid var(--border)', borderRadius: 'var(--r-pill)', color: 'var(--text-soft)', cursor: 'pointer', display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }} />
                            <button
                                onClick={() => handleQuickPhoto(drill.id)}
                                aria-label="Posa-hi una foto"
                                title="Posa-hi una foto"
                                style={{ width: '38px', height: '38px', flexShrink: 0, marginLeft: 'auto', padding: 0, background: 'var(--emerald-soft)', color: 'var(--emerald)', border: '1px solid var(--emerald)', borderRadius: 'var(--r-pill)', cursor: 'pointer', display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}
                            ><FaCamera size={15} /></button>
                        </div>


                        <SourceCredit drill={drill} />
                        <hr style={{ border: 'none', height: '1px', background: 'var(--border)', margin: '2px 0' }} />

                        {/* Posar-hi la teva veu.
                            Es deia «Veus» i ocupava el mateix que mirar una foto. És la feina que
                            fa créixer la biblioteca —i la que cap màquina no pot fer per
                            nosaltres—, de manera que va sola, ampla, i diu què fa.
                            El gest de mantenir premut arriba amb el #370; mentre no hi sigui, el
                            botó no el promet: un botó que diu una cosa i en fa una altra és
                            pitjor que un que diu poc. */}
                        <div style={{ marginBottom: '8px' }}>
                            <MicrofonMantingut
                                drill={drill}
                                perfil={perfilVeu}
                                onCalPerfil={() => setRecordDrill(drill)}
                            />
                        </div>

                        {/* Previews for pending media */}
                        {pendingMedia[drill.id] && (
                            <div style={{ background: 'var(--amber-soft)', padding: '12px', borderRadius: 'var(--r-md)', border: '1px dashed var(--amber)', marginBottom: '8px' }}>
                                <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--amber-strong)', marginBottom: '6px' }}>Canvis pendents:</div>
                                <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                                    {pendingMedia[drill.id].image && <img src={pendingMedia[drill.id].image} alt="" style={{ width: '40px', height: '40px', borderRadius: 'var(--r-sm)', objectFit: 'cover' }} />}
                                    {pendingMedia[drill.id].audioUrl && <button onClick={() => new Audio(pendingMedia[drill.id].audioUrl).play()} aria-label="Reprodueix l'àudio" style={{ background: 'none', border: 'none', fontSize: '18px', cursor: 'pointer', color: 'var(--sky)' }}><FaVolumeUp /></button>}
                                    {pendingMedia[drill.id].videoUrl && <video src={pendingMedia[drill.id].videoUrl} controls playsInline preload="metadata" aria-label="Vídeo pendent" style={{ width: '96px', height: '54px', borderRadius: 'var(--r-sm)', background: '#000' }} />}
                                    <div style={{ flex: 1 }}></div>
                                    <button
                                        onClick={() => handleQuickSave(drill)}
                                        disabled={actionLoadingId !== null}
                                        style={{ background: 'var(--emerald)', color: 'white', border: 'none', borderRadius: 'var(--r-sm)', padding: '8px 14px', fontWeight: 700, fontSize: '13px', opacity: actionLoadingId ? 0.5 : 1, cursor: actionLoadingId ? 'not-allowed' : 'pointer' }}
                                    >
                                        {actionLoadingId === `save-${drill.id}` ? '...' : '💾 Desa ara'}
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
                                        <FaEdit /> Edita
                                    </button>
                                )}
                                <button
                                    onClick={() => handleDeleteIntent(drill.id)}
                                    style={{ display: 'flex', alignItems: 'center', gap: '6px', background: 'var(--rose-soft)', color: 'var(--rose)', border: '1px solid var(--rose)', borderRadius: 'var(--r-md)', padding: '10px 18px', fontSize: '14px', fontWeight: 700, cursor: 'pointer' }}
                                >
                                    <FaTrash /> Elimina
                                </button>
                            </div>
                        </div>
                    </div>
                ))}
                {mobileLimit < rowData.length && (
                    <div ref={moreRef} style={{ textAlign: 'center', padding: '12px', color: 'var(--text-muted)', fontSize: '13px' }}>
                        <button onClick={() => setMobileLimit((n) => Math.min(n + MOBILE_PAGE, rowData.length))} style={{ padding: '10px 18px', borderRadius: 'var(--r-pill)', border: '1px solid var(--border)', background: 'var(--surface)', color: 'var(--text)', fontWeight: 700, cursor: 'pointer' }}>
                            Mostra'n més · {rowData.length - mobileLimit} restants
                        </button>
                    </div>
                )}

                {/* Password confirmation pop-up */}
                {deleteDialog && createPortal(deleteDialog, document.body)}{tagDialog && createPortal(tagDialog, document.body)}
                {previewDialog && createPortal(previewDialog, document.body)}
            </div>
        );
    }

    // 🖥️ DESKTOP INTERFACE: Standard High-Performance spreadsheet view
    const columnDefs: ColDef<Drill>[] = [
        // Not editable: a drill's id is not a field of the drill. Typing in this cell used to
        // change the number on screen, send it, and have the server ignore it — so until you
        // refreshed it looked like it had worked.
        { field: 'id', headerName: 'ID', width: 80, sortable: true, editable: false },
        { field: 'verified', headerName: '✓', width: 52, sortable: true, headerTooltip: 'Verificat per un parlant',
          cellRenderer: (p: any) => (p.value ? <span title="Verificat" style={{ color: 'var(--emerald)', fontWeight: 800 }}>✓</span> : null) },
        {
            field: 'image_url',
            headerName: 'Preview',
            width: 90,
            cellRenderer: (p: any) => p.value ? <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}><img src={getMediaUrl(p.value)} alt="Imatge del drill" onError={(e) => { e.currentTarget.style.display = 'none'; }} style={{ width: '60px', height: '60px', objectFit: 'cover', borderRadius: 'var(--r-sm)', border: '1px solid var(--border)' }} /></div> : null
        },
        { field: 'text_catalan', headerName: 'Català', flex: 2, minWidth: 150, filter: true, wrapText: true, autoHeight: true, editable: true,
          tooltipValueGetter: (p: { data?: Drill }) => p.data?.text_catalan_suggested ? `Suggeriment IA: ${p.data.text_catalan_suggested}` : undefined,
          cellRenderer: (p: { value?: string; data?: Drill }) => <span>{p.value}{p.data?.text_catalan_suggested ? <span title={`Suggeriment IA: ${p.data.text_catalan_suggested}`} style={{ marginLeft: 6, fontSize: 12 }}>💡</span> : null}</span>,
          cellStyle: { 'line-height': '20px', 'padding-top': '10px', 'padding-bottom': '10px', 'color': 'var(--text)', 'font-weight': '600' } },
        { field: 'text_tachelhit', headerName: 'Tamazight', flex: 2, minWidth: 150, filter: true, wrapText: true, autoHeight: true, editable: true,
          tooltipValueGetter: (p: { data?: Drill }) => p.data?.text_tachelhit_suggested ? `Suggeriment IA: ${p.data.text_tachelhit_suggested}` : undefined,
          cellRenderer: (p: { value?: string; data?: Drill }) => p.value
            ? <span>{p.value}{p.data?.text_tachelhit_suggested ? <span title="Lectura automàtica (no substitueix el text del parlant)" style={{ display: 'block', fontSize: 12, fontWeight: 500, fontStyle: 'italic', color: 'var(--text-muted)', fontFamily: 'var(--font-body)' }}>💡 {p.data.text_tachelhit_suggested}</span> : null}</span>
            : (p.data?.text_tachelhit_suggested && draftUsable(p.data)
                ? <span title="Esborrany automàtic (no verificat): edita el drill per confirmar-lo" style={{ color: 'var(--text-muted)', fontStyle: 'italic', fontWeight: 500 }}>{p.data.text_tachelhit_suggested}{p.data.text_tachelhit_latin ? <span style={{ display: 'block', fontSize: 11, fontFamily: 'var(--font-body)' }}>{p.data.text_tachelhit_latin}</span> : null}<span style={{ display: 'block', fontSize: 10, letterSpacing: '0.04em', textTransform: 'uppercase' }}>esborrany</span></span>
                : (p.data?.text_tachelhit_suggested ? <span style={{ color: 'var(--text-muted)', fontSize: 11, fontFamily: 'var(--font-body)', fontWeight: 500 }}>{DRAFT_REJECTED_LABEL}</span> : null)),
          cellStyle: { 'line-height': '20px', 'padding-top': '10px', 'padding-bottom': '10px', 'font-family': 'var(--font-tifinagh)', 'color': 'var(--brand-1)', 'font-weight': '700' } },
        { field: 'text_arabic', headerName: 'العربية', flex: 2, minWidth: 150, filter: true, wrapText: true, autoHeight: true, editable: true, cellStyle: { 'line-height': '20px', 'padding-top': '10px', 'padding-bottom': '10px', 'direction': 'rtl', 'color': 'var(--emerald)', 'font-weight': '600' } },
        { field: 'tag', headerName: 'Etiqueta', width: 120, filter: true, editable: true },
        {
            headerName: 'Multimèdia',
            width: 120,
            cellRenderer: (params: any) => (
                <div style={{ display: 'flex', gap: '10px', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
                    {params.data.audio_url && (
                        <AmbSo url={params.data.audio_url}><button onClick={() => new Audio(audioSrc(params.data.audio_url)).play()} style={{ background: 'var(--brand-gradient-soft)', border: '1px solid var(--border)', borderRadius: 'var(--r-sm)', padding: '8px', cursor: 'pointer', color: 'var(--brand-1)' }} title="Reprodueix la gravació" aria-label="Reprodueix la gravació"><FaVolumeUp size={16} /></button></AmbSo>
                    )}
                    {params.data.audio_tts_url && (
                        <button onClick={() => new Audio(audioSrc(params.data.audio_tts_url)).play()} style={{ background: 'var(--surface-2)', border: '1px solid var(--border)', borderRadius: 'var(--r-sm)', padding: '6px 7px', cursor: 'pointer', color: 'var(--text-soft)', fontSize: '11px', fontWeight: 800 }} title="Veu sintètica (català)" aria-label="Veu sintètica en català">CA</button>
                    )}
                    {params.data.video_url && (
                        <button onClick={() => openPreviewOf(params.data)} style={{ background: 'var(--brand-gradient-soft)', border: '1px solid var(--border)', borderRadius: 'var(--r-sm)', padding: '8px', cursor: 'pointer', color: 'var(--brand-2)' }} title="Reprodueix el vídeo" aria-label="Reprodueix el vídeo"><FaVideo size={16} /></button>
                    )}
                </div>
            )
        },
        {
            headerName: 'Font',
            width: 170,
            cellRenderer: (params: { data: Drill }) => (
                <div style={{ display: 'flex', alignItems: 'center', height: '100%', overflow: 'hidden' }}>
                    <SourceCredit drill={params.data} compact />
                </div>
            )
        },
        {
            headerName: 'Eines IA',
            width: 150,
            cellRenderer: (params: any) => {
                const d: Drill = params.data;
                const media = d.audio_url || d.video_url;
                // The speaker's recording first (clean, close to the mouth); the video's sound only
                // when there is no recording, or on purpose from its own menu item.
                const transcribe = () => handleTranscribe(d, d.audio_url ? 'audio' : 'video');
                const save = async () => {
                    if (!media) return;
                    setActionLoadingId(`down-${d.id}`);
                    const fet = d.audio_url ? await baixaAudio(d) : !!(await syncManager.downloadAndCacheMedia(media, 'video'));
                    setActionLoadingId(null);
                    if (fet) toast.success('Mèdia descarregat per a ús fora de línia!');
                    else toast.error("No s'ha pogut desar: només es pot a l'app, i amb connexió.");
                };
                return (
                    <div style={{ display: 'flex', alignItems: 'center', height: '100%' }}>
                        <AiToolsMenu busy={actionLoadingId !== null} tools={[
                            { key: 'explain', icon: '💡', title: "Explica'm la frase", description: 'Paraula per paraula, com està construïda i altres drills amb les mateixes paraules.', run: () => setExplainDrill(d), disabled: !(d.text_tachelhit || d.text_tachelhit_suggested || d.text_tachelhit_latin) },
                            { key: 'ask', icon: '💬', title: "Pregunta a l'assistent", description: 'Xat sobre aquest drill: gramàtica, pronunciació, variants. Es basa en el compendi amazic.', run: () => setAskDrill(d) },
                            { key: 'ca-ta', icon: <span style={{ color: 'var(--brand-1)', display: 'flex' }}><FaLanguage /></span>, title: 'Tradueix català → amazic', description: 'Proposa la frase en amazic. Si ja hi ha text, la proposta es desa com a suggeriment i no el toca.', run: () => handleTranslate(d, 'ca', 'shi'), disabled: !d.text_catalan },
                            { key: 'ta-ca', icon: <span style={{ color: 'var(--emerald)', display: 'flex' }}><FaLanguage /></span>, title: 'Tradueix amazic → català', description: 'Proposa la traducció catalana. Si ja n\'hi ha, va com a suggeriment.', run: () => handleTranslate(d, 'shi', 'ca'), disabled: !d.text_tachelhit },
                            { key: 'transcribe', icon: <span style={{ color: 'var(--sky)', display: 'flex' }}><FaMagic /></span>, title: "Transcriu l'àudio", description: 'La màquina escolta la gravació i escriu el que sent. Va com a esborrany; el text del parlant es manté.', run: transcribe, disabled: !media },
                            ...(d.audio_url && d.video_url ? [{ key: 'transcribe-video', icon: <span style={{ color: 'var(--sky)', display: 'flex' }}><FaMagic /></span>, title: 'Transcriu el so del vídeo', description: 'Escolta el vídeo en lloc de la gravació. També va com a esborrany.', run: () => handleTranscribe(d, 'video'), disabled: actionLoadingId !== null }] : []),
                            { key: 'voices', icon: <span style={{ color: 'var(--rose)', display: 'flex' }}><FaMicrophone /></span>, title: 'Veus del drill', description: 'Escolta o grava parlants reals dient aquesta frase, cadascú amb la seva varietat.', run: () => setRecordDrill(d) },
                            { key: 'save', icon: <span style={{ color: 'var(--text-muted)', display: 'flex' }}><FaSave /></span>, title: 'Desa fora de línia', description: 'Guarda l\'àudio o el vídeo al dispositiu per practicar sense connexió.', run: save, disabled: !media },
                        ]} />
                    </div>
                );
            }
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
                            title="Edita"
                            aria-label="Edita"
                        >
                            <FaEdit size={16} />
                        </button>
                    )}
                    <button
                        onClick={() => handleDeleteIntent(params.data.id)}
                        style={{ background: 'var(--rose-soft)', color: 'var(--rose)', border: '1px solid var(--rose)', borderRadius: 'var(--r-sm)', padding: '8px', cursor: 'pointer', display: 'flex', alignItems: 'center' }}
                        title="Elimina"
                        aria-label="Elimina"
                    >
                        <FaTrash size={16} />
                    </button>
                </div>
            )
        }
    ];

    return (
        <div style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 120px)', padding: '20px' }}>
            <div style={{ marginBottom: '16px', display: 'flex', gap: '10px', alignItems: 'center', background: 'var(--surface)', padding: '12px 16px', borderRadius: 'var(--r-lg)', border: '1px solid var(--border)' }}>
                <span style={{ fontSize: '14px', fontWeight: 700, color: selectedRows.length ? 'var(--text)' : 'var(--text-muted)', marginRight: 'auto', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <FaCheckSquare style={{ color: selectedRows.length ? 'var(--brand-1)' : 'var(--text-muted)' }} /> {selectedRows.length} seleccionats
                </span>
                <button
                    onClick={() => setShowTestConfig(true)}
                    disabled={selectedRows.length === 0}
                    style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '9px 16px', background: 'var(--brand-1)', color: '#fff', border: '1px solid transparent', borderRadius: 'var(--r-md)', cursor: selectedRows.length ? 'pointer' : 'not-allowed', opacity: selectedRows.length ? 1 : 0.45, fontWeight: 700, fontSize: '13px' }}
                >
                    <FaPlus /> Crea pràctica
                </button>
                <button
                    onClick={handleBulkEditTags}
                    disabled={selectedRows.length === 0}
                    style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '9px 16px', background: 'var(--surface-2)', color: 'var(--text-soft)', border: '1px solid var(--border)', borderRadius: 'var(--r-md)', cursor: selectedRows.length ? 'pointer' : 'not-allowed', opacity: selectedRows.length ? 1 : 0.45, fontWeight: 700, fontSize: '13px' }}
                >
                    <FaTag /> Edita etiquetes
                </button>
                <button
                    onClick={handleBulkDelete}
                    disabled={selectedRows.length === 0}
                    title="Elimina els drills seleccionats"
                    style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '9px 16px', background: 'var(--surface)', color: 'var(--rose)', border: '1px solid var(--rose)', borderRadius: 'var(--r-md)', cursor: selectedRows.length ? 'pointer' : 'not-allowed', opacity: selectedRows.length ? 1 : 0.45, fontWeight: 700, fontSize: '13px' }}
                >
                    <FaTrash /> Elimina
                </button>
            </div>
            {rowData.length === 0 ? (
                <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <div style={{ textAlign: 'center', padding: '56px 40px', background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--r-xl)', boxShadow: 'var(--shadow-sm)', maxWidth: '420px' }}>
                        <div style={{ fontSize: '52px', marginBottom: '16px' }}>{loadError === 'error' ? '📡' : '📭'}</div>
                        <h3 style={{ margin: '0 0 8px 0', fontSize: '20px', fontWeight: 800, color: 'var(--text)', fontFamily: 'var(--font-display)' }}>{loadError === 'error' ? "No s'han pogut carregar els drills" : 'Encara no hi ha cap drill'}</h3>
                        {loadError === 'error' && <p style={{ margin: '0 0 12px 0', fontSize: '14px', color: 'var(--text-muted)' }}>El servidor no respon (pot estar despertant-se).</p>}
                        {loadError === 'error' && <button onClick={() => refreshData()} style={{ padding: '10px 18px', borderRadius: 'var(--r-pill)', border: 'none', background: 'var(--brand-gradient)', color: '#fff', fontWeight: 700, cursor: 'pointer' }}>Torna-ho a provar</button>}
                        <p style={{ margin: 0, fontSize: '14px', color: 'var(--text-muted)' }}>Crea el teu primer drill per veure'l aquí.</p>
                    </div>
                </div>
            ) : (
            <div className="ag-theme-alpine" style={{ flex: 1 }}>
                <AgGridReact
                    rowData={rowData}
                    // The drill an AI tool is working on stays highlighted while it runs.
                    getRowStyle={getRowStyle}
                    onGridReady={(e) => { gridApiRef.current = e.api; }}
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
                    onRowDoubleClicked={(event: any) => {
                        // Double-click opens the drill's card (listen, read, meaning, next),
                        // except on the text cells, where a double-click still edits the text.
                        const d: Drill | undefined = event.data;
                        const col = event.column;
                        if (!d || (col && col.getColDef().editable)) return;
                        if (d.video_url || d.audio_url) openPreviewOf(d); else onEditDrill?.(d);
                    }}
                    onSelectionChanged={(event) => {
                        const rows = event.api.getSelectedRows();
                        setSelectedRows(rows);
                        onSelectionChange?.(rows);
                        setSelectedDrillIds(rows.map((r: Drill) => r.id));
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
            )}

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
            {explainDrill && <AiAssistant drillId={explainDrill.id} drillLabel={explainDrill.text_catalan || explainDrill.text_tachelhit || `#${explainDrill.id}`} autoAction="explain" onClose={() => setExplainDrill(null)} />}
            {askDrill && <AiAssistant drillId={askDrill.id} drillLabel={askDrill.text_catalan || askDrill.text_tachelhit || `#${askDrill.id}`} onClose={() => setAskDrill(null)} />}
            {recordDrill && (
                <RecordAudioModal
                    drill={recordDrill}
                    onClose={() => setRecordDrill(null)}
                    onSaved={() => { refreshData(); }}
                />
            )}
            {deleteDialog && createPortal(deleteDialog, document.body)}{tagDialog && createPortal(tagDialog, document.body)}
            {previewDialog && createPortal(previewDialog, document.body)}
        </div>
    );
}
