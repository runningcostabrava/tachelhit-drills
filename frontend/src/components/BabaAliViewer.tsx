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
 * o, a les dues pujades que YouTube serveix mudes, mirant quan canvia el subtítol de la imatge;
 * aquí només se suma: segon del vídeo = `t + desplacament`.
 *
 * ELS QUE NO CASEN hi surten igualment, sense vídeo, amb els talls de so frase a frase: val més
 * dir «d'aquest no sabem quin vídeo és» que ensenyar-ne un que no sigui.
 *
 * El text està SENSE REVISAR: l'àrab el va llegir una màquina de la imatge i el català el va
 * traduir una altra. Per això es mostren els dos de costat — qui sap àrab veu de seguida si el
 * que falla és la lectura o la traducció — i la pàgina ho diu a dalt.
 *
 * I HI HA UNA TERCERA LÍNIA (#535): l'amazic que un model d'ASR sent al tall de veu. Va en
 * cursiva, dita com el que és, perquè no és text de cap parlant: el model enganxa els mots i
 * s'inventa lletres. Van marcades les poques on dues lectures coincideixen LLETRA PER LLETRA
 * (50 de 2.727). Assemblar-se no es marca: els dos models són de la mateixa família i
 * s'assemblen gairebé sempre, així que no voldria dir res (veg. `backend/baba_ali.py`).
 *
 * DUES MANERES DE MIRAR-S'HO. En Pablo (13-11-2026): «el que volem és un sistema per estudiar,
 * però també per simplement mirar l'episodi amb subtítols». Fins avui només hi havia la
 * primera, i mirar un capítol volia dir seguir una llista de 300 files.
 *
 * - **Mirar**: el vídeo i una banda de subtítol a sota. Res més.
 * - **Estudiar**: el que hi havia — les tres línies, la llista sencera, els talls de veu
 *   frase a frase i les proves de com s'ha casat amb la pujada.
 *
 * En mirar, el subtítol és el CATALÀ i prou, i això és una decisió, no un descuit: la pantalla
 * ja porta l'àrab cremat a la imatge. Posar-l'hi altra vegada a sota seria repetir el que ja es
 * veu i tapar mig telèfon. Qui el vulgui a més a més, el té a un clic.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { FaPlay, FaExclamationTriangle, FaYoutube, FaVolumeUp } from 'react-icons/fa';
import { api, type BabaAliEpisodi, type BabaAliEpisodiData, type BabaAliLinia } from '../api';
import { loadYouTubeApi } from '../utils/youtubeUtils';
import { liniaAra } from '../services/liniaAra';

const rellotge = (s: number) => {
  const m = Math.floor(Math.max(0, s) / 60);
  const q = Math.floor(Math.max(0, s) % 60);
  return `${m}:${String(q).padStart(2, '0')}`;
};

const numero = (ep: string) => {
  const m = ep.match(/\d+/);
  return m ? m[0] : ep;
};


/**
 * La veu diu el mateix que el subtítol.
 *
 * Dues vies independents: el subtítol és àrab llegit de la imatge, i la lectura és taixelhit
 * treta del so. Es casen pel significat àrab que el diccionari de l'IRCAM dona a les paraules
 * amazigues, sense cap traductor pel mig. Mesurat sobre les 3.621 línies: 206 coincideixen,
 * contra 13 quan es comparen amb el subtítol d'una altra frase a l'atzar — 15,8 vegades més que
 * per casualitat. El control és la meitat de la mesura: sense ell, 206 no voldria dir res.
 */
const ApuntDiuIgual = ({ mot }: { mot: string }) => (
  <span title={`El diccionari diu que una paraula de la veu vol dir «${mot}», i «${mot}» surt al subtítol`}
        style={{ marginLeft: 6, padding: '0 5px', borderRadius: 6, fontSize: 10,
                 fontStyle: 'normal', verticalAlign: 'middle', whiteSpace: 'nowrap',
                 background: 'var(--info-bg, #e7f0fb)', color: 'var(--info, #1f5fa8)' }}>
    la veu ho diu també
  </span>
);

/**
 * Dues lectures de màquina coincideixen lletra per lletra.
 *
 * Passa a 50 línies de les 2.727 llegides dues vegades. No fa certa la lectura —els dos models
 * són parents i s'assemblen gairebé sempre—, però coincidir del tot els costa, i per això val
 * la pena mirar-se just aquestes.
 */
const ApuntAcord = () => (
  <span title="dues lectures coincideixen lletra per lletra; no vol dir que encertin"
        style={{ marginLeft: 6, padding: '0 5px', borderRadius: 6, fontSize: 10,
                 fontStyle: 'normal', verticalAlign: 'middle', whiteSpace: 'nowrap',
                 background: 'var(--ok-bg, #e6f4ea)', color: 'var(--ok, #1e7b34)' }}>
    dues lectures iguals
  </span>
);

export default function BabaAliViewer() {
  const [episodis, setEpisodis] = useState<BabaAliEpisodi[] | null>(null);
  const [triat, setTriat] = useState<string | null>(null);
  const [dades, setDades] = useState<BabaAliEpisodiData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [temps, setTemps] = useState(0);           // en el nostre temps, no el del vídeo
  const [mostra, setMostra] = useState<'tots' | 'ca' | 'ar' | 'am'>('tots');
  const [seguir, setSeguir] = useState(true);
  // Mirar o estudiar. Es recorda, perquè qui ve a mirar la sèrie hi torna a mirar-la i qui hi
  // estudia hi torna a estudiar; i es llegeix dins d'un try perquè en una finestra privada
  // llegir això llança, i una preferència no ha de tombar la pàgina.
  const [manera, setManera] = useState<'mirar' | 'estudiar'>(() => {
    try {
      return localStorage.getItem('baba-ali-manera') === 'estudiar' ? 'estudiar' : 'mirar';
    } catch { return 'mirar'; }
  });
  //: En mirar, l'àrab no hi surt: la pantalla ja el porta cremat. Qui el vulgui, aquí.
  const [arabTambe, setArabTambe] = useState(false);
  /**
   * Quants segons s'avancen els subtítols respecte del que diu el rellotge del vídeo.
   *
   * El desplaçament de cada episodi està mesurat, però no tots igual de bé: l'episodi 2 es va
   * casar amb 5 talls d'acord de 19 i el 13 amb 4, mentre que la resta en fan de 10 a 16.
   * Estudiant no es nota —es clica una línia i el vídeo hi salta—, però mirant-ho sí: la
   * pantalla ja ensenya la frase següent i la banda encara va a la d'abans.
   *
   * Això no esmena la mesura, que és feina d'una altra banda; deixa que qui mira ho quadri amb
   * els seus ulls, com qualsevol reproductor de subtítols. Es recorda PER EPISODI, perquè el
   * desfasament és de cada pujada i no del visor.
   */
  const [ajust, setAjust] = useState(0);

  useEffect(() => {
    try { localStorage.setItem('baba-ali-manera', manera); } catch { /* finestra privada */ }
  }, [manera]);

  // L'ajust és de cada episodi: en canviar-lo, es recupera el que s'hi havia quadrat.
  useEffect(() => {
    if (!triat) return;
    try {
      const desat = Number(localStorage.getItem(`baba-ali-ajust-${triat}`));
      setAjust(Number.isFinite(desat) ? desat : 0);
    } catch { setAjust(0); }
  }, [triat]);

  const quadra = useCallback((segons: number) => {
    setAjust(ara => {
      const nou = Math.round(Math.max(-30, Math.min(30, ara + segons)) * 2) / 2;
      try {
        if (triat) localStorage.setItem(`baba-ali-ajust-${triat}`, String(nou));
      } catch { /* finestra privada */ }
      return nou;
    });
  }, [triat]);

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
    //: -1 i no 0: «encara no sona res». Amb 0, l'episodi que s'obre sense vídeo ensenyava una
    //: línia marcada com si sonés —l'última lectura del rellotge de l'episodi anterior.
    setTemps(-1);
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
  //: Quina línia es veu. La regla viu a `services/liniaAra` perquè es pugui provar: la va
  //: canviar una mesura i no un criteri, i val més que la pròxima vegada caigui una prova.
  //: `ajust` és el que qui mira hagi quadrat a mà (0 mentre no hi toqui ningú).
  const ara = useMemo(() => liniaAra(linies, temps + ajust), [linies, temps, ajust]);

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
  //: quines de les tres línies es veuen. «tot» les ensenya totes; «el que se sent» deixa sola
  //: la lectura de la màquina, que és com es repassa de pressa si val res.
  const veuCa = mostra === 'tots' || mostra === 'ca';
  const veuAr = mostra === 'tots' || mostra === 'ar';
  const veuAm = mostra === 'tots' || mostra === 'am';
  //: Passada l'última frase. Les pujades porten dos o tres episodis seguits, de manera que el
  //: vídeo continua encara que el capítol s'hagi acabat: val més dir-ho que deixar la banda
  //: buida i que sembli que els subtítols han fallat.
  const acabat = linies.length > 0 && temps + ajust > linies[linies.length - 1].fi + 2;

  return (
    <div style={{ maxWidth: 1100, margin: '0 auto', width: '100%', boxSizing: 'border-box', padding: '16px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                    gap: 12, flexWrap: 'wrap', margin: '0 0 4px' }}>
        <h1 style={{ margin: 0, fontSize: 22, display: 'flex', alignItems: 'center', gap: 8 }}>
          <FaYoutube color="#c4302b" /> Baba Ali
        </h1>
        <div role="tablist" aria-label="Com vols mirar-t'ho"
             style={{ display: 'flex', borderRadius: 'var(--r-pill, 999px)', overflow: 'hidden',
                      border: '1px solid var(--border, #ddd)' }}>
          {([['mirar', 'Mirar'], ['estudiar', 'Estudiar']] as const).map(([k, diu]) => (
            <button key={k} role="tab" aria-selected={manera === k} onClick={() => setManera(k)}
                    style={{ padding: '7px 18px', cursor: 'pointer', border: 'none', fontSize: 14,
                             fontWeight: manera === k ? 700 : 500,
                             background: manera === k ? 'var(--brand-1, #2b6cb0)' : 'transparent',
                             color: manera === k ? '#fff' : 'inherit' }}>
              {diu}
            </button>
          ))}
        </div>
      </div>
      <p style={{ margin: '0 0 12px', color: 'var(--text-2, #666)', fontSize: 13, lineHeight: 1.5 }}>
        {manera === 'mirar' ? (
          <>La sèrie és de la SNRT i es mira del seu canal. Els subtítols en català són nostres i{' '}
            <strong>no els ha revisat ningú</strong>: els va traduir una màquina de l'àrab, que
            una altra havia llegit de la pantalla.</>
        ) : (
          <>La sèrie és de la SNRT i es mira del seu canal. El text de sota és nostre: l'àrab el va
            llegir una màquina de la pantalla i el català el va traduir una altra, i{' '}
            <strong>no l'ha revisat ningú</strong>. Es mostren tots dos de costat perquè qui sàpiga
            àrab vegi si el que falla és la lectura o la traducció.</>
        )}
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

      {manera === 'mirar' && dades?.video && (
        <>
          {/* La banda del subtítol. Té alçada mínima a posta: si creixés i minvés amb cada
              frase, el vídeo saltaria amunt i avall tota l'estona. */}
          <div aria-live="polite" style={{
            minHeight: 86, display: 'flex', flexDirection: 'column', justifyContent: 'center',
            gap: 6, padding: '14px 18px', marginBottom: 10, borderRadius: 12, textAlign: 'center',
            background: 'var(--surface-2, #f7f7f8)', border: '1px solid var(--border, #ddd)',
          }}>
            {ara >= 0 ? (
              <>
                <div style={{ fontSize: 'clamp(17px, 2.4vw, 23px)', fontWeight: 600,
                              lineHeight: 1.35 }}>
                  {linies[ara].ca}
                </div>
                {arabTambe && (
                  <div dir="rtl" lang="ar" style={{ fontSize: 17, color: 'var(--text-2, #666)' }}>
                    {linies[ara].ar}
                  </div>
                )}
              </>
            ) : (
              <div style={{ fontSize: 13, color: 'var(--text-3, #999)' }}>
                {acabat ? "Aquí s'acaba l'episodi." : 'Aquí no hi ha cap frase escrita.'}
              </div>
            )}
          </div>

          <div style={{ display: 'flex', gap: 14, alignItems: 'center', flexWrap: 'wrap',
                        marginBottom: 12, fontSize: 13, color: 'var(--text-2, #666)' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer' }}>
              <input type="checkbox" checked={arabTambe}
                     onChange={e => setArabTambe(e.target.checked)} />
              també l'àrab
            </label>
            <span style={{ flex: '1 1 auto' }}>
              La pantalla ja el porta cremat; això el posa també a sota, en el nostre text.
            </span>
            <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span>el subtítol:</span>
              {([[-0.5, '−0,5 s'], [0.5, '+0,5 s']] as const).map(([q, diu]) => (
                <button key={q} onClick={() => quadra(q)}
                        title="Si la banda no va al compàs del que diu la pantalla, quadra-la"
                        style={{ padding: '2px 8px', borderRadius: 7, cursor: 'pointer',
                                 border: '1px solid var(--border, #ddd)', background: 'transparent',
                                 font: 'inherit' }}>
                  {diu}
                </button>
              ))}
              {ajust !== 0 && (
                <button onClick={() => quadra(-ajust)}
                        style={{ padding: '2px 8px', borderRadius: 7, cursor: 'pointer',
                                 border: '1px solid var(--border, #ddd)',
                                 background: 'var(--brand-1-soft, #e8f0fb)', font: 'inherit' }}>
                  {ajust > 0 ? '+' : '−'}{Math.abs(ajust).toFixed(1).replace('.', ',')} s · desfés
                </button>
              )}
            </span>
          </div>
        </>
      )}

      {manera === 'mirar' && tria && !tria.video && (
        <p style={{ fontSize: 13, color: 'var(--text-2, #666)', marginBottom: 12 }}>
          D'aquest episodi no en tenim el vídeo, així que no es pot mirar. Les{' '}
          {tria.linies} línies hi són i cada una sona amb el seu tall:{' '}
          <button onClick={() => setManera('estudiar')}
                  style={{ padding: 0, border: 'none', background: 'none', cursor: 'pointer',
                           color: 'var(--brand-1, #2b6cb0)', font: 'inherit',
                           textDecoration: 'underline' }}>
            obre'l per estudiar
          </button>.
        </p>
      )}

      {manera === 'estudiar' && dades?.video && ara >= 0 && (
        <div style={{
          padding: '12px 14px', marginBottom: 12, borderRadius: 12,
          background: 'var(--surface-2, #f7f7f8)', border: '1px solid var(--border, #ddd)',
        }}>
          {veuCa && <div style={{ fontSize: 17, fontWeight: 600 }}>{linies[ara].ca}</div>}
          {veuAr && (
            <div dir="rtl" lang="ar" style={{ fontSize: 19, marginTop: 6, textAlign: 'right' }}>
              {linies[ara].ar}
            </div>
          )}
          {veuAm && linies[ara].am && (
            <div style={{ marginTop: 8, paddingTop: 8, fontSize: 14, fontStyle: 'italic',
                          borderTop: '1px dashed var(--border, #ddd)',
                          color: 'var(--text-2, #666)' }}>
              <span style={{ fontStyle: 'normal', fontSize: 11, textTransform: 'uppercase',
                             letterSpacing: '.04em', marginRight: 6 }}>
                la màquina hi sent
              </span>
              {linies[ara].am}
              {linies[ara].am_acord && <ApuntAcord />}
              {linies[ara].am_diu_igual && <ApuntDiuIgual mot={linies[ara].am_diu_igual} />}
            </div>
          )}
        </div>
      )}

      {manera === 'estudiar' && (
       <>
      <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap',
                    marginBottom: 8, fontSize: 13 }}>
        {(['tots', 'ca', 'ar', 'am'] as const).map(m => (
          <button key={m} onClick={() => setMostra(m)}
                  style={{ padding: '4px 10px', borderRadius: 8, cursor: 'pointer', fontSize: 13,
                           border: '1px solid var(--border, #ddd)',
                           background: mostra === m ? 'var(--brand-1, #2b6cb0)' : 'transparent',
                           color: mostra === m ? '#fff' : 'inherit' }}>
            {m === 'tots' ? 'tot' : m === 'ca' ? 'català' : m === 'ar' ? 'àrab'
              : 'el que se sent'}
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
              {veuCa && <span style={{ display: 'block' }}>{l.ca}</span>}
              {veuAr && (
                <span dir="rtl" lang="ar" style={{ display: 'block', textAlign: 'right',
                                                   color: 'var(--text-2, #555)' }}>{l.ar}</span>
              )}
              {veuAm && l.am && (
                <span style={{ display: 'block', fontSize: 13, fontStyle: 'italic',
                               color: 'var(--text-2, #777)' }}>
                  {l.am}{l.am_acord && <ApuntAcord />}
                  {l.am_diu_igual && <ApuntDiuIgual mot={l.am_diu_igual} />}
                </span>
              )}
            </span>
          </button>
        ))}
      </div>

      {dades && (
        <p style={{ marginTop: 10, fontSize: 12, color: 'var(--text-2, #666)', lineHeight: 1.6 }}>
          {!proves && <>Sense vídeo comprovat.</>}
          {proves?.com === 'so' && (
            <>El vídeo és aquesta pujada («{dades.titol_pujada}») i l'episodi hi comença a{' '}
              {rellotge(desplacament)}: {proves.talls_dacord} talls de {proves.talls} hi sonen al
              mateix segon{proves.dispersio !== null && <> (±{proves.dispersio.toFixed(2)} s)</>},
              i que caiguin junts per atzar dins de {proves.minuts_de_la_pujada} minuts passa{' '}
              {proves.falsos_esperats.toExponential(0)} vegades.</>
          )}
          {proves?.com === 'imatge' && (
            <>El vídeo és aquesta pujada («{dades.titol_pujada}») i l'episodi hi comença a{' '}
              {rellotge(desplacament)}. Aquesta pujada ve MUDA de YouTube, així que no s'hi ha
              pogut comparar el so: s'ha casat per la imatge, perquè el subtítol de la pantalla
              canvia quan canvien les nostres línies. Hi casen {proves.marques_amb_canvi} de{' '}
              {proves.marques} marques (±{proves.dispersio.toFixed(2)} s); dels{' '}
              {proves.desplacaments_possibles_s} s de desplaçaments possibles, el millor de tots
              els altres només n'hi casa {proves.millor_dels_altres_desplacaments}. I{' '}
              {proves.frases_comprovades_a_la_pantalla} frases s'han llegit de la pantalla al
              segon que això prediu, i hi diuen la nostra línia paraula per paraula.</>
          )}
          {dades.esmenades > 0 && <> · {dades.esmenades} línies es mostren esmenades (el nom del
            mercader i les fórmules que la màquina feia marianes); a la biblioteca el text queda
            tal com el va deixar la màquina.</>}
          {dades.duplicades_tretes > 0 && <> · {dades.duplicades_tretes} línies duplicades tretes.</>}
          {dades.amb_veu_sentida > 0 && <> · La tercera línia, en cursiva, és l'amazic que un
            model d'ASR sent al tall de veu: {dades.amb_veu_sentida} d'aquest episodi. No és text
            de ningú —el model enganxa els mots i s'inventa lletres—, i per això va a part.{' '}
            {dades.acords > 0
              ? <>A {dades.acords} hi coincideixen dues lectures lletra per lletra, i van
                  marcades: no vol dir que encertin, però coincidir del tot els costa.</>
              : <>En aquest episodi no n'hi ha cap on dues lectures coincideixin del tot.</>}</>}
          {(dades.diuen_igual || 0) > 0 && <> · A {dades.diuen_igual} línies, el que la veu diu
            i el que diu el subtítol <strong>volen dir el mateix</strong>, i van marcades. Són
            dues vies independents —el subtítol és àrab llegit de la imatge; la lectura, taixelhit
            tret del so— i es casen pel significat àrab que el diccionari de l'IRCAM dona a les
            paraules amazigues, sense cap traductor pel mig. Sobre les 3.621 línies de la sèrie
            passa a 206; comparant cada lectura amb el subtítol d'una altra frase a l'atzar, a 13.
            El control és la meitat de la mesura: sense ell, 206 no voldria dir res.</>}
        </p>
      )}
       </>
      )}
    </div>
  );
}
