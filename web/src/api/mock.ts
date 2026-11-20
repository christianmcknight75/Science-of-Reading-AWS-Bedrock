// Mock API: lets every screen work without Bedrock or a database.
//
// Rules for this file:
//  - Every response carries example: true. The UI marks examples clearly.
//  - Sources are limited to documents already approved for the corpus (WWC practice guides,
//    National Reading Panel, UK reading framework). Nothing is cited from a held-back source.
//  - Passage text below is SAMPLE text written for the demo. It is NOT a real quotation, and the
//    Sources panel says so for examples. Real passages come from the API.
import { classifyPair, plural, unknownSounds } from "../lib/decode";
import {
  ApiError,
  type AskRequest,
  type AskResult,
  type Feedback,
  type GroupPlan,
  type MistakePair,
  type MistakeResult,
  type PlanStep,
  type Refresher,
  type Skill,
  type SourceOut,
  type Story,
  type StoryRequest,
  type TrainingPlan,
  type TrainingTopic,
} from "./types";

export const MOCK_DISCLAIMER =
  "Reading Helper offers research-based ideas for teachers. It is advice only. It does not evaluate you, your students, or any program.";
export const MOCK_OFFER =
  "I can help with research on phonemic awareness, phonics and decoding, fluency, vocabulary, comprehension, and supporting struggling readers in kindergarten through 3rd grade.";
export const MOCK_CONTENT_DATE = "2026-11-20";

declare global {
  interface Window {
    __MOCK_DELAY__?: number;
  }
}
const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));
const delay = () => sleep(window.__MOCK_DELAY__ ?? 900);

// ---------------------------------------------------------------- sources (approved only)
type Key = "wwcR2" | "wwcR3" | "wwcR4" | "nrp" | "rti" | "uk";
const BANK: Record<Key, Omit<SourceOut, "n">> = {
  wwcR2: {
    passage_id: "example_src_0011_a",
    title:
      "Foundational Skills to Support Reading for Understanding in Kindergarten Through 3rd Grade",
    year: 2016,
    source_type: "practice_guide",
    section: "Recommendation 2: Develop awareness of the segments of sounds in speech",
    page: "17",
    passage_text:
      "Students who can hear the separate sounds in a word and link each sound to a letter learn to read and spell more easily. Teachers can begin with words of two or three sounds and move to longer words as students gain skill. Practice should be brief, happen every day, and use letters as soon as students know them.",
    quote:
      "begin with words of two or three sounds and move to longer words as students gain skill",
  },
  wwcR3: {
    passage_id: "example_src_0011_b",
    title:
      "Foundational Skills to Support Reading for Understanding in Kindergarten Through 3rd Grade",
    year: 2016,
    source_type: "practice_guide",
    section: "Recommendation 3: Teach students to decode words",
    page: "29",
    passage_text:
      "Students should be taught to look at every letter in a word and say its sound, then blend the sounds into the word. Guessing a word from a picture or from the first letter keeps students from learning how the letters work. Teachers can build the habit by asking students to point to each letter and say the sound before they say the word.",
    quote: "look at every letter in a word and say its sound, then blend the sounds into the word",
  },
  wwcR4: {
    passage_id: "example_src_0011_c",
    title:
      "Foundational Skills to Support Reading for Understanding in Kindergarten Through 3rd Grade",
    year: 2016,
    source_type: "practice_guide",
    section: "Recommendation 4: Ensure that each student reads connected text every day",
    page: "40",
    passage_text:
      "Students need to read connected text every day, with a teacher or a partner who can help when they get stuck. Reading the same short passage more than once, with feedback, helps students read more smoothly and with fewer mistakes. Text should be matched to the sounds students have already been taught.",
    quote: "Reading the same short passage more than once, with feedback, helps students read",
  },
  nrp: {
    passage_id: "example_nrp_a",
    title: "Report of the National Reading Panel: Teaching Children to Read",
    year: 2000,
    source_type: "foundational",
    section: "Phonemic awareness instruction",
    page: "2-40",
    passage_text:
      "Teaching children to manipulate the sounds in words helped them learn to read and spell. The effects were larger when teachers also showed children how to use the letters. Instruction that focused on one or two kinds of sound tasks worked better than instruction that tried to cover many at once.",
    quote: "The effects were larger when teachers also showed children how to use the letters",
  },
  rti: {
    passage_id: "example_rti_a",
    title:
      "Assisting Students Struggling with Reading: Response to Intervention and Multi-Tier Intervention in the Primary Grades",
    year: 2009,
    source_type: "practice_guide",
    section: "Recommendation 3: Provide intensive, systematic instruction",
    page: "26",
    passage_text:
      "Students who struggle benefit from small-group time each day that focuses on a few foundational skills. Lessons should be short, move at a steady pace, and give each student many chances to respond and get feedback.",
    quote: "small-group time each day that focuses on a few foundational skills",
  },
  uk: {
    passage_id: "example_uk_a",
    title: "The reading framework",
    year: 2023,
    source_type: "practice_guide",
    section: "Teaching early reading: decoding",
    page: "58",
    passage_text:
      "Beginning readers should be given books that match the sounds they have been taught, so they can practise reading words by sounding them out. Children should not be encouraged to guess unfamiliar words from pictures or other clues when they can work them out from the letters.",
    quote: "should not be encouraged to guess unfamiliar words from pictures",
  },
};
export const sources = (...keys: Key[]): SourceOut[] =>
  keys.map((k, i) => ({ ...BANK[k], n: i + 1 }));

