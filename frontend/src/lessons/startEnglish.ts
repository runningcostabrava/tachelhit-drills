// The first lesson for English speakers (#487).
//
// Only the English lives here. The Amazigh sentence, its Tifinagh and the voice are read live from
// the library by drill id, so the day someone records a word that is missing here, the lesson
// plays it without a new release. A word without a drill is shown as the owner wrote it and says
// it has no recording yet: it never gets a machine voice (docs/SCOPE.md).
//
// The words are the owner's list (29-10-2026): «Salam, tinmirt, meitanit, timensiwin, araska,
// agrom, zit, aman, nikin ismino…, I'm tired — not much more than that».

export interface StartWord {
  key: string;
  /** What it means, in English. */
  en: string;
  /** How it sounds to an English ear. */
  say: string;
  /** The library drill whose voice and spelling are used. */
  drillId?: number;
  /** When the drill is a longer sentence: what that sentence means. */
  example?: string;
  /** The word as the owner gave it, when the library has no drill for it. */
  text?: string;
  note?: string;
}

export interface StartBlock {
  title: string;
  words: StartWord[];
}

export const START_BLOCKS: StartBlock[] = [
  {
    title: 'Hello, how are you, thank you',
    words: [
      { key: 'salam', en: 'Hello (literally “peace”)', say: 'sa-LAAM', text: 'Salam',
        note: 'Borrowed from Arabic and heard everywhere in the valleys. Azul is the Amazigh hello.' },
      { key: 'maytenid', en: 'How are you?', say: 'my-teh-NEED', drillId: 6695,
        note: 'Literally “what do you say?”.' },
      { key: 'tanmmirt', en: 'Thank you', say: 'tan-MEERT (hold the mm)', drillId: 6717 },
      { key: 'timnsiwin', en: 'Good evening / good night', say: 'tee-men-see-WEEN', drillId: 6694,
        note: 'From imnsi, “dinner”: the evening greeting is named after the evening meal.' },
      { key: 'araskka', en: 'See you tomorrow', say: 'ar-ASS-ka', text: 'Ar askka',
        note: 'ar “until” + askka “tomorrow”.' },
    ],
  },
  {
    title: 'At the table',
    words: [
      { key: 'aghrum', en: 'Bread', say: 'a-GHROOM (gh like a French r)', drillId: 511,
        example: '“Bring me the bread.” Listen for aɣrum at the end.' },
      { key: 'aman', en: 'Water', say: 'a-MAN', drillId: 197,
        example: '“Cold water”: aman + ibrdn, cold.' },
      { key: 'zit', en: 'Olive oil', say: 'ZEET (a strong z)', drillId: 4736 },
    ],
  },
  {
    title: 'About you',
    words: [
      { key: 'isminu', en: 'My name is …', say: 'NEE-keen, is-mee-NOO …', text: 'Nkkin, ism inu …',
        note: 'nkkin “me” · ism “name” · inu “my”. Then say your name.' },
      { key: 'tired', en: 'Are you tired?', say: 'is tyu-HELD', drillId: 5102,
        note: 'To answer “I’m tired”: suhalx (soo-HALKH). Same verb, said by “I”.' },
    ],
  },
];

/** Every drill the lesson reads, in order. */
export const START_DRILL_IDS: number[] = START_BLOCKS.flatMap((b) => b.words.map((w) => w.drillId))
  .filter((x): x is number => typeof x === 'number');
