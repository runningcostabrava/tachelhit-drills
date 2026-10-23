import { useEffect, useState } from 'react';
import { FaRedo } from 'react-icons/fa';
import { subscribeStaleBuild } from '../utils/freshness';

// La barra que apareix quan tens una app vella a la mà.
//
// No és un toast: un toast se'n va als quatre segons i això no es resol sol. Es queda fins que
// recarregues, perquè fins llavors hi ha trossos de l'app que senzillament no es poden carregar.
//
// I no recarrega sola: qui està escrivint un drill té text a la pantalla sense desar.

export default function StaleBuildBanner() {
  const [stale, setStale] = useState(false);
  useEffect(() => subscribeStaleBuild(setStale), []);
  if (!stale) return null;
  return (
    <div
      role="status"
      style={{
        position: 'fixed', left: 0, right: 0, bottom: 0, zIndex: 12000,
        padding: '12px 16px calc(12px + env(safe-area-inset-bottom, 0px))',
        background: 'var(--brand-1)', color: '#fff',
        display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 14,
        flexWrap: 'wrap', fontSize: 13.5, lineHeight: 1.45, fontFamily: 'var(--font-sans)',
        boxShadow: '0 -6px 20px rgba(0,0,0,0.18)',
      }}
    >
      <span>
        <strong>L’app s’ha actualitzat</strong> mentre la tenies oberta, i hi ha trossos que ja no
        es poden carregar. Recarrega per continuar.
      </span>
      <button
        onClick={() => window.location.reload()}
        style={{
          display: 'inline-flex', alignItems: 'center', gap: 7, padding: '8px 16px',
          borderRadius: 'var(--r-pill)', border: 'none', background: '#fff',
          color: 'var(--brand-1)', fontWeight: 800, fontSize: 13, cursor: 'pointer',
          fontFamily: 'inherit', flexShrink: 0,
        }}
      >
        <FaRedo size={11} /> Recarrega
      </button>
    </div>
  );
}
