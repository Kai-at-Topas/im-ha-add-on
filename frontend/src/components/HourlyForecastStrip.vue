<script setup>
import { ref, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { api } from '../services/api.js';
import { weatherIcon } from '../utils/format.js';
import { useHaTimezone } from '../composables/useHaTimezone.js';

const { t, te, locale } = useI18n();
const { timeZone } = useHaTimezone();

const hourly = ref([]);
const status = ref('loading');

// 12 hours is the useful decision window; beyond that daily view is better.
const MAX_HOURS = 12;

// Capture "now" once on mount so the label doesn't drift during render.
let nowMs = 0;

onMounted(async () => {
  nowMs = Date.now();
  try {
    const res = await api.getForecast('hourly');
    status.value = res.status;
    if (res.status === 'ok') {
      // Allow the current hour to show even if it started up to 30 min ago.
      const cutoff = nowMs - 30 * 60 * 1000;
      hourly.value = (res.forecast || [])
        .filter(h => new Date(h.datetime).getTime() >= cutoff)
        .slice(0, MAX_HOURS);
      if (!hourly.value.length) status.value = 'empty';
    }
  } catch {
    status.value = 'error';
  }
});

function timeLabel(dt) {
  const ms = new Date(dt).getTime();
  // Within ±35 min of now → show "Now"
  if (Math.abs(ms - nowMs) < 35 * 60 * 1000) return t('forecast.now');
  return new Date(dt).toLocaleTimeString(locale.value, {
    hour: '2-digit',
    minute: '2-digit',
    hour12: locale.value.startsWith('en'),
    ...(timeZone.value ? { timeZone: timeZone.value } : {}),
  });
}

function condLabel(c) {
  const key = `weather.conditions.${c}`;
  return c && te(key) ? t(key) : (c || '');
}

function tempClass(temp) {
  if (temp == null) return 'text-gray-400 dark:text-gray-500';
  if (temp >= 28) return 'text-orange-500 dark:text-orange-400';
  if (temp >= 20) return 'text-amber-500 dark:text-amber-400';
  if (temp >= 10) return 'text-emerald-600 dark:text-emerald-400';
  if (temp >= 2)  return 'text-sky-500 dark:text-sky-400';
  return 'text-indigo-500 dark:text-indigo-400';
}

function precipClass(prob) {
  if (!prob) return 'text-gray-300 dark:text-gray-600';
  if (prob >= 60) return 'text-blue-500 dark:text-blue-400';
  if (prob >= 25) return 'text-sky-500 dark:text-sky-400';
  return 'text-sky-400 dark:text-sky-500';
}
</script>

<template>
  <div>
    <div v-if="status === 'loading'" class="py-8 text-center text-sm text-gray-400 dark:text-gray-500">
      {{ t('common.loading') }}
    </div>
    <div v-else-if="status !== 'ok' || !hourly.length" class="py-8 text-center text-sm text-gray-400 dark:text-gray-500">
      {{ t('forecast.unavailable') }}
    </div>

    <ul v-else class="divide-y divide-gray-100 dark:divide-gray-700/60">
      <li
        v-for="(h, i) in hourly"
        :key="i"
        class="flex items-center gap-3 py-3"
      >
        <!-- Time or "Now" -->
        <span class="w-16 shrink-0 whitespace-nowrap text-base tabular-nums text-gray-400 dark:text-gray-500">
          {{ timeLabel(h.datetime) }}
        </span>

        <!-- Condition emoji -->
        <span class="w-8 shrink-0 text-center text-2xl leading-none" aria-hidden="true">
          {{ weatherIcon(h.condition) }}
        </span>

        <!-- Condition label -->
        <span class="min-w-0 flex-1 truncate text-base text-gray-600 dark:text-gray-300 capitalize">
          {{ condLabel(h.condition) }}
        </span>

        <!-- Precipitation probability -->
        <span
          v-if="h.precipitation_probability != null"
          :class="['flex w-12 shrink-0 items-center justify-end gap-1 text-sm tabular-nums', precipClass(h.precipitation_probability)]"
        >
          <!-- Raindrop icon -->
          <svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5 shrink-0" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 2C8.5 7 5 10.5 5 14a7 7 0 0 0 14 0c0-3.5-3.5-7-7-12Z"/>
          </svg>
          {{ h.precipitation_probability }}%
        </span>

        <!-- Wind speed -->
        <span
          v-if="h.wind_speed != null"
          class="flex w-16 shrink-0 whitespace-nowrap items-center justify-end gap-1 text-sm tabular-nums text-gray-400 dark:text-gray-500"
        >
          <!-- Wind icon -->
          <svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M17.7 7.7a2.5 2.5 0 1 1 1.8 4.3H2"/>
            <path d="M9.6 4.6A2 2 0 1 1 11 8H2"/>
            <path d="M12.6 19.4A2 2 0 1 0 14 16H2"/>
          </svg>
          {{ Math.round(h.wind_speed) }} km/h
        </span>

        <!-- Temperature -->
        <span :class="['w-10 shrink-0 text-right text-base font-semibold tabular-nums', tempClass(h.temperature)]">
          {{ h.temperature != null ? Math.round(h.temperature) + '°' : '–' }}
        </span>
      </li>
    </ul>
  </div>
</template>
