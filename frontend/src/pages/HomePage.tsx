import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { Shell } from "../components/Shell";
import { useI18n } from "../i18n/I18nContext";
import { api, ApiError } from "../services/api";
import { loadConfig } from "../services/config";
import { getSavedName, saveName, saveSession } from "../services/storage";
import type { JoinResponse } from "../types";

export function HomePage() {
  const { t, tError, lang } = useI18n();
  const navigate = useNavigate();

  const [name, setName] = useState(getSavedName());
  const [turnOptions, setTurnOptions] = useState<number[]>([10, 20, 30]);
  const [turns, setTurns] = useState(10);
  const [busy, setBusy] = useState<"friend" | "random" | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadConfig().then((c) => {
      setTurnOptions(c.allowed_turn_counts);
      if (!c.allowed_turn_counts.includes(turns)) setTurns(c.allowed_turn_counts[0]);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const afterJoin = (res: JoinResponse) => {
    saveName(name.trim());
    saveSession({
      storyId: res.story.id,
      token: res.token,
      playerNumber: res.player.player_number,
      displayName: res.player.display_name,
    });
    navigate(`/play/${res.story.id}`);
  };

  const begin = async (mode: "friend" | "random") => {
    setError(null);
    if (!name.trim()) {
      setError(t("enter_name_first"));
      return;
    }
    setBusy(mode);
    try {
      const res =
        mode === "friend"
          ? await api.createFriendStory(name.trim(), lang, turns)
          : await api.matchRandom(name.trim(), lang, turns);
      afterJoin(res);
    } catch (e) {
      setError(e instanceof ApiError ? tError(e.code) : t("err_request_failed"));
      setBusy(null);
    }
  };

  return (
    <Shell>
      <div className="centered">
        <div className="text-center stack" style={{ gap: 6 }}>
          <h1 className="hero-title">{t("app_name")}</h1>
          <p className="hero-sub">{t("tagline")}</p>
        </div>

        <div className="card stack fade-in">
          <div>
            <label className="field-label" htmlFor="name">
              {t("your_name")}
            </label>
            <input
              id="name"
              className="text-input"
              value={name}
              maxLength={40}
              placeholder={t("name_placeholder")}
              onChange={(e) => setName(e.target.value)}
            />
          </div>

          <div>
            <label className="field-label">{t("number_of_turns")}</label>
            <div className="segmented">
              {turnOptions.map((n) => (
                <button
                  key={n}
                  type="button"
                  className={turns === n ? "active" : ""}
                  onClick={() => setTurns(n)}
                >
                  {n} {t("turns_suffix")}
                </button>
              ))}
            </div>
          </div>

          {error && <div className="banner banner-error">{error}</div>}

          <div className="mode-grid">
            <button
              type="button"
              className="mode-tile is-random"
              disabled={busy !== null}
              onClick={() => begin("random")}
            >
              <span className="mode-emoji">🎲</span>
              <span className="mode-title">{t("play_with_random")}</span>
              <span className="mode-sub">
                {busy === "random" ? t("loading") : t("play_with_random_sub")}
              </span>
            </button>
            <button
              type="button"
              className="mode-tile is-friend"
              disabled={busy !== null}
              onClick={() => begin("friend")}
            >
              <span className="mode-emoji">💌</span>
              <span className="mode-title">{t("play_with_friend")}</span>
              <span className="mode-sub">
                {busy === "friend" ? t("loading") : t("play_with_friend_sub")}
              </span>
            </button>
          </div>
        </div>
      </div>
    </Shell>
  );
}
