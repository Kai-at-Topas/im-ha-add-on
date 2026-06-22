<script setup>
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import { api } from '../services/api.js';

const { t } = useI18n();
const router = useRouter();

// step: 0=hero, 1=beta?, 2a=wattwaechter?, 2b=has power sensor?, 2a_no=not set up yet
const step = ref(0);
const saving = ref(false);
const error = ref(null);

const WATTWAECHTER_POWER = 'sensor.wattwaechter_tasmota_sgm_power';
const WATTWAECHTER_ENERGY = 'sensor.wattwaechter_tasmota_sgm_e_in';

function finish(destination = '/') {
  localStorage.setItem('topas_onboarding_done', 'true');
  router.push(destination);
}

function skip() {
  finish('/');
}

async function confirmWattwaechterSetup() {
  saving.value = true;
  error.value = null;
  try {
    await api.saveConfig({
      power_entity: WATTWAECHTER_POWER,
      energy_entity: WATTWAECHTER_ENERGY,
    });
    localStorage.setItem('topas_is_beta_tester', 'true');
    finish('/');
  } catch (err) {
    error.value = err.message;
  } finally {
    saving.value = false;
  }
}
</script>

<template>
  <div class="min-h-[calc(100vh-3.5rem)] flex flex-col items-center justify-center px-4 py-6">
    <div class="w-full max-w-lg">

      <!-- Skip link directly above card -->
      <div class="flex justify-end mb-3">
        <button
          @click="skip"
          class="text-sm text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
        >
          {{ t('welcome.skip') }}
        </button>
      </div>

      <!-- Card -->
      <div class="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-8">

        <!-- Error -->
        <div v-if="error" class="mb-4 p-3 bg-red-50 dark:bg-red-900/40 border border-red-300 dark:border-red-600 text-red-700 dark:text-red-200 rounded-md text-sm">
          {{ error }}
        </div>

        <!-- Step 0: Hero -->
        <div v-if="step === 0">
          <div class="text-center mb-8">
            <h1 class="text-2xl font-bold text-gray-900 dark:text-white mb-4">
              {{ t('welcome.step0.title') }}
            </h1>
            <p class="text-gray-500 dark:text-gray-400 leading-relaxed">
              {{ t('welcome.step0.body') }}
            </p>
          </div>
          <button
            @click="step = 1"
            class="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 px-6 rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
          >
            {{ t('welcome.step0.cta') }}
          </button>
        </div>

        <!-- Step 1: Beta tester? -->
        <div v-else-if="step === 1">
          <h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-6 leading-snug">
            {{ t('welcome.step1.question') }}
          </h2>
          <div class="space-y-3">
            <button
              @click="step = '2a'"
              class="w-full text-left px-4 py-3 rounded-lg border-2 border-gray-200 dark:border-gray-600 hover:border-blue-400 dark:hover:border-blue-500 hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-colors text-gray-800 dark:text-gray-200 font-medium"
            >
              {{ t('welcome.step1.yes') }}
            </button>
            <button
              @click="step = '2b'"
              class="w-full text-left px-4 py-3 rounded-lg border-2 border-gray-200 dark:border-gray-600 hover:border-blue-400 dark:hover:border-blue-500 hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-colors text-gray-800 dark:text-gray-200 font-medium"
            >
              {{ t('welcome.step1.no') }}
            </button>
          </div>
          <button
            @click="step = 0"
            class="mt-6 flex items-center gap-1.5 text-sm font-medium text-gray-500 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 transition-colors"
          >
            ← {{ t('common.back') }}
          </button>
        </div>

        <!-- Step 2A: Is Wattwächter set up? -->
        <div v-else-if="step === '2a'">
          <h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-6 leading-snug">
            {{ t('welcome.step2a.question') }}
          </h2>
          <div class="space-y-3">
            <button
              @click="confirmWattwaechterSetup"
              :disabled="saving"
              class="w-full text-left px-4 py-3 rounded-lg border-2 border-gray-200 dark:border-gray-600 hover:border-green-400 dark:hover:border-green-500 hover:bg-green-50 dark:hover:bg-green-900/20 transition-colors text-gray-800 dark:text-gray-200 font-medium disabled:opacity-50"
            >
              {{ saving ? t('common.saving') : t('welcome.step2a.yes') }}
            </button>
            <button
              @click="step = '2a_no'"
              :disabled="saving"
              class="w-full text-left px-4 py-3 rounded-lg border-2 border-gray-200 dark:border-gray-600 hover:border-blue-400 dark:hover:border-blue-500 hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-colors text-gray-800 dark:text-gray-200 font-medium disabled:opacity-50"
            >
              {{ t('welcome.step2a.no') }}
            </button>
          </div>
          <button
            @click="step = 1"
            class="mt-6 flex items-center gap-1.5 text-sm font-medium text-gray-500 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 transition-colors"
          >
            ← {{ t('common.back') }}
          </button>
        </div>

        <!-- Step 2A not yet: instructions to set up Wattwächter -->
        <div v-else-if="step === '2a_no'">
          <div class="text-center mb-6">
            <div class="text-3xl mb-3">📦</div>
            <h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-3">
              {{ t('welcome.step2a.no') }}
            </h2>
            <p class="text-gray-500 dark:text-gray-400 text-sm leading-relaxed">
              {{ t('welcome.step2a.notYetBody') }}
            </p>
          </div>
          <button
            @click="finish('/')"
            class="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 px-6 rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {{ t('welcome.step2a.notYetCta') }}
          </button>
          <button
            @click="step = '2a'"
            class="mt-4 flex items-center gap-1.5 text-sm font-medium text-gray-500 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 transition-colors mx-auto"
          >
            ← {{ t('common.back') }}
          </button>
        </div>

        <!-- Step 2B: General user — has power sensor? -->
        <div v-else-if="step === '2b'">
          <h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-6 leading-snug">
            {{ t('welcome.step2b.question') }}
          </h2>
          <div class="space-y-3">
            <button
              @click="finish('/settings?guided=true')"
              class="w-full text-left px-4 py-3 rounded-lg border-2 border-gray-200 dark:border-gray-600 hover:border-green-400 dark:hover:border-green-500 hover:bg-green-50 dark:hover:bg-green-900/20 transition-colors text-gray-800 dark:text-gray-200 font-medium"
            >
              {{ t('welcome.step2b.yes') }}
            </button>
            <button
              @click="step = '2b_no'"
              class="w-full text-left px-4 py-3 rounded-lg border-2 border-gray-200 dark:border-gray-600 hover:border-blue-400 dark:hover:border-blue-500 hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-colors text-gray-800 dark:text-gray-200 font-medium"
            >
              {{ t('welcome.step2b.no') }}
            </button>
          </div>
          <button
            @click="step = 1"
            class="mt-6 flex items-center gap-1.5 text-sm font-medium text-gray-500 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 transition-colors"
          >
            ← {{ t('common.back') }}
          </button>
        </div>

        <!-- Step 2B no: explain importance of power sensor -->
        <div v-else-if="step === '2b_no'">
          <div class="mb-6">
            <div class="text-3xl text-center mb-3">🔌</div>
            <p class="text-gray-600 dark:text-gray-300 text-sm leading-relaxed">
              {{ t('welcome.step2b.noBody') }}
            </p>
          </div>
          <button
            @click="finish('/')"
            class="w-full bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-200 font-medium py-3 px-6 rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-gray-400"
          >
            {{ t('welcome.step2b.noCta') }}
          </button>
          <button
            @click="step = '2b'"
            class="mt-4 flex items-center gap-1.5 text-sm font-medium text-gray-500 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 transition-colors mx-auto"
          >
            ← {{ t('common.back') }}
          </button>
        </div>

      </div>
    </div>
  </div>
</template>
