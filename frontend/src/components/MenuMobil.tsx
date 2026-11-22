import { useEffect, useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  FaLayerGroup, FaFeatherAlt, FaBookOpen, FaBook, FaGraduationCap, FaMicrophone,
  FaVideo, FaSearch, FaUser, FaComments, FaInfo, FaPlus, FaEllipsisH, FaTimes,
} from 'react-icons/fa';

/**
 * El menú del mòbil, a baix.
 *
 * Abans les nou portes anaven a dalt, en una fila, amb icones de 16 px i sense nom: qui premia
 * la lupa obria el perfil (#372). Aquí hi ha quatre portes amb nom, i «Nova frase» al mig, que
 * és l'acció que fa créixer la biblioteca i no pot ser una icona com les altres.
 *
 * El que no és navegació —el perfil, el copilot, el per què— no competeix per l'espai de les
 * seccions: viu darrere de «Més», que també és una llista de noms, no d'icones.
 *
 * L'alçada de la barra es publica a `--menu-mobil-h` perquè les pàgines que tenen la seva
 * pròpia barra enganxada a baix (les històries, la gramàtica) s'hi posin a sobre i no a sota.
 */
const ALCADA = 'calc(60px + env(safe-area-inset-bottom, 0px))';

type Porta = { to: string; label: string; Icon: typeof FaLayerGroup };

const PORTES: Porta[] = [
  { to: '/drills', label: 'Frases', Icon: FaLayerGroup },
  { to: '/stories', label: 'Històries', Icon: FaFeatherAlt },
  { to: '/metode', label: 'Mètode', Icon: FaBookOpen },
];

const MES: Porta[] = [
  { to: '/grammar', label: 'Gramàtica', Icon: FaBook },
  { to: '/tests', label: 'Pràctica', Icon: FaGraduationCap },
  { to: '/veus', label: 'Posa-hi veu', Icon: FaMicrophone },
  { to: '/video-creator', label: 'Captura d’un vídeo', Icon: FaVideo },
  { to: '/cerca', label: 'Cerca una frase', Icon: FaSearch },
  { to: '/profile', label: 'El meu perfil', Icon: FaUser },
];

