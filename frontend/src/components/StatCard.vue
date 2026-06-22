<script setup>
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import Icon from './Icon.vue';
import { formatNumber } from '../utils/format.js';

const NAMED_ICONS = ['activity', 'clock', 'trending-up', 'moon', 'scale'];

const props = defineProps({
  title: { type: String, required: true },
  value: { type: Number, default: null },
  unit: { type: String, default: null },
  costValue: { type: Number, default: null },
  costExtra: { type: Number, default: null },
  subValue: { type: Number, default: null },
  subLabel: { type: String, default: null },
  subUnit: { type: String, default: null },
  // dual-value mode: show value and dualValue side by side (e.g. Min / Max)
  dualValue: { type: Number, default: null },
  dualLabel: { type: String, default: null },
  // lines mode: stacked text rows [{ label, valueText, unit, sub, colorClass }]
  lines: { type: Array, default: null },
  prefix: { type: String, default: null },
  loading: { type: Boolean, default: false },
  decimals: { type: Number, default: 1 },
  variant: { type: String, default: 'energy' }, // 'energy' | 'power' | 'cost'
  clickable: { type: Boolean, default: false },
  locked: { type: Boolean, default: false }, // teaser state: hide value, show unlock hint
  emptyText: { type: String, default: null }, // shown instead of N/A when value is null
  icon: { type: String, default: null }, // named icon override (else variant default)
  description: { type: String, default: null }, // small gray explainer below the value
});

const emit = defineEmits(['open']);

const { t, locale } = useI18n();

const formattedValue = computed(() =>
  props.value !== null ? formatNumber(props.value, locale.value, props.decimals) : null
);
const formattedCost = computed(() =>
  props.costValue !== null ? formatNumber(props.costValue, locale.value, 2) : null
);
const formattedCostExtra = computed(() =>
  props.costExtra !== null ? formatNumber(props.costExtra, locale.value, 2) : null
);
const formattedSub = computed(() =>
  props.subValue !== null ? formatNumber(props.subValue, locale.value, props.decimals) : null
);
const formattedDual = computed(() =>
  props.dualValue !== null ? formatNumber(props.dualValue, locale.value, props.decimals) : null
);

const hasLines = computed(() => Array.isArray(props.lines) && props.lines.length > 0);
const isNamedIcon = computed(() => NAMED_ICONS.includes(props.icon));

const isInteractive = computed(
  () => props.clickable && !props.loading && (props.locked || hasLines.value || props.value !== null)
);

const accentClass = computed(() => {
  if (props.variant === 'power') return 'border-l-amber-400 dark:border-l-amber-500';
  if (props.variant === 'cost') return 'border-l-blue-400 dark:border-l-blue-500';
  return 'border-l-emerald-400 dark:border-l-emerald-500';
});

const badgeClass = computed(() => {
  if (props.variant === 'power') return 'bg-amber-100 text-amber-600 dark:bg-amber-500/20 dark:text-amber-400';
  if (props.variant === 'cost') return 'bg-blue-100 text-blue-600 dark:bg-blue-500/20 dark:text-blue-400';
  return 'bg-emerald-100 text-emerald-600 dark:bg-emerald-500/20 dark:text-emerald-400';
});

function open() {
  if (isInteractive.value) emit('open');
}
</script>

