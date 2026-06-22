<script setup>
import { useI18n } from 'vue-i18n';
import ThemeToggle from './ThemeToggle.vue';
import LangSwitch from './LangSwitch.vue';

const { t } = useI18n();
</script>

<template>
  <header class="sticky top-0 z-10 border-b border-gray-200 dark:border-gray-700 bg-white/80 dark:bg-gray-900/80 backdrop-blur">
    <div class="max-w-5xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">
      <router-link to="/" class="flex items-center gap-2 font-semibold text-gray-900 dark:text-white">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-blue-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M3 3v18h18" />
          <path d="M7 14l4-4 3 3 5-6" />
        </svg>
        <span>{{ t('app.title') }}</span>
      </router-link>

      <nav class="flex items-center gap-2">
        <!-- Settings link: icon+text on all sizes, text hidden on very small screens -->
        <router-link
          to="/settings"
          class="inline-flex items-center gap-1.5 h-9 px-3 rounded-md text-sm text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500"
          :aria-label="t('nav.settings')"
        >
          <!-- Sliders/settings icon -->
          <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="4" y1="21" x2="4" y2="14"/>
            <line x1="4" y1="10" x2="4" y2="3"/>
            <line x1="12" y1="21" x2="12" y2="12"/>
            <line x1="12" y1="8" x2="12" y2="3"/>
            <line x1="20" y1="21" x2="20" y2="16"/>
            <line x1="20" y1="12" x2="20" y2="3"/>
            <line x1="1" y1="14" x2="7" y2="14"/>
            <line x1="9" y1="8" x2="15" y2="8"/>
            <line x1="17" y1="16" x2="23" y2="16"/>
          </svg>
          <span class="hidden sm:inline">{{ t('nav.settings') }}</span>
        </router-link>
        <LangSwitch />
        <ThemeToggle />
      </nav>
    </div>
  </header>
</template>
