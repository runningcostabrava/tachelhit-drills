import { useEffect, useState } from 'react';
import NotaOrtografia from './NotaOrtografia';
import { useNavigate, useParams } from 'react-router-dom';
import { FaBookOpen, FaMicrophone, FaPlay, FaTag } from 'react-icons/fa';
import { api, type LessonProposal, type MethodChapterData, type MethodSentence } from '../api';
import { getMediaUrl, hasIdentity, thumb } from '../config';
import { toast } from '../toast';
import { whyItFailed } from '../utils/errors';
import MethodLesson from './MethodLesson';
import { useIsMobileLayout } from '../utils/layout';
import SentenceVariants from './SentenceVariants';

// Un capítol del Mètode.
//
// L'ordre de la pàgina és l'ordre en què s'aprèn: primer què en sabràs fer, després les frases
// que ho fan —les NOSTRES, cap del manual—, i al final el que ens falta per acabar-lo. Aquesta
// última part no és una disculpa: és la llista del que s'ha d'anar a gravar, amb el botó per
// demanar-ho.

function Sentence({ s }: { s: MethodSentence }) {
  const [asked, setAsked] = useState(false);
  const play = () => { if (s.audio_url) new Audio(getMediaUrl(s.audio_url)).play().catch(() => {}); };
  const askForVoice = async () => {
    try { await api.askForVoice(s.id); setAsked(true); toast.success('Demanada a les nostres veus'); }
    catch (e) { toast.error(whyItFailed(e, 'No s’ha pogut demanar')); }
  };
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '10px 12px', background: 'var(--surface-2)', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)' }}>
      {s.image_url && (
        <img src={thumb(getMediaUrl(s.image_url), 120)} alt="" loading="lazy"
             style={{ width: 60, height: 60, objectFit: 'cover', borderRadius: 'var(--r-md)', flexShrink: 0 }}
             onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = 'none'; }} />
      )}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div lang="shi" style={{ fontWeight: 800, fontSize: 16.5, lineHeight: 1.3 }}>{s.text_tachelhit}</div>
        <div style={{ fontSize: 13.5, color: 'var(--text-soft)' }}>{s.text_catalan}</div>
        {/* De qui és la frase i d'on: la varietat no s'amaga mai (docs/SCOPE.md). */}
        <div style={{ fontSize: 11.5, color: 'var(--text-muted)', marginTop: 2 }}>
          {s.speaker || 'sense nom'}{s.variety ? ` · ${s.variety}` : ''}{s.region ? ` · ${s.region}` : ''}
          {!s.audio_url && ' · encara sense veu'}
        </div>
        <SentenceVariants variants={s.variants} size="sm" />
      </div>
      {s.audio_url ? (
        <button onClick={play} aria-label="Escolta-la" title="Escolta-la"
                style={{ width: 38, height: 38, borderRadius: '50%', border: 'none', background: 'var(--brand-gradient)', color: '#fff', cursor: 'pointer', flexShrink: 0 }}>
          <FaPlay size={12} />
        </button>
      ) : hasIdentity() && (
        <button onClick={askForVoice} disabled={asked} title="Demana que algú la digui"
                style={{ padding: '6px 10px', borderRadius: 'var(--r-pill)', border: '1px solid var(--border)', background: 'var(--surface)', color: 'var(--text-soft)', fontSize: 11.5, fontWeight: 700, cursor: 'pointer', fontFamily: 'inherit', flexShrink: 0, whiteSpace: 'nowrap' }}>
          <FaMicrophone size={10} /> {asked ? 'demanada' : 'demana veu'}
        </button>
      )}
    </div>
  );
}

/** La línia de la capçalera: només números d'aquest capítol, i cadascun una cosa que es veu.
 *
 *  Es construeix amb el que el capítol porta i prou: una part que val zero no s'escriu (un
 *  capítol sense diàleg no ha de dir «diàleg de 0 rèpliques»). A mòbil cau «i N al voltant»,
 *  que és el que el pedagog va dir que trauria si no hi cabia.
 */
