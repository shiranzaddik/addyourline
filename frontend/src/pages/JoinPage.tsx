import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { Shell } from "../components/Shell";
import { useI18n } from "../i18n/I18nContext";
import { api, ApiError } from "../services/api";
import { getSavedName, getSession, saveName, saveSession } from "../services/storage";
import type { StoryState } from "../types";

type View = "loading" | "join" | "full" | "notfound";

export function JoinPage() {
  const { storyId } = useParams<{ storyId: string }>();
  const navigate = useNavigate();
  const { t, tError } = useI18n();

  const [view, setView] = useState<View>("loading");
  const [story, setStory] = useState<StoryState | null>(null);
  const [name, setName] = useState(getSavedName());
  const [joining, setJoining] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!storyId) return;
    // Already a player in this story → resume.
    if (getSession(storyId)) {
      navigate(`/play/${storyId}`, { replace: true });
      return;
    }
    api
      .getStory(storyId)
      .then((r) => {
        if (r.story.status === "completed") {
          navigate(`/story/${storyId}`, { replace: true });
          return;
        }
        setStory(r.story);
        // Joinable only if waiting with a single player.
        setView(r.story.status === "waiting" && r.story.players.length < 2 ? "join" : "full");
      })
      .catch(() => setView("notfound"));
  }, [storyId, navigate]);

  const join = async () => {
    if (!storyId || !name.trim()) {
      setError(t("enter_name_first"));
      return;
    }
    setError(null);
    setJoining(true);
    try {
      const res = await api.joinStory(storyId, name.trim());
      saveName(name.trim());
      saveSession({
        storyId: res.story.id,
        token: res.token,
        playerNumber: res.player.player_number,
        displayName: res.player.display_name,
      });
      navigate(`/play/${res.story.id}`, { replace: true });
    } catch (e) {
      setError(e instanceof ApiError ? tError(e.code) : t("err_request_failed"));
      setJoining(false);
    }
  };

  const hostName = story?.players[0]?.display_name ?? "";

  return (
    <Shell>
      <div className="centered">
        {view === "loading" && (
          <div className="waiting-wrap">
            <div className="dots">
              <span />
              <span />
              <span />
            </div>
            <p className="muted">{t("loading")}</p>
          </div>
        )}

        {view === "join" && (
          <div className="card stack fade-in">
            <div className="text-center stack" style={{ gap: 4 }}>
              <h1 className="hero-title" style={{ fontSize: "2rem" }}>
                {t("join_title")}
              </h1>
              {hostName && <p className="hero-sub">{t("join_sub", { name: hostName })}</p>}
            </div>
            <div>
              <label className="field-label" htmlFor="join-name">
                {t("your_name")}
              </label>
              <input
                id="join-name"
                className="text-input"
                value={name}
                maxLength={40}
                placeholder={t("name_placeholder")}
                onChange={(e) => setName(e.target.value)}
              />
            </div>
            {error && <div className="banner banner-error">{error}</div>}
            <button className="btn btn-green btn-lg btn-block" disabled={joining} onClick={join}>
              {joining ? t("loading") : t("join_button")}
            </button>
          </div>
        )}

        {view === "full" && (
          <div className="card stack text-center fade-in">
            <div className="banner banner-warn">{t("game_full")}</div>
            <button className="btn btn-primary" onClick={() => navigate("/")}>
              {t("back_home")}
            </button>
          </div>
        )}

        {view === "notfound" && (
          <div className="card stack text-center fade-in">
            <div className="banner banner-error">{t("story_not_found")}</div>
            <button className="btn btn-primary" onClick={() => navigate("/")}>
              {t("back_home")}
            </button>
          </div>
        )}
      </div>
    </Shell>
  );
}
