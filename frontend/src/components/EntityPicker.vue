<script setup>
import { ref, computed, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import InfoTooltip from './InfoTooltip.vue';

const props = defineProps({
  candidates: { type: Array, default: () => [] },
  modelValue: { type: String, default: '' },
  label: { type: String, default: '' },
  helpText: { type: String, default: '' },
  role: { type: String, default: '' },
  clearable: { type: Boolean, default: false },
});
const emit = defineEmits(['update:modelValue']);
const { t, te } = useI18n();

const showChooser = ref(false);

// Auto-select the recommended candidate (first in sorted list) when none is
// configured yet. Runs when candidates load in (async) — does nothing if the
// user already has a saved entity.
watch(
  () => props.candidates,
  (candidates) => {
    if (!props.modelValue && !props.clearable && candidates.length > 0) {
      emit('update:modelValue', candidates[0].entity_id);
    }
  },
  { immediate: true },
);

const selected = computed(() =>
  props.candidates.find((c) => c.entity_id === props.modelValue) ?? null,
);

function formatReading(c) {
  if (c.value === null || c.value === undefined) return '—';
  if (props.role === 'weather') {
    const key = `weather.conditions.${c.value}`;
    return te(key) ? t(key) : c.value;
  }
  if (typeof c.value === 'number') {
    const formatted = c.value.toLocaleString(undefined, { maximumFractionDigits: 1 });
    return c.unit ? `${formatted} ${c.unit}` : formatted;
  }
  return String(c.value);
}

function choose(entityId) {
  emit('update:modelValue', entityId);
  showChooser.value = false;
}

function optionLabel(c) {
  const reading = formatReading(c);
  const warn = c.validation.status === 'warn' ? ' ⚠' : '';
  return `${c.friendly_name} — ${reading}${warn}`;
}
</script>

<template>
  <div>
    <label v-if="label" class="flex items-center gap-2 text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
      {{ label }}
      <InfoTooltip v-if="helpText" :text="helpText" />
    </label>

    <!-- No candidates at all -->
    <div
      v-if="candidates.length === 0"
      class="rounded-lg border border-dashed border-gray-300 dark:border-gray-600 p-4 text-sm text-gray-500 dark:text-gray-400 text-center"
    >
      {{ t('settings.noEntitiesFound') }}
    </div>

    <!-- Empty state (clearable, nothing selected, chooser closed) -->
    <div
      v-else-if="clearable && !selected && !showChooser"
      class="rounded-lg border border-dashed border-gray-300 dark:border-gray-600 p-3.5 flex items-center justify-between"
    >
      <span class="text-sm text-gray-400 dark:text-gray-500 italic">{{ t('settings.selectEntity') }}</span>
      <button
        type="button"
        @click="showChooser = true"
        class="text-xs text-blue-600 dark:text-blue-400 hover:underline focus:outline-none focus:ring-2 focus:ring-blue-500 rounded"
      >
        {{ t('settings.changeEntity') }} ▾
      </button>
    </div>

    <!-- Confirmation card: entity is selected and chooser is closed -->
    <div
      v-else-if="selected && !showChooser"
      :class="[
        'rounded-lg border p-3.5 transition-colors',
        selected.validation.status === 'warn'
          ? 'border-amber-300 dark:border-amber-600 bg-amber-50/60 dark:bg-amber-900/20'
          : 'border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-700/60',
      ]"
    >
      <div class="flex items-center justify-between gap-2">
        <div class="min-w-0">
          <p class="text-sm font-medium text-gray-900 dark:text-white truncate">
            {{ selected.friendly_name }}
          </p>
          <p class="text-xs text-gray-500 dark:text-gray-400 mt-0.5 tabular-nums">
            {{ formatReading(selected) }}
          </p>
        </div>

        <div class="flex items-center gap-2 shrink-0">
          <!-- Validation badge -->
          <span
            v-if="selected.validation.status === 'ok'"
            class="flex items-center justify-center h-5 w-5 rounded-full bg-green-100 dark:bg-green-900/40 text-green-600 dark:text-green-400"
            aria-label="Valid"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
              <path d="M20 6 9 17l-5-5" />
            </svg>
          </span>
          <span
            v-else
            class="flex items-center justify-center h-5 w-5 rounded-full bg-amber-100 dark:bg-amber-900/40 text-amber-600 dark:text-amber-400"
            aria-label="Warning"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
              <path d="M12 9v4M12 17h.01" />
              <path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
            </svg>
          </span>

          <div class="flex items-center gap-2">
            <button
              v-if="clearable"
              type="button"
              @click="choose('')"
              class="text-xs text-gray-400 dark:text-gray-500 hover:text-red-500 dark:hover:text-red-400 focus:outline-none transition-colors leading-none"
              title="Remove"
            >
              ✕
            </button>
            <button
              type="button"
              @click="showChooser = true"
              class="text-xs text-blue-600 dark:text-blue-400 hover:underline focus:outline-none focus:ring-2 focus:ring-blue-500 rounded"
            >
              {{ t('settings.changeEntity') }} ▾
            </button>
          </div>
        </div>
      </div>

      <!-- Validation warning reason -->
      <p
        v-if="selected.validation.status === 'warn' && selected.validation.reason"
        class="mt-2 text-xs text-amber-700 dark:text-amber-300"
      >
        {{ t(`settings.validation.${selected.validation.reason}`) }}
      </p>
    </div>

    <!-- Chooser dropdown: no selection yet, or user clicked Change -->
    <div v-else>
      <select
        :value="modelValue"
        @change="choose($event.target.value)"
        class="w-full bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md py-2 px-3 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
      >
        <option value="">{{ t('settings.selectEntity') }}</option>
        <option v-for="c in candidates" :key="c.entity_id" :value="c.entity_id">
          {{ optionLabel(c) }}
        </option>
      </select>
      <button
        v-if="selected"
        type="button"
        @click="showChooser = false"
        class="mt-1.5 text-xs text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300 focus:outline-none"
      >
        ← {{ t('common.back') }}
      </button>
    </div>
  </div>
</template>
