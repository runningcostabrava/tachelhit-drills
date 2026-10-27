import { useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { howLongAgo, onData, type StaleWhy } from '../utils/dataState';

/**
 * Què s'està ensenyant i d'on surt.
 *
 * Dues coses que abans passaven en silenci:
 *
 *  · el servidor triga a despertar-se —el servei gratuït s'adorm quan no s'usa— i la pantalla es
 *    quedava en blanc sense dir per què, que és com es veu una app trencada;
 *  · s'ensenya l'última resposta desada perquè la xarxa va lenta. Això fa que l'app s'obri de
 *    seguida, però ensenyar una cosa vella sense dir-ho seria el mateix pecat que el botó que
 *    deia «escolta el capítol» i feia sonar una altra cosa. Es diu de quan és, i quan la xarxa
 *    acaba portant una cosa DIFERENT, es diu també i es pot actualitzar.
 */
export default function DataNotice() {
  const [waking, setWaking] = useState(false);
  const [stale, setStale] = useState<{ at: number; why: StaleWhy } | null>(null);
  const [fresh, setFresh] = useState(false);
  const location = useLocation();

  // Canviar de pantalla és començar de nou: el que es deia d'allà no val aquí.
  useEffect(() => { setStale(null); setFresh(false); }, [location.pathname]);

  useEffect(() => onData((e) => {
    if (e.kind === 'waking') setWaking(e.on);
    if (e.kind === 'stale') setStale({ at: e.at, why: e.why });
    if (e.kind === 'fresh') setFresh(true);
  }), []);

  if (!waking && !stale) return null;

  /**
   * Una fitxa petita a un costat, no una barra de banda a banda.
   *
   * Això és un avís secundari —diu d'on surt el que s'està veient— i s'estava quedant una
   * franja sencera de pantalla, a baix de tot, que és on van els comandaments del que s'està
   * fent: a una història tapava el botó d'aturar (#393), i a qualsevol altra pantalla es menja
   * l'espai del contingut. Va a dalt a la dreta, sota el menú, on no hi ha res més, i ocupa el
   * que diu.
   */
  const bar: React.CSSProperties = {
    position: 'fixed', zIndex: 1200,
    top: `calc(var(--nav-h, 56px) + env(safe-area-inset-top, 0px) + 10px)`,
    right: `max(12px, env(safe-area-inset-right, 0px))`,
    maxWidth: 'min(320px, calc(100vw - 24px))',
    display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap',
    padding: '9px 13px',
    background: 'var(--surface)', border: '1px solid var(--border)',
    borderRadius: 'var(--r-lg)',
    fontSize: 12.5, color: 'var(--text-soft)', lineHeight: 1.4,
    boxShadow: '0 6px 18px rgba(15,23,42,0.12)',
  };

  if (waking) {
    return (
      <div style={bar} role="status">
        <span>Despertant el servidor… El servei gratuït s’adorm i triga una mica a tornar.</span>
      </div>
    );
  }

  return (
    <div style={bar} role="status">
      {fresh ? (
        <>
          <span>Desat {howLongAgo(stale!.at)}. Al servidor hi ha una altra cosa.</span>
          <button onClick={() => window.location.reload()}
                  style={{ flexShrink: 0, padding: '6px 12px', borderRadius: 'var(--r-pill)', border: 'none', background: 'var(--brand-gradient)', color: '#fff', fontWeight: 800, fontSize: 12, cursor: 'pointer', fontFamily: 'inherit' }}>
            Actualitza
          </button>
        </>
      ) : (
        // «Mirant si hi ha res nou» només és cert quan la petició encara corre. Si ja ha
        // fallat, dir-ho igualment seria inventar-se una feina que ningú no està fent.
        <span>
          {stale!.why === 'offline'
            ? `Sense servidor. Això és del que tenies desat, ${howLongAgo(stale!.at)}.`
            : `Desat ${howLongAgo(stale!.at)}. Mirant si hi ha res nou…`}
        </span>
      )}
    </div>
  );
}
