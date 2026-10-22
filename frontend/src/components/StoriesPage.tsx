import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { FaChevronLeft, FaExternalLinkAlt, FaPause, FaPlay } from 'react-icons/fa';
import { api, type Story, type StoryPage } from '../api';
import { getMediaUrl } from '../config';
import type { Drill } from '../types';
import WordGloss from './WordGloss';

// Whole stories and songs, instead of loose sentences (#189).
//
// The library had these all along, broken into pieces: a fable told start to finish, a song with
// its lyrics, each line a drill like any other. They share a source and they say when they are
// spoken, so putting them back in order gives the text back — with every line's voice, meaning
// and word-by-word gloss still attached.
//
// A line whose Amazigh words nobody has written down keeps its place and says so. A story with
// holes is still a story, and the hole is work somebody can do.

export default function StoriesPage() {
  const { slug } = useParams<{ slug: string }>();
  return slug ? <OneStory slug={slug} /> : <StoryList />;
}

function StoryList() {
  const navigate = useNavigate();
  const [stories, setStories] = useState<Story[] | null>(null);

  useEffect(() => {
    document.title = 'Històries i cançons · Tamazight';
    api.stories().then((r) => setStories(r.stories)).catch(() => setStories([]));
  }, []);

  return (
    <div style={{ padding: '20px 16px 40px', maxWidth: 900, margin: '0 auto' }}>
      <button onClick={() => navigate('/grammar')} style={back}><FaChevronLeft /> Gramàtica</button>
      <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 24, margin: '6px 0 4px' }}>Històries i cançons</h1>
      <p style={{ color: 'var(--text-soft)', fontSize: 14, margin: '0 0 18px', lineHeight: 1.55 }}>
        Coses senceres, no frases soltes: un conte explicat de cap a fi, una cançó amb la seva lletra.
        Cada línia porta la veu de qui la diu i què vol dir.
      </p>

      {!stories && <p style={{ color: 'var(--text-muted)' }}>Carregant…</p>}
      {stories && stories.length === 0 && (
        <p style={{ color: 'var(--text-muted)', lineHeight: 1.6 }}>
          Encara no n’hi ha cap de sencera. Perquè una captura es converteixi en història li calen
          sis línies o més, amb el moment en què es diuen i amb veu.
        </p>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))', gap: 14 }}>
        {(stories || []).map((s) => (
          <button key={s.slug} onClick={() => navigate(`/stories/${s.slug}`)} style={card}>
            {s.cover && (
              <img src={getMediaUrl(s.cover)} alt="" style={{ width: '100%', aspectRatio: '16 / 9', objectFit: 'cover', borderRadius: 'var(--r-md)', marginBottom: 8 }}
                   onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = 'none'; }} />
            )}
            <div style={{ fontWeight: 800, fontSize: 15, lineHeight: 1.3 }}>{s.title}</div>
            <div style={{ fontSize: 12.5, color: 'var(--text-soft)', marginTop: 3 }}>
              {s.lines} línies{s.speaker ? ` · ${s.speaker}` : ''}
            </div>
            {s.missing_words > 0 && (
              <div style={{ fontSize: 12, color: 'var(--saffron-dark, #7A4A12)', fontWeight: 700, marginTop: 4 }}>
                {s.missing_words} {s.missing_words === 1 ? 'línia encara sense paraules escrites' : 'línies encara sense paraules escrites'}
              </div>
            )}
          </button>
        ))}
      </div>
    </div>
  );
}

