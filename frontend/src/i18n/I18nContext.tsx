import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import type { Language } from "../types";
import { getSavedLang, saveLang } from "../services/storage";
import { errorKey, translations, type TranslationKey } from "./translations";

interface I18nValue {
  lang: Language;
  dir: "ltr" | "rtl";
  setLang: (lang: Language) => void;
  t: (key: TranslationKey, params?: Record<string, string | number>) => string;
  tError: (code: string) => string;
}

const I18nContext = createContext<I18nValue | null>(null);

function interpolate(template: string, params?: Record<string, string | number>): string {
  if (!params) return template;
  return template.replace(/\{(\w+)\}/g, (_, k) => String(params[k] ?? `{${k}}`));
}

export function I18nProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Language>(() => getSavedLang() ?? "en");

  const setLang = useCallback((next: Language) => {
    setLangState(next);
    saveLang(next);
  }, []);

  const dir: "ltr" | "rtl" = lang === "he" ? "rtl" : "ltr";

  // Keep the document direction and language in sync for proper RTL layout.
  useEffect(() => {
    document.documentElement.lang = lang;
    document.documentElement.dir = dir;
  }, [lang, dir]);

  const value = useMemo<I18nValue>(() => {
    const dict = translations[lang];
    const t = (key: TranslationKey, params?: Record<string, string | number>) =>
      interpolate(dict[key] ?? key, params);
    return {
      lang,
      dir,
      setLang,
      t,
      tError: (code: string) => t(errorKey(code)),
    };
  }, [lang, dir, setLang]);

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n(): I18nValue {
  const ctx = useContext(I18nContext);
  if (!ctx) throw new Error("useI18n must be used within I18nProvider");
  return ctx;
}
