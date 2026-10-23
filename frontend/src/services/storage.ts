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

// Tracks whether the "writer found" intro has already been shown for a story,
// so it appears once (not again after a refresh mid-game).
export function matchedSeen(storyId: string): boolean {
  try {
    return localStorage.getItem(`ayl:matched:${storyId}`) === "1";
  } catch {
    return false;
  }
}

export function markMatchedSeen(storyId: string): void {
  try {
    localStorage.setItem(`ayl:matched:${storyId}`, "1");
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

export function getSavedTheme(): "light" | "dark" | null {
  try {
    const v = localStorage.getItem("ayl:theme");
    return v === "light" || v === "dark" ? v : null;
  } catch {
    return null;
  }
}

export function saveTheme(theme: "light" | "dark"): void {
  try {
    localStorage.setItem("ayl:theme", theme);
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
