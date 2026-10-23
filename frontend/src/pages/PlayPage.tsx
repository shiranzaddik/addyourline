import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { ShareButtons } from "../components/ShareButtons";
import { Shell } from "../components/Shell";
import { useI18n } from "../i18n/I18nContext";
import { useGameSocket } from "../hooks/useGameSocket";
import { api, ApiError } from "../services/api";
import { loadConfig, type PublicConfig } from "../services/config";
import { clearSession, getSession, markMatchedSeen, matchedSeen } from "../services/storage";
import type { SocketMessage, StoryState } from "../types";
import { getOpponent } from "../utils/players";
import { countSentences, handoffHint } from "../utils/sentences";

export function PlayPage() {
  const { storyId } = useParams<{ storyId: string }>();
  const navigate = useNavigate();
  const { t, tError } = useI18n();

  const session = useMemo(() => (storyId ? getSession(storyId) : null), [storyId]);

  const [story, setStory] = useState<StoryState | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [text, setText] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [presence, setPresence] = useState<{ kind: "warn" | "info"; msg: string } | null>(null);
  const [cfg, setCfg] = useState<PublicConfig | null>(null);
  const [matchedAck, setMatchedAck] = useState(() => (storyId ? matchedSeen(storyId) : false));
  const [customLen, setCustomLen] = useState("");
  const [settingsError, setSettingsError] = useState<string | null>(null);

  // No local session for this story → send to the join landing.
  useEffect(() => {
    if (storyId && !session) navigate(`/${storyId}`, { replace: true });
  }, [storyId, session, navigate]);

  useEffect(() => {
    loadConfig().then(setCfg);
  }, []);

  // Initial authoritative state load.
  useEffect(() => {
    if (!storyId || !session) return;
    api
      .getStory(storyId, session.token)
      .then((r) => setStory(r.story))
      .catch((e) =>
        setLoadError(e instanceof ApiError ? tError(e.code) : t("err_request_failed"))
      );
  }, [storyId, session, t, tError]);

  const onMessage = useCallback(
    (msg: SocketMessage) => {
      if (msg.type === "state") {
        setStory(msg.story);
      } else if (msg.type === "presence" && session) {
        if (msg.player_number === session.playerNumber) return; // ignore self
        const oppName = story ? getOpponent(story, session.playerNumber)?.display_name : undefined;
        const name = oppName ?? "…";
        if (msg.event === "player_disconnected") {
          setPresence({ kind: "warn", msg: t("disconnected_banner", { name }) });
        } else if (msg.event === "player_reconnected") {
          setPresence({ kind: "info", msg: t("reconnected_banner", { name }) });
          setTimeout(() => setPresence(null), 4000);
        }
      }
    },
    [session, story, t]
  );

  const socketStatus = useGameSocket(storyId, session?.token, onMessage);

  // When the story completes, move everyone to the public read-only view.
  useEffect(() => {
    if (story?.status === "completed" && storyId) {
      navigate(`/story/${storyId}`, { replace: true });
    }
  }, [story?.status, storyId, navigate]);

  // Show the "writer found" intro briefly, then start the game automatically.
  useEffect(() => {
    if (
      story &&
      story.status === "active" &&
      !matchedAck &&
      story.current_turn === 1 &&
      story.sentences.length === 0
    ) {
      const timer = setTimeout(() => {
        if (storyId) markMatchedSeen(storyId);
        setMatchedAck(true);
      }, 2200);
      return () => clearTimeout(timer);
    }
  }, [story, matchedAck, storyId]);

  if (!session) return null;

  if (loadError) {
    return (
      <Shell>
        <div className="centered">
          <div className="card stack text-center">
            <div className="banner banner-error">{loadError}</div>
            <button className="btn btn-primary" onClick={() => navigate("/")}>
              {t("back_home")}
            </button>
          </div>
        </div>
      </Shell>
    );
  }

  if (!story) {
    return (
      <Shell>
        <div className="centered">
          <div className="waiting-wrap">
            <div className="dots">
              <span />
              <span />
              <span />
            </div>
            <p className="muted">{t("loading")}</p>
          </div>
        </div>
      </Shell>
    );
  }

  const me = session.playerNumber;
  const opponent = getOpponent(story, me);
  const oppName = opponent?.display_name;
  const maxLen = cfg?.max_turn_length ?? 600;

  // ---- Waiting room ----
  if (story.status === "waiting") {
    const cancel = async () => {
      try {
        await api.cancelWaiting(story.id, session.token);
      } catch {
        /* ignore */
      }
      clearSession(story.id);
      navigate("/");
    };

    const presets = cfg?.allowed_turn_counts ?? [10, 20, 30];
    const minT = cfg?.min_turns ?? 2;
    const maxT = cfg?.max_turns ?? 50;
    const changeTurns = async (n: number) => {
      try {
        const r = await api.updateSettings(story.id, session.token, n);
        setStory(r.story);
        setSettingsError(null);
      } catch (e) {
        setSettingsError(e instanceof ApiError ? tError(e.code) : t("err_request_failed"));
      }
    };
    const applyCustom = () => {
      const n = parseInt(customLen, 10);
      if (!Number.isInteger(n) || n < minT || n > maxT) {
        setSettingsError(t("turns_range_hint", { min: minT, max: maxT }));
        return;
      }
      changeTurns(n);
    };

    return (
      <Shell>
        <div className="centered">
          <div className="card stack fade-in">
            <div className="waiting-wrap">
              <div className="pen">✍️</div>
              <h2 className="hero-title" style={{ fontSize: "1.8rem" }}>
                {story.mode === "friend" ? t("waiting_for_friend") : t("waiting_for_writer")}
              </h2>
              <div className="dots">
                <span />
                <span />
                <span />
              </div>
            </div>

            {story.mode === "friend" ? (
              <div className="stack">
                <div>
                  <label className="field-label">
                    {t("choose_length")} · {story.total_turns} {t("turns_suffix")}
                  </label>
                  <div className="segmented">
                    {presets.map((n) => (
                      <button
                        key={n}
                        type="button"
                        className={story.total_turns === n ? "active" : ""}
                        onClick={() => changeTurns(n)}
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
                      placeholder={`${minT}–${maxT}`}
                      value={customLen}
                      onChange={(e) => setCustomLen(e.target.value)}
                    />
                    <button className="btn btn-ghost" type="button" onClick={applyCustom}>
                      {t("set_length")}
                    </button>
                  </div>
                  {settingsError && (
                    <div className="banner banner-error" style={{ marginTop: 8 }}>
                      {settingsError}
                    </div>
                  )}
                </div>

                <div className="row-between">
                  <strong>{t("invite_a_friend")}</strong>
                </div>
                <p className="muted" style={{ margin: 0 }}>
                  {t("invite_hint")}
                </p>
                <ShareButtons
                  url={story.invite_url}
                  message={t("invite_message")}
                  includeCopyField
                  variant="invite"
                />
              </div>
            ) : (
              <p className="muted text-center">{t("waiting_hint")}</p>
            )}

            <button className="btn btn-ghost btn-block" onClick={cancel}>
              {t("cancel")}
            </button>
          </div>
        </div>
      </Shell>
    );
  }

  // ---- "Writer found" intro (shown once, when the game first becomes active) ----
  if (
    story.status === "active" &&
    !matchedAck &&
    story.current_turn === 1 &&
    story.sentences.length === 0
  ) {
    const i1 = story.players.find((p) => p.player_number === 1);
    const i2 = story.players.find((p) => p.player_number === 2);
    return (
      <Shell>
        <div className="centered">
          <div className="card stack text-center fade-in">
            <div style={{ fontSize: "2.6rem" }}>🤝</div>
            <h1 className="hero-title" style={{ fontSize: "2rem" }}>
              {t("writer_found")}
            </h1>
            {oppName && <p className="hero-sub">{t("matched_with", { name: oppName })}</p>}
            <div className="player-pills" style={{ justifyContent: "center" }}>
              {i1 && (
                <span className="pill pill-p1">
                  <span className="swatch" />
                  {i1.display_name}
                  {me === 1 ? ` (${t("you_label")})` : ""}
                </span>
              )}
              {i2 && (
                <span className="pill pill-p2">
                  <span className="swatch" />
                  {i2.display_name}
                  {me === 2 ? ` (${t("you_label")})` : ""}
                </span>
              )}
            </div>
            <p className="muted">{t("matched_hint")}</p>
            <div className="dots">
              <span />
              <span />
              <span />
            </div>
          </div>
        </div>
      </Shell>
    );
  }

  // ---- Active game ----
  const myTurn = story.active_player_number === me;
  const activeIsP2 = story.active_player_number === 2;
  const completedTurns = story.current_turn - 1;
  const progressPct = Math.round((completedTurns / story.total_turns) * 100);
  const liveCount = countSentences(text);
  const canSubmit = liveCount === 2 && text.length <= maxLen && !submitting;

  const submit = async () => {
    if (!canSubmit) return;
    setSubmitError(null);
    setSubmitting(true);
    try {
      const r = await api.submitTurn(story.id, session.token, text.trim());
      setStory(r.story);
      setText("");
    } catch (e) {
      setSubmitError(e instanceof ApiError ? tError(e.code) : t("err_request_failed"));
    } finally {
      setSubmitting(false);
    }
  };

  const p1 = story.players.find((p) => p.player_number === 1);
  const p2 = story.players.find((p) => p.player_number === 2);

  return (
    <Shell>
      <div className="stack fade-in" style={{ gap: 16 }}>
        <div className="card stack">
          <div className="row-between">
            <span className={`turn-badge ${activeIsP2 ? "is-p2" : ""}`}>
              {t("turn_indicator", { current: story.current_turn, total: story.total_turns })}
            </span>
            <div className="player-pills">
              {p1 && (
                <span className="pill pill-p1">
                  <span className="swatch" />
                  {p1.display_name}
                  {me === 1 ? ` (${t("you_label")})` : ""}
                </span>
              )}
              {p2 && (
                <span className="pill pill-p2">
                  <span className="swatch" />
                  {p2.display_name}
                  {me === 2 ? ` (${t("you_label")})` : ""}
                </span>
              )}
            </div>
          </div>
          <div className="progress">
            <span style={{ width: `${progressPct}%` }} />
          </div>
          {socketStatus !== "open" && <div className="muted text-center">{t("connection_lost")}</div>}
        </div>

        {presence && (
          <div className={`banner ${presence.kind === "warn" ? "banner-warn" : "banner-info"}`}>
            {presence.msg}
          </div>
        )}

        {myTurn ? (
          <div className="card stack">
            <div>
              <strong>{story.current_turn === 1 ? t("write_to_start") : t("continue_story")}</strong>
              <p className="muted" style={{ margin: "6px 0 0", fontSize: "0.88rem" }}>
                {t("blind_hint")}
              </p>
            </div>
            {story.continuation_hint && (
              <div className="handoff-lead">
                <span className="handoff-label">{t("continue_from")}</span>
                <span className="handoff-chip" dir={story.language === "he" ? "rtl" : "ltr"}>
                  …{story.continuation_hint}
                </span>
              </div>
            )}
            <textarea
              className="text-input"
              value={text}
              maxLength={maxLen}
              placeholder={story.language === "he" ? "…כתבו כאן" : "Write here…"}
              dir={story.language === "he" ? "rtl" : "ltr"}
              onChange={(e) => setText(e.target.value)}
              autoFocus
            />
            {text.trim() && (
              <div className="handoff-out">
                <span className="muted">{t("partner_will_see")}</span>
                <span className="handoff-chip" dir={story.language === "he" ? "rtl" : "ltr"}>
                  {handoffHint(text) || "…"}
                </span>
              </div>
            )}
            <div className="row-between">
              <span className="muted" style={{ fontSize: "0.85rem" }}>
                {text.trim() && liveCount !== 2 ? t("two_sentences_rule") : ""}
              </span>
              <span className="char-count">
                {text.length}/{maxLen}
              </span>
            </div>
            {submitError && <div className="banner banner-error">{submitError}</div>}
            <button
              className={`btn btn-lg btn-block ${me === 2 ? "btn-green" : "btn-primary"}`}
              disabled={!canSubmit}
              onClick={submit}
            >
              {submitting
                ? t("sending")
                : t("send_to", { name: oppName ?? (story.language === "he" ? "השותף" : "partner") })}
            </button>
          </div>
        ) : (
          <div className="card">
            <div className="waiting-wrap">
              <div className="pen">✍️</div>
              <h3 style={{ margin: 0 }}>{t("waiting_for", { name: oppName ?? "…" })}</h3>
              <div className="dots">
                <span />
                <span />
                <span />
              </div>
            </div>
          </div>
        )}
      </div>
    </Shell>
  );
}
