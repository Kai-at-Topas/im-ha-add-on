// Polls GET /api/ha/energy/stats every 5 minutes and exposes the full
// energy statistics block computed by the backend.
//
// The response contains:
//   energy.today              — kWh consumed since midnight
//   energy.yesterday_so_far   — kWh at the same elapsed time yesterday
//   energy.this_month         — kWh since the 1st of the month
//   energy.month_end_estimate — projected month-end total
//   energy.annual_estimate    — rolling 12-month or extrapolated annual
//   energy.annual_basis       — "lts" | "extrapolated"
//   energy.vs_last_year_pct   — YTD change vs prior year (LTS only)
//   energy.daily_avg          — 30-day average daily consumption (kWh)
//   power.base_load           — avg W between 02:00–04:00 local
//   power.min_today / min_time — peak solar export value + timestamp
//   power.max_today / max_time — peak grid draw value + timestamp
//   cost.*                    — optional cost fields (when cost_per_kwh set)
//
// The 5-minute interval is intentional — the backend fetches up to 30
// days of sensor history plus a WebSocket LTS query on each call, so
// polling faster would be wasteful and stats don't change within seconds.
import { ref, onMounted, onUnmounted } from 'vue';
import { api } from '../services/api.js';

const REFRESH_INTERVAL = 5 * 60 * 1000; // 5 minutes

export function useEnergyStats() {
  const stats = ref(null);
  const loading = ref(true);
  const error = ref(null);

  let timer = null;

  async function refresh() {
    try {
      stats.value = await api.getEnergyStats();
      error.value = null;
    } catch (err) {
      error.value = err.message;
    } finally {
      loading.value = false;
    }
  }

  onMounted(() => {
    refresh();
    timer = setInterval(refresh, REFRESH_INTERVAL);
  });

  onUnmounted(() => {
    if (timer) clearInterval(timer);
  });

  return { stats, loading, error, refresh };
}
