import type { PlayerPublic, StoryState } from "../types";

export function getPlayer(story: StoryState, playerNumber: number): PlayerPublic | undefined {
  return story.players.find((p) => p.player_number === playerNumber);
}

export function getOpponent(story: StoryState, myNumber: number): PlayerPublic | undefined {
  return story.players.find((p) => p.player_number !== myNumber);
}
