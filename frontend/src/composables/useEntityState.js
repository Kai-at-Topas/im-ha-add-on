// Polls GET /api/ha/state every 10 s and exposes reactive refs for the
// current weather/power/energy entity states.
//
// Each block in the response carries a `status` field:
//   'ok'            — live value present
//   'unavailable'   — entity configured but HA is unreachable or the
//                     entity has state "unknown"/"unavailable"
//   'unconfigured'  — no entity selected yet in Settings
//
// The 10-second interval keeps the live power tile fresh without
// hammering the HA API.
import { ref, onMounted, onUnmounted } from 'vue';
import { api } from '../services/api.js';

const DEFAULT_INTERVAL = 10000;

export function useEntityState(intervalMs = DEFAULT_INTERVAL) {
  const state = ref(null);
  const loading = ref(true);
  const error = ref(null);
  const lastUpdated = ref(null);

  let timer = null;

  async function refresh() {
    try {
      state.value = await api.getState();
      error.value = null;
      lastUpdated.value = new Date();
    } catch (err) {
      error.value = err.message;
    } finally {
      loading.value = false;
    }
  }

  onMounted(() => {
    refresh();
    timer = setInterval(refresh, intervalMs);
  });

  onUnmounted(() => {
    if (timer) clearInterval(timer);
  });

  return { state, loading, error, lastUpdated, refresh };
}
