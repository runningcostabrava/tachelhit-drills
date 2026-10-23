import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { FaBookOpen, FaMicrophone, FaPlay, FaTag } from 'react-icons/fa';
import { api, type MethodChapterData, type MethodSentence } from '../api';
import { getMediaUrl, hasIdentity } from '../config';
import { toast } from '../toast';
import { whyItFailed } from '../utils/errors';
import MethodLesson from './MethodLesson';

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
        <img src={getMediaUrl(s.image_url)} alt="" loading="lazy"
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

export default function MethodChapter() {
  const { slug } = useParams();
  const navigate = useNavigate();
  const [c, setC] = useState<MethodChapterData | null>(null);
  const [error, setError] = useState<string | null>(null);
  // Qui administra pot corregir el text del capítol allà mateix, sense desplegar res.
  const [me, setMe] = useState<{ is_admin?: boolean } | null>(null);
  useEffect(() => { api.me().then(setMe).catch(() => setMe(null)); }, []);

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

      <div style={{ fontSize: 12, fontWeight: 800, color: 'var(--brand-1)', letterSpacing: '0.06em' }}>CAPÍTOL {c.n}</div>
      {c.name && <h1 lang="shi" style={{ fontFamily: 'var(--font-display)', fontSize: 27, margin: '2px 0 0' }}>{c.name}</h1>}
      <h2 style={{ fontFamily: 'var(--font-display)', fontSize: c.name ? 19 : 26, fontWeight: c.name ? 600 : 800, color: c.name ? 'var(--text-soft)' : 'var(--text)', margin: '0 0 8px' }}>{c.title}</h2>
      <p style={{ color: 'var(--text-soft)', fontSize: 14.5, margin: '0 0 6px', lineHeight: 1.55 }}>{c.about}</p>
      <p style={{ color: 'var(--text-muted)', fontSize: 12.5, margin: '0 0 18px' }}>
        {c.sentences} frases · {c.with_voice} amb veu · {c.sections_ready} de {c.sections_total} seccions a punt
      </p>

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

      {c.content && c.sections.some((s) => s.sentences.length > 0) && (
        <h3 style={{ fontFamily: 'var(--font-display)', fontSize: 18, margin: '26px 0 2px' }}>
          Dit per les nostres veus
        </h3>
      )}
      {c.content && (
        <p style={{ fontSize: 13, color: 'var(--text-muted)', margin: '0 0 12px', lineHeight: 1.55 }}>
          Les frases de la biblioteca que fan el que aquest capítol ensenya, amb qui les diu i d’on és.
        </p>
      )}

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