// ---------------------------------------------------------------- Ask
const base = {
  mixed: false,
  short_answer: "",
  research_says: [],
  idea_for_class: [],
  watch_out: null,
  sources: [],
  message: "",
  offer: "",
  disclaimer: MOCK_DISCLAIMER,
  content_last_updated: MOCK_CONTENT_DATE,
  example: true,
};

function answerFor(q: string): AskResult {
  const t = q.toLowerCase();
  if (
    /(retain|retention|promot|hold (him|her|them) back|evaluat|rate my|which program|curriculum|buy )/.test(
      t,
    )
  )
    return {
      ...base,
      kind: "out_of_scope",
      evidence_label: "No research found",
      message:
        "That is a decision for you and your school team, so I can't advise on it. I don't make decisions about individual students, rate teachers, or recommend products.",
      offer: MOCK_OFFER,
    };
  if (/(\bb and d\b|b\/d|reverse|mirror|backwards)/.test(t))
    return {
      ...base,
      kind: "answer",
      evidence_label: "Very sure",
      short_answer:
        "Mixing up b and d is common at this age. It helps to teach each letter with its own sound and a motion, and to practise them in words, not just on cards.",
      research_says: [
        {
          text: "Linking each sound to its letter, and practising it in words, helps students learn letters.",
          citations: [1, 2],
        },
      ],
      idea_for_class: [
        {
          text: 'Teach one letter at a time. Say "b" and show a bat and ball shape with your hands.',
          minutes: 2,
        },
        { text: "Once b is solid, add d. Read bad, dab, bid, did together.", minutes: 3 },
      ],
      watch_out: null,
      sources: sources("wwcR2", "nrp"),
    };
  if (/(letter sounds|can't read words|cannot read words|blend|sound out)/.test(t))
    return {
      ...base,
      kind: "answer",
      evidence_label: "Very sure",
      short_answer:
        "Knowing letter sounds is step one. Kids also need daily practice putting sounds together to make words. Start with 2 sounds, then 3, and connect the sounds to letters.",
      research_says: [
        {
          text: "Students who hear the separate sounds in a word and link them to letters learn to read more easily.",
          citations: [1, 2],
        },
        {
          text: "Begin with two- and three-sound words, then move to longer words.",
          citations: [1],
        },
      ],
      idea_for_class: [
        { text: 'Say: "I’m a robot. m… a… p. What word?"', minutes: 2 },
        { text: 'Kids say "map" together on your tap. Do 5 words.', minutes: 2 },
        { text: "Show the letters. Kids touch each one and say the word fast.", minutes: 1 },
      ],
      watch_out: {
        myth: "Kids who know their letter sounds will work out reading on their own.",
        correction: "Most need direct practice blending sounds into words.",
        citations: [1],
      },
      sources: sources("wwcR2", "nrp"),
    };
  if (/(picture|guess|three.?cue|context clue|first letter)/.test(t))
    return {
      ...base,
      kind: "answer",
      evidence_label: "Very sure",
      short_answer:
        "Guessing from pictures can feel like reading, but it skips the letters. Kids learn faster when they look at every letter, say each sound, and blend.",
      research_says: [
        {
          text: "Students should look at every letter, say its sound, and blend the sounds into the word.",
          citations: [1],
        },
        {
          text: "Beginning readers should not be encouraged to guess words from pictures.",
          citations: [2],
        },
      ],
      idea_for_class: [
        { text: "Cover the picture. Say: “Point to each letter. What sound?”", minutes: 2 },
        {
          text: "Blend the sounds, then look at the picture to check the word makes sense.",
          minutes: 2,
        },
      ],
      watch_out: {
        myth: "Good readers use pictures and first letters to work out words.",
        correction: "Skilled readers look at all the letters in a word.",
        citations: [1, 2],
      },
      sources: sources("wwcR3", "uk"),
    };
  if (/(fluen|smooth|repeated|speed|read aloud|reread)/.test(t))
    return {
      ...base,
      kind: "answer",
      evidence_label: "Fairly sure",
      short_answer:
        "Reading the same short passage a few times, with a helper who gives feedback, helps kids read more smoothly. Pick text that matches the sounds they know.",
      research_says: [
        {
          text: "Reading a short passage more than once with feedback helps students read smoothly with fewer mistakes.",
          citations: [1],
        },
        { text: "Text should match the sounds students have been taught.", citations: [1, 2] },
      ],
      idea_for_class: [
        {
          text: "Pick a 3-sentence passage kids can mostly sound out. Read it to them once.",
          minutes: 1,
        },
        {
          text: "Partners read it twice. The listener points out one word to fix, kindly.",
          minutes: 4,
        },
      ],
      watch_out: null,
      sources: sources("wwcR4", "uk"),
    };
  if (/(decodable|leveled|levelled)/.test(t))
    return {
      ...base,
      kind: "answer",
      evidence_label: "Not sure yet",
      mixed: true,
      short_answer:
        "The research is mixed on how much beginning readers should read only decodable books. Sound-it-out text early on is supported, but the sources do not agree on how long to keep it up.",
      research_says: [
        {
          text: "Beginning readers should get books that match the sounds they have been taught.",
          citations: [1],
        },
        {
          text: "Text should be matched to the sounds students have already learned.",
          citations: [2],
        },
      ],
      idea_for_class: [
        {
          text: "Pick a short text that uses only the sounds taught so far, and read it together.",
          minutes: 4,
        },
      ],
      watch_out: null,
      sources: sources("uk", "wwcR4"),
    };
  if (/(small group|struggl|intervention|behind|catch up)/.test(t))
    return {
      ...base,
      kind: "answer",
      evidence_label: "Fairly sure",
      short_answer:
        "For kids who are behind, a short small-group lesson every day on a few core skills works better than covering many skills at once.",
      research_says: [
        {
          text: "Daily small-group time that focuses on a few foundational skills helps students who struggle.",
          citations: [1],
        },
      ],
      idea_for_class: [
        {
          text: "Pick one skill for the group this week. Keep the lesson to 15 minutes.",
          minutes: 2,
        },
        {
          text: "Give every child many turns to answer, and tell them right away how they did.",
          minutes: 10,
        },
      ],
      watch_out: null,
      sources: sources("rti"),
    };
  return {
    ...base,
    kind: "no_research",
    evidence_label: "No research found",
    message:
      "I looked through the approved research and did not find anything that answers this, so I won't guess.",
    offer: MOCK_OFFER,
  };
}

export async function ask(req: AskRequest): Promise<AskResult> {
  await delay();
  if (/\b(unavailable-test)\b/i.test(req.question))
    throw new ApiError("Reading Helper Q&A is switched off right now.", 503);
  return answerFor(req.question);
}

// ---------------------------------------------------------------- Group plan
const S = (
  title: string,
  minutes: number,
  body: string,
  extra: Partial<PlanStep> = {},
): PlanStep => ({
  title,
  minutes,
  body,
  ...extra,
});

const PLANS: Record<Skill, { why: string; steps: (sounds: string[]) => PlanStep[] }> = {
  blend: {
    why: "This group is putting sounds together, so we keep the sounds they know and add more blending practice before anything new.",
    steps: (sounds) => [
      S("Warm up the sounds", 2, "Flash each card. Say: Sound? Kids say it together.", {
        sounds,
        tip: 'Quick reminder: hold "mmm" and "sss." Clip "t" and "p" short, no "tuh."',
      }),
      S("Robot Talk", 4, "Say each sound, then: Everyone, on my tap... what word?", {
        words: ["sat", "pin", "fan", "mad", "tip", "dim"],
        tip: "Keeps kids with you: everyone answers on your tap, so no one shouts out and no one hides.",
      }),
      S(
        "Write it",
        3,
        "Say a word. Kids tap the sounds, then write one letter per box: pat, fin, sad.",
      ),
      S("Read a story they can sound out", 4, "Read it together, then once more with partners.", {
        story: "Sam and Pam sat. Pam had a map. Sam had a fan. Pam and Sam sat in the sand.".split(
          " ",
        ),
      }),
      S("Quick check", 2, "Point to each word. See how many most of the group can read.", {
        words: ["nap", "sit", "fad", "pit", "man"],
      }),
    ],
  },
  "hear-sounds": {
    why: "This group is hearing the sounds in words, so we spend most of the time on tapping sounds before adding letters.",
    steps: (sounds) => [
      S("Warm up the sounds", 2, "Say each sound with its mouth motion. Kids copy you.", {
        sounds,
      }),
      S("Tap it out", 5, "Say a word. Kids tap one finger for each sound, then say the sounds.", {
        words: ["sun", "map", "sit", "top", "fan", "pig"],
        tip: 'Hold "sss" and "nnn." Don’t add "uh" at the end.',
      }),
      S(
        "Sound boxes",
        4,
        "Draw one box per sound. Kids push a counter into a box for each sound, then add letters.",
      ),
      S("Say it fast", 2, "Say the sounds slowly, kids say the word fast: m-a-p... map!", {
        words: ["map", "sit", "pin"],
      }),
      S("Quick check", 2, "Say a word. Can most kids say each sound? Note it for tomorrow.", {
        words: ["nap", "tip", "dim"],
      }),
    ],
  },
  digraphs: {
    why: "This group is learning that two letters can make one sound (sh, ch), so we sort and read words with those letters.",
    steps: (sounds) => [
      S("Warm up the sounds", 2, "Flash each card, including sh and ch. Say: Sound?", { sounds }),
      S(
        "Two letters, one sound",
        4,
        'Show sh. Say: "These two letters make one sound, shhh." Kids trace it in the air.',
      ),
      S(
        "Sort cards",
        4,
        'Sort word cards into "s" and "sh" piles. Kids say the first sound before they sort.',
        {
          words: ["sip", "ship", "sell", "shell", "sop", "shop"],
        },
      ),
      S("Read a story they can sound out", 3, "Read it together, then once more with partners.", {
        story: "Dan has a fish. The fish is in a tin. Dan has a shop.".split(" "),
      }),
      S("Quick check", 2, "Point to each word. See how many most of the group can read.", {
        words: ["ship", "shop", "shin", "shed"],
      }),
    ],
  },
  "tricky-words": {
    why: "This group needs the tricky words that cannot be sounded out yet, so we teach a few at a time and use them in reading.",
    steps: (sounds) => [
      S("Warm up the sounds", 2, "Flash each card. Say: Sound?", { sounds }),
      S(
        "Teach two tricky words",
        4,
        'Say the word, point to each letter, and circle the part that is tricky. Start with "a" and "the".',
        {
          words: ["a", "the"],
        },
      ),
      S(
        "Use them",
        4,
        "Read a sentence with the tricky words. Kids point to each word as they read.",
        {
          words: ["a", "the"],
        },
      ),
      S(
        "Read a story they can sound out",
        3,
        "Read it together. Kids tap the tricky words when they see them.",
        {
          story: "Sam had a hat. The hat is in the sand.".split(" "),
        },
      ),
      S("Quick check", 2, "Flash the tricky words. See how many most of the group know."),
    ],
  },
};

export async function getGroupPlan(focus: Skill, sounds: string[]): Promise<GroupPlan> {
  await delay();
  const p = PLANS[focus];
  const steps = p.steps(sounds);
  return {
    example: true,
    minutes: steps.reduce((a, s) => a + s.minutes, 0),
    why: p.why,
    evidence_label: "Very sure",
    research_says: [
      { text: "Review sounds daily and teach one step at a time.", citations: [1] },
      {
        text: "Daily small-group time on a few foundational skills helps students who struggle.",
        citations: [2],
      },
    ],
    steps,
    sources: sources("wwcR2", "rti"),
  };
}

// ---------------------------------------------------------------- Story
const LIBRARY: { title: string; text: string }[] = [
  {
    title: "Sam’s Fish",
    text: "Sam had a fish. The fish is in a tin. Pam had a hat. Sam and Pam sat in the sand.",
  },
  {
    title: "Pam’s Map",
    text: "Pam had a map. Sam had a fan. Pam and Sam sat in the sand. Sam had a tin of fish.",
  },
  {
    title: "Tip and Dan",
    text: "Dan has a tin. Tip has a pin. Dan hid the tin. Tip hid the pin. Dan and Tip sat in the sand.",
  },
  {
    title: "Chip and Dan",
    text: "Chip and Dan chat. Chip has a map. Dan has a hat. Chip and Dan sat in the sand.",
  },
];
let storyIndex = -1;

export async function makeStory(req: StoryRequest): Promise<Story> {
  await delay();
  const known = new Set(req.sounds);
  const missing = (text: string) =>
    text
      .toLowerCase()
      .replace(/[^a-z ]/g, "")
      .split(" ")
      .filter(Boolean)
      .reduce((n, w) => n + (unknownSounds(w, known).length > 0 ? 1 : 0), 0);
  // Prefer a story whose words all use taught sounds; walk on from the last one so "new story" changes it.
  const order = LIBRARY.map((_, i) => (storyIndex + 1 + i) % LIBRARY.length);
  const best = order.reduce((a, b) =>
    missing(LIBRARY[b].text) < missing(LIBRARY[a].text) ? b : a,
  );
  storyIndex = best;
  const s = LIBRARY[best];
  return {
    example: true,
    title: s.title,
    words: s.text.split(" "),
    sources: sources("uk", "wwcR4"),
  };
}

// ---------------------------------------------------------------- Why is a kid stuck?
const PATTERNS = {
  digraph: {
    pattern: 'Reads "sh" as just "s"',
    skill: "Two letters that make one sound (sh)",
    try_it: {
      text: 'Sort cards into "s" and "sh" piles: sip / ship, sell / shell. Have kids say the sound before they sort.',
      minutes: 5,
    },
    also_watch: "Also watch for ch and th.",
    keys: ["wwcR3", "uk"] as Key[],
  },
  blend: {
    pattern: "Leaves out a sound in a word",
    skill: "Hearing every sound in a word",
    try_it: {
      text: "Use sound boxes: one box per sound. Say the word slowly and push a counter for each sound, then add letters.",
      minutes: 5,
    },
    also_watch: "Check two-letter starts like st, tr, and bl.",
    keys: ["wwcR2", "nrp"] as Key[],
  },
  vowel: {
    pattern: "Mixes up the short vowel sound",
    skill: "Short vowel sounds (a, e, i, o, u)",
    try_it: {
      text: "Vowel sort: put bat, bit, but in three piles. Kids say the middle sound before they sort.",
      minutes: 5,
    },
    also_watch: "Say each vowel with its mouth motion.",
    keys: ["wwcR2", "wwcR3"] as Key[],
  },
  guess: {
    pattern: "Guesses from meaning or the picture, not the letters",
    skill: "Looking at every letter",
    try_it: {
      text: "Cover the picture. Point to each letter, say its sound, then blend. Check the picture last.",
      minutes: 5,
    },
    also_watch: "Notice when a wrong word starts with a different letter.",
    keys: ["wwcR3", "uk"] as Key[],
  },
};

export async function diagnoseMistakes(pairs: MistakePair[]): Promise<MistakeResult> {
  await delay();
  const found = pairs
    .map((p) => classifyPair(p.word, p.said))
    .filter((x): x is keyof typeof PATTERNS => !!x);
  if (found.length === 0)
    return {
      example: true,
      kind: "no_match",
      pattern: "",
      skill: "",
      try_it: null,
      also_watch: "",
      evidence_label: "No research found",
      evidence_note: "",
      sources: [],
      message:
        "I can't tell which skill is behind this one yet. Try adding another mistake, or check the word and what the child said.",
    };
  const tally = found.reduce<Record<string, number>>(
    (a, k) => ({ ...a, [k]: (a[k] ?? 0) + 1 }),
    {},
  );
  const top = Object.keys(tally).sort((a, b) => tally[b] - tally[a])[0] as keyof typeof PATTERNS;
  const n = tally[top];
  const p = PATTERNS[top];
  return {
    example: true,
    kind: "match",
    pattern: p.pattern,
    skill: p.skill,
    try_it: p.try_it,
    also_watch: p.also_watch,
    evidence_label: "Very sure",
    evidence_note:
      n >= 3
        ? `${n} mistakes point to the same skill.`
        : `Based on ${plural(n, "mistake")} so far. Add ${3 - n} more to be surer.`,
    sources: sources(...p.keys),
    message: "",
  };
}

// ---------------------------------------------------------------- Training
export const TOPICS: TrainingTopic[] = [
  {
    id: "segmenting",
    title: "Breaking words into sounds",
    summary: "Kids hear a word and say each sound in it.",
    training_word: "segmenting",
    fits: "Fits Group B right now",
  },
  {
    id: "digraphs",
    title: "Two letters, one sound",
    summary: "Teach sh, ch, th as one sound each.",
    training_word: "digraphs",
    fits: "Fits Group A next week",
  },
  {
    id: "letters-not-pictures",
    title: "Look at the letters, not the picture",
    summary: "Help kids check the letters instead of guessing.",
    training_word: "three-cueing",
    fits: "For the whole class",
  },
];

const PLAN_BASE = {
  example: true,
  evidence_label: "Very sure",
} as const;

export async function listTrainingTopics(): Promise<TrainingTopic[]> {
  await delay();
  return TOPICS;
}

export async function getTrainingPlan(topicId: string): Promise<TrainingPlan> {
  await delay();
  const topic = TOPICS.find((t) => t.id === topicId);
  if (!topic) throw new ApiError("We couldn't find that training topic.", 404);
  if (topic.id === "digraphs")
    return {
      ...PLAN_BASE,
      topic,
      remember: {
        sentence: "Two letters can team up to make one sound.",
        sounds: [
          { letter: "sh", hint: '"shh" like quiet' },
          { letter: "ch", hint: '"ch" like a train' },
          { letter: "th", hint: '"th" tongue out' },
        ],
        tip: "Say each digraph as one sound, not two.",
      },
      research_says: [
        {
          text: "Teaching kids to link sounds to letters, and to read word parts, helps them decode words.",
          citations: [1],
        },
      ],
      idea: {
        title: "Team-up cards",
        minutes: 8,
        steps: [
          "Show sh. Say: These two letters team up to make one sound, shhh.",
          "Kids sort word cards into s and sh piles: sip, ship, sell, shell.",
          "Read the words in a list, then in a sentence.",
        ],
        need: "word cards (we'll print them)",
      },
      short_idea: {
        title: "Team-up cards (short)",
        minutes: 4,
        steps: ["Show sh and say its sound.", "Sort four word cards into s and sh piles."],
        need: "four word cards",
      },
      if_stuck: "Start with only sh and two word pairs, like sip and ship.",
      if_easy: "Add ch and read words like chip and chat.",
      for_english_learners:
        "Some English sounds may be new. Show your mouth, go slow, and let them say it with you.",
      sources: sources("wwcR3", "nrp"),
    };
  if (topic.id === "letters-not-pictures")
    return {
      ...PLAN_BASE,
      topic,
      remember: {
        sentence: "Look at every letter, say the sounds, then check the picture.",
        sounds: [
          { letter: "c", hint: '"k" like cat' },
          { letter: "a", hint: '"a" like apple' },
          { letter: "t", hint: '"t" like top' },
        ],
        tip: "Cover the picture first, so the letters do the work.",
      },
      research_says: [
        {
          text: "Students should look at every letter, say its sound, and blend the sounds into the word.",
          citations: [1],
        },
        {
          text: "Beginning readers should not be encouraged to guess words from pictures.",
          citations: [2],
        },
      ],
      idea: {
        title: "Cover and check",
        minutes: 6,
        steps: [
          "Cover the picture. Point to each letter and say its sound.",
          "Blend the sounds into the word.",
          "Uncover the picture to check that the word fits.",
        ],
        need: "a short book or word cards with pictures",
      },
      short_idea: {
        title: "Cover and check (short)",
        minutes: 3,
        steps: ["Cover the picture and sound out one word.", "Uncover it to check."],
        need: "one picture card",
      },
      if_stuck: "Use words with two or three sounds, like cat and pig.",
      if_easy: "Try words with blends, like frog and stop.",
      for_english_learners: "Say the word before covering the picture, so the meaning is clear.",
      sources: sources("wwcR3", "uk"),
    };
  return {
    ...PLAN_BASE,
    topic,
    remember: {
      sentence: "Kids hear a word and say each sound in it.",
      sounds: [
        { letter: "s", hint: '"sss" like snake' },
        { letter: "u", hint: '"uh" like up' },
        { letter: "n", hint: '"nnn" like nose' },
      ],
      tip: 'Tip: hold sounds like "sss" and "nnn." Don’t add "uh" at the end ("suh," "nuh").',
    },
    research_says: [
      {
        text: "Practice hearing the sounds in words, and then matching those sounds to letters, helps young kids learn to read and spell.",
        citations: [1, 2],
      },
    ],
    idea: {
      title: "Tap it out",
      minutes: 8,
      steps: [
        "Show it. Say: Sun. Let’s tap each sound. Tap one finger for each sound: s, u, n.",
        "Do it together. Say a word. Kids tap and say each sound with you. Try: mat, sit, top, fan.",
        "Add letters. Kids push a letter tile into a box for each sound.",
      ],
      need: "sound box sheet (we'll print it) and letter tiles or paper squares",
    },
    short_idea: {
      title: "Tap it out (short)",
      minutes: 4,
      steps: ["Say a word. Kids tap one finger for each sound.", "Do three words: mat, sit, top."],
      need: "just your fingers",
    },
    if_stuck: 'Use 2-sound words first, like "at" and "up."',
    if_easy: 'Try 4-sound words, like "stop" and "jump."',
    for_english_learners:
      "Some English sounds may be new. Show your mouth, go slow, and let them say it with you.",
    sources: sources("wwcR2", "nrp"),
  };
}

export async function getRefresher(): Promise<Refresher> {
  await delay();
  return {
    example: true,
    day: 4,
    statement: "Good readers guess words from pictures and the first letter.",
    is_true: false,
    explanation:
      "Not true. Skilled readers look at every letter in a word. Guessing from pictures keeps kids from learning how letters work.",
    citations: [1, 2],
    sources: sources("wwcR3", "uk"),
    skills: ["Putting sounds together", "Breaking words into sounds", "Tricky words"],
    picked: [
      {
        minutes: 5,
        kind: "with sound clips",
        title: "Saying each sound the right way",
        you_get: "clean sounds, so kids blend faster.",
      },
      {
        minutes: 5,
        kind: "practice out loud",
        title: "Rehearse tomorrow's lesson",
        you_get: "walk in feeling ready, not winging it.",
      },
    ],
  };
}

export async function sendFeedback(fb: Feedback): Promise<void> {
  void fb;
  await sleep(200);
}
