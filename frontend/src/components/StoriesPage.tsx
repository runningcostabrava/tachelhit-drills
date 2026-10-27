import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { FaChevronLeft, FaCrosshairs, FaExternalLinkAlt, FaPause, FaPlay, FaRedo, FaStepBackward, FaStepForward, FaStop } from 'react-icons/fa';
import { api, type Story, type StoryPage, type WordTime } from '../api';
import { getMediaUrl, thumb } from '../config';
import type { Drill } from '../types';
import WordGloss, { parseGlosses, type Gloss } from './WordGloss';
import Frase from './Frase';
import { llum } from '../utils/llum';
import { ara, continua, esPausat, gap, keepAwake, nowPlaying, pausa, ritme, say, stop } from '../utils/veu';

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

/**
 * L'oració desmuntada: què hi passa i quines unitats del curs l'expliquen (#341).
 *
 * El propietari ho va demanar per a les històries: «un anàlisi gramàtic semblant al que fem en
 * gramàtica, per cada oració». La diferència amb la nota del curs no és d'estil sinó d'ancoratge:
 * allà la nota penja d'una parella (frase, unitat), i una línia d'un conte no pertany a cap
 * unitat. Aquí la pregunta va del revés —què passa aquí, i què ho explica— i les unitats que en
 * surten són portes cap al curs: sents un conte, et quedes encallat en una frase, i la frase et
 * porta a la unitat que l'explica.
 *
 * Va tancada. Qui ve a escoltar una història no ve a una classe de gramàtica; qui s'hi encalla,
 * sí. I diu que l'ha escrita una màquina, com les notes del curs i pel mateix motiu.
 */
