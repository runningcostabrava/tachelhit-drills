/**
 * El visor del Baba Ali: la sèrie, encastada del canal, amb el nostre text a sota.
 *
 * El vídeo no és nostre (és de la SNRT i és públic a YouTube), així que no se'n serveix cap
 * còpia: s'encasta el canal i a sota hi va el que SÍ que és nostre, les 3.621 línies llegides
 * de la pantalla amb OCR i traduïdes per màquina.
 *
 * EL TEMPS. Les nostres marques les va escriure qui va fer els talls, i no casen amb la pujada:
 * cada pujada comença amb uns dos minuts de resum, i algunes porten dos o tres episodis seguits.
 * El desplaçament de cada episodi s'ha mesurat correlacionant el so (veg. `backend/baba_ali.py`),
 * i aquí només se suma: segon del vídeo = `t + desplacament`.
 *
 * ELS QUE NO CASEN hi surten igualment, sense vídeo, amb els talls de so frase a frase: val més
 * dir «d'aquest no sabem quin vídeo és» que ensenyar-ne un que no sigui.
 *
 * El text està SENSE REVISAR: l'àrab el va llegir una màquina de la imatge i el català el va
 * traduir una altra. Per això es mostren els dos de costat — qui sap àrab veu de seguida si el
 * que falla és la lectura o la traducció — i la pàgina ho diu a dalt.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { FaPlay, FaExclamationTriangle, FaYoutube, FaVolumeUp } from 'react-icons/fa';
import { api, type BabaAliEpisodi, type BabaAliEpisodiData, type BabaAliLinia } from '../api';
import { loadYouTubeApi } from '../utils/youtubeUtils';

const rellotge = (s: number) => {
  const m = Math.floor(Math.max(0, s) / 60);
  const q = Math.floor(Math.max(0, s) % 60);
  return `${m}:${String(q).padStart(2, '0')}`;
};

const numero = (ep: string) => {
  const m = ep.match(/\d+/);
  return m ? m[0] : ep;
};

export default function BabaAliViewer() {
  const [episodis, setEpisodis] = useState<BabaAliEpisodi[] | null>(null);
  const [triat, setTriat] = useState<string | null>(null);
  const [dades, setDades] = useState<BabaAliEpisodiData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [temps, setTemps] = useState(0);           // en el nostre temps, no el del vídeo
  const [mostra, setMostra] = useState<'tots' | 'ca' | 'ar'>('tots');
  const [seguir, setSeguir] = useState(true);

  const playerRef = useRef<any>(null);
  const contenidorId = useRef(`baba-ali-${Math.random().toString(36).slice(2, 8)}`);
  const llistaRef = useRef<HTMLDivElement | null>(null);
  const activaRef = useRef<HTMLButtonElement | null>(null);
  const soRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    api.babaAliIndex()
      .then(r => {
        setEpisodis(r.episodis);
        const amb = r.episodis.find(e => e.video) || r.episodis[0];
        if (amb) setTriat(amb.episodi);
      })
      .catch(e => setError(String(e?.message || e)));
  }, []);

  useEffect(() => {
    if (!triat) return;
    setDades(null);
    setTemps(0);
    api.babaAliEpisodi(triat).then(setDades).catch(e => setError(String(e?.message || e)));
  }, [triat]);

  const desplacament = dades?.desplacament ?? 0;

  // El reproductor del canal. Es torna a fer només quan canvia el vídeo.
  useEffect(() => {
    const videoId = dades?.video;
    if (!videoId) return;
    let cancelat = false;

    loadYouTubeApi().then(YT => {
      if (cancelat || !YT?.Player) return;
      if (playerRef.current) { try { playerRef.current.destroy(); } catch { /* ja no hi era */ } }
      playerRef.current = new YT.Player(contenidorId.current, {
        videoId,
        playerVars: {
          // comença on comença l'episodi de debò, no al resum de la pujada
          start: Math.max(0, Math.round(desplacament)),
          controls: 1, rel: 0, modestbranding: 1, enablejsapi: 1, origin: window.location.origin,
        },
      });
    });

    // cinc cops per segon: prou per a un subtítol i no fa suar el telèfon
    const rellotgeId = setInterval(() => {
      const p = playerRef.current;
      if (p && typeof p.getCurrentTime === 'function') setTemps(p.getCurrentTime() - desplacament);
    }, 200);

    return () => {
      cancelat = true;
      clearInterval(rellotgeId);
      if (playerRef.current) { try { playerRef.current.destroy(); } catch { /* ja no hi era */ } }
      playerRef.current = null;
    };
  }, [dades?.video, desplacament]);

  const linies = dades?.linies || [];

  // Quina línia sona ara. Es busca per bisecció: amb 335 línies i cinc comptes per segon,
  // recórrer-les totes cada vegada es nota al mòbil.
  const ara = useMemo(() => {
    if (!linies.length) return -1;
    let a = 0, b = linies.length - 1, trobada = -1;
    while (a <= b) {
      const m = (a + b) >> 1;
      if (linies[m].t <= temps) { trobada = m; a = m + 1; } else { b = m - 1; }
    }
    if (trobada < 0) return -1;
    return temps <= linies[trobada].fi + 0.4 ? trobada : -1;
  }, [linies, temps]);

  useEffect(() => {
    if (!seguir || ara < 0) return;
    const fila = activaRef.current;
    const caixa = llistaRef.current;
    if (!fila || !caixa) return;
    const dalt = fila.offsetTop - caixa.offsetTop;
    if (dalt < caixa.scrollTop || dalt > caixa.scrollTop + caixa.clientHeight - 80) {
      caixa.scrollTo({ top: dalt - caixa.clientHeight / 2, behavior: 'smooth' });
    }
  }, [ara, seguir]);

  const vesA = useCallback((l: BabaAliLinia) => {
    const p = playerRef.current;
    if (p && typeof p.seekTo === 'function') {
      p.seekTo(Math.max(0, l.t + desplacament), true);
      if (typeof p.playVideo === 'function') p.playVideo();
      setTemps(l.t);
      return;
    }
    // sense vídeo: sona el tall que tenim d'aquella frase
    if (!l.so) return;
    if (soRef.current) { soRef.current.pause(); }
    const so = new Audio(l.so);
    soRef.current = so;
    so.play().catch(() => { /* el navegador vol que algú toqui la pantalla primer */ });
    setTemps(l.t);
  }, [desplacament]);

  if (error) {
    return <div style={{ padding: 24, color: 'var(--danger, #c0392b)' }}>
      No s'ha pogut llegir la sèrie: {error}
    </div>;
  }
  if (!episodis) return <div style={{ padding: 24 }}>Carregant els episodis…</div>;

  const tria = episodis.find(e => e.episodi === triat);
  const proves = dades?.comprovat;

  return (
    <div style={{ maxWidth: 1100, margin: '0 auto', padding: '16px' }}>
      <h1 style={{ margin: '0 0 4px', fontSize: 22, display: 'flex', alignItems: 'center', gap: 8 }}>
        <FaYoutube color="#c4302b" /> Baba Ali
      </h1>
      <p style={{ margin: '0 0 12px', color: 'var(--text-2, #666)', fontSize: 13, lineHeight: 1.5 }}>
        La sèrie és de la SNRT i es mira del seu canal. El text de sota és nostre: l'àrab el va
        llegir una màquina de la pantalla i el català el va traduir una altra, i{' '}
        <strong>no l'ha revisat ningú</strong>. Es mostren tots dos de costat perquè qui sàpiga
        àrab vegi si el que falla és la lectura o la traducció.
      </p>

      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 12 }}>
        {episodis.map(e => (
          <button
            key={e.episodi}
            onClick={() => setTriat(e.episodi)}
            title={e.video
              ? `${e.linies} línies · vídeo comprovat (${e.titol_pujada})`
              : `${e.linies} línies · no sabem quin vídeo és`}
            style={{
              padding: '6px 12px', borderRadius: 'var(--r-pill, 999px)', cursor: 'pointer',
              border: `1px solid ${e.episodi === triat ? 'transparent' : 'var(--border, #ddd)'}`,
              background: e.episodi === triat ? 'var(--brand-1, #2b6cb0)' : 'var(--surface, #fff)',
              color: e.episodi === triat ? '#fff' : 'inherit',
              fontWeight: e.episodi === triat ? 700 : 500, fontSize: 14,
              opacity: e.video ? 1 : 0.65,
            }}
          >
            {numero(e.episodi)}{!e.video && ' ·'}
          </button>
        ))}
      </div>

      {tria && !tria.video && (
        <div style={{
          display: 'flex', gap: 8, alignItems: 'flex-start', padding: '10px 12px', marginBottom: 12,
          background: 'var(--warn-bg, #fff8e1)', border: '1px solid var(--warn, #f0c36d)',
          borderRadius: 10, fontSize: 13,
        }}>
          <FaExclamationTriangle style={{ marginTop: 2, flexShrink: 0 }} />
          <span>
            {tria.per_que_sense_video
              || "D'aquest episodi no sabem quin vídeo del canal és: el so dels nostres talls no hi casa amb prou proves."}
            {' '}Les línies hi són igualment, i cada una sona amb el seu tall.
          </span>
        </div>
      )}

      {dades?.video && (
        <div style={{ position: 'relative', paddingBottom: '56.25%', height: 0, marginBottom: 10,
                      borderRadius: 12, overflow: 'hidden', background: '#000' }}>
          <div id={contenidorId.current}
               style={{ position: 'absolute', inset: 0, width: '100%', height: '100%' }} />
        </div>
      )}

      {dades?.video && ara >= 0 && (
        <div style={{
          padding: '12px 14px', marginBottom: 12, borderRadius: 12,
          background: 'var(--surface-2, #f7f7f8)', border: '1px solid var(--border, #ddd)',
        }}>
          {mostra !== 'ar' && <div style={{ fontSize: 17, fontWeight: 600 }}>{linies[ara].ca}</div>}
          {mostra !== 'ca' && (
            <div dir="rtl" lang="ar" style={{ fontSize: 19, marginTop: 6, textAlign: 'right' }}>
              {linies[ara].ar}
            </div>
          )}
        </div>
      )}

      <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap',
                    marginBottom: 8, fontSize: 13 }}>
        {(['tots', 'ca', 'ar'] as const).map(m => (
          <button key={m} onClick={() => setMostra(m)}
                  style={{ padding: '4px 10px', borderRadius: 8, cursor: 'pointer', fontSize: 13,
                           border: '1px solid var(--border, #ddd)',
                           background: mostra === m ? 'var(--brand-1, #2b6cb0)' : 'transparent',
                           color: mostra === m ? '#fff' : 'inherit' }}>
            {m === 'tots' ? 'els dos' : m === 'ca' ? 'català' : 'àrab'}
          </button>
        ))}
        <label style={{ display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer' }}>
          <input type="checkbox" checked={seguir} onChange={e => setSeguir(e.target.checked)} />
          segueix el vídeo
        </label>
        {dades && <span style={{ color: 'var(--text-2, #666)' }}>{dades.linies.length} línies</span>}
      </div>

      <div ref={llistaRef}
           style={{ maxHeight: 420, overflowY: 'auto', border: '1px solid var(--border, #ddd)',
                    borderRadius: 12,
                    // posicionat a posta: l'`offsetTop` de la fila es mesura contra aquesta
                    // caixa, que és la que es desplaça quan el vídeo avança
                    position: 'relative' }}>
        {!dades && <div style={{ padding: 16 }}>Carregant les línies…</div>}
        {linies.map((l, i) => (
          <button
            key={l.id}
            ref={i === ara ? activaRef : undefined}
            onClick={() => vesA(l)}
            style={{
              display: 'grid', gridTemplateColumns: 'auto minmax(0, 1fr)', gap: 10,
              width: '100%', textAlign: 'left', padding: '8px 12px', cursor: 'pointer',
              border: 'none', borderBottom: '1px solid var(--border, #eee)',
              background: i === ara ? 'var(--brand-1-soft, #e8f0fb)' : 'transparent',
              font: 'inherit',
            }}
          >
            <span style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'var(--text-2, #666)',
                           fontVariantNumeric: 'tabular-nums', fontSize: 12 }}>
              {dades?.video ? <FaPlay size={9} /> : l.so ? <FaVolumeUp size={11} /> : null}
              {rellotge(l.t)}
            </span>
            <span style={{ minWidth: 0 }}>
              {mostra !== 'ar' && <span style={{ display: 'block' }}>{l.ca}</span>}
              {mostra !== 'ca' && (
                <span dir="rtl" lang="ar" style={{ display: 'block', textAlign: 'right',
                                                   color: 'var(--text-2, #555)' }}>{l.ar}</span>
              )}
            </span>
          </button>
        ))}
      </div>

      {dades && (
        <p style={{ marginTop: 10, fontSize: 12, color: 'var(--text-2, #666)', lineHeight: 1.6 }}>
          {proves
            ? <>El vídeo és aquesta pujada («{dades.titol_pujada}») i l'episodi hi comença a{' '}
              {rellotge(desplacament)}: {proves.talls_dacord} talls de {proves.talls} hi sonen al
              mateix segon{proves.dispersio !== null && <> (±{proves.dispersio.toFixed(2)} s)</>},
              i que caiguin junts per atzar dins de {proves.minuts_de_la_pujada} minuts passa{' '}
              {proves.falsos_esperats.toExponential(0)} vegades.</>
            : <>Sense vídeo comprovat.</>}
          {dades.esmenades > 0 && <> · {dades.esmenades} línies es mostren esmenades (el nom del
            mercader i les fórmules que la màquina feia marianes); a la biblioteca el text queda
            tal com el va deixar la màquina.</>}
          {dades.duplicades_tretes > 0 && <> · {dades.duplicades_tretes} línies duplicades tretes.</>}
        </p>
      )}
    </div>
  );
}
