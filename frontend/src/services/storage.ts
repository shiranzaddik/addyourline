// Local persistence of per-story player sessions and user preferences.
// Lets a player refresh or reconnect without losing their identity.

import type { Language } from "../types";

export interface StorySession {
  storyId: string;
  token: string;
  playerNumber: number;
  displayName: string;
}

const sessionKey = (storyId: string) => `ayl:session:${storyId}`;
const NAME_KEY = "ayl:name";
const LANG_KEY = "ayl:lang";

export function saveSession(session: StorySession): void {
  try {
    localStorage.setItem(sessionKey(session.storyId), JSON.stringify(session));
  } catch {
    /* storage unavailable (private mode) — session simply won't persist */
  }
}

export function getSession(storyId: string): StorySession | null {
  try {
    const raw = localStorage.getItem(sessionKey(storyId));
    return raw ? (JSON.parse(raw) as StorySession) : null;
  } catch {
    return null;
  }
}

export function clearSession(storyId: string): void {
  try {
    localStorage.removeItem(sessionKey(storyId));
  } catch {
    /* ignore */
  }
}

export function getSavedName(): string {
  try {
    return localStorage.getItem(NAME_KEY) ?? "";
  } catch {
    return "";
  }
}

export function saveName(name: string): void {
  try {
    localStorage.setItem(NAME_KEY, name);
  } catch {
    /* ignore */
  }
}

export function getSavedLang(): Language | null {
  try {
    const v = localStorage.getItem(LANG_KEY);
    return v === "en" || v === "he" ? v : null;
  } catch {
    return null;
  }
}

export function saveLang(lang: Language): void {
  try {
    localStorage.setItem(LANG_KEY, lang);
  } catch {
    /* ignore */
  }
}
