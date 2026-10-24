// Fetches public gameplay configuration once and caches it.

export interface PublicConfig {
  allowed_turn_counts: number[];
  min_turns: number;
  max_turns: number;
  max_name_length: number;
  max_turn_length: number;
  min_words: number;
  public_base_url: string;
}

const FALLBACK: PublicConfig = {
  allowed_turn_counts: [10, 20, 30],
  min_turns: 2,
  max_turns: 50,
  max_name_length: 40,
  max_turn_length: 600,
  min_words: 4,
  public_base_url: "",
};

let cached: Promise<PublicConfig> | null = null;

export function loadConfig(): Promise<PublicConfig> {
  if (!cached) {
    cached = fetch("/api/config")
      .then((r) => (r.ok ? r.json() : FALLBACK))
      .catch(() => FALLBACK);
  }
  return cached;
}
