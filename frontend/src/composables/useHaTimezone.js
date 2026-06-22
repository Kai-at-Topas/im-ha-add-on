import { ref } from 'vue';
import { api } from '../services/api.js';

// Shared singleton: Home Assistant's IANA timezone name (e.g. "Europe/Berlin").
// `null` until loaded, or on error → callers fall back to the browser timezone.
const timeZone = ref(null);
let started = false;

async function load() {
  if (started) return;
  started = true;
  try {
    const res = await api.getTime();
    timeZone.value = res?.time_zone || null;
  } catch {
    timeZone.value = null; // fall back to browser tz
  }
}

export function useHaTimezone() {
  load(); // fire once on first use; subsequent calls are no-ops
  return { timeZone };
}
