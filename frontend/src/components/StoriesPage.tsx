import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { FaChevronLeft, FaExternalLinkAlt, FaPause, FaPlay } from 'react-icons/fa';
import { api, type Story, type StoryPage, type WordTime } from '../api';
import { getMediaUrl } from '../config';
import type { Drill } from '../types';
import WordGloss, { parseGlosses } from './WordGloss';
import { ara, gap, keepAwake, nowPlaying, say, stop } from '../utils/veu';

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
  const parts = useMemo(() => seccions(stories || []), [stories]);

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

      {parts.map(({ serie, quines }) => (
        <section key={serie || '—'} style={{ marginBottom: 26 }}>
          {serie && (
            <h2 style={{ fontFamily: 'var(--font-display)', fontSize: 17, margin: '0 0 2px', lineHeight: 1.3 }}>
              {serie}
            </h2>
          )}
          {serie && (
            <p style={{ fontSize: 12.5, color: 'var(--text-soft)', margin: '0 0 10px' }}>
              {quines.length} capítols, del primer a l’últim
            </p>
          )}
          {!serie && parts.length > 1 && (
            <h2 style={{ fontFamily: 'var(--font-display)', fontSize: 17, margin: '0 0 10px' }}>
              Contes i cançons solts
            </h2>
          )}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))', gap: 14 }}>
            {quines.map((s) => (
              <button key={s.slug} onClick={() => navigate(`/stories/${s.slug}`)} style={card}>
                {s.cover && (
                  <img src={getMediaUrl(s.cover)} alt="" loading="lazy"
                       style={{ width: '100%', aspectRatio: '16 / 9', objectFit: 'cover', borderRadius: 'var(--r-md)', marginBottom: 8, background: 'var(--surface-2)' }}
                       onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = 'none'; }} />
                )}
                {/* Dins d'una sèrie la targeta no repeteix el nom set vegades: diu quin capítol és,
                    que és l'única cosa que la distingeix de les del costat. */}
                <div style={{ fontWeight: 800, fontSize: 15, lineHeight: 1.3 }}>
                  {s.chapter != null && s.series ? `Capítol ${s.chapter}` : s.title}
                </div>
                <div style={{ fontSize: 12.5, color: 'var(--text-soft)', marginTop: 3 }}>
                  {s.lines} línies{s.speaker ? ` · ${s.speaker}` : ''}
                </div>
                {/* El que es pot llegir es diu en positiu; el que encara no, una vegada i curt.
                    Abans cada targeta cridava «33 línies encara sense paraules escrites» i, com
                    que ho deien totes, deixava de voler dir res. */}
                <div style={{ fontSize: 12, fontWeight: 700, marginTop: 4,
                              color: s.written ? 'var(--brand-1)' : 'var(--text-muted)' }}>
                  {s.written
                    ? `${s.written} de ${s.lines} línies escrites en amazic`
                    : 'encara no es pot llegir, només escoltar'}
                </div>
              </button>
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}

/** Partir una frase en paraules i en el que les separa, per poder encendre'n una de sola. */
const TROSSOS = /([^\s.,;:!?¡¿«»"'()،؛؟]+)/u;

function trossos(text: string): string[] {
  return (text || '').split(TROSSOS).filter((x) => x !== '');
}

/** Cada tros amb el número de paraula que li toca; −1 per als espais i els signes. */
function numerades(text: string): { p: string; n: number }[] {
  const fora: { p: string; n: number }[] = [];
  let n = -1;
  for (const p of trossos(text)) {
    if (p.trim()) n += 1;
    fora.push({ p, n: p.trim() ? n : -1 });
  }
  return fora;
}

/**
 * La frase amaziga amb la paraula que sona encesa (#340).
 *
 * Els temps vénen de l'alineament, que es va fer sobre aquest mateix text, de manera que la
 * paraula número *i* del rellotge és la número *i* de la frase. Quan els comptes no quadren
 * —perquè l'alineament en va ajuntar dues, o perquè algú ha reescrit la frase després— no
 * s'endevina: s'encén la paraula que **diu el mateix** que la que sona, i si no n'hi ha cap, cap.
 */
function FraseEncesa({ text, mots, i, estil }: {
  text: string; mots?: WordTime[]; i: number | null; estil: React.CSSProperties;
}) {
  const parts = numerades(text);
  const quants = parts.filter((x) => x.n >= 0).length;
  const quadren = !!mots && mots.length === quants;
  const diu = i != null && mots && mots[i] ? mots[i].w.toLowerCase() : null;
  return (
    <div style={estil}>
      {parts.map(({ p, n: q }, k) => {
        const encesa = i != null && q >= 0 && (quadren ? q === i : p.toLowerCase() === diu);
        return encesa ? <mark key={k} style={llum}>{p}</mark> : <span key={k}>{p}</span>;
      })}
    </div>
  );
}

/**
 * El català amb la paraula que respon a la que sona, encesa.
 *
 * Aquí la posició no serveix de res: la paraula amaziga i la catalana no ocupen el mateix lloc de
 * la frase, i de vegades no n'hi ha ni el mateix nombre. Qui les casa és la **glossa** —el
 * paraula per paraula que ja porta cada línia, `{shi, tif, ca}`—, de manera que s'encén el que la
 * glossa diu, allà on sigui. Quan la glossa posa «—» és que el català ho diu d'una altra manera,
 * i aleshores no s'encén res: val més no encendre que encendre malament.
 */
function CatalaEncès({ text, ca, estil }: { text: string; ca: string | null; estil: React.CSSProperties }) {
  const busca = (ca || '').trim();
  const bones = busca && busca !== '—'
    ? new Set(trossos(busca).filter((x) => x.trim()).map((x) => x.toLowerCase()))
    : null;
  return (
    <div style={estil}>
      {trossos(text).map((p, k) => (
        bones && p.trim() && bones.has(p.toLowerCase())
          ? <mark key={k} style={llum}>{p}</mark>
          : <span key={k}>{p}</span>
      ))}
    </div>
  );
}

const llum: React.CSSProperties = {
  background: 'var(--brand-1)', color: '#fff', borderRadius: 4,
  padding: '0 2px', margin: '0 -2px',
};

/**
 * Les històries repartides en seccions: una per sèrie, i una per als contes sols.
 *
 * L'ordre el dona el servidor (#346) —cada sèrie seguida, els capítols del primer a l'últim, i al
 * davant el que es pot llegir—, de manera que aquí només s'agrupa el que ja ve en ordre. Abans la
 * graella anava per nombre de línies i *The Traveller* 1 a 7 quedava escampat pertot: ningú no
 * podia començar un conte pel principi.
 */
function seccions(stories: Story[]): { serie: string | null; quines: Story[] }[] {
  const fora: { serie: string | null; quines: Story[] }[] = [];
  for (const s of stories) {
    const serie = s.series || null;
    const ultima = fora[fora.length - 1];
    if (ultima && ultima.serie === serie) ultima.quines.push(s);
    else fora.push({ serie, quines: [s] });
  }
  return fora;
}

function OneStory({ slug }: { slug: string }) {
  const navigate = useNavigate();
  const [page, setPage] = useState<StoryPage | null>(null);
  const [missing, setMissing] = useState(false);
  const [at, setAt] = useState<number | null>(null);     // which line is sounding
  // Sentir-la de cap a cap es pot fer de dues maneres, i no competeixen: una és escoltar el
  // conte, l'altra és estudiar-lo. `null` = aturada.
  const [reading, setReading] = useState<null | 'sol' | 'amb-catala'>(null);
  const readingRef = useRef(false);
  // Quina paraula sona ara: la línia i la seva posició dins la línia (#340).
  const [mot, setMot] = useState<{ drill: number; i: number } | null>(null);
  // La pantalla segueix la veu, però qui llegeix mana: si mou la pàgina a mà, deixa de
  // seguir-la fins que torni a prémer play. Una pantalla que t'estira cap on ella vol és
  // pitjor que una de quieta.
  const seguint = useRef(true);
  const linies = useRef<Record<number, HTMLDivElement | null>>({});

  useEffect(() => {
    api.story(slug).then((r) => { setPage(r); document.title = `${r.title} · Tamazight`; })
      .catch(() => setMissing(true));
    return () => { readingRef.current = false; stop(); keepAwake(false); nowPlaying(null); };
  }, [slug]);

  // La pantalla s'acosta a la línia que sona. A «The Traveller», que en té 219, la veu se
  // n'anava avall i qui escoltava es quedava mirant una altra part del conte.
  useEffect(() => {
    if (at == null || !seguint.current) return;
    linies.current[at]?.scrollIntoView({ block: 'center', behavior: 'smooth' });
  }, [at]);

  // Qui llegeix mana sobre la pantalla: tocar-la atura el seguiment fins al pròxim play.
  useEffect(() => {
    const seu = () => { seguint.current = false; };
    window.addEventListener('wheel', seu, { passive: true });
    window.addEventListener('touchmove', seu, { passive: true });
    return () => { window.removeEventListener('wheel', seu); window.removeEventListener('touchmove', seu); };
  }, []);

  // Un so, i s'espera que s'acabi. El reproductor és el de tota l'app: un sol element, dins el
  // document i declarat al sistema, perquè la veu no calli quan s'apaga la pantalla (#342).
  const sona = useCallback((url: string) => say(url.trim() ? getMediaUrl(url) : ''), []);

  /**
   * La veu amaziga d'una línia, amb la paraula encesa a mesura que es diu (#340).
   *
   * Els temps no se'ls inventa ningú: els va desar l'alineament forçat i els serveix la pàgina
   * (`word_times`). El rellotge que mana és el de l'àudio —es llegeix cada fotograma—, no un
   * comptador nostre, que se n'aniria en quant el navegador estrangolés els temporitzadors o la
   * gravació triguéssim a carregar-se.
   *
   * Una línia sense alineament sona igual i s'encén **sencera**: repartir-la pel rellotge, com
   * si les paraules duressin totes el mateix, encendria la paraula equivocada, i això ensenya a
   * sentir el que no és.
   */
  const sonaEncenent = useCallback(async (drill: Drill, url: string) => {
    const mots: WordTime[] | undefined = page?.word_times?.[String(drill.id)];
    if (!mots || !mots.length) return sona(url);
    let viu = true;
    const mira = () => {
      if (!viu) return;
      const t = ara();
      const i = mots.findIndex((m) => t >= m.start && t < m.end);
      setMot(i >= 0 ? { drill: drill.id, i } : null);
      requestAnimationFrame(mira);
    };
    requestAnimationFrame(mira);
    try { return await sona(url); } finally { viu = false; setMot(null); }
  }, [sona, page]);

  const amazic = (d: Drill) => (d.audio_url || d.audio_tts_shi_url || '').trim();

  // Estudiar una línia: primer saps QUÈ sentiràs, i després ho sents dues vegades.
  //
  // L'ordre no és capritxós. Sentir amazic sense saber què vol dir és soroll; sentir-lo una sola
  // vegada no deixa temps de tornar-hi. Amb el català al davant, l'orella ja busca alguna cosa, i
  // la segona passada és on es comença a distingir on acaba una paraula i on comença l'altra.
  const playLine = useCallback(async (drill: Drill, i: number) => {
    const veu = amazic(drill);
    const ca = (drill.audio_tts_url || '').trim();
    if (!veu && !ca) return;
    setAt(i);
    if (ca) {
      await sona(ca);
      await gap(250);
    }
    if (!veu) return;
    await sonaEncenent(drill, veu);
    await gap(300);
    await sonaEncenent(drill, veu);
  }, [sona, sonaEncenent]);

  // Sentir-la de cap a cap, de dues maneres que no fan la mateixa feina:
  //
  //   `sol`         el conte seguit, només en amazic, tal com el va dir qui el va dir. És el que
  //                 vols quan ja l'has treballat, o quan només el vols sentir.
  //   `amb-catala`  cada línia en català i després l'amazic dues vegades, sense haver de prémer
  //                 res. És la mateixa seqüència del botó de cada línia, però de cap a cap: per
  //                 a qui encara no entén la història i la vol anar seguint.
  //
  // Prémer el botó que ja sona l'atura; prémer l'altre canvia de manera sense parar-se.
  const readThrough = async (manera: 'sol' | 'amb-catala') => {
    if (!page) return;
    const sonava = reading;
    readingRef.current = false;
    stop();
    if (sonava === manera) { setReading(null); setAt(null); keepAwake(false); nowPlaying(null); return; }
    await gap(60);                                 // deixa acabar la fila anterior
    seguint.current = true;                        // tornar a prémer play torna a seguir la veu
    readingRef.current = true; setReading(manera);
    keepAwake(true);
    for (let i = 0; i < page.drills.length; i++) {
      if (!readingRef.current) break;
      // Dir al sistema què sona ara: així surt a la pantalla de bloqueig amb el títol de la
      // història, i el botó de pausa de l'auricular atura de debò en comptes de no fer res.
      nowPlaying({
        title: (page.drills[i].text_tachelhit || '').trim() || page.drills[i].text_catalan || page.title,
        artist: page.speaker && page.speaker !== 'Auto Capture' ? page.speaker : (page.channel || ''),
        album: page.title,
        onPause: () => { readingRef.current = false; stop(); setReading(null); setAt(null); keepAwake(false); },
      });
      if (manera === 'amb-catala') {
        await playLine(page.drills[i], i);
      } else {
        setAt(i);
        await sonaEncenent(page.drills[i], amazic(page.drills[i]));
      }
      await gap(350);
    }
    if (readingRef.current) { readingRef.current = false; setReading(null); setAt(null); }
    keepAwake(false);
    nowPlaying(null);
  };

  if (missing) return <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-soft)' }}>Aquesta història no existeix.</div>;
  if (!page) return <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-soft)' }}>Carregant…</div>;

  return (
    <div style={{ padding: '20px 16px 60px', maxWidth: 760, margin: '0 auto' }}>
      <button onClick={() => navigate('/stories')} style={back}><FaChevronLeft /> Històries</button>
      <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 25, margin: '6px 0 4px', lineHeight: 1.25 }}>{page.title}</h1>
      <p style={{ color: 'var(--text-soft)', fontSize: 13.5, margin: '0 0 14px' }}>
        {page.lines} línies · {page.voiced} amb veu
      </p>

      {/* El crèdit no és lletra petita.
          Qui ens deixa escoltar una història seva es mereix que la gent hi vagi, i qui l'escolta
          ha de saber de qui és la veu abans de sentir-la. Per això va en un bloc que es veu, amb
          el nom del canal i la porta oberta cap al vídeo.
          «Auto Capture» no és ningú: és el procés que va retallar la frase (#324), de manera que
          no es diu mai com si fos una persona. */}
      <section style={credit}>
        <div style={{ fontWeight: 800, fontSize: 13.5, marginBottom: 4 }}>D'on surt aquesta història</div>
        <p style={{ margin: 0, fontSize: 13.5, lineHeight: 1.55 }}>
          {page.channel
            ? <>La veu i les paraules són del canal <strong>{page.channel}</strong>.</>
            : <>La veu i les paraules són del vídeo original.</>}
          {page.speaker && page.speaker !== 'Auto Capture' && <> Ho diu <strong>{page.speaker}</strong>.</>}
          {' '}La traducció al català és nostra{page.speaker === 'Auto Capture' ? ', i encara sense comprovar' : ''}.
        </p>
        {page.source_url && (
          <p style={{ margin: '8px 0 0', fontSize: 13.5 }}>
            Si t'agrada, ves-hi:{' '}
            <a href={page.source_url} target="_blank" rel="noopener noreferrer" style={enllac}>
              mira el vídeo original <FaExternalLinkAlt size={9} />
            </a>
            {page.channel && <> i visita el canal.</>}
          </p>
        )}
      </section>

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, alignItems: 'center', marginBottom: 6 }}>
        <button onClick={() => readThrough('sol')} style={primary}>
          {reading === 'sol' ? <><FaPause size={12} /> Atura</> : <><FaPlay size={12} /> Escolta-la sencera</>}
        </button>
        <button onClick={() => readThrough('amb-catala')} style={secundari}>
          {reading === 'amb-catala' ? <><FaPause size={12} /> Atura</> : <><FaPlay size={12} /> Escolta-la amb el català</>}
        </button>
      </div>
      <p style={{ color: 'var(--text-soft)', fontSize: 12.5, margin: '0 0 18px', lineHeight: 1.5 }}>
        Sencera, només en amazic · amb el català, cada línia et diu primer què vol dir i després
        la sents dues vegades.
      </p>

      {/* Dir-ho tot, i dir-ho abans que ningú estudiï res d'aquí.
          Una història capturada per la màquina no porta només el text amazic a mitges: el
          SIGNIFICAT també el va escriure ella, escoltant, i no l'ha mirat ningú. Vam mesurar-ho
          (#335): escoltant, la màquina resumeix la faula sencera i correcta; transcrivint-la,
          dinou de trenta línies no volien dir res. Ensenyar el significat sense dir d'on surt és
          fer-lo passar per una traducció feta per algú.
          I qui ho pot arreglar no som nosaltres: és qui parla la llengua i és aquí. */}
      {(page.missing_words > 0 || page.speaker === 'Auto Capture') && (
        <div style={{ padding: '12px 14px', borderRadius: 'var(--r-lg)', background: 'var(--brand-gradient-soft)', marginBottom: 16, fontSize: 13.5, lineHeight: 1.6 }}>
          {page.missing_words > 0 && (
            <>Hi ha <strong>{page.missing_words} {page.missing_words === 1 ? 'línia' : 'línies'}</strong> que encara
            no tenen les paraules escrites: se senten, però no es poden llegir.{' '}</>
          )}
          {page.speaker === 'Auto Capture' && (
            <><strong>I el significat en català el va escriure una màquina escoltant la gravació:
            encara no l'ha comprovat ningú.</strong> Pren-lo com una ajuda, no com una traducció
            segura.{' '}</>
          )}
          <br />
          <strong>Si parles amazic, aquí ens pots ajudar de debò</strong>: digues què diu una línia,
          o grava-la amb la teva veu. Amb una sola línia teva, aquesta història millora per a
          tothom qui la vingui a escoltar després.
        </div>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {page.drills.map((d, i) => {
          const written = (d.text_tachelhit || '').trim();
          const mots = page.word_times?.[String(d.id)];
          const dins = mot && mot.drill === d.id ? mot.i : null;
          // Quina paraula catalana respon a la que sona: ho diu la glossa, no la posició.
          const gl = dins != null ? parseGlosses(d)[dins] : undefined;
          return (
            <div key={d.id}
                 ref={(n) => { linies.current[i] = n; }}
                 style={{
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
                  <FraseEncesa text={written} mots={mots} i={dins}
                               estil={{ fontSize: 16.5, fontWeight: 800, lineHeight: 1.35 }} />
                ) : (
                  // La lectura de màquina es veu, però mai com si fos el text del parlant: va
                  // en gris, amb el seu avís, i no es pot confondre amb una frase escrita per
                  // ningú. Amagar-la no ajudava —la línia quedava muda a la pantalla tot i que
                  // en teníem una proposta— i donar-la per bona seria inventar-li les paraules.
                  <>
                    <div style={{ fontSize: 14, color: 'var(--saffron-dark, #7A4A12)', fontWeight: 700 }}>
                      (aquesta línia encara no té les paraules escrites)
                    </div>
                    {(d.text_tachelhit_suggested || '').trim() && (
                      <div style={{ fontSize: 15, color: 'var(--text-soft)', lineHeight: 1.35, marginTop: 2 }}>
                        <span style={{ fontSize: 11, fontWeight: 700, letterSpacing: '.04em', textTransform: 'uppercase', marginRight: 6 }}>
                          lectura de màquina
                        </span>
                        {d.text_tachelhit_suggested}
                      </div>
                    )}
                  </>
                )}
                <CatalaEncès text={d.text_catalan || ''} ca={gl?.ca ?? null}
                             estil={{ fontSize: 14, color: 'var(--text-soft)', lineHeight: 1.45 }} />
                <WordGloss drill={d} size="sm" />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

const credit: React.CSSProperties = {
  padding: '12px 14px', borderRadius: 'var(--r-lg)', border: '1px solid var(--border)',
  background: 'var(--surface-2)', margin: '0 0 16px',
};
const enllac: React.CSSProperties = { color: 'var(--brand-1)', fontWeight: 700 };
const secundari: React.CSSProperties = {
  display: 'inline-flex', alignItems: 'center', gap: 8, padding: '10px 18px',
  borderRadius: 'var(--r-pill)', border: '1.5px solid var(--brand-1)', background: 'transparent',
  color: 'var(--brand-1)', fontWeight: 800, fontSize: 14, cursor: 'pointer', fontFamily: 'inherit',
};
const card: React.CSSProperties ={ textAlign: 'left', padding: 12, borderRadius: 'var(--r-lg)', border: '1px solid var(--border)', background: 'var(--surface)', cursor: 'pointer', color: 'var(--text)', fontFamily: 'inherit' };
const primary: React.CSSProperties = { display: 'inline-flex', alignItems: 'center', gap: 8, padding: '10px 18px', borderRadius: 'var(--r-pill)', border: 'none', background: 'var(--brand-gradient)', color: '#fff', fontWeight: 800, fontSize: 14, cursor: 'pointer', fontFamily: 'inherit' };
const back: React.CSSProperties = { display: 'inline-flex', alignItems: 'center', gap: 6, padding: 0, border: 'none', background: 'none', color: 'var(--brand-1)', fontWeight: 700, fontSize: 13, cursor: 'pointer', fontFamily: 'inherit' };
