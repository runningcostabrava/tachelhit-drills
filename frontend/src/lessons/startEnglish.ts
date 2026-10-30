// The two English lessons of /start (#487, #500). Rebuilt on 30-10-2026 after two audits: a
// dialectologist of the Azilal–M'Goun zone and a teacher of Afroasiatic languages to English
// speakers (docs/adr/0005). What they changed, and why the data looks like this:
//
// - a lesson is a script of screens, not a list of cards: the learner speaks aloud in every set;
// - only a recording can be a core item, and Aït Mraw voices come first. Where the zone's form has
//   no recording yet (salam ɛlikum, lhamdullah) it is a line of text, never a card;
// - one respelling scheme: ah, ee, oo, hyphens, no capitals, doubled letters written doubled;
// - only the three sound problems that block understanding are taught: held consonants, gh/x, and
//   no added vowels. ɛ, ḥ, the emphatics and q are left out on purpose.
//
// The voice and the Tifinagh come live from the library by drill id; `lat` is the spelling shown
// here, so that one word is not spelled two ways on one screen.

export interface StartWord {
  key: string;
  drillId: number;
  en: string;
  lat: string;
  say: string;
  /** Said when the recording is not exactly the bare word, or when a form needs a warning. */
  note?: string;
}

export type Screen =
  | { t: 'goal'; title: string; can: string[] }
  | { t: 'sound'; title: string; body: string }
  | { t: 'meet'; key: string }
  | { t: 'pick'; key: string; others: string[] }
  | { t: 'pickAudio'; key: string; others: string[] }
  | { t: 'shadow'; key: string; check: string }
  | { t: 'situation'; prompt: string; key: string }
  | { t: 'exchange'; title: string; lines: { key: string; you: boolean }[] }
  | { t: 'read'; tif: string; lat: string; en: string; letters: string[] }
  | { t: 'done'; next?: string };

export const WORDS: Record<string, StartWord> = {
  morning: { key: 'morning', drillId: 6691, en: 'Good morning', lat: 'tifawin', say: 'tee-fah-ween' },
  how: { key: 'how', drillId: 360, en: 'How are you?', lat: 'manimsh tjit', say: 'mah-neemsh t-jeet' },
  fine: { key: 'fine', drillId: 499, en: 'I’m fine, thank you', lat: 'jigh labas, tanmmirt', say: 'jeegh lah-bahss, tan-mmeert' },
  thanks: { key: 'thanks', drillId: 6778, en: 'Thank you', lat: 'tanmmirt', say: 'tan-mmeert' },
  later: { key: 'later', drillId: 194, en: 'See you soon', lat: 'ar imik', say: 'ar ee-meek' },
  water: { key: 'water', drillId: 197, en: 'Cold water', lat: 'aman ibrdn', say: 'ah-mahn ee-brdn', note: 'aman is water; ibrdn is cold.' },
  bread: { key: 'bread', drillId: 511, en: 'Bring me bread', lat: 'awi-yi-d aɣrum', say: 'ah-wee-yeed ah-ghroom', note: 'aɣrum is bread. Halima says it aghrom. Add ɛafak (ah-fak), “please”: a bare “bring me” sounds rude.' },
  name: { key: 'name', drillId: 6703, en: 'My name is…', lat: 'ism inu…', say: 'eesm ee-noo', note: 'Then say your name.' },
  slowly: { key: 'slowly', drillId: 461, en: 'Slowly', lat: 'lhil lhil', say: 'l-heel l-heel' },
  wait: { key: 'wait', drillId: 179, en: 'Wait', lat: 'shora', say: 'shoo-rah' },
  tiredq: { key: 'tiredq', drillId: 5102, en: 'Are you tired?', lat: 'is tyuheld?', say: 'ees t-yoo-held', note: 'From Beni Mellal. You will hear this one more than you say it.' },
  hungry: { key: 'hungry', drillId: 9, en: 'I’m hungry', lat: 'ingha-yi laz', say: 'een-ghah-yee lahz' },
  foot: { key: 'foot', drillId: 303, en: 'My foot hurts', lat: 'inghay utar', say: 'een-ghah-ee oo-tar' },
  tomorrow: { key: 'tomorrow', drillId: 153, en: 'Tomorrow', lat: 'aska', say: 'ah-ska', note: 'Driss says it twice.' },
};

export interface StartLesson {
  id: string;
  title: string;
  minutes: number;
  screens: Screen[];
}

