import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';

import viTranslation from '../locales/vi/translation.json';
import enTranslation from '../locales/en/translation.json';
import jaTranslation from '../locales/ja/translation.json';
import koTranslation from '../locales/ko/translation.json';
import frTranslation from '../locales/fr/translation.json';
import zhTranslation from '../locales/zh/translation.json';

export type SupportedLanguage = 'vi' | 'en' | 'ja' | 'ko' | 'fr' | 'zh';

export interface LanguageMeta {
  code: SupportedLanguage;
  name: string;
  nativeName: string;
  flag: string;
  cjk?: boolean;
}

export const SUPPORTED_LANGUAGES: LanguageMeta[] = [
  { code: 'vi', name: 'Vietnamese', nativeName: 'Tiếng Việt', flag: '🇻🇳' },
  { code: 'en', name: 'English', nativeName: 'English', flag: '🇬🇧' },
  { code: 'ja', name: 'Japanese', nativeName: '日本語', flag: '🇯🇵', cjk: true },
  { code: 'ko', name: 'Korean', nativeName: '한국어', flag: '🇰🇷', cjk: true },
  { code: 'fr', name: 'French', nativeName: 'Français', flag: '🇫🇷' },
  { code: 'zh', name: 'Chinese', nativeName: '简体中文', flag: '🇨🇳', cjk: true },
];

export const DEFAULT_LANGUAGE: SupportedLanguage = 'vi';

const savedLang = (localStorage.getItem('app_language') as SupportedLanguage) || DEFAULT_LANGUAGE;

const resources = {
  vi: { translation: viTranslation },
  en: { translation: enTranslation },
  ja: { translation: jaTranslation },
  ko: { translation: koTranslation },
  fr: { translation: frTranslation },
  zh: { translation: zhTranslation },
};

i18n
  .use(initReactI18next)
  .init({
    resources,
    lng: savedLang,
    fallbackLng: DEFAULT_LANGUAGE,
    interpolation: {
      escapeValue: false, // React already escapes values
    },
    detection: {
      order: ['localStorage', 'navigator'],
      caches: ['localStorage'],
    },
  });

export function applyLanguageHtmlAttributes(lang: string) {
  if (typeof document !== 'undefined') {
    document.documentElement.lang = lang;
    const isCjk = ['ja', 'ko', 'zh'].includes(lang);
    if (isCjk) {
      document.body.classList.add('cjk-font');
    } else {
      document.body.classList.remove('cjk-font');
    }
  }
}

// Initialize html attributes on boot
applyLanguageHtmlAttributes(savedLang);

export async function setAppLanguage(lang: SupportedLanguage) {
  await i18n.changeLanguage(lang);
  localStorage.setItem('app_language', lang);
  applyLanguageHtmlAttributes(lang);
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new CustomEvent('app:languageChanged', { detail: { lang } }));
  }
}

export default i18n;