export default function MenuMobil({ onCopilot, onAbout }: { onCopilot: () => void; onAbout: () => void }) {
  const navigate = useNavigate();
  const location = useLocation();
  const [mesObert, setMesObert] = useState(false);

  // Les pàgines amb barra pròpia a baix necessiten saber quant ocupa aquesta.
  useEffect(() => {
    const arrel = document.documentElement;
    arrel.style.setProperty('--menu-mobil-h', ALCADA);
    return () => { arrel.style.setProperty('--menu-mobil-h', '0px'); };
  }, []);

  // Canviar de pàgina tanca el full: si no, es queda tapant el que acabes d'obrir.
  useEffect(() => { setMesObert(false); }, [location.pathname]);

  const aqui = (to: string) => location.pathname === to || location.pathname.startsWith(to + '/');
  const dinsDeMes = MES.some(p => aqui(p.to));

  const botoStyle = (actiu: boolean): React.CSSProperties => ({
    flex: 1, minWidth: 0, minHeight: 56, display: 'flex', flexDirection: 'column',
    alignItems: 'center', justifyContent: 'center', gap: 3, padding: '6px 2px',
    background: 'none', border: 'none', cursor: 'pointer',
    color: actiu ? 'var(--brand-1)' : 'var(--text-soft)', fontWeight: actiu ? 800 : 600, fontSize: 11,
  });

  const filaStyle: React.CSSProperties = {
    display: 'flex', alignItems: 'center', gap: 12, width: '100%', minHeight: 52,
    padding: '12px 14px', borderRadius: 'var(--r-md)', border: '1px solid var(--border)',
    background: 'var(--surface)', color: 'var(--text)', fontSize: 15, fontWeight: 700,
    cursor: 'pointer', textAlign: 'start',
  };

  return (
    <>
      {mesObert && (
        <div role="dialog" aria-modal="true" aria-label="Més seccions"
             onClick={() => setMesObert(false)}
             style={{ position: 'fixed', inset: 0, zIndex: 1200, background: 'rgba(15,23,42,0.45)', display: 'flex', alignItems: 'flex-end' }}>
          <div onClick={e => e.stopPropagation()}
               style={{ width: '100%', maxHeight: '80dvh', overflowY: 'auto', background: 'var(--bg)',
                        borderTopLeftRadius: 'var(--r-2xl)', borderTopRightRadius: 'var(--r-2xl)',
                        padding: `18px max(16px, env(safe-area-inset-left, 0px)) calc(18px + ${ALCADA}) max(16px, env(safe-area-inset-right, 0px))`,
                        display: 'flex', flexDirection: 'column', gap: 10, boxSizing: 'border-box' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
              <strong style={{ fontSize: 17 }}>Més</strong>
              <button onClick={() => setMesObert(false)} aria-label="Tanca"
                      style={{ width: 44, height: 44, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', borderRadius: 'var(--r-pill)', border: '1px solid var(--border)', background: 'var(--surface)', color: 'var(--text-soft)', cursor: 'pointer' }}>
                <FaTimes size={16} />
              </button>
            </div>
            {MES.map(p => (
              <button key={p.to} onClick={() => { setMesObert(false); navigate(p.to); }}
                      style={{ ...filaStyle, ...(aqui(p.to) ? { borderColor: 'var(--brand-1)', color: 'var(--brand-1)' } : null) }}>
                <p.Icon size={16} /> {p.label}
              </button>
            ))}
            <button onClick={() => { setMesObert(false); onCopilot(); }} style={filaStyle}>
              <FaComments size={16} /> Copilot
            </button>
            <button onClick={() => { setMesObert(false); onAbout(); }} style={filaStyle}>
              <FaInfo size={16} /> Per què existeix això
            </button>
          </div>
        </div>
      )}

      <nav aria-label="Menú"
           style={{ position: 'fixed', left: 0, right: 0, bottom: 0, zIndex: 1100,
                    height: ALCADA, boxSizing: 'border-box',
                    paddingBottom: 'env(safe-area-inset-bottom, 0px)',
                    paddingLeft: 'max(4px, env(safe-area-inset-left, 0px))',
                    paddingRight: 'max(4px, env(safe-area-inset-right, 0px))',
                    display: 'flex', alignItems: 'stretch',
                    background: 'var(--surface)', borderTop: '1px solid var(--border)',
                    boxShadow: '0 -1px 3px rgba(15,23,42,0.06)' }}>
        {PORTES.slice(0, 2).map(p => (
          <button key={p.to} onClick={() => navigate(p.to)} style={botoStyle(aqui(p.to))}>
            <p.Icon size={18} /><span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '100%' }}>{p.label}</span>
          </button>
        ))}

        {/* Fer una frase nova no és una icona més: té nom, color i el lloc del mig. */}
        <button onClick={() => navigate('/afegeix')} aria-label="Fes una frase nova"
                style={{ flex: 1.15, minWidth: 0, display: 'flex', flexDirection: 'column', alignItems: 'center',
                         justifyContent: 'center', gap: 2, background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}>
          <span style={{ width: 46, height: 46, marginTop: -16, borderRadius: 'var(--r-pill)',
                         background: 'var(--brand-gradient)', color: '#fff', display: 'inline-flex',
                         alignItems: 'center', justifyContent: 'center', boxShadow: 'var(--shadow-brand)',
                         border: '3px solid var(--surface)' }}>
            <FaPlus size={18} />
          </span>
          <span style={{ fontSize: 11, fontWeight: 800, color: 'var(--brand-1)' }}>Nova frase</span>
        </button>

        {PORTES.slice(2).map(p => (
          <button key={p.to} onClick={() => navigate(p.to)} style={botoStyle(aqui(p.to))}>
            <p.Icon size={18} /><span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '100%' }}>{p.label}</span>
          </button>
        ))}

        <button onClick={() => setMesObert(v => !v)} aria-expanded={mesObert} style={botoStyle(mesObert || dinsDeMes)}>
          <FaEllipsisH size={18} /><span>Més</span>
        </button>
      </nav>
    </>
  );
}
