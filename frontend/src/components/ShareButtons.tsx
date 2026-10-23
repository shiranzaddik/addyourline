import { useState } from "react";

import { useI18n } from "../i18n/I18nContext";

interface Props {
  url: string;
  message: string;
  includeCopyField?: boolean;
  variant?: "invite" | "story";
}

// Share actions: copy link, WhatsApp, Facebook, X/Twitter, native share.
export function ShareButtons({ url, message, includeCopyField, variant = "story" }: Props) {
  const { t } = useI18n();
  const [copied, setCopied] = useState(false);

  const fullText = `${message}${url}`;
  const canNativeShare = typeof navigator !== "undefined" && !!navigator.share;

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(url);
    } catch {
      // Fallback for insecure contexts.
      const el = document.createElement("textarea");
      el.value = url;
      document.body.appendChild(el);
      el.select();
      try {
        document.execCommand("copy");
      } catch {
        /* ignore */
      }
      document.body.removeChild(el);
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 1800);
  };

  const openShare = (shareUrl: string) =>
    window.open(shareUrl, "_blank", "noopener,noreferrer,width=600,height=500");

  const whatsapp = () => openShare(`https://wa.me/?text=${encodeURIComponent(fullText)}`);
  const facebook = () =>
    openShare(`https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(url)}`);
  const twitter = () =>
    openShare(
      `https://twitter.com/intent/tweet?text=${encodeURIComponent(message)}&url=${encodeURIComponent(url)}`
    );
  const nativeShare = async () => {
    try {
      await navigator.share({ title: t("app_name"), text: message, url });
    } catch {
      /* user dismissed */
    }
  };

  return (
    <div className="stack">
      {includeCopyField && (
        <div className="link-field">
          <input className="text-input" readOnly value={url} onFocus={(e) => e.target.select()} />
          <button className="btn btn-primary" type="button" onClick={copy}>
            {copied ? t("copied") : t("copy_link")}
          </button>
        </div>
      )}
      <div className="share-row">
        {!includeCopyField && (
          <button className="btn btn-ghost" type="button" onClick={copy}>
            {copied ? t("copied") : variant === "story" ? t("copy_story_link") : t("copy_link")}
          </button>
        )}
        <button className="btn chip-wa" type="button" onClick={whatsapp}>
          {t("share_whatsapp")}
        </button>
        <button className="btn chip-fb" type="button" onClick={facebook}>
          {t("share_facebook")}
        </button>
        {variant === "story" && (
          <button className="btn chip-x" type="button" onClick={twitter}>
            {t("share_x")}
          </button>
        )}
        {canNativeShare && (
          <button className="btn btn-ghost" type="button" onClick={nativeShare}>
            {t("share_native")}
          </button>
        )}
      </div>
    </div>
  );
}
