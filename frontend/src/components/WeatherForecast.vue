<script setup>
import { ref, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { api } from '../services/api.js';
import { weatherIcon, formatNumber } from '../utils/format.js';

const { t, te, locale } = useI18n();

const forecast = ref([]);
const status = ref('loading');

onMounted(async () => {
  try {
    const res = await api.getForecast('daily');
    status.value = res.status;
    forecast.value = res.forecast || [];
    if (res.status === 'ok' && forecast.value.length === 0) status.value = 'empty';
  } catch {
    status.value = 'unavailable';
  }
});

function dayLabel(dt) {
  return new Date(dt).toLocaleDateString(locale.value, { weekday: 'long', day: 'numeric', month: 'short' });
}
function condLabel(c) {
  const key = `weather.conditions.${c}`;
  return c && te(key) ? t(key) : c || '';
}
function temp(v) {
  const n = formatNumber(v, locale.value, 0);
  return n === null ? '–' : `${n}°`;
}
</script>

<template>
  <div>
    <div v-if="status === 'loading'" class="py-10 text-center text-gray-500 dark:text-gray-400">
      {{ t('common.loading') }}
    </div>
    <div v-else-if="status !== 'ok'" class="py-10 text-center text-gray-500 dark:text-gray-400">
      {{ t('forecast.unavailable') }}
    </div>
    <ul v-else class="divide-y divide-gray-100 dark:divide-gray-700">
      <li v-for="(day, i) in forecast" :key="i" class="flex items-center gap-4 py-3">
        <span class="text-2xl w-8 text-center" aria-hidden="true">{{ weatherIcon(day.condition) }}</span>
        <div class="flex-1 min-w-0">
          <p class="font-medium text-gray-900 dark:text-white capitalize truncate">{{ dayLabel(day.datetime) }}</p>
          <p class="text-xs text-gray-500 dark:text-gray-400 truncate">{{ condLabel(day.condition) }}</p>
        </div>
        <div
          v-if="day.precipitation_probability != null"
          class="text-xs text-sky-600 dark:text-sky-400 tabular-nums w-14 text-right"
        >
          {{ day.precipitation_probability }}%
        </div>
        <div class="text-right tabular-nums w-20">
          <span class="font-semibold text-gray-900 dark:text-white">{{ temp(day.temperature) }}</span>
          <span class="text-gray-400 dark:text-gray-500 ml-1">{{ temp(day.templow) }}</span>
        </div>
      </li>
    </ul>
  </div>
</template>