<template>
  <section
    :class="[
      'rounded-2xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-5 shadow-sm',
      'border-l-4 transition-all duration-200',
      accentClass,
      isInteractive ? 'cursor-pointer hover:shadow-md hover:-translate-y-0.5 focus:outline-none focus:ring-2 focus:ring-blue-500' : '',
    ]"
    :role="isInteractive ? 'button' : null"
    :tabindex="isInteractive ? 0 : null"
    @click="open"
    @keydown.enter="open"
    @keydown.space.prevent="open"
  >
    <div class="flex items-center gap-3 mb-3">
      <span :class="['inline-flex items-center justify-center h-9 w-9 rounded-lg flex-shrink-0', badgeClass]">
        <Icon v-if="isNamedIcon" :name="icon" class="h-5 w-5" />
        <svg v-else-if="variant === 'energy'" xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <rect x="3" y="4" width="18" height="18" rx="2" ry="2" /><line x1="16" y1="2" x2="16" y2="6" /><line x1="8" y1="2" x2="8" y2="6" /><line x1="3" y1="10" x2="21" y2="10" />
        </svg>
        <svg v-else-if="variant === 'power'" xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 24 24" fill="currentColor">
          <path d="M13 2 4.5 13.5H11l-1 8.5 8.5-11.5H12l1-8.5z" />
        </svg>
        <svg v-else xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="10" /><path d="M15 9.354a4 4 0 1 0 0 5.292" />
        </svg>
      </span>
      <h2 class="text-sm font-medium text-gray-500 dark:text-gray-400 min-w-0 truncate">{{ title }}</h2>
      <!-- padlock when locked, chevron otherwise -->
      <svg
        v-if="locked"
        class="ml-auto flex-shrink-0 h-4 w-4 text-gray-400 dark:text-gray-500"
        xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"
      >
        <rect x="3" y="11" width="18" height="11" rx="2" ry="2" /><path d="M7 11V7a5 5 0 0 1 10 0v4" />
      </svg>
      <svg
        v-else-if="isInteractive"
        class="ml-auto flex-shrink-0 h-4 w-4 text-gray-400 dark:text-gray-500"
        xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"
      >
        <path d="M9 18l6-6-6-6" />
      </svg>
    </div>

    <!-- Locked teaser: hide the value, invite opt-in -->
    <div v-if="locked" class="py-3">
      <p class="text-sm text-gray-400 dark:text-gray-500">{{ t('placeholders.lockedHint') }}</p>
    </div>

    <div v-else-if="loading" class="animate-pulse space-y-2">
      <div class="h-8 bg-gray-200 dark:bg-gray-700 rounded w-28"></div>
      <div class="h-4 bg-gray-100 dark:bg-gray-700/60 rounded w-16"></div>
    </div>

    <!-- Lines mode: stacked labelled rows (e.g. Max Export / Max Grid Usage) -->
    <div v-else-if="hasLines" class="space-y-2.5">
      <div v-for="(line, i) in lines" :key="i" class="flex items-baseline justify-between gap-2">
        <span class="text-xs text-gray-500 dark:text-gray-400">{{ line.label }}</span>
        <span class="text-right">
          <span :class="['text-xl font-semibold tabular-nums', line.colorClass || 'text-gray-900 dark:text-white']">
            {{ line.valueText ?? '—' }}<span v-if="line.valueText && line.unit" class="text-sm text-gray-500 dark:text-gray-400 ml-1">{{ line.unit }}</span>
          </span>
          <span v-if="line.sub" class="block text-[11px] text-gray-400 dark:text-gray-500">{{ line.sub }}</span>
        </span>
      </div>
    </div>

    <div v-else-if="value !== null">
      <!-- Dual-value mode (e.g. Min / Max side by side) -->
      <div v-if="dualValue !== null" class="flex gap-6">
        <div>
          <p class="text-xs text-gray-400 dark:text-gray-500 mb-0.5">{{ dualLabel }}</p>
          <p class="text-2xl font-semibold text-gray-900 dark:text-white tabular-nums">
            {{ formattedDual }}<span v-if="unit" class="text-base text-gray-500 dark:text-gray-400 ml-1">{{ unit }}</span>
          </p>
        </div>
        <div>
          <p class="text-xs text-gray-400 dark:text-gray-500 mb-0.5">Max</p>
          <p class="text-2xl font-semibold text-gray-900 dark:text-white tabular-nums">
            {{ formattedValue }}<span v-if="unit" class="text-base text-gray-500 dark:text-gray-400 ml-1">{{ unit }}</span>
          </p>
        </div>
      </div>

      <!-- Standard single-value mode -->
      <template v-else>
        <p class="text-3xl font-semibold text-gray-900 dark:text-white tracking-tight tabular-nums">
          <span v-if="prefix" class="text-xl text-gray-400 dark:text-gray-500 mr-0.5">{{ prefix }}</span>{{ formattedValue }}<span v-if="unit" class="text-lg text-gray-500 dark:text-gray-400 ml-1">{{ unit }}</span>
        </p>
        <p v-if="formattedCost !== null" class="mt-1 text-sm text-gray-500 dark:text-gray-400">
          € {{ formattedCost }}<template v-if="formattedCostExtra !== null"> (+ {{ formattedCostExtra }})</template>
        </p>
        <!-- Contextual line: "label value unit", or label-only when no subValue.
             Shown alongside cost when both are present. -->
        <p v-if="formattedSub !== null || subLabel" class="mt-1 text-sm text-gray-500 dark:text-gray-400">
          <span v-if="subLabel" :class="{'mr-1.5': formattedSub !== null}">{{ subLabel }}</span><template v-if="formattedSub !== null"> {{ formattedSub }}<span v-if="subUnit" class="ml-0.5">{{ subUnit }}</span></template>
        </p>
      </template>
    </div>

    <div v-else class="py-3">
      <p :class="emptyText ? 'text-sm text-gray-400 dark:text-gray-500' : 'text-gray-400 dark:text-gray-500 text-sm text-center'">
        {{ emptyText ?? t('common.notAvailable') }}
      </p>
    </div>

    <!-- Computation hint (gray) — fills space freed by removing the detail modal -->
    <p v-if="description && !locked && !loading" class="mt-2 text-xs leading-snug text-gray-400 dark:text-gray-500">
      {{ description }}
    </p>
  </section>
</template>
