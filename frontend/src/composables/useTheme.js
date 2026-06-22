import { ref } from 'vue';

const STORAGE_KEY = 'topas-theme';

function resolveInitialTheme() {
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored === 'light' || stored === 'dark') return stored;
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

// Shared singleton state so every component reflects the same theme.
const theme = ref(resolveInitialTheme());

function apply(value) {
  document.documentElement.classList.toggle('dark', value === 'dark');
}

export function initTheme() {
  apply(theme.value);
}

export function useTheme() {
  function setTheme(value) {
    theme.value = value;
    localStorage.setItem(STORAGE_KEY, value);
    apply(value);
  }

  function toggleTheme() {
    setTheme(theme.value === 'dark' ? 'light' : 'dark');
  }

  return { theme, setTheme, toggleTheme };
}
