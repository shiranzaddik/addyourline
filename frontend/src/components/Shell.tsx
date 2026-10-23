import type { ReactNode } from "react";
import { Link } from "react-router-dom";

import { useI18n } from "../i18n/I18nContext";
import { useTheme } from "../theme/ThemeContext";
import { LanguageSelector } from "./LanguageSelector";
import { ThemeToggle } from "./ThemeToggle";

export function Shell({ children, showLang = true }: { children: ReactNode; showLang?: boolean }) {
  const { t } = useI18n();
  const { theme } = useTheme();
  const wideLogo = theme === "dark" ? "/logo-dark.png" : "/logo.png";
  const iconLogo = theme === "dark" ? "/icon-dark.png" : "/icon.png";
  return (
    <div className="app-shell">
      <header className="brand">
        <Link to="/" className="brand-lockup-link" aria-label="Add Your Line">
          <img src={wideLogo} alt="Add Your Line" className="brand-img" />
          <img src={iconLogo} alt="Add Your Line" className="brand-icon" />
        </Link>
        <div className="header-actions">
          <ThemeToggle />
          {showLang && <LanguageSelector />}
        </div>
      </header>
      {children}
      <div className="footer-note">{t("app_name")} — addyourline.com</div>
    </div>
  );
}
