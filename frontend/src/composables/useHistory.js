import { ref, watch, onMounted, onUnmounted, unref } from 'vue';
import { api } from '../services/api.js';

const REFRESH_INTERVAL = 60000;

// `hours` may be a ref so the dashboard's range selector can drive refetches.
export function useHistory(hours) {
  const history = ref(null);
  const loading = ref(true);
  const error = ref(null);

  let timer = null;

  async function refresh() {
    try {
      history.value = await api.getHistory(unref(hours));
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

  watch(
    () => unref(hours),
    () => {
      loading.value = true;
      refresh();
    }
  );

  return { history, loading, error, refresh };
}