function chapterLine(c: MethodChapterData, isMobile: boolean): string {
  const b = c.content;
  const bits: string[] = [];
  const turns = b?.dialogue?.turns?.length || 0;
  if (turns) bits.push(`Diàleg de ${turns} ${turns === 1 ? 'rèplica' : 'rèpliques'}`);
  const words = b?.vocabulary?.length || 0;
  if (words) bits.push(`${words} ${words === 1 ? 'paraula' : 'paraules'}`);
  const secs = b?.sections || [];
  const aside = secs.filter((x) => x.zone === 'aside').length;
  const main = secs.length - aside;
  if (main) {
    bits.push(`${main} ${main === 1 ? 'explicació' : 'explicacions'} de com funciona`
              + (aside && !isMobile ? ` i ${aside} al voltant` : ''));
  }
  const p = c.practice_test;
  if (p) bits.push(`una pràctica de ${p.steps} ${p.steps === 1 ? 'pas' : 'passos'}`);
  // Un capítol que encara no s'ha escrit no té res d'això: llavors la pàgina són les frases de
  // la biblioteca que li toquen, i aquí es diu això mateix en comptes de callar.
  return bits.length ? bits.join(' · ') : 'Aquest capítol encara no s’ha escrit.';
}

export default function MethodChapter() {
  const { slug } = useParams();
  const navigate = useNavigate();
  const isMobile = useIsMobileLayout();
  const [c, setC] = useState<MethodChapterData | null>(null);
  const [error, setError] = useState<string | null>(null);
  // Qui administra pot corregir el text del capítol allà mateix, sense desplegar res.
  const [me, setMe] = useState<{ is_admin?: boolean } | null>(null);
  useEffect(() => { api.me().then(setMe).catch(() => setMe(null)); }, []);
  // La llista per unitat de gramàtica, plegada quan el capítol ja té text (vegeu més avall).
  const [openRest, setOpenRest] = useState(false);
  // El que algú ha proposat per a aquest capítol: qui administra les veu totes i les decideix,
  // qui no, veu les seves. Mateixa cua que les propostes del curs de gramàtica.
  const [proposals, setProposals] = useState<LessonProposal[]>([]);
  const loadProposals = () => {
    if (!slug) return;
    api.lessonProposals(`metode:${slug}`).then(setProposals).catch(() => setProposals([]));
  };
  useEffect(loadProposals, [slug]);

  useEffect(() => {
    if (!slug) return;
    setC(null); setError(null);
    api.methodChapter(slug).then(setC).catch((e) => setError(whyItFailed(e, 'No s’ha pogut carregar el capítol')));
  }, [slug]);

  if (error) return (
    <div style={{ padding: '40px 16px', textAlign: 'center' }}>
      <p style={{ color: 'var(--text-soft)' }}>{error}</p>
      <button onClick={() => navigate('/metode')} style={pill}>← El Mètode</button>
    </div>
  );
  if (!c) return <p style={{ padding: 40, textAlign: 'center', color: 'var(--text-soft)' }}>Carregant el capítol…</p>;

  return (
    <div style={{ padding: '18px 16px 40px', maxWidth: 760, margin: '0 auto' }}>
      <button onClick={() => navigate('/metode')} style={{ ...pill, marginBottom: 12 }}>← El Mètode</button>

      {/* El dibuix del capítol: de què va, abans de llegir-ne una paraula. */}
      {c.cover && (
        <img src={c.cover} alt="" loading="lazy"
             style={{ width: '100%', aspectRatio: '16 / 7', objectFit: 'cover', display: 'block', borderRadius: 'var(--r-lg)', marginBottom: 14 }}
             onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = 'none'; }} />
      )}
      <div style={{ fontSize: 12, fontWeight: 800, color: 'var(--brand-1)', letterSpacing: '0.06em' }}>CAPÍTOL {c.n}</div>
      {c.name && <h1 lang="shi" style={{ fontFamily: 'var(--font-display)', fontSize: 27, margin: '2px 0 0' }}>{c.name}</h1>}
      <h2 style={{ fontFamily: 'var(--font-display)', fontSize: c.name ? 19 : 26, fontWeight: c.name ? 600 : 800, color: c.name ? 'var(--text-soft)' : 'var(--text)', margin: '0 0 8px' }}>{c.title}</h2>
      <p style={{ color: 'var(--text-soft)', fontSize: 14.5, margin: '0 0 6px', lineHeight: 1.55 }}>{c.about}</p>
      {/* Al capítol dels sons: que la mateixa lletra s'escriu de dues maneres (#364). És el
          capítol on s'aprèn quina lletra fa quin so, i és on es topa amb «rix» i «riɣ». */}
      <NotaOrtografia nota={c.ortografia} />
      {/* Què hi ha EN AQUEST CAPÍTOL, i res més.

          Abans deia «3.412 frases · 1.180 amb veu · 4 de 4 seccions a punt». Cap dels tres
          números era del capítol: els dos primers compten tota la biblioteca que porta alguna de
          les seves unitats de gramàtica —fa dos dies deien 1.608 · 1.337, i en dos dies el total
          va pujar 1.800 i les veus van BAIXAR 157: això no descriu un capítol, descriu
          importacions— i el tercer era el capítol posant-se nota a si mateix, amb el denominador
          triat per qui el posava.

          Ara cada element és una promesa que la pàgina compleix tres dits més avall, i en
          l'ordre de les preguntes de qui l'obre: què hi passa, quantes paraules, quanta
          gramàtica (i que n'hi ha de secundària, que és el que les dues zones volen dir), i si
          en acabar hi ha res a fer. Cap número de veus: n'hi ha un de millor al botó de play, i
          dos comptadors de veus a la mateixa pantalla és el pecat original d'aquesta pàgina. */}
      <p style={{ color: 'var(--text-muted)', fontSize: 12.5, margin: '0 0 18px', lineHeight: 1.55 }}>
        {chapterLine(c, isMobile)}
      </p>
      {/* El comptador de manteniment: què queda per fer. No és per a qui aprèn —«a punt» no li
          vol dir res— i el capítol no s'ha de poder certificar a si mateix davant seu. */}
      {me?.is_admin && (
        <p style={{ color: 'var(--text-muted)', fontSize: 11.5, margin: '-12px 0 18px' }}>
          Manteniment: {c.sections_ready} de {c.sections_total} unitats del capítol tenen prou veu
          a la biblioteca.
        </p>
      )}

      <section style={{ padding: '14px 16px', borderRadius: 'var(--r-lg)', background: 'var(--brand-gradient-soft)', marginBottom: 20 }}>
        <h3 style={h3}>Què en sabràs fer</h3>
        <ul style={{ margin: '6px 0 0', paddingInlineStart: 18, fontSize: 14, lineHeight: 1.7 }}>
          {c.functions.map((f) => <li key={f}>{f}</li>)}
        </ul>
        {c.roles.length > 0 && (
          <p style={{ margin: '8px 0 0', fontSize: 12.5, color: 'var(--text-soft)' }}>
            Hi parlen: {c.roles.join(' i ')}.
          </p>
        )}
      </section>

      {/* La lliçó: el text del capítol, adaptat del manual i desat a la base de dades. Un capítol
          que encara no s'ha escrit no en té, i llavors la pàgina són les frases de la biblioteca
          que li toquen, que és el que hi havia fins ara. */}
      {c.content && slug && (
        <MethodLesson slug={slug} content={c.content} canEdit={!!me?.is_admin}
                      onChanged={() => api.methodChapter(slug).then(setC).catch(() => {})} />
      )}

      {/* La sortida del capítol.

          Un capítol s'acabava i no tornava mai: es llegia, i la següent vegada que la llengua
          et calia ja no te'n recordaves. La pràctica és el que ho arregla — puntua cada frase
          i el repàs espaiat les fa tornar soles, sense que te n'hagis de recordar tu.

          Les veus de la pràctica són de la biblioteca, no del manual: allà on el capítol
          escriu dar-, les nostres diuen ɣur-. És la mateixa cosa dita a l'Atles. */}
      {c.practice_test && (
        <section style={{ marginTop: 24, padding: '16px 18px', borderRadius: 'var(--r-lg)', background: 'var(--brand-gradient-soft)', border: '1px solid var(--border)' }}>
          <div style={{ fontSize: 11.5, fontWeight: 800, color: 'var(--brand-1)', letterSpacing: '0.07em' }}>
            I ARA, A PROVAR-HO
          </div>
          <h3 style={{ fontFamily: 'var(--font-display)', fontSize: 19, margin: '3px 0 5px' }}>
            {c.practice_test.title}
          </h3>
          <p style={{ fontSize: 13.5, color: 'var(--text-soft)', lineHeight: 1.6, margin: '0 0 12px' }}>
            {c.practice_test.steps} passos amb veus d’Aït Mraw: escoltar i triar, omplir el buit,
            escriure el que sents i dir-ho tu. El que marquis com a « encara no » tornarà sol
            d’aquí a uns dies.
          </p>
          <button onClick={() => navigate(`/tests/${c.practice_test!.id}`)}
                  style={{ padding: '10px 18px', borderRadius: 'var(--r-pill)', border: 'none', background: 'var(--brand-gradient)', color: '#fff', fontWeight: 800, fontSize: 14.5, cursor: 'pointer', fontFamily: 'inherit' }}>
            Fes la pràctica →
          </button>
        </section>
      )}

      {proposals.length > 0 && (
        <section style={{ marginTop: 22, padding: '12px 16px', borderRadius: 'var(--r-lg)', border: '1px solid var(--border)', background: 'var(--surface)' }}>
          <h3 style={h3}>{me?.is_admin ? 'PROPOSTES PER DECIDIR' : 'EL QUE HAS PROPOSAT'}</h3>
          {proposals.map((p) => (
            <div key={p.id} style={{ padding: '8px 0', borderTop: '1px solid var(--border)' }}>
              <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                {p.display_name || 'algú'}{p.region ? ` · ${p.region}` : ''} · secció {p.step + 1}
              </div>
              <p style={{ fontSize: 13.5, lineHeight: 1.55, margin: '4px 0 6px', whiteSpace: 'pre-line' }}>{p.text}</p>
              {me?.is_admin && (
                <div style={{ display: 'flex', gap: 6 }}>
                  <button onClick={async () => {
                    try {
                      await api.decideProposal(p.id, true);
                      toast.success('Acceptada');
                      loadProposals();
                      if (slug) api.methodChapter(slug).then(setC).catch(() => {});
                    } catch (e) { toast.error(whyItFailed(e, 'No s’ha pogut acceptar')); }
                  }} style={{ ...pill, borderColor: 'var(--emerald)', color: 'var(--emerald)' }}>Posa-la al capítol</button>
                  <button onClick={async () => {
                    try { await api.decideProposal(p.id, false); loadProposals(); }
                    catch (e) { toast.error(whyItFailed(e, 'No s’ha pogut fer')); }
                  }} style={pill}>Deixa-ho estar</button>
                </div>
              )}
            </div>
          ))}
        </section>
      )}

      {/* La llista de frases per unitat de gramàtica.

          Quan el capítol JA TÉ text, això no és el capítol: són totes les frases que porten
          alguna de les seves unitats, i l'amo ho va veure de seguida — «és realment aquest el
          mètode? vols dir que aquests drills il·lustren bé la secció "Els noms…"?». No: les
          frases triades per a cada secció són a dins de la lliçó, al costat del que expliquen.
          Això és la resta de la biblioteca, i va plegat i dit pel seu nom.

          Un capítol que encara no s'ha escrit no té res més, i llavors la llista ÉS la pàgina. */}

      {c.content && (
        <button onClick={() => setOpenRest((v) => !v)}
                style={{ width: '100%', textAlign: 'left', marginTop: 26, padding: '12px 16px', borderRadius: 'var(--r-lg)', border: '1px solid var(--border)', background: 'var(--surface)', cursor: 'pointer', fontFamily: 'inherit', color: 'var(--text)' }}>
          <span style={{ fontWeight: 800, fontSize: 15 }}>
            {openRest ? '▾' : '▸'} La resta de la biblioteca d’aquest capítol
          </span>
          <span style={{ display: 'block', fontSize: 12.5, color: 'var(--text-muted)', marginTop: 2, lineHeight: 1.5 }}>
            {c.sentences} frases, {c.with_voice} amb veu: totes les que porten alguna de les
            unitats de gramàtica del capítol, agrupades per unitat. No estan triades per a cap
            secció —les triades són a dins de la lliçó— i el número puja cada vegada que
            s’importa material, sense que el capítol hagi canviat.
          </span>
        </button>
      )}

      {(!c.content || openRest) && <div style={{ marginTop: 14 }}>
      {c.sections.map((s, k) => (
        <section key={s.slug} style={{ marginBottom: 22 }}>
          <h3 style={{ ...h3, fontSize: 12.5 }}>{k + 1}. {s.title.toUpperCase()}</h3>
          {s.sentences.length === 0 ? (
            <p style={{ fontSize: 13.5, color: 'var(--text-muted)', margin: '6px 0 0', lineHeight: 1.55 }}>
              D’això encara no en tenim cap frase. No és un punt que es vegi escrit a la frase, o
              encara no s’ha gravat.
            </p>
          ) : (
            <>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 8 }}>
                {s.sentences.map((x) => <Sentence key={x.id} s={x} />)}
              </div>
              <p style={{ fontSize: 12, color: 'var(--text-muted)', margin: '6px 0 0' }}>
                {s.with_voice} de {s.total} amb veu
                {s.total > s.sentences.length && ` · se’n mostren ${s.sentences.length}`}
                {' · '}
                <button onClick={() => navigate(`/grammar/${s.slug}`)} style={linkBtn}>la unitat sencera</button>
              </p>
            </>
          )}
        </section>
      ))}

      {c.also.length > 0 && (
        <section style={{ marginBottom: 22 }}>
          <h3 style={{ ...h3, fontSize: 12.5 }}>TAMBÉ D’AQUEST CAPÍTOL</h3>
          <p style={{ fontSize: 12.5, color: 'var(--text-muted)', margin: '2px 0 8px' }}>
            Frases del tema del capítol que no cauen en cap de les seccions de dalt.
          </p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {c.also.map((x) => <Sentence key={x.id} s={x} />)}
          </div>
        </section>
      )}
      </div>}

      {(c.missing.thin.length > 0 || c.missing.voiceless_total > 0) && (
        <section style={{ padding: '14px 16px', borderRadius: 'var(--r-lg)', border: '1px solid var(--border)', background: 'var(--surface)', marginBottom: 20 }}>
          <h3 style={h3}>El que falta per acabar-lo</h3>
          {c.missing.thin.map((t) => (
            <p key={t.slug} style={{ margin: '6px 0 0', fontSize: 13.5, lineHeight: 1.55 }}>
              <strong>{t.title}</strong>{' — '}
              {t.nowhere
                ? 'cap frase de la biblioteca no el porta. No és un punt que es vegi escrit a la frase.'
                : `${t.sentences} ${t.sentences === 1 ? 'frase' : 'frases'}, i només ${t.with_voice} amb veu. En calen tres que es puguin escoltar.`}
            </p>
          ))}
          {c.missing.voiceless_total > 0 && (
            <p style={{ margin: '10px 0 0', fontSize: 13.5, lineHeight: 1.55 }}>
              {c.missing.voiceless_total} {c.missing.voiceless_total === 1 ? 'frase d’aquest capítol encara no té veu' : 'frases d’aquest capítol encara no tenen veu'}.
              Pots demanar-les una a una a la seva targeta, o gravar-les tu a <button onClick={() => navigate('/veus')} style={linkBtn}>Posa-hi veu</button>.
            </p>
          )}
        </section>
      )}

      {c.topics.length > 0 && (
        <p style={{ fontSize: 12.5, color: 'var(--text-muted)', marginBottom: 18 }}>
          <FaTag size={10} /> Temes d’aquest capítol: {c.topics.map((t) => t.label).join(' · ')}
        </p>
      )}

      <footer style={{ padding: '14px 16px', borderRadius: 'var(--r-lg)', background: 'var(--surface-2)', fontSize: 12.5, color: 'var(--text-soft)', lineHeight: 1.6 }}>
        <FaBookOpen size={11} /> Basat en <strong>{c.source.author}</strong>,
        «{c.source.title}», {c.source.publisher}, {c.source.place} {c.source.year},
        adaptat a la varietat que ensenyem.
        <br />
        Les veus són nostres: cada frase la diu una persona de debò que el projecte coneix.
      </footer>
    </div>
  );
}

const h3: React.CSSProperties = {
  margin: 0, fontSize: 11.5, fontWeight: 800, letterSpacing: '0.06em',
  textTransform: 'uppercase', color: 'var(--text-muted)',
};
const pill: React.CSSProperties = {
  display: 'inline-flex', alignItems: 'center', gap: 6, padding: '6px 12px',
  borderRadius: 'var(--r-pill)', border: '1px solid var(--border)', background: 'var(--surface)',
  color: 'var(--text-soft)', fontWeight: 700, fontSize: 12.5, cursor: 'pointer', fontFamily: 'inherit',
};
const linkBtn: React.CSSProperties = {
  background: 'transparent', border: 'none', padding: 0, color: 'var(--brand-1)',
  fontWeight: 700, fontSize: 'inherit', cursor: 'pointer', fontFamily: 'inherit',
};