function OneStory({ slug }: { slug: string }) {
  const navigate = useNavigate();
  const [page, setPage] = useState<StoryPage | null>(null);
  const [missing, setMissing] = useState(false);
  const [at, setAt] = useState<number | null>(null);     // which line is sounding
  const [reading, setReading] = useState(false);          // reading it through, line after line
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const readingRef = useRef(false);

  useEffect(() => {
    api.story(slug).then((r) => { setPage(r); document.title = `${r.title} · Tamazight`; })
      .catch(() => setMissing(true));
    return () => { readingRef.current = false; audioRef.current?.pause(); };
  }, [slug]);

  const playLine = useCallback((drill: Drill, i: number) => new Promise<void>((resolve) => {
    const url = (drill.audio_url || drill.audio_tts_shi_url || '').trim();
    if (!url) { resolve(); return; }
    audioRef.current?.pause();
    const a = new Audio(getMediaUrl(url));
    audioRef.current = a;
    setAt(i);
    a.onended = () => resolve();
    a.onerror = () => resolve();
    a.play().catch(() => resolve());
  }), []);

  // Read it through: the point of a story is hearing it as one thing.
  const readThrough = async () => {
    if (!page) return;
    if (readingRef.current) { readingRef.current = false; setReading(false); audioRef.current?.pause(); setAt(null); return; }
    readingRef.current = true; setReading(true);
    for (let i = 0; i < page.drills.length; i++) {
      if (!readingRef.current) break;
      await playLine(page.drills[i], i);
      await new Promise((r) => setTimeout(r, 350));
    }
    readingRef.current = false; setReading(false); setAt(null);
  };

  if (missing) return <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-soft)' }}>Aquesta història no existeix.</div>;
  if (!page) return <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-soft)' }}>Carregant…</div>;

  return (
    <div style={{ padding: '20px 16px 60px', maxWidth: 760, margin: '0 auto' }}>
      <button onClick={() => navigate('/stories')} style={back}><FaChevronLeft /> Històries</button>
      <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 25, margin: '6px 0 4px', lineHeight: 1.25 }}>{page.title}</h1>
      <p style={{ color: 'var(--text-soft)', fontSize: 13.5, margin: '0 0 14px' }}>
        {page.lines} línies{page.speaker ? ` · ho diu ${page.speaker}` : ''}{page.channel ? ` · ${page.channel}` : ''}
        {page.source_url && (
          <> · <a href={page.source_url} target="_blank" rel="noopener noreferrer" style={{ color: 'var(--brand-1)', fontWeight: 700 }}>
            vídeo original <FaExternalLinkAlt size={9} />
          </a></>
        )}
      </p>

      <button onClick={readThrough} style={{ ...primary, marginBottom: 18 }}>
        {reading ? <><FaPause size={12} /> Atura</> : <><FaPlay size={12} /> Escolta-la sencera</>}
      </button>

      {page.missing_words > 0 && (
        <div style={{ padding: '10px 14px', borderRadius: 'var(--r-lg)', background: 'var(--brand-gradient-soft)', marginBottom: 16, fontSize: 13.5, lineHeight: 1.55 }}>
          Hi ha {page.missing_words} {page.missing_words === 1 ? 'línia' : 'línies'} que encara no tenen les
          paraules escrites: se senten, però no es poden llegir. Són a la cua de verificació, amb una
          lectura de màquina esperant que algú la miri.
        </div>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {page.drills.map((d, i) => {
          const written = (d.text_tachelhit || '').trim();
          return (
            <div key={d.id} style={{
              display: 'flex', gap: 10, padding: '10px 12px', borderRadius: 'var(--r-lg)',
              border: '1px solid var(--border)',
              background: at === i ? 'var(--brand-gradient-soft)' : 'var(--surface)',
            }}>
              <button onClick={() => playLine(d, i)} aria-label={`Escolta la línia ${i + 1}`}
                      style={{ flexShrink: 0, width: 34, height: 34, borderRadius: '50%', border: 'none', background: 'var(--surface-2)', color: 'var(--brand-1)', cursor: 'pointer', display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}>
                <FaPlay size={11} />
              </button>
              <div style={{ flex: 1, minWidth: 0 }}>
                {written ? (
                  <div style={{ fontSize: 16.5, fontWeight: 800, lineHeight: 1.35 }}>{written}</div>
                ) : (
                  <div style={{ fontSize: 14, color: 'var(--saffron-dark, #7A4A12)', fontWeight: 700 }}>
                    (aquesta línia encara no té les paraules escrites)
                  </div>
                )}
                <div style={{ fontSize: 14, color: 'var(--text-soft)', lineHeight: 1.45 }}>{d.text_catalan}</div>
                <WordGloss drill={d} size="sm" />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

const card: React.CSSProperties = { textAlign: 'left', padding: 12, borderRadius: 'var(--r-lg)', border: '1px solid var(--border)', background: 'var(--surface)', cursor: 'pointer', color: 'var(--text)', fontFamily: 'inherit' };
const primary: React.CSSProperties = { display: 'inline-flex', alignItems: 'center', gap: 8, padding: '10px 18px', borderRadius: 'var(--r-pill)', border: 'none', background: 'var(--brand-gradient)', color: '#fff', fontWeight: 800, fontSize: 14, cursor: 'pointer', fontFamily: 'inherit' };
const back: React.CSSProperties = { display: 'inline-flex', alignItems: 'center', gap: 6, padding: 0, border: 'none', background: 'none', color: 'var(--brand-1)', fontWeight: 700, fontSize: 13, cursor: 'pointer', fontFamily: 'inherit' };
