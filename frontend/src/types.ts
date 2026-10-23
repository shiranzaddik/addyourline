// Mirrors the backend Pydantic schemas.

export type Language = "en" | "he";
export type Mode = "random" | "friend";
export type Status = "waiting" | "active" | "completed";

export interface PlayerPublic {
  id: string;
  display_name: string;
  player_number: number;
}

export interface SentencePublic {
  id: number;
  player_id: string;
  player_number: number;
  position: number;
  turn_number: number;
  text: string;
}

export interface StoryState {
  id: string;
  language: Language;
  mode: Mode;
  total_turns: number;
  current_turn: number;
  status: Status;
  active_player_number: number | null;
  players: PlayerPublic[];
  sentences: SentencePublic[];
  created_at: string;
  completed_at: string | null;
  invite_url: string;
  share_url: string;
  continuation_hint: string;
}

export interface JoinResponse {
  token: string;
  player: PlayerPublic;
  story: StoryState;
}

export interface StoryStateResponse {
  story: StoryState;
  you: PlayerPublic | null;
}

// WebSocket message shapes.
export interface StateMessage {
  type: "state";
  event: string;
  story: StoryState;
  submitted_turn?: number;
}

export interface PresenceMessage {
  type: "presence";
  event: string;
  player_number: number;
}

export type SocketMessage = StateMessage | PresenceMessage;
