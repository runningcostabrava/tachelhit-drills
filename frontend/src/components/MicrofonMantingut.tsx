/**
 * Gravar una frase com un gest: mantenir premut (#370).
 *
 * Posar la veu a una frase és la feina més important que algú pot fer aquí —sense veu no hi ha
 * ni biblioteca ni curs— i era la que costava més passos: obrir el diàleg, llegir la llista de
 * preses, prémer grava, prémer atura, triar varietat, escriure el poble, contestar si ets
 * parlant de tota la vida, i prémer desa. Set passos per a una frase d'un segon.
 *
 * Per al cas normal —una frase sense cap veu, gravada per algú que ja té perfil— això és:
 * mantenir premut, deixar anar, i ja està. Sense desar. La presa va a la cua del dispositiu i
 * puja sola (`cuaDeVeus`), de manera que ni la cobertura ni tancar l'app la poden perdre.
 *
 * Els dos casos que SÍ que s'aturen a preguntar:
 *
 * · **Qui encara no té varietat ni poble.** Una veu sense lloc no s'accepta —cada veu porta el
 *   seu— i això es demana UNA vegada, al diàleg de sempre, no a cada frase.
 * · **Qui ja hi havia posat la seva veu.** Tornar-hi és feina teva d'abans; no es perd (la vella
 *   es queda i la nova se li posa al costat), però es diu abans de fer-ho.
 *
 * Una veu d'una ALTRA persona no pregunta res: dues persones dient la mateixa frase no és una
 * correcció, és el que aquesta biblioteca vol.
 */
import { useEffect, useRef, useState } from 'react';
import { FaMicrophone, FaPlay, FaTrash } from 'react-icons/fa';
import { api, type Recording } from '../api';
import { toast } from '../toast';
import * as cua from '../services/cuaDeVeus';
import type { Drill } from '../types';

/** Un toc no és un gest de gravar: per sota d'això, era un dit que ha relliscat. */
const MINIM_MS = 400;

export interface PerfilVeu {
  variety: string | null;
  region: string | null;
  is_native?: boolean | null;
}

