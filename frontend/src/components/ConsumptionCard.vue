<script setup>
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { formatNumber, adaptiveDecimals } from '../utils/format.js';

const props = defineProps({
  today: { type: Number, default: null },
  yesterday: { type: Number, default: null },
  thirtyDayAvg: { type: Number, default: null },
  thirtyDayAvgDays: { type: Number, default: null }, // actual days behind the avg
  unit: { type: String, default: 'kWh' },
  loading: { type: Boolean, default: false },
  clickable: { type: Boolean, default: false },
});

const emit = defineEmits(['open']);

const { t, locale } = useI18n();

const hasData = computed(
  () => props.today !== null || props.yesterday !== null || props.thirtyDayAvg !== null
);
const isInteractive = computed(() => props.clickable && hasData.value && !props.loading);

// Adaptive precision so the label matches the (raw-valued) bar.
function fmt(v) {
  return v !== null && v !== undefined ? formatNumber(v, locale.value, adaptiveDecimals(v)) : null;
}

// Build a comparison badge: today vs a baseline (yesterday, or the daily avg).
// Returns null when the baseline is missing/zero so the badge is simply hidden.
function makeDelta(base) {
  if (props.today === null || base === null || base === undefined || base === 0) return null;
  const value = ((props.today - base) / base) * 100;
  return {
    text: formatNumber(Math.abs(value), locale.value, 0),
    arrow: value > 0 ? '↑' : '↓',
    colorClass: value > 0 ? 'text-red-500 dark:text-red-400' : 'text-emerald-500 dark:text-emerald-400',
  };
}

const badges = computed(() =>
  [
    { label: t('stats.vsYesterdayShort'), delta: makeDelta(props.yesterday) },
    { label: t('stats.vsAvgShort'), delta: makeDelta(props.thirtyDayAvg) },
  ].filter((b) => b.delta !== null)
);

// Three vertical bars sharing one scale. Labels sit above, values atop each bar
// — no empty middle band, no wasted vertical space.
const avgLabel = computed(() =>
  props.thirtyDayAvgDays && props.thirtyDayAvgDays < 30
    ? t('stats.dayAvg', { n: props.thirtyDayAvgDays })
    : t('stats.thirtyDayAvg')
);

const bars = computed(() => [
  { key: 'today', label: t('stats.today'), value: props.today, color: 'bg-amber-400 dark:bg-amber-500' },
  { key: 'yesterday', label: t('stats.yesterday'), value: props.yesterday, color: 'bg-emerald-400 dark:bg-emerald-500' },
  { key: 'avg', label: avgLabel.value, value: props.thirtyDayAvg, color: 'bg-blue-400 dark:bg-blue-500' },
]);

const barMax = computed(() => {
  const vals = bars.value.map((b) => b.value).filter((v) => v !== null && v !== undefined);
  return vals.length ? Math.max(...vals, 0.0001) : 0;
});
function barHeight(v) {
  if (v === null || v === undefined || barMax.value <= 0) return 4;
  return Math.max(4, (v / barMax.value) * 100);
}

function open() {
  if (isInteractive.value) emit('open');
}
</script>

<template>
  <section
    :class="[
      'rounded-2xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-5 shadow-sm',
      'border-l-4 border-l-blue-400 dark:border-l-blue-500 transition-all duration-200',
      isInteractive ? 'cursor-pointer hover:shadow-md hover:-translate-y-0.5 focus:outline-none focus:ring-2 focus:ring-blue-500' : '',
    ]"
    :role="isInteractive ? 'button' : null"
    :tabindex="isInteractive ? 0 : null"
    @click="open"
    @keydown.enter="open"
    @keydown.space.prevent="open"
  >
    <div class="flex items-center gap-2 mb-4">
      <!-- comparison ⇄ icon -->
      <svg class="flex-shrink-0 h-4 w-4 text-blue-400 dark:text-blue-500" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M7 16V4m0 0L3 8m4-4l4 4M17 8v12m0 0l4-4m-4 4l-4-4" />
      </svg>
      <h2 class="text-sm font-medium text-gray-500 dark:text-gray-400 flex-1">{{ t('stats.consumptionTitle') }}</h2>
      <span
        v-for="badge in badges" :key="badge.label"
        class="text-[11px] font-medium text-gray-400 dark:text-gray-500 whitespace-nowrap"
      >
        {{ badge.label }} <span :class="badge.delta.colorClass">{{ badge.delta.arrow }} {{ badge.delta.text }}%</span>
      </span>
      <svg
        v-if="isInteractive"
        class="flex-shrink-0 h-4 w-4 text-gray-400 dark:text-gray-500"
        xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"
      >
        <path d="M9 18l6-6-6-6" />
      </svg>
    </div>

    <div v-if="loading" class="animate-pulse flex items-end gap-4 h-40">
      <div class="flex-1 bg-gray-200 dark:bg-gray-700 rounded-t-lg" style="height: 60%"></div>
      <div class="flex-1 bg-gray-100 dark:bg-gray-700/60 rounded-t-lg" style="height: 90%"></div>
      <div class="flex-1 bg-gray-100 dark:bg-gray-700/60 rounded-t-lg" style="height: 45%"></div>
    </div>

    <!-- Thick vertical bars: value atop, label below -->
    <div v-else-if="hasData" class="flex items-end justify-between gap-4 h-40">
      <div v-for="bar in bars" :key="bar.key" class="flex-1 flex flex-col items-center h-full">
        <span class="mb-1 text-sm font-semibold text-gray-900 dark:text-white tabular-nums">
          {{ fmt(bar.value) ?? '—' }}<span class="text-[11px] font-normal text-gray-400 ml-0.5">{{ unit }}</span>
        </span>
        <div class="flex-1 w-full flex items-end">
          <div
            :class="['w-full rounded-t-lg transition-all duration-500 min-h-[4px]', bar.color]"
            :style="{ height: barHeight(bar.value) + '%' }"
          />
        </div>
        <span class="mt-2 text-xs text-gray-400 dark:text-gray-500 text-center leading-tight">{{ bar.label }}</span>
      </div>
    </div>

    <div v-else class="py-4 text-center">
      <p class="text-gray-400 dark:text-gray-500 text-sm">{{ t('common.notAvailable') }}</p>
    </div>
  </section>
</template>
