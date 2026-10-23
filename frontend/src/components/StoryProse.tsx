import { useEffect, useRef } from "react";

import type { Language, SentencePublic } from "../types";

// Renders the story as flowing prose, color-coded per player. The text
// direction follows the story's own language, not the UI language.
export function StoryProse({
  sentences,
  language,
  highlightTurn,
}: {
  sentences: SentencePublic[];
  language: Language;
  highlightTurn?: number;
}) {
  const endRef = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [sentences.length]);

  const dir = language === "he" ? "rtl" : "ltr";
  const ordered = [...sentences].sort((a, b) => a.position - b.position);

  return (
    <div className="story-prose" dir={dir} lang={language}>
      {ordered.map((s) => (
        <span
          key={s.id}
          className={[
            "seg",
            s.player_number === 1 ? "seg-p1" : "seg-p2",
            highlightTurn && s.turn_number === highlightTurn ? "just-added" : "",
          ].join(" ")}
        >
          {s.text}{" "}
        </span>
      ))}
      <span ref={endRef} />
    </div>
  );
}
