import { useEffect, useMemo, useState } from 'react';
import { FaVolumeUp } from 'react-icons/fa';
import { api } from '../api';
import { getMediaUrl } from '../config';
import type { Drill } from '../types';
import { duesCares } from '../utils/tifinag';
import { say } from '../utils/veu';
import { START_BLOCKS, START_DRILL_IDS, type StartWord } from '../lessons/startEnglish';

// «Start here · English» (#487): the one page of the app written for English speakers.
//
// The rest of the app stays in Catalan (owner, 29-10-2026). This page is the first hour of
// someone who is coming to run in the Atlas: a few words, the voice of somebody who speaks them,
// and enough about the language and the people to know what they are hearing.

const VARIETY_EN: Record<string, string> = {
  tzm: 'Central Atlas Tamazight',
  tdl: 'Tadla–Azilal (transition Tashelhit)',
  shi: 'Tashelhit',
  zgh: 'Standard Moroccan Amazigh',
};

/** Who is speaking, said the way the rest of the app says it: a person if we know them. */
function whoSpeaks(d: Drill): string {
  const tag = d.tag || '';
  const place = (d.region || '').trim();
  if (/\bHalima\b/.test(tag)) return `Halima${place ? ` · ${place}` : ''}`;
  if (/\bDriss\b/.test(tag)) return `Driss${place ? ` · ${place}` : ''}`;
  // The library writes its labels in Catalan; on this page the reader has no Catalan.
  const who = (d.speaker || d.source_channel || '').trim().replace(/\(parlant nadiu\)/i, '(native speaker)');
  return [who, place].filter(Boolean).join(' · ') || 'a speaker from our library';
}

function WordCard({ w, d, playing, onPlay }: { w: StartWord; d?: Drill; playing: boolean; onPlay: () => void }) {
  const cares = d ? duesCares(d.text_tachelhit || '', d.text_tachelhit_latin) : (w.text ? duesCares(w.text) : null);
  const voice = !!d?.audio_url;
  return (
    <div style={{ minWidth: 0, display: 'flex', flexDirection: 'column', gap: 6, padding: '14px 14px 12px',
                  borderRadius: 'var(--r-lg)', border: '1px solid var(--border)', background: 'var(--surface)' }}>
      <div style={{ fontWeight: 800, fontSize: 16 }}>{w.en}</div>
      {cares && (
        <>
          <div lang="zgh" className="tifinagh" style={{ fontSize: 22, lineHeight: 1.3, color: 'var(--brand-1)', overflowWrap: 'anywhere' }}>{cares.tif}</div>
          <div style={{ fontSize: 15, fontWeight: 600, overflowWrap: 'anywhere' }}>{cares.lat}</div>
        </>
      )}
      <div style={{ fontSize: 13, color: 'var(--text-soft)' }}>Say it: <em>{w.say}</em></div>
      {w.example && <div style={{ fontSize: 13, color: 'var(--text-soft)', lineHeight: 1.5 }}>{w.example}</div>}
      {w.note && <div style={{ fontSize: 13, color: 'var(--text-soft)', lineHeight: 1.5 }}>{w.note}</div>}
      <div style={{ marginTop: 'auto', paddingTop: 6, display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8, flexWrap: 'wrap' }}>
        <span style={{ fontSize: 11.5, color: 'var(--text-muted)', minWidth: 0 }}>
          {d ? <>{whoSpeaks(d)}{d.variety && VARIETY_EN[d.variety] ? ` · ${VARIETY_EN[d.variety]}` : ''}</> : 'Written by our guide · no recording yet'}
        </span>
        {voice ? (
          <button type="button" onClick={onPlay} aria-pressed={playing}
                  style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '7px 14px', minHeight: 36,
                           borderRadius: 'var(--r-pill)', border: '1px solid var(--brand-1)', cursor: 'pointer', fontFamily: 'inherit',
                           fontWeight: 700, fontSize: 13, background: playing ? 'var(--brand-1)' : 'transparent',
                           color: playing ? '#fff' : 'var(--brand-1)' }}>
            <FaVolumeUp size={12} /> Listen
          </button>
        ) : d ? <span style={{ fontSize: 12, color: 'var(--text-muted)', fontStyle: 'italic' }}>no recording yet</span> : null}
      </div>
    </div>
  );
}