export const LESSONS: StartLesson[] = [
  {
    id: 'arrive',
    title: 'Lesson 1 · Arrive',
    minutes: 12,
    screens: [
      { t: 'goal', title: 'By the end you can say', can: ['Good morning, and how are you', 'I’m fine, thank you', 'See you soon', 'Water and bread, please', 'Your name'] },
      { t: 'sound', title: 'How this lesson works', body: 'Say everything out loud, even on a bus. Saying it badly teaches you more than reading it well. Use the slow button as often as you like.' },
      { t: 'meet', key: 'morning' }, { t: 'meet', key: 'how' }, { t: 'meet', key: 'fine' },
      { t: 'pick', key: 'how', others: ['morning', 'fine'] },
      { t: 'pick', key: 'fine', others: ['how', 'morning'] },
      { t: 'pick', key: 'morning', others: ['fine', 'how'] },
      { t: 'shadow', key: 'morning', check: 'Did you stress every syllable evenly?' },
      { t: 'shadow', key: 'how', check: 'Did you say the t and the j together, with no vowel between them?' },
      { t: 'sound', title: 'Held letters', body: 'A doubled letter is held longer: tan-mmeert. Hum the m for a moment. In Tifinagh the letter is written twice, so you can see the hold.' },
      { t: 'meet', key: 'thanks' }, { t: 'meet', key: 'later' },
      { t: 'shadow', key: 'thanks', check: 'Did you hold the m?' },
      { t: 'exchange', title: 'Meeting your guide', lines: [{ key: 'morning', you: true }, { key: 'how', you: false }, { key: 'fine', you: true }, { key: 'later', you: false }] },
      { t: 'sound', title: 'The sound gh', body: 'ɣ, written gh here, is a gargle with no water, at the very back of the mouth. The French r is close to it.' },
      { t: 'meet', key: 'water' }, { t: 'meet', key: 'bread' }, { t: 'meet', key: 'name' },
      { t: 'pickAudio', key: 'bread', others: ['water', 'name'] },
      { t: 'pickAudio', key: 'water', others: ['bread', 'thanks'] },
      { t: 'shadow', key: 'bread', check: 'Did you gargle the gh in aghrom?' },
      { t: 'shadow', key: 'water', check: 'Did you say brdn with no vowels in it?' },
      { t: 'situation', prompt: 'The guide pours you tea.', key: 'thanks' },
      { t: 'situation', prompt: 'It is 7 in the morning and you meet a neighbour.', key: 'morning' },
      { t: 'situation', prompt: 'You have just run for three hours and want a drink.', key: 'water' },
      { t: 'situation', prompt: 'A child asks who you are.', key: 'name' },
      { t: 'read', tif: 'ⴰⵎⴰⵏ', lat: 'aman', en: 'water', letters: ['ⴰ a', 'ⵎ m', 'ⴰ a', 'ⵏ n'] },
      { t: 'done', next: 'trail' },
    ],
  },
  {
    id: 'trail',
    title: 'Lesson 2 · On the trail',
    minutes: 14,
    screens: [
      { t: 'goal', title: 'By the end you can say', can: ['Slowly, and wait', 'That you are hungry', 'That your foot hurts', 'Tomorrow', 'And understand “are you tired?”'] },
      { t: 'situation', prompt: 'First, from memory. You meet your guide in the morning.', key: 'morning' },
      { t: 'situation', prompt: 'Your host hands you a plate.', key: 'thanks' },
      { t: 'situation', prompt: 'You ask for bread.', key: 'bread' },
      { t: 'pick', key: 'fine', others: ['later', 'how'] },
      { t: 'sound', title: 'No extra vowels', body: 'Tamazight stacks consonants: tjit, brdn, lhil. Do not slip a vowel in. Say them tight, even if it feels too short.' },
      { t: 'meet', key: 'slowly' }, { t: 'meet', key: 'wait' }, { t: 'meet', key: 'tiredq' },
      { t: 'pick', key: 'tiredq', others: ['slowly', 'wait'] },
      { t: 'pick', key: 'wait', others: ['tiredq', 'slowly'] },
      { t: 'shadow', key: 'slowly', check: 'Did you start on the l with no vowel before it?' },
      { t: 'shadow', key: 'wait', check: 'Did you make it short and easy?' },
      { t: 'pickAudio', key: 'water', others: ['slowly', 'thanks'] },
      { t: 'meet', key: 'hungry' }, { t: 'meet', key: 'foot' }, { t: 'meet', key: 'tomorrow' },
      { t: 'pickAudio', key: 'foot', others: ['hungry', 'tomorrow'] },
      { t: 'pickAudio', key: 'hungry', others: ['foot', 'wait'] },
      { t: 'shadow', key: 'hungry', check: 'Did you gargle the gh?' },
      { t: 'shadow', key: 'foot', check: 'Did you gargle the gh and say oo-tar clearly?' },
      { t: 'exchange', title: 'A stop on the climb', lines: [{ key: 'tiredq', you: false }, { key: 'slowly', you: true }, { key: 'wait', you: true }, { key: 'water', you: true }] },
      { t: 'situation', prompt: 'The group is going too fast for you.', key: 'slowly' },
      { t: 'situation', prompt: 'You turned your ankle on the descent.', key: 'foot' },
      { t: 'situation', prompt: 'You need the group to stop for a moment.', key: 'wait' },
      { t: 'situation', prompt: 'Lunch is late.', key: 'hungry' },
      { t: 'situation', prompt: 'Saying goodbye after the run.', key: 'later' },
      { t: 'situation', prompt: 'Your guide asks when you run again.', key: 'tomorrow' },
      { t: 'done' },
    ],
  },
];

export const START_DRILL_IDS: number[] = Object.values(WORDS).map((w) => w.drillId);
