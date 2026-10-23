import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { FaBookOpen, FaCheck, FaMicrophone } from 'react-icons/fa';
import { api, type MethodIndex } from '../api';
import { toast } from '../toast';

// El Mètode: deu capítols que porten algú de zero a dir alguna cosa al mercat.
//
// L'àrea és nova, però el que ensenya no: cada capítol s'omple amb frases de la nostra
// biblioteca, dites per gent que coneixem. Del manual que segueix el recorregut se'n pren el
// pla i no se'n pren ni una paraula (ADR 0003), i la citació va al peu de cada capítol.
//
// La barra d'un capítol NO és el teu progrés. És quantes de les seves seccions tenen prou
// frases que es puguin ESCOLTAR, perquè una frase muda ensenya a llegir-la i això és un curs
// per parlar. Un capítol curt no està mal fet: és una llista de feina de gravació.

export default function MethodPage() {
  const navigate = useNavigate();
  const [data, setData] = useState<MethodIndex | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    api.methodIndex().then(setData).catch(() => {
      setFailed(true);
      toast.error('No s’ha pogut carregar el Mètode');
    });
  }, []);

  if (failed) return <p style={{ padding: 40, textAlign: 'center', color: 'var(--text-soft)' }}>No s’ha pogut carregar el Mètode.</p>;
  if (!data) return <p style={{ padding: 40, textAlign: 'center', color: 'var(--text-soft)' }}>Carregant els capítols…</p>;

  const ready = data.chapters.filter((c) => c.sections_ready === c.sections_total).length;

  return (
    <div style={{ padding: '20px 16px 40px', maxWidth: 900, margin: '0 auto' }}>
      <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 26, margin: '0 0 4px' }}>El Mètode</h1>
      <p style={{ color: 'var(--text-soft)', fontSize: 14.5, margin: '0 0 6px', lineHeight: 1.55 }}>
        Deu capítols, de saludar a tenir convidats a taula. Cada frase la diu algú de debò, i diu
        qui és i d’on.
      </p>
      <p style={{ color: 'var(--text-muted)', fontSize: 13, margin: '0 0 20px' }}>
        {ready} de {data.chapters.length} capítols tenen prou veu a totes les seccions.
      </p>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {data.chapters.map((c) => {
          const full = c.sections_total ? (c.sections_ready / c.sections_total) * 100 : 0;
          return (
            <button
              key={c.slug}
              onClick={() => navigate(`/metode/${c.slug}`)}
              style={{ textAlign: 'left', padding: '14px 16px', borderRadius: 'var(--r-lg)', border: '1px solid var(--border)', background: 'var(--surface)', cursor: 'pointer', fontFamily: 'inherit', color: 'var(--text)', display: 'flex', flexDirection: 'column', gap: 6 }}
            >
              <div style={{ display: 'flex', alignItems: 'baseline', gap: 10, flexWrap: 'wrap' }}>
                <span style={{ fontSize: 12, fontWeight: 800, color: 'var(--brand-1)', letterSpacing: '0.06em' }}>
                  CAPÍTOL {c.n}
                </span>
                {c.name && <span lang="shi" style={{ fontSize: 15.5, fontWeight: 800 }}>{c.name}</span>}
                <span style={{ fontSize: 15.5, fontWeight: 700, color: c.name ? 'var(--text-soft)' : 'var(--text)' }}>
                  {c.name ? `· ${c.title}` : c.title}
                </span>
              </div>
              <p style={{ margin: 0, fontSize: 13.5, color: 'var(--text-soft)', lineHeight: 1.5 }}>{c.about}</p>

              <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginTop: 2 }}>
                <div style={{ flex: 1, height: 8, borderRadius: 4, background: 'var(--surface-2)', overflow: 'hidden' }}>
                  <div style={{ width: `${full}%`, height: 8, background: full === 100 ? 'var(--emerald)' : 'var(--brand-1)' }} />
                </div>
                <span style={{ fontSize: 12, color: 'var(--text-muted)', fontWeight: 700, whiteSpace: 'nowrap' }}>
                  {c.sections_ready === c.sections_total
                    ? <><FaCheck size={10} style={{ color: 'var(--emerald)' }} /> a punt</>
                    : `${c.sections_ready} de ${c.sections_total} seccions`}
                </span>
              </div>

              <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                {c.sentences} {c.sentences === 1 ? 'frase' : 'frases'} · <FaMicrophone size={9} /> {c.with_voice} amb veu
                {c.varieties.length > 0 && ` · ${c.varieties.join(', ')}`}
              </div>
            </button>
          );
        })}
      </div>

      <footer style={{ marginTop: 24, padding: '14px 16px', borderRadius: 'var(--r-lg)', background: 'var(--surface-2)', fontSize: 12.5, color: 'var(--text-soft)', lineHeight: 1.6 }}>
        <FaBookOpen size={11} /> El recorregut segueix el pla de <strong>{data.source.author}</strong>,
        «{data.source.title}», {data.source.publisher}, {data.source.place} {data.source.year}.
        <br />
        N’hem pres {data.source.took}. No n’hem pres {data.source.did_not_take}.
      </footer>
    </div>
  );
}