/** Listen, then pick the meaning. Only words with a real voice can be asked. */
function Practice({ words, drills }: { words: StartWord[]; drills: Record<number, Drill> }) {
  const pool = useMemo(() => words.filter((w) => w.drillId && drills[w.drillId]?.audio_url), [words, drills]);
  const [n, setN] = useState(0);
  const [picked, setPicked] = useState<string | null>(null);
  const [right, setRight] = useState(0);
  const q = useMemo(() => {
    if (pool.length < 2) return null;
    const answer = pool[Math.floor(Math.random() * pool.length)];
    const others = pool.filter((w) => w.key !== answer.key).sort(() => Math.random() - 0.5).slice(0, 3);
    return { answer, options: [answer, ...others].sort(() => Math.random() - 0.5) };
    // n is the question number: a new one each time
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pool, n]);
  if (!q) return null;
  const play = () => { const d = drills[q.answer.drillId as number]; if (d?.audio_url) say(getMediaUrl(d.audio_url)); };
  return (
    <div style={{ padding: 16, borderRadius: 'var(--r-xl)', border: '1px solid var(--border)', background: 'var(--surface)', display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10, flexWrap: 'wrap', alignItems: 'baseline' }}>
        <strong>Question {n + 1}</strong>
        <span style={{ fontSize: 13, color: 'var(--text-soft)' }}>{right} right</span>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
        Listen, then pick the meaning.
        <button type="button" onClick={play}
                style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '7px 14px', minHeight: 36, borderRadius: 'var(--r-pill)',
                         border: '1px solid var(--brand-1)', background: 'transparent', color: 'var(--brand-1)', fontWeight: 700, cursor: 'pointer', fontFamily: 'inherit' }}>
          <FaVolumeUp size={12} /> Play
        </button>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: 8 }}>
        {q.options.map((o) => {
          const isRight = o.key === q.answer.key;
          const shown = picked !== null && (isRight || picked === o.key);
          return (
            <button key={o.key} type="button" disabled={picked !== null}
                    onClick={() => { setPicked(o.key); if (isRight) setRight((r) => r + 1); }}
                    style={{ textAlign: 'left', padding: '11px 13px', minHeight: 46, borderRadius: 'var(--r-lg)', fontFamily: 'inherit', fontSize: 14,
                             cursor: picked === null ? 'pointer' : 'default', background: 'var(--bg)', color: 'var(--text)',
                             border: `1px solid ${shown ? (isRight ? 'var(--emerald)' : 'var(--rose, #b3364a)') : 'var(--border)'}`,
                             fontWeight: shown && isRight ? 800 : 500 }}>
              {o.en}
            </button>
          );
        })}
      </div>
      {picked !== null && (
        <button type="button" onClick={() => { setPicked(null); setN((x) => x + 1); }}
                style={{ alignSelf: 'flex-start', padding: '9px 18px', minHeight: 42, borderRadius: 'var(--r-pill)', border: 'none',
                         background: 'var(--brand-gradient)', color: '#fff', fontWeight: 800, cursor: 'pointer', fontFamily: 'inherit' }}>
          Next
        </button>
      )}
    </div>
  );
}

const H2: React.CSSProperties = { fontFamily: 'var(--font-display)', fontSize: 20, margin: '0 0 8px', lineHeight: 1.25 };
const P: React.CSSProperties = { margin: '0 0 10px', fontSize: 15, lineHeight: 1.65, maxWidth: '66ch' };

