<script setup>
import { useI18n } from 'vue-i18n';
import { toggleLocale } from '../i18n/index.js';

const { locale, t } = useI18n();
</script>

<template>
  <button
    type="button"
    :title="t('lang.toggle')"
    :aria-label="t('lang.toggle')"
    @click="toggleLocale"
    class="inline-flex items-center justify-center h-9 min-w-9 px-2 rounded-md border border-gray-300 dark:border-gray-600 text-sm font-semibold text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
  >
    {{ locale.toUpperCase() }}
  </button>
</template>
