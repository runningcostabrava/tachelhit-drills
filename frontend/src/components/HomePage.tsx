import { useEffect, useState, type ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  FaBook, FaBookOpen, FaChevronRight, FaFire, FaGraduationCap, FaLayerGroup, FaMicrophone,
  FaPlay, FaPlus, FaRedo, FaSearch, FaVideo,
} from 'react-icons/fa';
import { api, type HomeData } from '../api';
import { getMediaUrl, thumb } from '../config';

// La casa.
//
// Fins avui la portada era la graella de drills: s'obria l'app i et queia a sobre una taula de
// mil sis-centes files de sis megues, amb la resta de l'app penjada d'una barra a dalt. Les
// parts hi eren totes i no es veia cap de les dues coses que importen: QUÈ pots fer, i QUANT
// n'hi ha fet.
//
// Això és el que la casa ha de dir, en aquest ordre:
//
//   1. el que has de fer ara (el repàs que tens pendent, o posar-te a practicar);
//   2. les portes, cadascuna amb el seu número de debò — no una graella d'icones boniques:
//      «8 de 10 capítols escrits» diu alhora on ets i què falta;
//   3. com està la biblioteca, que és el projecte mateix: frases, veus, varietats. Una frase
//      sense veu és feina pendent, i per això el número que falta també hi surt.
//
// Tot plegat és UNA crida que només compta files (`/home`): obrir l'app no ha de baixar la
// biblioteca.

//: Els dibuixos de les portes, sabuts de memòria.
//
// No és una còpia de la veritat: la veritat la diu `/artwork` i mana tan bon punt arriba. Però
// el navegador no pot començar a baixar una imatge fins que en sap l'adreça, i l'adreça venia
// després de l'API — que és un servei gratuït que s'adorm. Sabent-les, les portes es pinten
// mentre l'API encara s'aixeca.
const DOORS_KNOWN: Record<string, string> = {
  method: 'https://res.cloudinary.com/du26ppvh0/image/upload/v1792770886/tachelhit/app/porta-method.webp',
  grammar: 'https://res.cloudinary.com/du26ppvh0/image/upload/v1792770883/tachelhit/app/porta-grammar.webp',
  practice: 'https://res.cloudinary.com/du26ppvh0/image/upload/v1792770886/tachelhit/app/porta-practice.webp',
  library: 'https://res.cloudinary.com/du26ppvh0/image/upload/v1792770884/tachelhit/app/porta-library.webp',
  stories: 'https://res.cloudinary.com/du26ppvh0/image/upload/v1792770887/tachelhit/app/porta-stories.webp',
  capture: 'https://res.cloudinary.com/du26ppvh0/image/upload/v1792770883/tachelhit/app/porta-capture.webp',
};

