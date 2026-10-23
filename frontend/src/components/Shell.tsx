import type { ReactNode } from "react";

import { useI18n } from "../i18n/I18nContext";
import { LanguageSelector } from "./LanguageSelector";

export function Shell({ children, showLang = true }: { children: ReactNode; showLang?: boolean }) {
  const { t } = useI18n();
  return (
    <div className="app-shell">
      <header className="brand" style={{ justifyContent: "flex-end" }}>
        {showLang && <LanguageSelector />}
      </header>
      {children}
      <div className="footer-note">{t("app_name")} — addyourline.com</div>
    </div>
  );
}
