/**
 * El visor PRIVAT de Tamazight TV (SNRT): només per a administradors i convidats de la SNRT (docs/adr/0012). El vídeo, si hi és, viu al servidor d'Alibaba i es demana amb una adreça signada de 4 h.
 *
 * Material de recerca amb permís de la SNRT: recerca sí, republicar no. Aquí no es republica res: el vídeo no es guarda ni es
 * serveix (s'encasta de YouTube, o es carrega des de l'ordinador de qui mira), i el text només el veuen els administradors.
 * Les respostes no passen pel cau fora de línia de l'app (`api.ts`): s'han de poder oblidar en tancar la sessió.
 *
 * El text està SENSE REVISAR: el tifinag i l'àrab els va llegir una màquina de la imatge i el català el va traduir una altra.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { API_BASE } from '../config';
import { loadYouTubeApi } from '../utils/youtubeUtils';
import { formes } from '../utils/tifinag';
import { desaNansa, fitxerDeLaCarpeta, fitxerDeLaNansa, llegeixNansa, nomDeLaCarpeta, oblidaNansa,
         potRecordar, potTriarCarpeta, triaCarpeta, triaFitxer } from '../utils/videoDesat';

interface Episodi { slug: string; titol: string; durada: number | null; linies: number; amb_catala: number; video_youtube: string | null; url_pagina: string | null }
interface Linia { k: number; t_ini: number; t_fi: number; tifinag: string | null; arab: string | null; catala: string | null; catala_estat: string | null; sentit: string | null }
interface Dades { slug: string; titol: string; durada: number | null; url_pagina: string | null; video_youtube: string | null; avis: string; linies: Linia[] }

async function demana<T>(ruta: string): Promise<T> {
  const r = await fetch(`${API_BASE}${ruta}`, { cache: 'no-store' });
  if (r.status === 401 || r.status === 403) throw new Error('Només per a administradors.');
  if (!r.ok) throw new Error(`Error ${r.status}`);
  return r.json();
}

const mmss = (t: number) => `${Math.floor(t / 60)}:${String(Math.floor(t % 60)).padStart(2, '0')}`;

export default function SnrtPrivat() {
  const [admin, setAdmin] = useState<boolean | null>(null);
  const [eps, setEps] = useState<Episodi[]>([]);
  //: Es pot arribar aquí des d'Històries amb el capítol ja triat (`/snrt?ep=<slug>`, #695). Es
  //: llegeix un sol cop, en muntar: després mana el que tria qui mira, i canviar-li el capítol
  //: perquè l'adreça encara digui una altra cosa seria desconcertant.
  const [sel, setSel] = useState<string | null>(() => {
    try { return new URLSearchParams(window.location.search).get('ep'); } catch { return null; }
  });
  const [dades, setDades] = useState<Dades | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [ara, setAra] = useState(0);
  const [desp, setDesp] = useState(0);
  const [veu, setVeu] = useState({ catala: true, arab: true, tifinag: false, sentit: false });
  //: Amb quina grafia es pinta l'amazic. El tifinag primer, que és el seu alfabet; el llatí hi és
  //: perquè llegir-lo de pressa, sota un vídeo que no s'atura, encara costa a qui aprèn.
  const [grafia, setGrafia] = useState<'tif' | 'lat'>(() => {
    try { return localStorage.getItem('snrt.grafia') === 'lat' ? 'lat' : 'tif'; } catch { return 'tif'; }
  });
  useEffect(() => { try { localStorage.setItem('snrt.grafia', grafia); } catch { /* finestra privada */ } }, [grafia]);
  const marcRef = useRef<HTMLDivElement | null>(null);
  //: El nom del fitxer que aquest episodi ja va fer servir un altre dia, si el navegador el
  //: recorda. No és el vídeo: és una nansa al disc de qui mira, i cal un clic per reobrir-la.
  const [desat, setDesat] = useState<string | null>(null);
  //: La carpeta on són tots els vídeos. Triada un cop, cada episodi hi busca el seu pel nom, i
  //: així no s'han de buscar 39 fitxers a mà.
  const [carpeta, setCarpeta] = useState<string | null>(null);
  useEffect(() => { nomDeLaCarpeta().then(setCarpeta).catch(() => {}); }, []);
  const [fitxer, setFitxer] = useState<string | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const ytRef = useRef<{ getCurrentTime: () => number; seekTo: (s: number, a: boolean) => void; destroy?: () => void } | null>(null);
  const llistaRef = useRef<HTMLDivElement | null>(null);

  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  useEffect(() => {
    // L'accés (administrador o convidat de la SNRT) el decideix el servidor: si no hi deixa entrar, es diu i prou.
    demana<{ episodis: Episodi[] }>('/snrt-privat/').then((d) => { setEps(d.episodis); setAdmin(true); setSel((s) => (s && d.episodis.some((e) => e.slug === s) ? s : null)); }).catch((e) => { setAdmin(false); setError(String(e.message || e)); });
  }, []);
  useEffect(() => {
    if (!sel) return;
    setDades(null); setFitxer(null); setAra(0); setVideoUrl(null);
    try { setDesp(Number(localStorage.getItem(`snrt.desp.${sel}`)) || 0); } catch { setDesp(0); }
    setDesat(null);
    //: Si el permís encara hi és (mateixa sessió), el vídeo s'obre sol i no es pregunta res. Si
    //: ha caducat, només se'n diu el nom i es deixa el botó: demanar-lo sense un clic no val.
    (async () => {
      //: mana la nansa d'aquest episodi: si algú n'ha triat un fitxer a mà, no se li canvia
      const n = await llegeixNansa(sel);
      if (n) {
        const f = await fitxerDeLaNansa(n, false);
        if (f) { setFitxer(URL.createObjectURL(f)); return; }
        setDesat(n.name);
        return;
      }
      const g = await fitxerDeLaCarpeta(sel, false);
      if (g) setFitxer(URL.createObjectURL(g));
    })().catch(() => {});
    demana<Dades>(`/snrt-privat/${encodeURIComponent(sel)}`).then(setDades).catch((e) => setError(String(e.message || e)));
    // vídeo allotjat al servidor d'Alibaba: adreça signada de 4 h (si no n'hi ha, es carrega des de l'ordinador)
    demana<{ url: string | null }>(`/snrt-privat/${encodeURIComponent(sel)}/video`).then((d) => setVideoUrl(d.url)).catch(() => setVideoUrl(null));
  }, [sel]);
  useEffect(() => { try { if (sel) localStorage.setItem(`snrt.desp.${sel}`, String(desp)); } catch { /* finestra privada */ } }, [sel, desp]);

  // vídeo de YouTube, si l'episodi hi és
  useEffect(() => {
    if (!dades?.video_youtube || videoUrl) return;
    let viu = true;
    loadYouTubeApi().then((YT) => {
      if (!viu) return;
      ytRef.current = new YT.Player('snrt-yt', { videoId: dades.video_youtube, playerVars: { rel: 0, playsinline: 1 } });
    });
    return () => { viu = false; try { ytRef.current?.destroy?.(); } catch { /* ja no hi és */ } ytRef.current = null; };
  }, [dades?.video_youtube, videoUrl]);

  // el temps del vídeo, vingui d'on vingui
  useEffect(() => {
    const id = window.setInterval(() => {
      const v = videoRef.current;
      const t = v ? v.currentTime : (ytRef.current?.getCurrentTime ? ytRef.current.getCurrentTime() : null);
      if (t != null && Number.isFinite(t)) setAra(t);
    }, 250);
    return () => window.clearInterval(id);
  }, []);
  useEffect(() => () => { if (fitxer) URL.revokeObjectURL(fitxer); }, [fitxer]);

  const t = ara + desp;
  const actual = useMemo(() => {
    if (!dades) return -1;
    return dades.linies.findIndex((l) => t >= l.t_ini && t < l.t_fi);
  }, [dades, t]);
  useEffect(() => {
    if (actual < 0 || !llistaRef.current) return;
    const el = llistaRef.current.querySelector<HTMLElement>(`[data-k="${actual}"]`);
    el?.scrollIntoView({ block: 'nearest' });
  }, [actual]);

  const salta = useCallback((l: Linia) => {
    const s = Math.max(0, l.t_ini - desp);
    if (videoRef.current) { videoRef.current.currentTime = s; void videoRef.current.play(); }
    else ytRef.current?.seekTo(s, true);
    setAra(s);
  }, [desp]);

  if (admin === null) return <p style={{ padding: 16 }}>Carregant…</p>;
  if (!admin) return <p style={{ padding: 16 }}>Aquesta pàgina és només per a administradors i convidats de la SNRT. Entra amb el teu compte.</p>;
  const linia = dades && actual >= 0 ? dades.linies[actual] : null;

  return (
    <div className="snrt-privat" style={{ maxWidth: 1100, margin: '0 auto', padding: '12px 16px' }}>
      <style>{`
        .snrt-privat .avis{border:1px solid #c9a227;background:rgba(201,162,39,.12);border-radius:8px;padding:8px 12px;font-size:.85rem;margin:8px 0}
        .snrt-privat .cols{display:flex;gap:16px;flex-wrap:wrap;align-items:flex-start}
        .snrt-privat .video{flex:1 1 480px;min-width:0}
        .snrt-privat .llista{flex:1 1 320px;min-width:0;max-height:70vh;overflow:auto;border:1px solid rgba(128,128,128,.35);border-radius:8px}
        .snrt-privat .fila{padding:6px 10px;border-bottom:1px solid rgba(128,128,128,.2);cursor:pointer;overflow-wrap:anywhere}
        .snrt-privat .fila.ara{background:rgba(70,130,220,.2)}
        .snrt-privat .marc{position:relative;background:#000;border-radius:8px;overflow:hidden}
        .snrt-privat .marc:fullscreen{border-radius:0;display:flex;align-items:center;justify-content:center}
        .snrt-privat .marc:fullscreen video{max-height:100vh;width:auto}
        /* Damunt del vídeo i per sota dels seus controls: els controls natius seuen a sota i
           taparien el subtítol si aquest hi fos enganxat. */
        .snrt-privat .sub{position:absolute;left:0;right:0;bottom:3.2em;padding:6px 12px;color:#fff;text-align:center;overflow-wrap:anywhere;pointer-events:none;text-shadow:0 2px 4px #000,0 0 10px #000}
        .snrt-privat .sub>div{display:inline-block;background:rgba(0,0,0,.62);border-radius:6px;padding:2px 10px;margin:1px 0}
        .snrt-privat .pantalla{position:absolute;top:8px;right:8px;background:rgba(0,0,0,.55);color:#fff;border:0;border-radius:6px;padding:4px 9px;font-size:1rem;cursor:pointer}
        .snrt-privat .sub .se{font-size:1rem;opacity:.95;border:1px dashed rgba(255,255,255,.55)}
        .snrt-privat .sub .ca{font-size:1.25rem}.snrt-privat .sub .ar{font-size:1.05rem;opacity:.9;direction:rtl}.snrt-privat .sub .ti{font-size:1rem;opacity:.8}
        .snrt-privat video,.snrt-privat #snrt-yt{width:100%;aspect-ratio:16/9;background:#000;border-radius:8px}
        .snrt-privat .ep{display:block;width:100%;text-align:left;padding:8px 10px;margin:4px 0;border:1px solid rgba(128,128,128,.35);border-radius:8px;background:transparent;color:inherit;cursor:pointer}
        .snrt-privat .tria label{margin-right:12px;white-space:nowrap}
      `}</style>
      <h1 style={{ fontSize: '1.3rem' }}>Tamazight TV · visor privat</h1>
      <div className="avis">Material de la SNRT, només per a recerca i només visible per a administradors. El text és llegit i traduït per màquina, <strong>sense revisar</strong>. No es guarda ni es serveix cap vídeo.</div>
      {error && <p role="alert">{error}</p>}

      {!sel && (
        <div>
          {eps.length === 0 && !error && <p>Encara no hi ha cap episodi carregat.</p>}
          {eps.map((e) => (
            <button key={e.slug} className="ep" onClick={() => setSel(e.slug)}>
              <strong>{e.titol}</strong><br />
              <small>{e.durada ? mmss(e.durada) + ' · ' : ''}{e.linies} línies · {e.amb_catala} amb català{e.video_youtube ? ' · vídeo de YouTube' : ''}</small>
            </button>
          ))}
        </div>
      )}

      {sel && (
        <div>
          <button onClick={() => { setSel(null); setDades(null); }} style={{ marginBottom: 8 }}>← Episodis</button>
          {!dades && <p>Carregant l'episodi…</p>}
          {dades && (
            <>
              <h2 style={{ fontSize: '1.1rem' }}>{dades.titol}</h2>
              <div className="cols">
                <div className="video">
                  {/* El subtítol va DINS del marc del vídeo, no a sota: a pantalla completa el
                      navegador només ensenya el que hi ha dins de l'element que s'hi posa, i un
                      subtítol que desapareix justament quan mires de prop no serveix de res. */}
                  <div className="marc" ref={marcRef}>
                    {dades.video_youtube && !videoUrl ? <div id="snrt-yt" /> : (
                      <video ref={videoRef} src={videoUrl || fitxer || undefined} controls />
                    )}
                    <div className="sub" aria-live="polite">
                      {linia ? (<>
                        {veu.catala && <div className="ca">{linia.catala || <em>(sense traducció)</em>}</div>}
                        {veu.arab && linia.arab && <div className="ar" dir="rtl">{linia.arab}</div>}
                        {veu.tifinag && linia.tifinag && (
                          <div className="ti">{grafia === 'tif' ? formes(linia.tifinag).tif : formes(linia.tifinag).lat}</div>
                        )}
                        {/* El que ha sentit el nostre model, quan hi és. Va en una línia a part i
                            marcada: no és el subtítol de la cadena, és una altra font que sovint
                            el contradiu, i confondre-les faria perdre justament el que val. */}
                        {veu.sentit && linia.sentit && (
                          <div className="se">{grafia === 'tif' ? formes(linia.sentit).tif : formes(linia.sentit).lat}</div>
                        )}
                      </>) : <span style={{ opacity: .6 }}>…</span>}
                    </div>
                    <button className="pantalla" title="Pantalla completa amb els subtítols"
                            onClick={() => {
                              const m = marcRef.current;
                              if (!m) return;
                              if (document.fullscreenElement) document.exitFullscreen().catch(() => {});
                              else m.requestFullscreen().catch(() => {});
                            }}>⛶</button>
                  </div>
                  <p style={{ fontSize: '.85rem' }}>
                    {videoUrl ? "Vídeo del servidor privat." : fitxer ? "Vídeo carregat des del teu ordinador (no surt d'aquí)." : "Carrega el vídeo de l'episodi des del teu ordinador:"}{' '}
                    {!videoUrl && !dades.video_youtube && (potRecordar() ? (
                      <button onClick={async () => {
                        const nansa = await triaFitxer();
                        if (!nansa || !sel) return;
                        const f = await fitxerDeLaNansa(nansa, true);
                        if (!f) return;
                        setFitxer(URL.createObjectURL(f)); setDesat(null);
                        desaNansa(sel, nansa).catch(() => {});
                      }}>Tria el vídeo…</button>
                    ) : (
                      <input type="file" accept="video/*" onChange={(ev) => { const f = ev.target.files?.[0]; if (f) setFitxer(URL.createObjectURL(f)); }} />
                    ))}
                    {!videoUrl && !dades.video_youtube && potTriarCarpeta() && (
                      <> <button onClick={async () => {
                        const c = await triaCarpeta();
                        if (!c) return;
                        setCarpeta(c.name);
                        if (!sel) return;
                        const f = await fitxerDeLaCarpeta(sel, true);
                        if (f) { setFitxer(URL.createObjectURL(f)); setDesat(null); }
                      }}>{carpeta ? `Carpeta: ${carpeta}` : 'Tria la carpeta dels vídeos…'}</button></>
                    )}
                    {desat && !fitxer && !videoUrl && (
                      <> <button onClick={async () => {
                        const n = sel ? await llegeixNansa(sel) : null;
                        const f = n ? await fitxerDeLaNansa(n, true) : null;
                        //: si la nansa ha quedat orfe (fitxer mogut o esborrat), s'oblida en comptes
                        //: de deixar un botó que no farà mai res
                        if (f) { setFitxer(URL.createObjectURL(f)); setDesat(null); }
                        else if (sel) { oblidaNansa(sel).catch(() => {}); setDesat(null); }
                      }}>Torna a obrir «{desat}»</button></>
                    )}
                    {dades.url_pagina && <> · <a href={dades.url_pagina} target="_blank" rel="noreferrer noopener">pàgina original</a></>}
                  </p>
                  <div className="tria" style={{ marginTop: 8, fontSize: '.9rem' }}>
                    {(['catala', 'arab', 'tifinag', 'sentit'] as const).map((k) => (
                      <label key={k}><input type="checkbox" checked={veu[k]} onChange={() => setVeu({ ...veu, [k]: !veu[k] })} /> {k === 'catala' ? 'Català' : k === 'arab' ? 'Àrab' : k === 'tifinag' ? 'Amazic' : 'El que sentim'}</label>
                    ))}
                    {/* La grafia val per a l'amazic de la cadena i per al que sentim: són la
                        mateixa llengua escrita, i tenir-les en alfabets diferents impediria
                        justament el que es vol fer aquí, que és comparar-les d'un cop d'ull. */}
                    <label>Lletra:{' '}
                      <select value={grafia} onChange={(e) => setGrafia(e.target.value === 'lat' ? 'lat' : 'tif')}>
                        <option value="tif">ⵜⵉⴼⵉⵏⴰⵖ</option>
                        <option value="lat">llatina</option>
                      </select>
                    </label>
                    <label>Ajust dels subtítols: <input type="range" min={-6} max={6} step={0.25} value={desp} onChange={(e) => setDesp(Number(e.target.value))} /> {desp > 0 ? '+' : ''}{desp.toFixed(2)} s</label>
                  </div>
                </div>
                <div className="llista" ref={llistaRef}>
                  {dades.linies.map((l, i) => (
                    <div key={l.k} data-k={i} className={'fila' + (i === actual ? ' ara' : '')} onClick={() => salta(l)}>
                      <small>{mmss(l.t_ini)}</small> {l.catala || <em>(sense traducció)</em>}
                    </div>
                  ))}
                </div>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
