import type { ReactNode } from "react";
import { Link } from "react-router-dom";

import { useI18n } from "../i18n/I18nContext";
import { LanguageSelector } from "./LanguageSelector";

export function Shell({ children, showLang = true }: { children: ReactNode; showLang?: boolean }) {
  const { t } = useI18n();
  return (
    <div className="app-shell">
      <header className="brand">
        <Link to="/" className="brand-lockup-link" aria-label="Add Your Line">
          <img src="/logo.png" alt="Add Your Line" className="brand-img" />
        </Link>
        {showLang && <LanguageSelector />}
      </header>
      {children}
      <div className="footer-note">{t("app_name")} — addyourline.com</div>
    </div>
  );
}
