import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { Shell } from "../components/Shell";
import { useI18n } from "../i18n/I18nContext";
import { api, ApiError } from "../services/api";
import { loadConfig, type PublicConfig } from "../services/config";
import { saveSession } from "../services/storage";
import type { JoinResponse } from "../types";

// Default story length, used for the computer game and as the starting length
// for a friend game (the creator can still change a friend game on the next
// screen before their friend joins). Random games get a server-chosen length.
const DEFAULT_TURNS = 10;

export function HomePage() {
  const { t, tError, lang } = useI18n();
  const navigate = useNavigate();

  const [name, setName] = useState("");
  const [busy, setBusy] = useState<"friend" | "random" | "bot" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [cfg, setCfg] = useState<PublicConfig | null>(null);
  const [turns, setTurns] = useState(DEFAULT_TURNS);
  const [customLen, setCustomLen] = useState("");

  useEffect(() => {
    loadConfig().then(setCfg);
  }, []);

  const presets = cfg?.allowed_turn_counts ?? [10, 20, 30];
  const minT = cfg?.min_turns ?? 2;
  const maxT = cfg?.max_turns ?? 50;

  const pickPreset = (n: number) => {
    setTurns(n);
    setCustomLen("");
  };
  const onCustom = (v: string) => {
    setCustomLen(v);
    const n = parseInt(v, 10);
    if (Number.isInteger(n) && n >= minT && n <= maxT) setTurns(n);
  };

  const afterJoin = (res: JoinResponse) => {
    saveSession({
      storyId: res.story.id,
      token: res.token,
      playerNumber: res.player.player_number,
      displayName: res.player.display_name,
    });
    navigate(`/play/${res.story.id}`);
  };

  const begin = async (mode: "friend" | "random" | "bot") => {
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
          : mode === "bot"
            ? await api.playVsComputer(name.trim(), lang, turns)
            : await api.matchRandom(name.trim(), lang);
      afterJoin(res);
    } catch (e) {
      setError(e instanceof ApiError ? tError(e.code) : t("err_request_failed"));
      setBusy(null);
    }
  };

  return (
    <Shell>
      <div className="centered">
        <div className="text-center stack" style={{ gap: 8 }}>
          <h1 className="hero-title">{t("home_headline")}</h1>
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
            <label className="field-label">
              {t("choose_length")} · {turns} {t("turns_suffix")}
            </label>
            <div className="segmented">
              {presets.map((n) => (
                <button
                  key={n}
                  type="button"
                  className={turns === n && !customLen ? "active" : ""}
                  onClick={() => pickPreset(n)}
                >
                  {n}
                </button>
              ))}
            </div>
            <div className="link-field" style={{ marginTop: 10 }}>
              <input
                className="text-input"
                type="number"
                inputMode="numeric"
                min={minT}
                max={maxT}
                placeholder={t("custom_turns_label", { min: minT, max: maxT })}
                value={customLen}
                onChange={(e) => onCustom(e.target.value)}
              />
            </div>
            <p className="muted" style={{ margin: "8px 0 0", fontSize: "0.85rem" }}>
              {t("length_applies_hint")}
            </p>
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
            <button
              type="button"
              className="mode-tile is-bot"
              disabled={busy !== null}
              onClick={() => begin("bot")}
            >
              <span className="mode-emoji">🤖</span>
              <span className="mode-title">{t("play_with_computer")}</span>
              <span className="mode-sub">
                {busy === "bot" ? t("loading") : t("play_with_computer_sub")}
              </span>
            </button>
          </div>
        </div>
      </div>
    </Shell>
  );
}
