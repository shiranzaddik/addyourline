import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { ShareButtons } from "../components/ShareButtons";
import { Shell } from "../components/Shell";
import { StoryProse } from "../components/StoryProse";
import { useI18n } from "../i18n/I18nContext";
import { api } from "../services/api";
import { getSession } from "../services/storage";
import type { StoryState } from "../types";

export function CompletedPage() {
  const { storyId } = useParams<{ storyId: string }>();
  const navigate = useNavigate();
  const { t } = useI18n();

  const [story, setStory] = useState<StoryState | null>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "notready" | "notfound">("loading");

  useEffect(() => {
    if (!storyId) return;
    api
      .getStory(storyId)
      .then((r) => {
        if (r.story.status === "completed") {
          setStory(r.story);
          setStatus("ready");
        } else if (getSession(storyId)) {
          // A participant arrived early — send them to the live game.
          navigate(`/play/${storyId}`, { replace: true });
        } else {
          setStatus("notready");
        }
      })
      .catch(() => setStatus("notfound"));
  }, [storyId, navigate]);

  if (status === "loading") {
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

  if (status !== "ready" || !story) {
    return (
      <Shell>
        <div className="centered">
          <div className="card stack text-center fade-in">
            <div className="banner banner-error">{t("story_not_found")}</div>
            <button className="btn btn-primary" onClick={() => navigate("/")}>
              {t("back_home")}
            </button>
          </div>
        </div>
      </Shell>
    );
  }

  const p1 = story.players.find((p) => p.player_number === 1)?.display_name ?? "Player 1";
  const p2 = story.players.find((p) => p.player_number === 2)?.display_name ?? "Player 2";

  return (
    <Shell>
      <div className="stack fade-in" style={{ gap: 18 }}>
        <div className="text-center stack" style={{ gap: 6 }}>
          <div style={{ fontSize: "2.4rem" }}>🎉</div>
          <h1 className="hero-title" style={{ fontSize: "clamp(1.8rem, 6vw, 2.6rem)" }}>
            {t("story_ready")}
          </h1>
          <p className="hero-sub">{t("written_by", { a: p1, b: p2 })}</p>
          <div className="player-pills" style={{ justifyContent: "center" }}>
            <span className="pill pill-p1">
              <span className="swatch" />
              {p1}
            </span>
            <span className="pill pill-p2">
              <span className="swatch" />
              {p2}
            </span>
          </div>
        </div>

        <div className="card story-paper">
          <StoryProse sentences={story.sentences} language={story.language} />
        </div>

        <div className="card stack">
          <strong>{t("share_story")}</strong>
          <ShareButtons url={story.share_url} message={t("completed_share_message")} variant="story" />
        </div>

        <button className="btn btn-primary btn-lg btn-block" onClick={() => navigate("/")}>
          {t("write_another")}
        </button>
      </div>
    </Shell>
  );
}
