<script setup>
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import HistoryChart from './HistoryChart.vue';
import Icon from './Icon.vue';
import { formatNumber } from '../utils/format.js';

// Named icons render via the shared Icon component; legacy 'power'/'energy' keep
// their bespoke inline glyphs.
const NAMED_ICONS = ['activity', 'clock', 'trending-up', 'moon', 'scale'];

const props = defineProps({
  title: { type: String, required: true },
  metric: { type: Object, default: null },
  history: { type: Array, default: null },
  color: { type: String, default: '#3b82f6' },
  icon: { type: String, default: 'power' }, // 'power' | 'energy'
  clickable: { type: Boolean, default: false },
  // Optional overrides for dynamic display (e.g. signed power → kW + colour).
  valueText: { type: String, default: null },   // pre-formatted value string
  valueUnit: { type: String, default: null },    // overrides metric.unit
  valueColorClass: { type: String, default: null }, // colour for the big number
  subtext: { type: String, default: null },       // contextual line below value
});
const emit = defineEmits(['open']);

const { t, locale } = useI18n();

const status = computed(() => props.metric?.status ?? 'unconfigured');
const isOk = computed(() => status.value === 'ok');
const interactive = computed(() => props.clickable && isOk.value);

function open() {
  if (interactive.value) emit('open');
}

// valueText wins when provided; otherwise format the raw metric value.
const formattedValue = computed(() =>
  props.valueText !== null
    ? props.valueText
    : isOk.value ? formatNumber(props.metric?.value, locale.value) : null
);
const displayUnit = computed(() => props.valueUnit ?? props.metric?.unit);
const valueColor = computed(
  () => props.valueColorClass ?? 'text-gray-900 dark:text-white'
);

const badgeClass = computed(() =>
  props.icon === 'power'
    ? 'bg-amber-100 text-amber-600 dark:bg-amber-500/20 dark:text-amber-400'
    : 'bg-emerald-100 text-emerald-600 dark:bg-emerald-500/20 dark:text-emerald-400'
);
const isNamedIcon = computed(() => NAMED_ICONS.includes(props.icon));
</script>

<template>
  <section
    :class="[
      'rounded-2xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-5 shadow-sm transition-all duration-300',
      interactive ? 'cursor-pointer hover:shadow-md hover:-translate-y-0.5 focus:outline-none focus:ring-2 focus:ring-blue-500' : '',
    ]"
    :role="interactive ? 'button' : null"
    :tabindex="interactive ? 0 : null"
    @click="open"
    @keydown.enter="open"
    @keydown.space.prevent="open"
  >
    <div class="flex items-center gap-3 mb-4">
      <span :class="['inline-flex items-center justify-center h-9 w-9 rounded-lg', badgeClass]">
        <Icon v-if="isNamedIcon" :name="icon" class="h-5 w-5" />
        <!-- bolt -->
        <svg v-else-if="icon === 'power'" xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 24 24" fill="currentColor">
          <path d="M13 2 4.5 13.5H11l-1 8.5 8.5-11.5H12l1-8.5z" />
        </svg>
        <!-- gauge / cumulative -->
        <svg v-else xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M16 7h6v6"/><path d="m22 7-8.5 8.5-5-5L2 17"/>
        </svg>
      </span>
      <h2 class="text-sm font-medium text-gray-500 dark:text-gray-400">{{ title }}</h2>
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
      <p :class="['text-4xl font-semibold tracking-tight tabular-nums transition-colors', valueColor]">
        <span>{{ formattedValue ?? t('common.notAvailable') }}</span>
        <span v-if="formattedValue && displayUnit" class="text-lg text-gray-500 dark:text-gray-400 ml-1">{{ displayUnit }}</span>
      </p>

      <p v-if="subtext" class="mt-1 text-sm text-gray-500 dark:text-gray-400">{{ subtext }}</p>

      <div v-if="history" class="mt-4">
        <HistoryChart :points="history" :color="color" />
      </div>
    </div>
  </section>
</template>
