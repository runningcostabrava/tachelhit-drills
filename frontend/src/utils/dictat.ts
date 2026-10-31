import { useCallback, useEffect, useRef, useState } from 'react';
import { SpeechRecognition } from '@capacitor-community/speech-recognition';
import { isNativeApp } from '../config';
import { toast } from '../toast';
import { whyItFailed } from './errors';

// Dictar el que es busca (#546).
//
// L'amo: «vull que la búsqueda al mòbil funcioni amb un micròfon». És el reconeixedor del mateix
// telèfon —el mateix que fa el dictat de la pantalla de gravar—, i va **sense xarxa**, que és el
// que toca en una cerca que ja busca primer a la còpia del telèfon.
//
// Dicta en CATALÀ: la llengua del que busques, no la que busques. Cap telèfon no sap escriure
// amazic a l'oïda; per trobar una paraula amaziga s'escriu com es vulgui, que la cerca compara
// pel so.
//
// **El botó es veu sempre.** El primer intent el tapava si `available()` deia que no, i a l'amo
// no li sortia enlloc. Amagar una cosa que potser sí que va és pitjor que ensenyar-la i dir-li,
// si es prem, per què no pot ser.

export function useDictat(onFi: (text: string) => void) {
  const [dictant, setDictant] = useState(false);
  const text = useRef('');
  const fi = useRef(onFi);
  fi.current = onFi;

  useEffect(() => () => {
    void SpeechRecognition.removeAllListeners().catch(() => {});
    void SpeechRecognition.stop().catch(() => {});
  }, []);

  const acaba = useCallback(async () => {
    setDictant(false);
    try { await SpeechRecognition.stop(); } catch { /* ja s'ha aturat sol */ }
    const dit = text.current.trim();
    if (dit) fi.current(dit);
  }, []);

  const dicta = useCallback(async (mentre?: (parcial: string) => void) => {
    if (dictant) return void acaba();
    try {
      if (isNativeApp()) {
        const perm = await SpeechRecognition.checkPermissions();
        if (perm.speechRecognition !== 'granted'
          && (await SpeechRecognition.requestPermissions()).speechRecognition !== 'granted') {
          return toast.error('Cal permís de micròfon per dictar.');
        }
      }
      if (!(await SpeechRecognition.available()).available) {
        return toast.error('Aquest telèfon no sap dictar: escriu-ho.');
      }
      text.current = '';
      await SpeechRecognition.removeAllListeners();
      SpeechRecognition.addListener('partialResults', (data: { matches?: string[] }) => {
        const m = data.matches?.[0];
        if (m) { text.current = m; mentre?.(m); }
      });
      setDictant(true);
      await SpeechRecognition.start({ language: 'ca-ES', partialResults: true, popup: false });
    } catch (e) {
      setDictant(false);
      toast.error(whyItFailed(e, 'El dictat no ha funcionat'));
    }
  }, [dictant, acaba]);

  return { dictant, dicta };
}
