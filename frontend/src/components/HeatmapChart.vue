<script setup>
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { useTheme } from '../composables/useTheme.js';
import { formatNumber } from '../utils/format.js';

const props = defineProps({
  // Array of day objects: { date, weekday, label, hours: [24 values] }
  days: { type: Array, default: () => [] },
  unit: { type: String, default: 'W' },
  decimals: { type: Number, default: 0 },
});

const { t, locale } = useI18n();
const { theme } = useTheme();

const isDark = computed(() => theme.value === 'dark');

// Single source of truth for the colour scale endpoints, so the cells and the
// legend gradient can never drift apart. [low, high] as RGB triples.
const SCALE = {
  light: { low: [209, 250, 229], high: [4, 120, 87] },   // emerald-100 → emerald-700
  dark: { low: [22, 78, 56], high: [52, 211, 153] },      // lifted dark green → emerald-400
};
const NO_DATA = { light: '#f3f4f6', dark: '#1f2937' };    // gray-100 / gray-800

const scale = computed(() => (isDark.value ? SCALE.dark : SCALE.light));
const noDataColor = computed(() => (isDark.value ? NO_DATA.dark : NO_DATA.light));

// Max value across all cells (for colour scaling)
const maxVal = computed(() => {
  let m = 0;
  for (const day of props.days) {
    for (const v of day.hours) {
      if (v !== null && v > m) m = v;
    }
  }
  return m || 1;
});

// Interpolate colour between two RGB endpoints at t ∈ [0, 1]
function lerp(a, b, t) {
  return Math.round(a + (b - a) * t);
}
function rgbAt(t) {
  const { low, high } = scale.value;
  return `rgb(${lerp(low[0], high[0], t)},${lerp(low[1], high[1], t)},${lerp(low[2], high[2], t)})`;
}

function cellColor(value) {
  if (value === null) return noDataColor.value;
  return rgbAt(Math.min(1, value / maxVal.value));
}

const legendGradient = computed(() => `linear-gradient(to right, ${rgbAt(0)}, ${rgbAt(1)})`);

// Script-scope helper: locale.value resolves correctly here (in a template
// expression, `locale.value` would be undefined due to ref auto-unwrapping).
function fmtVal(value) {
  return formatNumber(value, locale.value, props.decimals);
}

function cellTitle(day, hour, value) {
  const valStr = value !== null ? `${formatNumber(value, locale.value, props.decimals)} ${props.unit}` : 'N/A';
  return `${day.label}  ${String(hour).padStart(2, '0')}:00 — ${valStr}`;
}

const HOUR_LABELS = Array.from({ length: 24 }, (_, i) => i);
</script>

<template>
  <div class="w-full overflow-x-auto select-none">
    <!-- Hour axis labels -->
    <div class="flex mb-1" style="padding-left: 3.25rem">
      <div
        v-for="h in HOUR_LABELS"
        :key="h"
        class="flex-1 text-center text-[9px] text-gray-400 dark:text-gray-500"
      >
        {{ h % 4 === 0 ? h : '' }}
      </div>
    </div>

    <!-- Rows: one per day -->
    <div v-for="day in days" :key="day.date" class="flex items-center mb-0.5">
      <!-- Day label -->
      <div class="w-12 flex-shrink-0 text-[11px] font-medium text-gray-500 dark:text-gray-400 text-right pr-2">
        {{ day.label }}
      </div>
      <div class="flex flex-1 gap-0.5">
        <div
          v-for="(val, h) in day.hours"
          :key="h"
          class="flex-1 h-7 rounded-sm transition-opacity duration-150 hover:opacity-75"
          :style="{ backgroundColor: cellColor(val) }"
          :title="cellTitle(day, h, val)"
        />
      </div>
    </div>

    <!-- Colour legend -->
    <div class="flex items-center gap-2 mt-3" style="padding-left: 3.25rem">
      <span class="text-[10px] text-gray-400 dark:text-gray-500 whitespace-nowrap">
        {{ fmtVal(0) }} {{ unit }}
      </span>
      <div class="flex-1 h-2 rounded" :style="{ background: legendGradient }" />
      <span class="text-[10px] text-gray-400 dark:text-gray-500 whitespace-nowrap">
        {{ fmtVal(maxVal) }} {{ unit }}
      </span>
      <!-- no-data swatch -->
      <span class="flex items-center gap-1 ml-2 whitespace-nowrap">
        <span class="inline-block h-2 w-2 rounded-sm" :style="{ backgroundColor: noDataColor }" />
        <span class="text-[10px] text-gray-400 dark:text-gray-500">{{ t('common.notAvailable') }}</span>
      </span>
    </div>

    <p v-if="days.length === 0" class="text-center text-sm text-gray-400 dark:text-gray-500 py-8">
      {{ t('detail.noData') }}
    </p>
  </div>
</template>
