<script setup>
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { weatherIcon, weatherGradient, formatNumber } from '../utils/format.js';

const props = defineProps({
  weather: { type: Object, default: null },
  clickable: { type: Boolean, default: false },
});
const emit = defineEmits(['open']);

const { t, te, locale } = useI18n();

const status = computed(() => props.weather?.status ?? 'unconfigured');
const isOk = computed(() => status.value === 'ok');
const interactive = computed(() => props.clickable && isOk.value);

const conditionLabel = computed(() => {
  const c = props.weather?.condition;
  if (!c) return t('common.notAvailable');
  const key = `weather.conditions.${c}`;
  return te(key) ? t(key) : c;
});

const icon = computed(() => weatherIcon(props.weather?.condition));
const gradient = computed(() =>
  isOk.value ? weatherGradient(props.weather?.condition) : 'bg-white dark:bg-gray-800'
);

function fmt(value, unit) {
  const n = formatNumber(value, locale.value);
  if (n === null) return t('common.notAvailable');
  return unit ? `${n} ${unit}` : n;
}

function open() {
  if (interactive.value) emit('open');
}
</script>

<template>
  <section
    :class="[
      'rounded-2xl border border-gray-200 dark:border-gray-700 p-5 shadow-sm transition-all duration-300',
      gradient,
      interactive ? 'cursor-pointer hover:shadow-md hover:-translate-y-0.5 focus:outline-none focus:ring-2 focus:ring-blue-500' : '',
    ]"
    :role="interactive ? 'button' : null"
    :tabindex="interactive ? 0 : null"
    @click="open"
    @keydown.enter="open"
    @keydown.space.prevent="open"
  >
    <div class="flex items-center gap-3 mb-4">
      <span
        class="inline-flex items-center justify-center h-9 w-9 rounded-lg bg-white/60 dark:bg-gray-900/40 text-xl leading-none"
        aria-hidden="true"
      >
        {{ isOk ? icon : '🌡️' }}
      </span>
      <h2 class="text-sm font-medium text-gray-600 dark:text-gray-300">{{ t('weather.title') }}</h2>
      <svg
        v-if="interactive"
        class="ml-auto h-4 w-4 text-gray-400 dark:text-gray-500"
        xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"
      >
        <path d="M9 18l6-6-6-6" />
      </svg>
    </div>

    <!-- Not configured / unavailable -->
    <div v-if="!isOk" class="py-6 text-center">
      <p class="text-gray-500 dark:text-gray-400 font-medium">
        {{ status === 'unconfigured' ? t('common.unconfigured') : t('common.unavailable') }}
      </p>
      <p v-if="status === 'unconfigured'" class="mt-1 text-xs text-gray-400 dark:text-gray-500">
        {{ t('common.configureHint') }}
      </p>
    </div>

    <!-- Live -->
    <div v-else>
      <div class="flex items-end justify-between mb-6">
        <span class="text-4xl font-semibold text-gray-900 dark:text-white tracking-tight tabular-nums">
          {{ fmt(weather.temperature, weather.temperature_unit) }}
        </span>
        <span class="text-base text-gray-600 dark:text-gray-300 pb-1 text-right">{{ conditionLabel }}</span>
      </div>

      <dl class="grid grid-cols-3 gap-3 text-center">
        <div class="rounded-lg bg-white/50 dark:bg-gray-900/30 px-1 py-2">
          <dt class="text-[11px] leading-tight text-gray-500 dark:text-gray-400 break-words">{{ t('weather.humidity') }}</dt>
          <dd class="mt-1 font-medium text-gray-900 dark:text-white tabular-nums">{{ fmt(weather.humidity, '%') }}</dd>
        </div>
        <div class="rounded-lg bg-white/50 dark:bg-gray-900/30 px-1 py-2">
          <dt class="text-[11px] leading-tight text-gray-500 dark:text-gray-400 break-words">{{ t('weather.wind') }}</dt>
          <dd class="mt-1 font-medium text-gray-900 dark:text-white tabular-nums">{{ fmt(weather.wind_speed, weather.wind_speed_unit) }}</dd>
        </div>
        <div class="rounded-lg bg-white/50 dark:bg-gray-900/30 px-1 py-2">
          <dt class="text-[11px] leading-tight text-gray-500 dark:text-gray-400 break-words">{{ t('weather.pressure') }}</dt>
          <dd class="mt-1 font-medium text-gray-900 dark:text-white tabular-nums">{{ fmt(weather.pressure, 'hPa') }}</dd>
        </div>
      </dl>
    </div>
  </section>
</template>