export default function MicrofonMantingut({ drill, perfil, onCalPerfil, onDesada }: {
  drill: Drill;
  /** `undefined` mentre es carrega; `null` si no hi ha sessió. */
  perfil: PerfilVeu | null | undefined;
  /** Quan falta el poble o la varietat: ho demana el diàleg de sempre, una vegada. */
  onCalPerfil: () => void;
  onDesada?: () => void;
}) {
  const [gravant, setGravant] = useState(false);
  const [segons, setSegons] = useState(0);
  const [feta, setFeta] = useState<{ blob: Blob; url: string } | null>(null);
  const [pregunta, setPregunta] = useState<{ blob: Blob; url: string } | null>(null);
  const recRef = useRef<MediaRecorder | null>(null);
  const trossos = useRef<Blob[]>([]);
  const des = useRef(0);
  const rellotge = useRef<number | null>(null);
  /** Si ja hi ha una veu MEVA en aquesta frase. Es demana en començar a gravar, no abans:
   *  una graella de cinquanta targetes no ha de fer cinquanta preguntes al servidor. */
  const meves = useRef<Recording[] | null>(null);

  useEffect(() => () => {
    if (feta) URL.revokeObjectURL(feta.url);
    if (pregunta) URL.revokeObjectURL(pregunta.url);
    if (rellotge.current) window.clearInterval(rellotge.current);
  }, [feta, pregunta]);

  const aLaCua = (blob: Blob) => {
    cua.afegeix({
      drillId: drill.id,
      frase: (drill.text_catalan || drill.text_tachelhit || `#${drill.id}`).slice(0, 60),
      blob,
      tipus: blob.type || 'audio/webm',
      variety: perfil?.variety || undefined,
      region: perfil?.region || undefined,
      isNative: perfil?.is_native ?? null,
    }).then(() => {
      toast.success('Veu desada. Puja sola.');
      onDesada?.();
    }).catch(() => toast.error('No s\'ha pogut desar la veu al dispositiu'));
  };

  const comenca = async () => {
    if (gravant || pregunta) return;
    if (perfil === undefined) return;                       // encara no se sap qui ets
    if (!perfil || !perfil.variety || !perfil.region) { onCalPerfil(); return; }
    try {
      const flux = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mr = new MediaRecorder(flux);
      trossos.current = [];
      mr.ondataavailable = (e) => { if (e.data.size) trossos.current.push(e.data); };
      mr.onstop = () => {
        flux.getTracks().forEach((t) => t.stop());
        const durada = Date.now() - des.current;
        const blob = new Blob(trossos.current, { type: mr.mimeType || 'audio/webm' });
        if (durada < MINIM_MS || !blob.size) {
          toast.error('Mantén premut el micròfon mentre ho dius.');
          return;
        }
        const url = URL.createObjectURL(blob);
        if (meves.current && meves.current.some((r) => r.mine)) {
          setPregunta({ blob, url });                      // ja hi havies posat la teva veu
          return;
        }
        setFeta({ blob, url });
        aLaCua(blob);
      };
      recRef.current = mr;
      des.current = Date.now();
      mr.start();
      setGravant(true);
      setSegons(0);
      rellotge.current = window.setInterval(() => setSegons((s) => s + 1), 1000);
      if (meves.current === null) {
        api.drillRecordings(drill.id).then((r) => { meves.current = r; }).catch(() => { meves.current = []; });
      }
    } catch {
      toast.error('No s\'ha pogut accedir al micròfon. Mira\'n els permisos al navegador.');
    }
  };

  const deixa = () => {
    if (!gravant) return;
    setGravant(false);
    if (rellotge.current) { window.clearInterval(rellotge.current); rellotge.current = null; }
    try { recRef.current?.stop(); } catch { /* ja estava aturat */ }
  };

  const escolta = (url: string) => { new Audio(url).play().catch(() => {}); };

  if (pregunta) {
    return (
      <div style={quadre}>
        <div style={{ fontSize: 13.5, lineHeight: 1.5, marginBottom: 10 }}>
          <strong>En aquesta frase ja hi ha una veu teva.</strong> La d'abans no es perd: la nova
          se li posa al costat, i qui estudiï les sentirà totes dues.
        </div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <button onClick={() => escolta(pregunta.url)} style={petit}><FaPlay size={11} /> escolta-la</button>
          <button onClick={() => { aLaCua(pregunta.blob); setFeta(pregunta); setPregunta(null); meves.current = null; }}
                  style={{ ...petit, background: 'var(--brand-gradient)', color: '#fff', border: 'none' }}>
            afegeix-la igualment
          </button>
          <button onClick={() => { URL.revokeObjectURL(pregunta.url); setPregunta(null); }} style={petit}>
            <FaTrash size={11} /> llença-la
          </button>
        </div>
      </div>
    );
  }

  return (
    <div>
      <button
        onPointerDown={(e) => { e.preventDefault(); comenca(); }}
        onPointerUp={deixa}
        onPointerCancel={deixa}
        onPointerLeave={deixa}
        // Mantenir premut sobre un text el selecciona i al mòbil obre el menú de copiar, que es
        // menja el gest; i el menú del clic dret també l'interromp.
        onContextMenu={(e) => e.preventDefault()}
        style={{
          display: 'flex', width: '100%', alignItems: 'center', justifyContent: 'center', gap: '10px',
          padding: '15px', border: '1.5px solid var(--rose)', borderRadius: 'var(--r-lg)',
          background: gravant ? 'var(--rose)' : 'var(--rose-soft)',
          color: gravant ? '#fff' : 'var(--rose)',
          fontSize: '15px', fontWeight: 800, cursor: 'pointer', fontFamily: 'inherit',
          userSelect: 'none', WebkitUserSelect: 'none', touchAction: 'none',
        }}
      >
        <FaMicrophone size={18} />
        {gravant
          ? <>Gravant… {segons > 0 ? `${segons}s` : ''} — deixa anar quan acabis</>
          : <>Grava la teva versió — <span style={{ fontWeight: 600 }}>mantén premut</span></>}
      </button>

      {feta && (
        <div style={{ ...quadre, marginTop: 8 }}>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
            <button onClick={() => escolta(feta.url)} style={petit}><FaPlay size={11} /> escolta el que has dit</button>
            <span style={{ fontSize: 12.5, color: 'var(--text-muted)' }}>
              Si no t'agrada, torna a mantenir premut i en fas una altra.
            </span>
          </div>
        </div>
      )}
    </div>
  );
}

const quadre: React.CSSProperties = {
  padding: '10px 12px', borderRadius: 'var(--r-lg)', border: '1px solid var(--border)',
  background: 'var(--surface-2)',
};
const petit: React.CSSProperties = {
  display: 'inline-flex', alignItems: 'center', gap: 6, padding: '7px 12px',
  borderRadius: 'var(--r-pill)', border: '1px solid var(--border)', background: 'var(--surface)',
  color: 'var(--text)', fontWeight: 700, fontSize: 12.5, cursor: 'pointer', fontFamily: 'inherit',
};
