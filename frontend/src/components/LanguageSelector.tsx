import { useI18n } from "../i18n/I18nContext";

export function LanguageSelector() {
  const { lang, setLang } = useI18n();
  return (
    <div className="segmented" role="group" aria-label="Language">
      <button className={lang === "en" ? "active" : ""} onClick={() => setLang("en")} type="button">
        English
      </button>
      <button className={lang === "he" ? "active" : ""} onClick={() => setLang("he")} type="button">
        עברית
      </button>
    </div>
  );
}
