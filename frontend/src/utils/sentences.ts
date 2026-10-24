// Client-side contribution validation: at least N words. The backend remains
// authoritative. \p{L}/\p{N} are used because JS \w is ASCII-only (excludes Hebrew).

const WORD_CHAR_RE = /[\p{L}\p{N}]/u;

export function countWords(text: string): number {
  return text
    .trim()
    .split(/\s+/)
    .filter((w) => WORD_CHAR_RE.test(w)).length;
}

export function isValidContribution(text: string, maxLength: number, minWords: number): boolean {
  if (text.length > maxLength) return false;
  return countWords(text) >= minWords;
}
