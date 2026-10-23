import type { ReactNode } from "react";
import { Link } from "react-router-dom";

import { useI18n } from "../i18n/I18nContext";
import { LanguageSelector } from "./LanguageSelector";

export function Shell({ children, showLang = true }: { children: ReactNode; showLang?: boolean }) {
  const { t } = useI18n();
  return (
    <div className="app-shell">
      <header className="brand">
        <Link to="/" className="brand-logo">
          <span>✍️</span>
          <span>
            {t("app_name")} <span className="dot-a">·</span>
            <span className="dot-b">·</span>
          </span>
        </Link>
        {showLang && <LanguageSelector />}
      </header>
      {children}
      <div className="footer-note">{t("app_name")} — addyourline.com</div>
    </div>
  );
}
