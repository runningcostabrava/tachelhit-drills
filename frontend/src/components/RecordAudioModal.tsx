import { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { FaMicrophone, FaStop, FaSave, FaUndo, FaTimes } from 'react-icons/fa';
import { API_BASE, getMediaUrl } from '../config';
import { toast } from '../toast';
import type { Drill } from '../types';

// Re-record a drill's Tachelhit audio (web MediaRecorder), upload it, and
// undo back to the previous recording. The "previous" URL is captured when the
// modal opens, so Desfés (ctrl-z) restores exactly what was there before.
export default function RecordAudioModal({ drill, onClose, onSaved }: {
  drill: Drill;
  onClose: () => void;
  onSaved: () => void;
}) {
  const originalUrl = useRef(drill.audio_url || '');
  const [recording, setRecording] = useState(false);
  const [blob, setBlob] = useState<Blob | null>(null);
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(false);
  const recRef = useRef<MediaRecorder | null>(null);
  const chunks = useRef<Blob[]>([]);

  useEffect(() => () => { if (blobUrl) URL.revokeObjectURL(blobUrl); }, [blobUrl]);

  const start = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      chunks.current = [];
      const mr = new MediaRecorder(stream);
      mr.ondataavailable = (e) => { if (e.data.size) chunks.current.push(e.data); };
      mr.onstop = () => {
        stream.getTracks().forEach((t) => t.stop());
        const b = new Blob(chunks.current, { type: mr.mimeType || 'audio/webm' });
        setBlob(b);
        setBlobUrl((prev) => { if (prev) URL.revokeObjectURL(prev); return URL.createObjectURL(b); });
      };
      recRef.current = mr;
      mr.start();
      setRecording(true);
    } catch {
      toast.error('No s\'ha pogut accedir al micròfon. Comprova els permisos del navegador.');
    }
  };

  const stop = () => { recRef.current?.stop(); setRecording(false); };

  const save = async () => {
    if (!blob) return;
    setBusy(true);
    try {
      const ext = blob.type.includes('webm') ? 'webm' : blob.type.includes('mp4') ? 'mp4' : 'ogg';
      const fd = new FormData();
      fd.append('file', blob, `rec_${drill.id}.${ext}`);
      const res = await fetch(`${API_BASE}/upload-media/${drill.id}/audio`, { method: 'POST', body: fd });
      if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || 'Error en pujar');
      setSaved(true);
      toast.success('Àudio actualitzat');
      onSaved();
    } catch (e: any) {
      toast.error(e.message || 'No s\'ha pogut desar l\'àudio');
    } finally { setBusy(false); }
  };

  const undo = async () => {
    setBusy(true);
    try {
      const res = await fetch(`${API_BASE}/drills/${drill.id}`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ audio_url: originalUrl.current }),
      });
      if (!res.ok) throw new Error('undo failed');
      toast.success('Restaurat l\'àudio anterior');
      onSaved();
      onClose();
    } catch {
      toast.error('No s\'ha pogut desfer');
    } finally { setBusy(false); }
  };

  return createPortal(
    <div role="dialog" aria-label="Torna a gravar l'àudio" style={{ position: 'fixed', inset: 0, zIndex: 30000, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'rgba(33,28,21,0.5)' }} onClick={onClose}>
      <div onClick={(e) => e.stopPropagation()} style={{ width: 'min(420px, 92vw)', background: 'var(--surface)', borderRadius: 'var(--r-xl)', padding: '20px', boxShadow: 'var(--shadow-lg)', border: '1px solid var(--border)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
          <h2 style={{ margin: 0, fontFamily: 'var(--font-display)', fontSize: '18px', color: 'var(--text)' }}>Torna a gravar l'àudio</h2>
          <button onClick={onClose} aria-label="Tanca" style={{ background: 'var(--surface-2)', border: '1px solid var(--border)', borderRadius: 'var(--r-pill)', width: 34, height: 34, cursor: 'pointer', color: 'var(--text-soft)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}><FaTimes /></button>
        </div>
        <div style={{ fontSize: '13px', color: 'var(--text-soft)', marginBottom: '14px' }}>{drill.text_catalan || `Drill #${drill.id}`}</div>

        {originalUrl.current && !blobUrl && (
          <div style={{ marginBottom: '12px' }}>
            <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '4px', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Àudio actual</div>
            <audio controls src={getMediaUrl(originalUrl.current)} style={{ width: '100%' }} />
          </div>
        )}
        {blobUrl && (
          <div style={{ marginBottom: '12px' }}>
            <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--sky)', marginBottom: '4px', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Gravació nova</div>
            <audio controls src={blobUrl} style={{ width: '100%' }} />
          </div>
        )}

        <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
          {!recording ? (
            <button onClick={start} disabled={busy} style={btn('var(--rose)', '#fff')}><FaMicrophone /> {blob ? 'Torna a gravar' : 'Grava'}</button>
          ) : (
            <button onClick={stop} style={btn('var(--rose)', '#fff')}><FaStop /> Atura</button>
          )}
          {blob && !recording && (
            <button onClick={save} disabled={busy} style={btn('var(--brand-1)', '#fff')}><FaSave /> {busy ? 'Desant…' : 'Desa'}</button>
          )}
          <button onClick={undo} disabled={busy || !saved} title="Torna a l'àudio anterior (Ctrl+Z)" style={btn('var(--surface-2)', 'var(--text-soft)', true)}><FaUndo /> Desfés</button>
        </div>
        <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '10px' }}>«Desfés» restaura l'àudio que hi havia abans d'aquesta gravació.</div>
      </div>
    </div>,
    document.body
  );
}

function btn(bg: string, color: string, outline = false): React.CSSProperties {
  return { display: 'inline-flex', alignItems: 'center', gap: '8px', padding: '10px 16px', borderRadius: 'var(--r-md)', fontWeight: 700, fontSize: '14px', cursor: 'pointer', background: bg, color, border: outline ? '1px solid var(--border)' : '1px solid transparent' };
}
