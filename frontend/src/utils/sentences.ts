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
