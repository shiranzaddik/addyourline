import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { ShareButtons } from "../components/ShareButtons";
import { Shell } from "../components/Shell";
import { StoryProse } from "../components/StoryProse";
import { useI18n } from "../i18n/I18nContext";
import { useGameSocket } from "../hooks/useGameSocket";
import { api, ApiError } from "../services/api";
import { loadConfig, type PublicConfig } from "../services/config";
import { clearSession, getSession } from "../services/storage";
import type { SocketMessage, StoryState } from "../types";
import { getOpponent } from "../utils/players";
import { countSentences } from "../utils/sentences";

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
  const [highlightTurn, setHighlightTurn] = useState<number | undefined>();
  const [cfg, setCfg] = useState<PublicConfig | null>(null);

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
        if (msg.event === "turn_submitted" && msg.submitted_turn) {
          setHighlightTurn(msg.submitted_turn);
        }
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

        {story.sentences.length > 0 && (
          <div className="card stack">
            <strong className="muted">{t("the_story_so_far")}</strong>
            <div className="story-scroll">
              <StoryProse
                sentences={story.sentences}
                language={story.language}
                highlightTurn={highlightTurn}
              />
            </div>
          </div>
        )}

        {myTurn ? (
          <div className="card stack">
            <strong>{story.current_turn === 1 ? t("write_to_start") : t("continue_story")}</strong>
            <textarea
              className="text-input"
              value={text}
              maxLength={maxLen}
              placeholder={story.language === "he" ? "…כתבו כאן" : "Write here…"}
              dir={story.language === "he" ? "rtl" : "ltr"}
              onChange={(e) => setText(e.target.value)}
              autoFocus
            />
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
