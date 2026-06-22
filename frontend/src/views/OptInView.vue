<script setup>
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import { api } from '../services/api.js';

const { t } = useI18n();
const router = useRouter();
const loading = ref(false);
const agreed = ref(false);
const error = ref(null);

const handleAccept = async () => {
  loading.value = true;
  error.value = null;
  try {
    await api.acceptOptIn();
    router.push('/settings?mqtt-wizard=true');
  } catch (err) {
    error.value = err.message;
  } finally {
    loading.value = false;
  }
};
</script>

<template>
  <div class="flex flex-col justify-center py-12 px-4 sm:px-6 lg:px-8">
    <div class="sm:mx-auto sm:w-full sm:max-w-xl mb-4">
      <router-link to="/" class="text-blue-600 dark:text-blue-400 hover:underline text-sm">
        {{ t('nav.backToDashboard') }}
      </router-link>
    </div>
    <div class="sm:mx-auto sm:w-full sm:max-w-md">
      <h2 class="text-center text-3xl font-extrabold text-gray-900 dark:text-white">
        {{ t('optIn.title') }}
      </h2>
    </div>

    <div class="mt-8 sm:mx-auto sm:w-full sm:max-w-xl">
      <div class="bg-white dark:bg-gray-800 py-8 px-4 shadow sm:rounded-lg sm:px-10 border border-gray-200 dark:border-gray-700">
        <div class="text-sm text-gray-500 dark:text-gray-400 mb-6 space-y-3">
          <h3 class="text-gray-900 dark:text-white font-semibold">{{ t('optIn.termsTitle') }}</h3>
          <p>{{ t('optIn.intro') }}</p>
          <ul class="list-disc pl-5 space-y-2">
            <li>{{ t('optIn.point1') }}</li>
            <li>{{ t('optIn.point2') }}</li>
            <li>{{ t('optIn.point3') }}</li>
          </ul>
          <p class="font-semibold text-orange-600 dark:text-orange-400">{{ t('optIn.locked') }}</p>
        </div>

        <label class="flex items-start gap-3 cursor-pointer mb-5">
          <input
            v-model="agreed"
            type="checkbox"
            class="mt-0.5 h-4 w-4 shrink-0 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
          />
          <span class="text-sm text-gray-700 dark:text-gray-300">{{ t('optIn.confirmLabel') }}</span>
        </label>

        <button
          @click="handleAccept"
          :disabled="!agreed || loading"
          class="w-full flex justify-center py-3 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {{ loading ? t('optIn.processing') : t('optIn.agree') }}
        </button>

        <div v-if="error" class="mt-4 text-sm text-red-600 dark:text-red-400 text-center">
          {{ error }}
        </div>
      </div>
    </div>
  </div>
</template>