function Desmuntada({ que }: { que?: { analisi: string; unitats: string[]; titols: string[] } }) {
  const [obert, setObert] = useState(false);
  if (!que?.analisi) return null;
  return (
    <div style={{ marginTop: 6 }}>
      <button onClick={() => setObert((o) => !o)}
              style={{ border: 'none', background: 'none', padding: 0, cursor: 'pointer',
                       color: 'var(--brand-1)', fontWeight: 700, fontSize: 12.5, fontFamily: 'inherit' }}>
        {obert ? '− com està feta' : '+ com està feta'}
      </button>
      {obert && (
        <div style={{ marginTop: 4, fontSize: 13, lineHeight: 1.55, color: 'var(--text)' }}>
          {que.analisi}
          {que.titols.length > 0 && (
            <div style={{ marginTop: 5, display: 'flex', flexWrap: 'wrap', gap: 6 }}>
              {que.unitats.map((u, i) => (
                <a key={u} href={`/grammar/${u}`} style={{ fontSize: 12, fontWeight: 700, color: 'var(--brand-1)',
                     border: '1px solid var(--border)', borderRadius: 'var(--r-pill)', padding: '2px 9px', textDecoration: 'none' }}>
                  {que.titols[i] || u}
                </a>
              ))}
            </div>
          )}
          <div style={{ marginTop: 5, fontSize: 11.5, color: 'var(--text-muted)' }}>
            Això ho ha escrit una màquina. Si saps que hi ha res que no és, digues-ho.
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * El català amb el tros que respon a la paraula que sona, encès.
 *
 * Aquí la posició no serveix de res: la paraula amaziga i la catalana no ocupen el mateix lloc de
 * la frase, i de vegades no n'hi ha ni el mateix nombre. Qui les casa és la **glossa**.
 *
 * La glossa, però, té dos camps perquè fa dues feines (#356). `ca_tram` és el tros **exacte** de
 * la frase, copiat lletra per lletra, i per això s'encén tal qual: és text d'aquesta frase.
 * `ca` és què vol dir la paraula, i ho diu amb la forma de diccionari —«confien» allà on la
 * frase diu «confiança»—, de manera que només encén quan les dues formes coincideixen: era el
 * 41% de les paraules glossades. Es fa servir igualment per a les milers de línies que encara no
 * tenen tros, perquè encendre'n el 41% és millor que no encendre'n res.
 *
 * El que no es fa mai és afluixar la comparació. «Confien» comparteix prefix amb «confirmar» i
 * amb «confitura», i «interjecció» no s'ha d'encendre enlloc: una paraula encesa que no toca
 * ensenya una correspondència falsa, i qui aprèn es creu el que la pantalla li encén.
 */
function CatalaEncès({ text, gl, estil }: { text: string; gl: Gloss | null | undefined; estil: React.CSSProperties }) {
  const tros = (gl?.ca_tram || '').trim();
  if (tros) {
    const i = text.indexOf(tros);
    if (i >= 0) {
      return (
        <div style={estil}>
          <span>{text.slice(0, i)}</span>
          <mark style={llum}>{text.slice(i, i + tros.length)}</mark>
          <span>{text.slice(i + tros.length)}</span>
        </div>
      );
    }
  }
  const busca = (gl?.ca || '').trim();
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
  // seguir-la. Una pantalla que t'estira cap on ella vol és pitjor que una de quieta.
  //
  // El que faltava és el camí de tornada: un cop desactivat, l'única manera de tornar-lo a
  // engegar era aturar la història i tornar-la a començar des de dalt. Ara hi ha un botó, i
  // qualsevol play el torna a engegar. Per això va a l'estat i no només a una referència: el
  // botó ha de poder dir en quin dels dos estats és.
  const seguint = useRef(true);
  const [segueix, setSegueix] = useState(true);
  const posaSeguiment = (v: boolean) => { seguint.current = v; setSegueix(v); };
  const linies = useRef<Record<number, HTMLDivElement | null>>({});
  // Per on va la lectura, i on ha de saltar quan s'acabi la línia d'ara. «Repeteix», «l'anterior»
  // i «la següent» no poden moure un índex de dins d'un `for`: deixen dit on anar i tallen el so,
  // i la fila ho recull en comptes de passar a la línia de sota.
  const idx = useRef(0);
  const salt = useRef<number | null>(null);
  /**
   * Quin torn de veu mana ara.
   *
   * Una línia no és un so: amb el català al davant en són tres, encadenats amb `await`. Tallar
   * el so que sona només acaba l'espera —les passades que queden de la línia vella arrencaven
   * igualment, i se sentia la frase d'abans per sobre de la nova, o la història continuava
   * parlant després de prémer «atura». Cada vegada que algú mana (play, saltar, repetir, aturar)
   * això puja, i el que estava a mig dir se'n va.
   */
  const torn = useRef(0);
  const [pausat, setPausat] = useState(false);
  const [vel, setVel] = useState(1);

  useEffect(() => {
    api.story(slug).then((r) => { setPage(r); document.title = `${r.title} · Tamazight`; })
      .catch(() => setMissing(true));
    return () => { readingRef.current = false; stop(); keepAwake(false); nowPlaying(null); };
  }, [slug]);

  // La pantalla s'acosta a la línia que sona. A «The Traveller», que en té 219, la veu se
  // n'anava avall i qui escoltava es quedava mirant una altra part del conte.
  useEffect(() => {
    if (at == null || !segueix) return;
    linies.current[at]?.scrollIntoView({ block: 'center', behavior: 'smooth' });
  }, [at, segueix]);

  // Qui llegeix mana sobre la pantalla: tocar-la atura el seguiment fins que el torni a demanar.
  useEffect(() => {
    const seu = () => { if (seguint.current) posaSeguiment(false); };
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
    idx.current = i;
    // Si entremig algú ha manat una altra cosa, les passades que queden d'aquesta línia ja no
    // s'han de sentir: continuar-les faria sonar la frase vella per sobre de la nova, o deixaria
    // la història parlant després d'aturar-la.
    const meu = ++torn.current;
    if (ca) {
      await sona(ca);
      if (torn.current !== meu) return;
      await gap(250);
    }
    if (!veu || torn.current !== meu) return;
    await sonaEncenent(drill, veu);
    if (torn.current !== meu) return;
    await gap(300);
    if (torn.current !== meu) return;
    await sonaEncenent(drill, veu);
  }, [sona, sonaEncenent]);

  /** Una línia sola: la veu amaziga i prou.
   *
   *  El botó de cada línia feia la seqüència d'estudi sencera —el català primer i després
   *  l'amazic dues vegades—, que té sentit per a qui escolta el conte de cap a cap i encara no
   *  l'entén, i per això existeix «Escolta-la amb el català». Però no és el que un botó al
   *  costat d'una frase amaziga sembla que farà: qui el prem ja té la frase i la traducció a la
   *  pantalla, i el que vol sentir és com sona.
   */
  const nomesAmazic = useCallback(async (drill: Drill, i: number) => {
    const veu = amazic(drill);
    if (!veu) return;
    setAt(i);
    idx.current = i;
    torn.current++;
    await sonaEncenent(drill, veu);
  }, [sonaEncenent]);

  /**
   * Anar a una línia: la mateixa (repetir-la), la d'abans o la de sota.
   *
   * Amb la història engegada no es torna a arrencar la fila —això la faria començar de zero—:
   * se li deixa dit on anar i se li talla el so d'ara, que és el que la desperta, i aquella
   * lectura continua com estava (si l'havies demanada amb el català, segueix amb el català).
   * Amb la història aturada, la línia sona sola i només en amazic.
   */
  const vesA = (j: number) => {
    if (!page) return;
    const n = Math.max(0, Math.min(page.drills.length - 1, j));
    posaSeguiment(true);
    setPausat(false);
    if (readingRef.current) {
      salt.current = n;
      torn.current++;               // el que s'estigui dient a mitges, es queda aquí
      stop();                       // deixa passar qui esperava el final, i treu la pausa
    } else {
      nomesAmazic(page.drills[n], n);
    }
  };

  /** Callar sense perdre el lloc: la fila es queda esperant on era. */
  const pausaOSegueix = () => {
    if (esPausat()) { continua(); setPausat(false); }
    else { pausa(); setPausat(true); }
  };

  const atura = () => {
    readingRef.current = false;
    salt.current = null;
    torn.current++;                 // i la línia que s'estava dient no acaba les seves passades
    stop();
    setReading(null); setAt(null); setPausat(false);
    keepAwake(false); nowPlaying(null);
  };

  const posaRitme = (v: number) => { ritme(v); setVel(v); };

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
    torn.current++;                                // calla el que s'estigui dient a mitges
    stop();
    if (sonava === manera) { setReading(null); setAt(null); setPausat(false); keepAwake(false); nowPlaying(null); return; }
    await gap(60);                                 // deixa acabar la fila anterior
    posaSeguiment(true);                           // tornar a prémer play torna a seguir la veu
    setPausat(false);
    readingRef.current = true; setReading(manera);
    keepAwake(true);
    // Comença per on s'havia quedat si algú ha demanat una línia abans d'engegar.
    let i = salt.current ?? 0;
    salt.current = null;
    while (readingRef.current && i >= 0 && i < page.drills.length) {
      idx.current = i;
      // Dir al sistema què sona ara: així surt a la pantalla de bloqueig amb el títol de la
      // història, i el botó de pausa de l'auricular atura de debò en comptes de no fer res.
      nowPlaying({
        title: (page.drills[i].text_tachelhit || '').trim() || page.drills[i].text_catalan || page.title,
        artist: page.speaker && page.speaker !== 'Auto Capture' ? page.speaker : (page.channel || ''),
        album: page.title,
        // Els botons de l'auricular fan el mateix que els de la pantalla: callar sense perdre el
        // lloc, tornar-hi, i passar de línia.
        onPlay: () => { continua(); setPausat(false); },
        onPause: () => { pausa(); setPausat(true); },
        onNext: () => vesA(idx.current + 1),
        onPrev: () => vesA(idx.current - 1),
      });
      if (manera === 'amb-catala') {
        await playLine(page.drills[i], i);
      } else {
        // Només en amazic, una línia és UN so: no hi ha cap passada posterior que es pugui
        // quedar sonant, i per això aquí no cal mirar el torn. Les dues línies de sota recullen
        // el que s'hagi manat mentre sonava.
        setAt(i);
        await sonaEncenent(page.drills[i], amazic(page.drills[i]));
      }
      if (salt.current != null) { i = salt.current; salt.current = null; continue; }
      await gap(350);
      if (salt.current != null) { i = salt.current; salt.current = null; continue; }
      i++;
    }
    if (readingRef.current) { readingRef.current = false; setReading(null); setAt(null); setPausat(false); }
    keepAwake(false);
    nowPlaying(null);
  };

  if (missing) return <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-soft)' }}>Aquesta història no existeix.</div>;
  if (!page) return <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-soft)' }}>Carregant…</div>;

  const sonant = reading != null || at != null;

  return (
    <div style={{ padding: sonant ? '20px 16px 120px' : '20px 16px 60px', maxWidth: 760, margin: '0 auto' }}>
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
              display: 'flex', flexDirection: 'column', gap: 10, padding: '10px 12px',
              borderRadius: 'var(--r-lg)', border: '1px solid var(--border)',
              background: at === i ? 'var(--brand-gradient-soft)' : 'var(--surface)',
            }}>
              {/* El dibuix de la línia.
                  Un conte es llegeix mirant: la imatge va a dalt i el text a sota, com en un
                  llibre. Les trenta-set d'una història són el mateix conte —el mateix llop, el
                  mateix riu, el mateix xai (#390)— i es demanen a la mida que es veuen, que no
                  és la que pesen. */}
              {(d.image_url || '').trim() && (
                <img src={thumb(getMediaUrl(d.image_url), 760)} alt=""
                     loading="lazy" decoding="async"
                     onError={(e) => { e.currentTarget.style.display = 'none'; }}
                     // Sencer, i no retallat. Amb un topall d'alçada i `cover` es perdia mitja
                     // escena: justament el llop que mira, o el xai que s'aparta. Un dibuix que
                     // ha d'explicar què passa no es pot ensenyar a trossos.
                     style={{ width: '100%', height: 'auto', aspectRatio: '4 / 3', objectFit: 'cover', borderRadius: 'var(--r-md)', display: 'block' }} />
              )}
              <div style={{ display: 'flex', gap: 10 }}>
              {/* Amb la història engegada, el ▶ d'una línia hi porta la lectura en comptes de
                  sonar-hi a sobre; i torni d'on torni, la pantalla torna a seguir la veu. */}
              <button onClick={() => vesA(i)} aria-label={`Escolta la línia ${i + 1}`}
                      style={{ flexShrink: 0, width: 34, height: 34, borderRadius: '50%', border: 'none', background: 'var(--surface-2)', color: 'var(--brand-1)', cursor: 'pointer', display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}>
                <FaPlay size={11} />
              </button>
              <div style={{ flex: 1, minWidth: 0 }}>
                {written ? (
                  <Frase text={written} latin={d.text_tachelhit_latin} mots={mots} encesa={dins} size="md" />
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
                      <div style={{ color: 'var(--text-soft)', marginTop: 2, opacity: 0.85 }}>
                        <span style={{ fontSize: 11, fontWeight: 700, letterSpacing: '.04em', textTransform: 'uppercase' }}>
                          lectura de màquina
                        </span>
                        <Frase text={d.text_tachelhit_suggested || ''} size="sm" />
                      </div>
                    )}
                  </>
                )}
                <CatalaEncès text={d.text_catalan || ''} gl={gl}
                             estil={{ fontSize: 14, color: 'var(--text-soft)', lineHeight: 1.45 }} />
                <WordGloss drill={d} size="sm" />
                <Desmuntada que={page.analisi?.[String(d.id)]} />
              </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Els comandaments, mentre soni alguna cosa.
          Una història en una llengua que no saps no s'escolta de cap a cap i prou: t'atures,
          tornes enrere, sents la mateixa frase quatre vegades i la poses lenta per saber on
          s'acaba una paraula. Fins ara l'única cosa que es podia fer era deixar-la sonar o
          parar-la del tot. */}
      {sonant && (
        <div style={barra}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <button onClick={() => vesA(idx.current - 1)} style={rodo} aria-label="La línia d'abans"><FaStepBackward size={12} /></button>
            <button onClick={pausaOSegueix} style={{ ...rodo, width: 42, height: 42, background: 'var(--brand-gradient)', color: '#fff', border: 'none' }}
                    aria-label={pausat ? 'Continua' : 'Para un moment'}>
              {pausat ? <FaPlay size={14} /> : <FaPause size={14} />}
            </button>
            <button onClick={() => vesA(idx.current)} style={rodo} aria-label="Torna a dir aquesta línia"><FaRedo size={12} /></button>
            <button onClick={() => vesA(idx.current + 1)} style={rodo} aria-label="La línia de sota"><FaStepForward size={12} /></button>
          </div>

          <div style={{ fontSize: 12.5, color: 'var(--text-soft)', minWidth: 74 }}>
            {at != null ? <>línia {at + 1} de {page.drills.length}</> : null}
          </div>

          {/* A mitja velocitat se senten les paraules per separat. La paraula encesa continua
              essent la bona: el rellotge que la mana és el del so, no el de la paret. */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            {[0.6, 0.8, 1].map((v) => (
              <button key={v} onClick={() => posaRitme(v)}
                      style={{ ...xip, ...(vel === v ? xipTriat : null) }}>
                {v === 1 ? 'normal' : `${v}×`}
              </button>
            ))}
          </div>

          <button onClick={() => posaSeguiment(!segueix)}
                  style={{ ...xip, ...(segueix ? xipTriat : null), display: 'inline-flex', alignItems: 'center', gap: 5 }}
                  title={segueix ? 'La pantalla va amb la veu' : 'La pantalla es queda on la deixis'}>
            <FaCrosshairs size={11} /> {segueix ? 'segueix la veu' : 'quieta'}
          </button>

          <button onClick={atura} style={{ ...xip, marginLeft: 'auto' }}><FaStop size={10} /> atura</button>
        </div>
      )}
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
/** Els comandaments es queden a baix de tot: amb 219 línies, el play de dalt no es torna a veure.
 *
 *  Baix de tot és d'ells. L'avís d'«això és del que tenies desat» se'ls hi posava a sobre i qui
 *  escoltava es quedava sense poder aturar ni repetir; ara aquell avís és una fitxa petita a
 *  dalt a la dreta i aquí no hi ha res més amb qui barallar-se (#393, #400). */
const barra: React.CSSProperties = {
  // A sobre del menú del mòbil, que ara és a baix de tot (#372).
  position: 'fixed', left: 0, right: 0, bottom: 'var(--menu-mobil-h, 0px)', zIndex: 900,
  display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap',
  padding: '10px 14px calc(10px + env(safe-area-inset-bottom, 0px))',
  background: 'var(--surface)', borderTop: '1px solid var(--border)',
  boxShadow: '0 -2px 10px rgba(15,23,42,0.06)',
};
const rodo: React.CSSProperties = {
  width: 36, height: 36, borderRadius: '50%', border: '1px solid var(--border)',
  background: 'var(--surface-2)', color: 'var(--brand-1)', cursor: 'pointer',
  display: 'inline-flex', alignItems: 'center', justifyContent: 'center', padding: 0,
};
const xip: React.CSSProperties = {
  display: 'inline-flex', alignItems: 'center', gap: 5, padding: '7px 11px',
  borderRadius: 'var(--r-pill)', border: '1px solid var(--border)', background: 'var(--surface)',
  color: 'var(--text-soft)', fontWeight: 700, fontSize: 12, cursor: 'pointer', fontFamily: 'inherit',
};
const xipTriat: React.CSSProperties = {
  borderColor: 'var(--brand-1)', background: 'var(--brand-gradient-soft)', color: 'var(--brand-1)',
};
