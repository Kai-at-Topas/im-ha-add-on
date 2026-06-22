// Locale-aware number formatting for sensor values.
export function formatNumber(value, locale = 'en', maximumFractionDigits = 2) {
  if (value === null || value === undefined || Number.isNaN(value)) return null;
  return new Intl.NumberFormat(locale, { maximumFractionDigits }).format(value);
}

// Pick a sensible decimal count by magnitude so small values keep meaningful
// precision (e.g. 0.05 kWh) while large ones stay tidy (e.g. 802 kWh).
export function adaptiveDecimals(value) {
  if (value === null || value === undefined || Number.isNaN(value)) return 1;
  const a = Math.abs(value);
  if (a < 1) return 2;
  if (a < 100) return 1;
  return 0;
}

// Scale a raw wattage to a tidy { value, unit } pair: kW with one decimal once
// the magnitude reaches 1000 W, otherwise whole watts. The sign is preserved,
// so callers wanting an absolute (e.g. solar export) should pass Math.abs().
export function formatPower(watts, locale = 'en') {
  if (watts === null || watts === undefined || Number.isNaN(watts)) {
    return { value: null, unit: 'W' };
  }
  if (Math.abs(watts) >= 1000) {
    return { value: formatNumber(watts / 1000, locale, 1), unit: 'kW' };
  }
  return { value: formatNumber(watts, locale, 0), unit: 'W' };
}

// Maps Home Assistant weather condition strings to an emoji glyph.
const WEATHER_ICONS = {
  'clear-night': '🌙',
  cloudy: '☁️',
  fog: '🌫️',
  hail: '🌨️',
  lightning: '🌩️',
  'lightning-rainy': '⛈️',
  partlycloudy: '⛅',
  pouring: '🌧️',
  rainy: '🌦️',
  snowy: '❄️',
  'snowy-rainy': '🌨️',
  sunny: '☀️',
  windy: '💨',
  'windy-variant': '💨',
  exceptional: '⚠️',
};

export function weatherIcon(condition) {
  return WEATHER_ICONS[condition] || '🌡️';
}

// A soft gradient (light, dark) tuned to the weather condition, used as the
// card's accent background.
const WEATHER_GRADIENTS = {
  sunny: ['from-amber-100 to-orange-50', 'dark:from-amber-500/20 dark:to-orange-500/10'],
  'clear-night': ['from-indigo-100 to-slate-50', 'dark:from-indigo-500/20 dark:to-slate-500/10'],
  partlycloudy: ['from-sky-100 to-slate-50', 'dark:from-sky-500/20 dark:to-slate-500/10'],
  cloudy: ['from-slate-200 to-slate-50', 'dark:from-slate-500/20 dark:to-slate-600/10'],
  rainy: ['from-sky-100 to-blue-50', 'dark:from-sky-500/20 dark:to-blue-500/10'],
  pouring: ['from-blue-100 to-slate-50', 'dark:from-blue-500/20 dark:to-slate-500/10'],
  'lightning-rainy': ['from-violet-100 to-slate-50', 'dark:from-violet-500/20 dark:to-slate-500/10'],
  lightning: ['from-violet-100 to-slate-50', 'dark:from-violet-500/20 dark:to-slate-500/10'],
  snowy: ['from-sky-50 to-slate-50', 'dark:from-sky-400/10 dark:to-slate-500/10'],
  fog: ['from-slate-200 to-slate-50', 'dark:from-slate-500/20 dark:to-slate-600/10'],
};

export function weatherGradient(condition) {
  const [light, dark] = WEATHER_GRADIENTS[condition] || [
    'from-slate-100 to-slate-50',
    'dark:from-slate-700/30 dark:to-slate-800/10',
  ];
  return `bg-gradient-to-br ${light} ${dark}`;
}
