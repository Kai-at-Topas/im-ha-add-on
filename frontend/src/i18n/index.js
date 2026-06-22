import { createI18n } from 'vue-i18n';
import en from './locales/en.js';
import de from './locales/de.js';

const SUPPORTED = ['en', 'de'];
const STORAGE_KEY = 'topas-locale';

function resolveInitialLocale() {
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored && SUPPORTED.includes(stored)) return stored;

  const browser = (navigator.language || 'en').slice(0, 2);
  return SUPPORTED.includes(browser) ? browser : 'en';
}

const i18n = createI18n({
  legacy: false,
  globalInjection: true,
  locale: resolveInitialLocale(),
  fallbackLocale: 'en',
  messages: { en, de },
});

export function setLocale(locale) {
  if (!SUPPORTED.includes(locale)) return;
  i18n.global.locale.value = locale;
  localStorage.setItem(STORAGE_KEY, locale);
  document.documentElement.setAttribute('lang', locale);
}

export function toggleLocale() {
  const current = i18n.global.locale.value;
  setLocale(current === 'de' ? 'en' : 'de');
}

export { SUPPORTED as supportedLocales };
export default i18n;
