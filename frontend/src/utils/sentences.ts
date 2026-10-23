// Client-side mirror of the backend sentence counter, for instant feedback.
// The backend remains authoritative.

const TERMINALS = ".!?…！？。";
const escaped = TERMINALS.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
const SENTENCE_RE = new RegExp(`[^${escaped}]*[${escaped}]+`, "g");
const HAS_WORD_RE = /[^\W\d_]|\d/u;

// Returns the number of terminated sentences, or -1 if there is trailing
// unterminated text (i.e. a sentence missing its final punctuation).
export function countSentences(text: string): number {
  const stripped = text.trim();
  if (!stripped) return 0;
  const matches = stripped.match(SENTENCE_RE) ?? [];
  const consumed = matches.join("");
  if (consumed.trim() !== stripped) return -1;
  return matches.filter((m) => m.trim() && HAS_WORD_RE.test(m)).length;
}

export function isValidContribution(text: string, maxLength: number): boolean {
  if (text.trim().length === 0 || text.length > maxLength) return false;
  return countSentences(text) === 2;
}

// The last N words of some text (the handoff passed to the next writer).
export function lastWords(text: string, count = 2): string {
  const words = text.trim().split(/\s+/).filter(Boolean);
  return words.slice(-count).join(" ");
}

// The exact handoff the partner receives: the last 2 words of the LAST
// sentence (mirrors the backend). Falls back to the last 2 words of the raw
// text while the second sentence is still being typed.
export function handoffHint(text: string): string {
  const stripped = text.trim();
  const matches = stripped.match(SENTENCE_RE) ?? [];
  const sentences = matches.map((m) => m.trim()).filter(Boolean);
  const last = sentences.length ? sentences[sentences.length - 1] : stripped;
  return lastWords(last, 2);
}