export default function StartEnglish() {
  const [drills, setDrills] = useState<Record<number, Drill>>({});
  // Words the owner wrote by hand: if somebody has since recorded one, it plays (#504).
  const [found, setFound] = useState<Record<string, Drill>>({});
  const [playing, setPlaying] = useState<string | null>(null);

  useEffect(() => {
    document.title = 'Start here · Tamazight';
    let alive = true;
    Promise.all(START_DRILL_IDS.map((id) => api.drill(id).then((d) => [id, d] as const).catch(() => null)))
      .then((rows) => { if (alive) setDrills(Object.fromEntries(rows.filter((r): r is readonly [number, Drill] => !!r))); });
    const written = START_BLOCKS.flatMap((b) => b.words).filter((w) => !w.drillId && w.text);
    if (written.length) {
      api.voiced(written.map((w) => w.text as string))
        .then((v) => Promise.all(written.map((w) => {
          const hit = v[w.text as string];
          return hit ? api.drill(hit.drill_id).then((d) => [w.key, d] as const).catch(() => null) : null;
        })))
        .then((rows) => { if (alive) setFound(Object.fromEntries(rows.filter((r): r is readonly [string, Drill] => !!r))); })
        .catch(() => {});
    }
    return () => { alive = false; };
  }, []);

  const play = (w: StartWord) => {
    const d = w.drillId ? drills[w.drillId] : found[w.key];
    if (!d?.audio_url) return;
    setPlaying(w.key);
    say(getMediaUrl(d.audio_url)).then(() => setPlaying((p) => (p === w.key ? null : p)));
  };
  const allWords = START_BLOCKS.flatMap((b) => b.words);

  return (
    <div lang="en" style={{ padding: '22px 16px 60px', maxWidth: 920, margin: '0 auto', width: '100%', boxSizing: 'border-box' }}>
      <div style={{ fontSize: 12, letterSpacing: '.1em', textTransform: 'uppercase', fontWeight: 800, color: 'var(--brand-1)' }}>Start here · English</div>
      <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 28, margin: '6px 0 8px', lineHeight: 1.15 }}>
        Your first Tamazight words <span lang="zgh" className="tifinagh" style={{ color: 'var(--brand-1)', fontWeight: 400 }}>ⵜⴰⵎⴰⵣⵉⵖⵜ</span>
      </h1>
      <p style={{ ...P, color: 'var(--text-soft)' }}>
        A handful of words for the mountains: to greet people, to thank them, to ask for bread and
        water, and to say who you are. Every word is written in Tifinagh, the Amazigh alphabet, and
        in Latin letters, and when you press Listen you hear a person from the Atlas, never a computer.
      </p>
      {/* Each source keeps its own spelling (a speaker's words are theirs), so the reader needs the
          key to read three ways of writing one sound. */}
      <p style={{ ...P, fontSize: 13.5, color: 'var(--text-soft)' }}>
        Reading the Latin letters: each speaker writes the way they learned, so the same sound can
        look different. <strong>c</strong>, <strong>š</strong> and <strong>sh</strong> are “sh”;
        {' '}<strong>ɣ</strong>, <strong>ġ</strong> and <strong>gh</strong> are a French “r” at the
        back of the throat; <strong>x</strong> is the “ch” of Scottish <em>loch</em>; <strong>ɛ</strong> and
        {' '}<strong>3</strong> are a sound made deep in the throat; a doubled letter is held longer.
      </p>

      {START_BLOCKS.map((b) => (
        <section key={b.title} style={{ margin: '26px 0' }}>
          <h2 style={H2}>{b.title}</h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: 12 }}>
            {b.words.map((w) => (
              <WordCard key={w.key} w={w} d={w.drillId ? drills[w.drillId] : found[w.key]}
                        playing={playing === w.key} onPlay={() => play(w)} />
            ))}
          </div>
        </section>
      ))}

      <section style={{ margin: '26px 0' }}>
        <h2 style={H2}>Practice</h2>
        <Practice words={allWords} drills={drills} />
      </section>

      <section style={{ margin: '22px 0' }}>
        <h2 style={H2}>The language</h2>
        <p style={P}>
          Tamazight (often called “Berber”, a word its speakers do not use) is the language of the
          Imazighen, North Africa’s first people. It is a family of closely related varieties spoken
          from Morocco to Egypt’s Siwa oasis and across the Sahara. In Morocco it has three big
          branches, Tarifit in the north, Central Atlas Tamazight in the Middle and High Atlas, and
          Tashelhit in the south-west, and since 2011 it has been an official language of the
          country, next to Arabic.
        </p>
        <p style={P}>
          It has its own alphabet, Tifinagh (ⵜⵉⴼⵉⵏⴰⵖ), whose letters go back more than two thousand
          years and are now taught in Moroccan schools. You will also see it written in Latin and in
          Arabic letters, and you will hear many Arabic and French words mixed in, like <em>salam</em>.
        </p>
      </section>

      <section style={{ margin: '22px 0' }}>
        <h2 style={H2}>The people</h2>
        <p style={P}>
          <em>Imazighen</em> (one man is an <em>Amazigh</em>, one woman a <em>Tamazight</em>) is usually
          explained as “the free people”. They lived in North Africa long before the Phoenicians, the
          Romans and the Arabs arrived; the kingdoms of Numidia and Mauretania were theirs, and so were
          the Almoravid and Almohad dynasties that ruled from Marrakech over Morocco and al-Andalus.
          Islam arrived in the 7th and 8th centuries and is the faith of the valleys today. In the High
          Atlas the Amazigh way of life is still very present: villages of earth and stone, terraced
          fields watered by shared channels, flocks that go up to the summer pastures, and a strong
          custom of welcoming guests, with tea, bread and olive oil.
        </p>
      </section>

      <section style={{ margin: '22px 0' }}>
        <h2 style={H2}>Where we run: Azilal and the M’Goun</h2>
        <p style={P}>
          Our routes cross the Central High Atlas, in the province of Azilal: the high valleys around
          the M’Goun massif, one of the highest summits of the Atlas at about 4,070 m, with valleys
          such as the Aït Bouguemmez on the north side and the M’Goun river and its gorges on the
          south side, down towards Kalaat M’Gouna. It is a land of Amazigh villages, where Tamazight
          is the language of home.
        </p>
        <p style={P}>
          The speech of this area sits on the border between Central Atlas Tamazight and Tashelhit,
          so it shares words with both and changes a little from valley to valley. The voices you hear
          on this page are tagged with where they come from: Halima and Driss are from Aït Mraw, in
          Azilal; other words come from speakers of Central Atlas Tamazight and of the Tadla–Azilal
          plain around Beni Mellal. The basic words, <em>aman</em>, <em>aɣrum</em>, <em>tanmmirt</em>,
          are understood all over.
        </p>
      </section>

      <p style={{ fontSize: 12.5, color: 'var(--text-muted)', lineHeight: 1.6, marginTop: 28 }}>
        The voices are from our library: Halima and Driss (Aït Mraw, Azilal), a native speaker recorded
        by ILoveLanguages!, and the Beni Mellal collection. The Tifinagh is written by our own
        transliterator from what each speaker wrote. A word marked “no recording yet” is waiting for a
        voice.
      </p>
    </div>
  );
}
