import { useEffect, useRef, useState } from 'react';
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

  /**
   * Quant ocupa això a baix de tot, dit a la pàgina sencera.
   *
   * Aquest avís i la barra de comandaments d'una història viuen tots dos a `bottom: 0` i no se
   * sabien l'un de l'altre: l'avís guanyava i qui escoltava es quedava sense poder aturar ni
   * repetir (#393). Pujar el `zIndex` de la barra només hauria canviat qui tapa qui, i l'avís
   * diu una cosa que s'ha de saber —que el que es veu no ve del servidor.
   *
   * Amb `--peu-encastat`, el que estigui encastat a baix s'enfila per sobre d'aquest avís en
   * comptes de barallar-s'hi, i val per a qualsevol barra que vingui després.
   */
  const caixa = useRef<HTMLDivElement | null>(null);
  const visible = waking || !!stale;
  useEffect(() => {
    const arrel = document.documentElement;
    if (!visible) { arrel.style.removeProperty('--peu-encastat'); return; }
    const mesura = () => {
      const h = caixa.current?.getBoundingClientRect().height;
      if (h) arrel.style.setProperty('--peu-encastat', `${Math.round(h)}px`);
    };
    mesura();
    const ro = typeof ResizeObserver !== 'undefined' ? new ResizeObserver(mesura) : null;
    if (ro && caixa.current) ro.observe(caixa.current);
    window.addEventListener('resize', mesura);
    return () => {
      ro?.disconnect();
      window.removeEventListener('resize', mesura);
      arrel.style.removeProperty('--peu-encastat');
    };
  }, [visible, fresh]);

  if (!waking && !stale) return null;

  const bar: React.CSSProperties = {
    position: 'fixed', left: 0, right: 0, bottom: 0, zIndex: 1200,
    display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10,
    padding: '10px 14px calc(10px + env(safe-area-inset-bottom, 0px))',
    background: 'var(--surface)', borderTop: '1px solid var(--border)',
    fontSize: 12.5, color: 'var(--text-soft)', lineHeight: 1.45,
    boxShadow: '0 -2px 10px rgba(15,23,42,0.06)',
  };

  if (waking) {
    return (
      <div ref={caixa} style={bar} role="status">
        <span>Despertant el servidor… El servei gratuït s’adorm quan ningú no l’usa i triga una mica a tornar.</span>
      </div>
    );
  }

  return (
    <div ref={caixa} style={bar} role="status">
      {fresh ? (
        <>
          <span>Això és del que tenies desat, {howLongAgo(stale!.at)}. Al servidor hi ha una altra cosa.</span>
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
            ? `No s’ha pogut arribar al servidor. Això és del que tenies desat, ${howLongAgo(stale!.at)}.`
            : `Això és del que tenies desat, ${howLongAgo(stale!.at)}. Mirant si hi ha res nou…`}
        </span>
      )}
    </div>
  );
}
