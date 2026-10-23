// Thin REST client. All requests are same-origin: in dev Vite proxies /api to
// the backend; in production the backend serves the frontend from one domain.

import type { JoinResponse, Language, Mode, StoryStateResponse } from "../types";

export class ApiError extends Error {
  code: string;
  status: number;
  constructor(code: string, status: number) {
    super(code);
    this.code = code;
    this.status = status;
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`/api${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    let code = "request_failed";
    try {
      const body = await res.json();
      code = typeof body?.code === "string" ? body.code : code;
    } catch {
      /* non-JSON error */
    }
    throw new ApiError(code, res.status);
  }
  return (await res.json()) as T;
}

export const api = {
  createFriendStory(displayName: string, language: Language, totalTurns: number) {
    return request<JoinResponse>("/stories", {
      method: "POST",
      body: JSON.stringify({
        display_name: displayName,
        language,
        total_turns: totalTurns,
        mode: "friend" as Mode,
      }),
    });
  },

  matchRandom(displayName: string, language: Language) {
    // Random mode: the server picks the length, so none is sent.
    return request<JoinResponse>("/matchmaking", {
      method: "POST",
      body: JSON.stringify({ display_name: displayName, language }),
    });
  },

  joinStory(storyId: string, displayName: string) {
    return request<JoinResponse>(`/stories/${storyId}/join`, {
      method: "POST",
      body: JSON.stringify({ display_name: displayName }),
    });
  },

  getStory(storyId: string, token?: string) {
    const qs = token ? `?token=${encodeURIComponent(token)}` : "";
    return request<StoryStateResponse>(`/stories/${storyId}${qs}`);
  },

  submitTurn(storyId: string, token: string, text: string) {
    return request<StoryStateResponse>(`/stories/${storyId}/turns`, {
      method: "POST",
      body: JSON.stringify({ token, text }),
    });
  },

  updateSettings(storyId: string, token: string, totalTurns: number) {
    return request<StoryStateResponse>(`/stories/${storyId}/settings`, {
      method: "POST",
      body: JSON.stringify({ token, total_turns: totalTurns }),
    });
  },

  cancelWaiting(storyId: string, token: string) {
    return request<{ ok: boolean }>(`/stories/${storyId}/cancel`, {
      method: "POST",
      body: JSON.stringify({ token }),
    });
  },
};