export default function HomePage() {
  const navigate = useNavigate();
  const [d, setD] = useState<HomeData | null>(null);
  // Si els comptes no arriben, la casa segueix sent la casa: les portes hi són i no s'hi queda
  // cap «…» penjat ni un «0% es pot escoltar» que seria mentida.
  const [failed, setFailed] = useState(false);
  const [due, setDue] = useState<{ due: number; new: number } | null>(null);
  const [streak, setStreak] = useState(0);
  const [find, setFind] = useState('');

  // Si els comptes triguen, es diu. El servidor és gratuït i quan s'ha adormit triga mig minut
  // a aixecar-se: una portada muda sembla una app trencada, i no ho és.
  const [slow, setSlow] = useState(false);
  const [tries, setTries] = useState(0);

  useEffect(() => {
    const t = window.setTimeout(() => setSlow(true), 2500);
    api.home()
      .then((h) => { setD(h); setFailed(false); })
      .catch(() => setFailed(true))
      .finally(() => { window.clearTimeout(t); setSlow(false); });
    return () => window.clearTimeout(t);
  }, [tries]);

  useEffect(() => {
    document.title = 'Tamazight';
    api.reviewStats().then((s) => setDue({ due: s.due, new: s.new })).catch(() => {});
    api.reviewStreak().then((s) => setStreak(s.streak_days || 0)).catch(() => {});
  }, []);

  const n = (x?: number) => (x === undefined ? '…' : x.toLocaleString('ca-ES'));
  // El que toca AVUI és el que ja has vist i torna, i prou.
  //
  // Aquest número era `due + new`, i `new` és tota la biblioteca que encara no has vist: la
  // portada deia «Repassa 4815» quan el que tocava eren quatre frases (#416). Era fals, era
  // desanimador, i no es podia arribar a zero mai, perquè cada frase que entra a la biblioteca
  // el feia pujar. Les que no has vist mai són una invitació, no un deute, i es diuen a part.
  const toca = due?.due || 0;
  const noVistes = due?.new || 0;
  const voiced = d && d.library.sentences ? Math.round((d.library.with_voice / d.library.sentences) * 100) : 0;

  return (
    <div style={{ padding: '22px 16px 48px', maxWidth: 920, margin: '0 auto', width: '100%', boxSizing: 'border-box' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 6 }}>
        <span aria-hidden style={{ width: 42, height: 42, borderRadius: 13, background: 'var(--brand-gradient)', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', fontSize: 22, color: '#fff', flexShrink: 0 }}>ⵣ</span>
        <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 27, margin: 0, lineHeight: 1.1 }}>
          {d?.you.name ? `Azul, ${d.you.name}` : 'Tamazight'}
        </h1>
      </div>
      <p style={{ color: 'var(--text-soft)', fontSize: 14.5, lineHeight: 1.6, margin: '0 0 18px', maxWidth: 620 }}>
        Una biblioteca viva d’amazic de l’Atles central, dita per gent amb nom i amb poble. Tot el
        que s’ensenya aquí surt d’aquí: cap frase inventada, cap veu de màquina fent-se passar per
        ningú.
      </p>

      {/* Cercar: la primera cosa que algú vol fer amb una biblioteca. */}
      <form onSubmit={(e) => { e.preventDefault(); navigate(`/cerca?q=${encodeURIComponent(find.trim())}`); }}
            style={{ display: 'flex', gap: 8, margin: '0 0 18px' }}>
        <input value={find} onChange={(e) => setFind(e.target.value)}
               placeholder="Cerca una frase o una paraula: pa, aɣrum, «tinc gana»…"
               aria-label="Cerca una frase o una paraula"
               autoCapitalize="off" autoCorrect="off" spellCheck={false}
               style={{ flex: 1, minWidth: 0, padding: '11px 16px', fontSize: 14.5, borderRadius: 'var(--r-pill)', border: '1px solid var(--border)', background: 'var(--surface)', color: 'var(--text)', fontFamily: 'inherit' }} />
        <button type="submit" aria-label="Cerca"
                style={{ padding: '11px 18px', borderRadius: 'var(--r-pill)', border: 'none', background: 'var(--brand-gradient)', color: '#fff', fontWeight: 800, cursor: 'pointer', fontFamily: 'inherit' }}>
          <FaSearch size={13} />
        </button>
        {/* I el signe de sumar, que és l'altra cosa que es vol fer amb una biblioteca: afegir-hi.
            L'amo: «falta un símbol + gran per crear un nou drill». */}
        <button type="button" onClick={() => navigate('/afegeix')} aria-label="Afegeix una frase"
                title="Afegeix una frase"
                style={{ padding: '11px 18px', borderRadius: 'var(--r-pill)', border: '1px solid var(--brand-1)', background: 'var(--surface)', color: 'var(--brand-1)', fontWeight: 800, cursor: 'pointer', fontFamily: 'inherit', flexShrink: 0 }}>
          <FaPlus size={14} />
        </button>
      </form>

      {(slow || failed) && !d && (
        <p style={{ fontSize: 12.5, color: 'var(--text-muted)', margin: '-8px 0 14px', lineHeight: 1.55 }}>
          {failed ? 'No s’ha pogut parlar amb el servidor. ' : 'El servidor s’està despertant: el primer cop després d’una estona triga mig minut. '}
          <button onClick={() => setTries((n) => n + 1)}
                  style={{ background: 'transparent', border: 'none', padding: 0, color: 'var(--brand-1)', fontWeight: 700, fontSize: 12.5, cursor: 'pointer', fontFamily: 'inherit', textDecoration: 'underline' }}>
            Torna-ho a provar
          </button>
        </p>
      )}

      {/* El que toca ara. Una sola cosa, grossa: si tens repàs pendent, el repàs. */}
      <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginBottom: 26 }}>
        <button onClick={() => navigate(toca ? '/player?mode=review' : '/player')}
                style={{ flex: '1 1 260px', display: 'inline-flex', alignItems: 'center', gap: 12, padding: '14px 18px', borderRadius: 'var(--r-lg)', border: 'none', cursor: 'pointer', fontFamily: 'inherit', textAlign: 'left', color: '#fff', background: toca ? 'var(--saffron)' : 'var(--brand-gradient)', boxShadow: 'var(--shadow-brand)' }}>
          {toca ? <FaRedo size={18} /> : <FaPlay size={16} />}
          <span style={{ flex: 1 }}>
            <span style={{ display: 'block', fontWeight: 800, fontSize: 16 }}>
              {toca ? `Repassa ${n(toca)}` : 'Practica'}
            </span>
            <span style={{ display: 'block', fontSize: 12.5, opacity: 0.9 }}>
              {toca
                ? `${toca === 1 ? 'Una frase et toca' : `${n(toca)} frases et toquen`} avui`
                : noVistes
                  ? 'Res per repassar avui: comença frases noves quan vulguis'
                  : 'Tot repassat: fes una volta per la biblioteca'}
            </span>
          </span>
          {streak > 0 && (
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, fontWeight: 800, fontSize: 14 }}>
              <FaFire size={13} />{streak}
            </span>
          )}
        </button>

        <button onClick={() => navigate('/veus')}
                style={{ flex: '1 1 260px', display: 'inline-flex', alignItems: 'center', gap: 12, padding: '14px 18px', borderRadius: 'var(--r-lg)', border: '1px solid var(--border)', background: 'var(--surface)', cursor: 'pointer', fontFamily: 'inherit', textAlign: 'left', color: 'var(--text)' }}>
          <FaMicrophone size={17} style={{ color: 'var(--brand-1)' }} />
          <span style={{ flex: 1 }}>
            {/* L'amo: «aquí l'explicació seria: si us plau, necessitem la teva veu». Una frase
                sense veu no és una fitxa incompleta, és una cosa que ningú no sap dir encara. */}
            <span style={{ display: 'block', fontWeight: 800, fontSize: 16 }}>Si us plau, necessitem la teva veu</span>
            <span style={{ display: 'block', fontSize: 12.5, color: 'var(--text-soft)' }}>
              {d && d.library.wanted
                ? `${n(d.library.wanted)} ${d.library.wanted === 1 ? 'frase espera' : 'frases esperen'} que algú les digui en veu alta`
                : 'Grava una frase que saps dir, o demana’n una que vols saber dir'}
            </span>
          </span>
          <FaChevronRight size={12} style={{ color: 'var(--text-muted)' }} />
        </button>
      </div>

      {/* I les que no has vist mai, dites com el que són: una invitació i no un deute (#416). */}
      {noVistes > 0 && (
        <p style={{ fontSize: 12.5, color: 'var(--text-muted)', margin: '-16px 0 26px', lineHeight: 1.55 }}>
          Hi ha {n(noVistes)} {noVistes === 1 ? 'frase' : 'frases'} que encara no has vist.
          No cal fer-les totes: comença quan vulguis i el repàs ja te les anirà tornant.
        </p>
      )}

      {/* Les portes. Cadascuna amb el seu número: on ets i què falta, a la mateixa línia. */}
      <h2 style={sectionTitle}>Per on vols entrar</h2>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))', gap: 10, marginBottom: 28 }}>
        <Door to="/metode" Icon={FaBookOpen} title="El Mètode" cover={d?.covers.method || DOORS_KNOWN.method}
              what="Deu capítols, de saludar a fer la compra, amb les nostres veus a dins."
              count={d && `${n(d.method.written)} de ${n(d.method.chapters)} capítols escrits`} />
        <Door to="/grammar" Icon={FaBook} title="La gramàtica" cover={d?.covers.grammar || DOORS_KNOWN.grammar}
              what="Les regles, explicades només amb frases que algú ha dit de debò."
              count={d && `${n(d.grammar.with_lesson)} de ${n(d.grammar.units)} unitats amb lliçó`} />
        <Door to="/tests" Icon={FaGraduationCap} title="La pràctica" cover={d?.covers.practice || DOORS_KNOWN.practice}
              what="Llistes per repassar i per posar-te a prova, teves o de tothom."
              count={d && `${n(d.practice.all)} pràctiques${d.practice.mine ? ` · ${n(d.practice.mine)} teves` : ''}`} />
        <Door to="/drills" Icon={FaLayerGroup} title="La biblioteca" cover={d?.covers.library || DOORS_KNOWN.library}
              what="Totes les frases, una a una: qui les diu, d’on són i com sonen."
              count={d && `${n(d.library.sentences)} frases · ${n(d.library.with_voice)} amb veu`} />
        <Door to="/stories" Icon={FaBookOpen} title="Històries i cançons" cover={d?.covers.stories || DOORS_KNOWN.stories}
              what="El que es llegeix de cap a cap: contes, cançons, converses senceres." />
        <Door to="/video-creator" Icon={FaVideo} title="Captura" cover={d?.covers.capture || DOORS_KNOWN.capture}
              what="Un vídeo entra, frases en surten: talla, escolta i decideix."
              count={d && `${n(d.library.videos)} vídeos a la biblioteca`} />
      </div>

      {/* La biblioteca és el projecte. Que es vegi créixer, i que es vegi què li falta. */}
      {!failed && <h2 style={sectionTitle}>La biblioteca ara mateix</h2>}
      {!failed && <div style={{ border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', background: 'var(--surface)', padding: '16px 18px', marginBottom: 26 }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(110px, 1fr))', gap: 14 }}>
          <Figure what="frases" value={n(d?.library.sentences)} />
          <Figure what="amb veu" value={n(d?.library.with_voice)} tone="var(--emerald)" />
          <Figure what="veus diferents" value={n(d?.library.speakers)} />
          <Figure what="varietats" value={n(d?.library.varieties)} />
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginTop: 14 }}>
          <div style={{ flex: 1, height: 8, borderRadius: 4, background: 'var(--surface-2)', overflow: 'hidden' }}>
            <div style={{ width: `${voiced}%`, height: 8, background: 'var(--emerald)' }} />
          </div>
          <span style={{ fontSize: 12, color: 'var(--text-muted)', fontWeight: 700, whiteSpace: 'nowrap' }}>
            {voiced}% es pot escoltar
          </span>
        </div>
        {/* El que falta, dit amb el número de debò —les frases que ningú no ha dit mai, no només
            les que algú ha demanat— i amb la invitació que l'amo vol: fes-te un compte i posa-hi
            la veu. Una frase muda no és una fitxa incompleta: és una cosa que encara no s'ha
            sentit. */}
        {d && d.library.sentences > d.library.with_voice && (
          <p style={{ fontSize: 12.5, color: 'var(--text-muted)', margin: '8px 0 0', lineHeight: 1.55 }}>
            La resta és feina de gravació, no un error: {n(d.library.sentences - d.library.with_voice)} frases
            encara no les ha dites ningú{d.library.wanted ? `, i ${n(d.library.wanted)} ja demanen una veu` : ''}.
          </p>
        )}
        <div style={{ marginTop: 10, paddingTop: 10, borderTop: '1px solid var(--border)', display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'center' }}>
          <p style={{ fontSize: 13, color: 'var(--text-soft)', margin: 0, lineHeight: 1.55, flex: '1 1 260px' }}>
            <strong>Parles amazic?</strong> Fes-te un compte i posa-hi la veu: qualsevol frase
            muda es pot gravar en trenta segons, i les preguntes de qui està aprenent esperen que
            algú les contesti. Cada gravació queda amb el teu nom i el teu poble.
          </p>
          <button onClick={() => navigate(d?.you.signed_in ? '/veus' : '/signin')}
                  style={{ padding: '9px 16px', borderRadius: 'var(--r-pill)', border: 'none', background: 'var(--brand-gradient)', color: '#fff', fontWeight: 800, fontSize: 13, cursor: 'pointer', fontFamily: 'inherit', flexShrink: 0 }}>
            {d?.you.signed_in ? 'Grava’n una' : 'Fes-te un compte i grava'}
          </button>
        </div>
      </div>}

      {/* Qui ets aquí. Sense nom no es pot gravar ni guardar el repàs, i val més dir-ho que amagar-ho. */}
      {d && !d.you.signed_in && (
        <div style={{ border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', background: 'var(--brand-gradient-soft)', padding: '14px 18px', marginBottom: 22 }}>
          <strong style={{ fontSize: 15 }}>Fes-te un nom</strong>
          <p style={{ fontSize: 13.5, color: 'var(--text-soft)', margin: '4px 0 10px', lineHeight: 1.55 }}>
            Amb un nom pots gravar la teva veu, guardar el teu repàs i que les teves frases portin
            qui les diu. No cal cap correu.
          </p>
          <button onClick={() => navigate('/signin')} style={{ padding: '9px 18px', borderRadius: 'var(--r-pill)', border: 'none', background: 'var(--brand-gradient)', color: '#fff', fontWeight: 800, fontSize: 13.5, cursor: 'pointer', fontFamily: 'inherit' }}>
            Entra o fes-te’n un
          </button>
        </div>
      )}
      {d && d.you.signed_in && d.you.recordings > 0 && (
        <p style={{ fontSize: 13, color: 'var(--text-soft)', margin: '0 0 22px' }}>
          <FaMicrophone size={11} style={{ color: 'var(--brand-1)' }} /> Hi has posat la veu{' '}
          <strong>{n(d.you.recordings)}</strong> {d.you.recordings === 1 ? 'vegada' : 'vegades'}. Gràcies.
        </p>
      )}

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
        <Small to="/library">Els vídeos</Small>
        <Small to="/corpus">El corpus</Small>
        <Small to="/credits">D’on surt tot</Small>
        <Small to="/profile">El teu perfil</Small>
        {d?.you.is_admin && <Small to="/verify">Per verificar</Small>}
      </div>
    </div>
  );
}

