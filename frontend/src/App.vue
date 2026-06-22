<script setup>
import AppHeader from './components/AppHeader.vue';
import logoUrl from './assets/logo-opt.svg';
import logoUrl2 from './assets/ubr_logo-opt.svg';
</script>

<template>
  <div class="relative overflow-hidden min-h-screen bg-gradient-to-b from-gray-50 to-gray-100 text-gray-900 dark:from-gray-900 dark:to-gray-950 dark:text-gray-100 transition-colors">
    <img
      :src="logoUrl"
      aria-hidden="true"
      class="pointer-events-none select-none absolute bottom-6 right-6 w-[42vw] max-w-[240px] min-w-[100px] opacity-[0.1] dark:opacity-[0.15] dark:invert"
    />
    <img
      :src="logoUrl2"
      aria-hidden="true"
      class="pointer-events-none select-none absolute bottom-6 left-6 w-[42vw] max-w-[240px] min-w-[100px] opacity-[0.1] dark:opacity-[0.15] dark:invert"
    />
    <AppHeader />
    <main>
      <router-view />
    </main>
  </div>
</template>