// Una porta porta la seva imatge: les mateixes il·lustracions que la resta de l'app fa servir per
// a una frase. No és decoració — és el que l'app ja és per dins, ensenyat a la portada.
function Door({ to, Icon, title, what, count, cover }: {
  to: string; Icon: typeof FaBook; title: string; what: string;
  count?: string | null | false; cover?: string | null;
}) {
  const navigate = useNavigate();
  return (
    <button onClick={() => navigate(to)}
            style={{ textAlign: 'left', padding: 0, borderRadius: 'var(--r-lg)', border: '1px solid var(--border)', background: 'var(--surface)', cursor: 'pointer', fontFamily: 'inherit', color: 'var(--text)', display: 'flex', flexDirection: 'column', overflow: 'hidden', minHeight: 112 }}>
      {cover && (
        <img src={thumb(getMediaUrl(cover), 560)} alt="" loading="eager" fetchPriority="high"
             style={{ width: '100%', aspectRatio: '16 / 9', objectFit: 'cover', display: 'block' }}
             onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = 'none'; }} />
      )}
      <span style={{ display: 'flex', flexDirection: 'column', gap: 5, padding: '12px 15px 13px', flex: 1 }}>
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
          <Icon size={14} style={{ color: 'var(--brand-1)' }} />
          <span style={{ fontWeight: 800, fontSize: 15.5 }}>{title}</span>
        </span>
        <span style={{ fontSize: 13, color: 'var(--text-soft)', lineHeight: 1.5, flex: 1 }}>{what}</span>
        {count && <span style={{ fontSize: 12, color: 'var(--text-muted)', fontWeight: 700 }}>{count}</span>}
      </span>
    </button>
  );
}

function Figure({ what, value, tone }: { what: string; value: string; tone?: string }) {
  return (
    <div>
      <div style={{ fontFamily: 'var(--font-display)', fontSize: 23, fontWeight: 800, color: tone || 'var(--text)', lineHeight: 1.1 }}>{value}</div>
      <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{what}</div>
    </div>
  );
}

function Small({ to, children }: { to: string; children: ReactNode }) {
  const navigate = useNavigate();
  return (
    <button onClick={() => navigate(to)}
            style={{ padding: '7px 14px', borderRadius: 'var(--r-pill)', border: '1px solid var(--border)', background: 'var(--surface)', color: 'var(--text-soft)', fontWeight: 700, fontSize: 12.5, cursor: 'pointer', fontFamily: 'inherit' }}>
      {children}
    </button>
  );
}

const sectionTitle: React.CSSProperties = {
  fontSize: 12, fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.06em',
  color: 'var(--text-muted)', margin: '0 0 8px',
};
