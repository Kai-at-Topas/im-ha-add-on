<script setup>
import { ref, computed } from 'vue';
import { useI18n } from 'vue-i18n';

const props = defineProps({
  initialConfig: { type: Object, default: () => ({}) },
});

const emit = defineEmits(['finish', 'exit']);

const { t } = useI18n();

// 'ask' | 'credentials' | 'noCredentials'
const step = ref('ask');

const isBetaTester = localStorage.getItem('topas_is_beta_tester') === 'true';

const mqttHost = ref(props.initialConfig.mqtt_host || '');
const mqttPort = ref(props.initialConfig.mqtt_port || 8883);
const mqttUser = ref(props.initialConfig.mqtt_user || '');
const mqttPassword = ref(props.initialConfig.mqtt_password || '');

const canSave = computed(
  () => !!(mqttHost.value && mqttUser.value && mqttPassword.value),
);

function showCredentials() {
  step.value = 'credentials';
}

function showNoCredentials() {
  step.value = 'noCredentials';
}

function goBack() {
  step.value = 'ask';
}

function finish() {
  emit('finish', {
    mqtt_host: mqttHost.value,
    mqtt_port: mqttPort.value,
    mqtt_user: mqttUser.value,
    mqtt_password: mqttPassword.value,
  });
}

function exit() {
  emit('exit');
}
</script>

<template>
  <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm px-4">
    <div class="w-full max-w-lg bg-white dark:bg-gray-800 rounded-xl shadow-xl border border-gray-200 dark:border-gray-700 overflow-hidden">

      <!-- Header -->
      <div class="px-6 pt-5 pb-4 border-b border-gray-100 dark:border-gray-700 flex items-center justify-between">
        <h2 class="text-base font-semibold text-gray-900 dark:text-white">
          {{ t('wizard.mqttStep1.title') }}
        </h2>
        <button
          type="button"
          @click="exit"
          class="text-xs text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
        >
          {{ t('wizard.exitWizard') }}
        </button>
      </div>

      <!-- Step: ask -->
      <div v-if="step === 'ask'" class="px-6 py-6">
        <p class="text-sm text-gray-600 dark:text-gray-300 mb-5">
          {{ t('wizard.mqttStep1.question') }}
        </p>
        <div class="space-y-3">
          <button
            type="button"
            @click="showCredentials"
            class="w-full text-left px-4 py-3 rounded-lg border-2 border-gray-200 dark:border-gray-600 hover:border-blue-400 dark:hover:border-blue-500 hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-colors text-gray-800 dark:text-gray-200 font-medium text-sm"
          >
            {{ t('wizard.mqttStep1.yes') }}
          </button>
          <button
            type="button"
            @click="showNoCredentials"
            class="w-full text-left px-4 py-3 rounded-lg border-2 border-gray-200 dark:border-gray-600 hover:border-blue-400 dark:hover:border-blue-500 hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-colors text-gray-800 dark:text-gray-200 font-medium text-sm"
          >
            {{ t('wizard.mqttStep1.no') }}
          </button>
        </div>
        <p v-if="isBetaTester" class="mt-4 text-xs text-blue-600 dark:text-blue-400">
          Wattwächter beta tester detected.
        </p>
      </div>

      <!-- Step: enter credentials -->
      <div v-else-if="step === 'credentials'" class="px-6 py-6">
        <p class="text-sm text-gray-500 dark:text-gray-400 mb-5">
          {{ t('wizard.mqttStep2a.description') }}
        </p>
        <div class="space-y-3">
          <div class="grid grid-cols-3 gap-3">
            <div class="col-span-2">
              <label class="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">{{ t('settings.mqttHost') }}</label>
              <input
                v-model="mqttHost"
                type="text"
                :placeholder="t('settings.mqttHostPlaceholder')"
                class="w-full bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md py-2 px-3 text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
              />
            </div>
            <div>
              <label class="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">{{ t('settings.mqttPort') }}</label>
              <input
                v-model.number="mqttPort"
                type="number"
                min="1"
                max="65535"
                class="w-full bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md py-2 px-3 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
              />
            </div>
          </div>
          <div>
            <label class="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">{{ t('settings.mqttUser') }}</label>
            <input
              v-model="mqttUser"
              type="text"
              autocomplete="username"
              class="w-full bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md py-2 px-3 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
            />
          </div>
          <div>
            <label class="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">{{ t('settings.mqttPassword') }}</label>
            <input
              v-model="mqttPassword"
              type="password"
              autocomplete="current-password"
              class="w-full bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md py-2 px-3 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
            />
          </div>
        </div>
        <div class="mt-5 flex items-center gap-3">
          <button
            type="button"
            @click="goBack"
            class="flex items-center gap-1.5 text-sm font-medium text-gray-500 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 transition-colors"
          >
            ← {{ t('wizard.back') }}
          </button>
          <div class="flex-1"></div>
          <button
            type="button"
            @click="finish"
            :disabled="!canSave"
            class="bg-blue-600 hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed text-white font-semibold py-2 px-5 rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
          >
            {{ t('wizard.mqttStep2a.saveAndFinish') }}
          </button>
        </div>
      </div>

      <!-- Step: no credentials -->
      <div v-else-if="step === 'noCredentials'" class="px-6 py-6">
        <div class="mb-6">
          <h3 class="text-base font-semibold text-gray-900 dark:text-white mb-3">
            {{ t('wizard.mqttStep2b.title') }}
          </h3>
          <p class="text-sm text-gray-500 dark:text-gray-400 leading-relaxed">
            {{ t('wizard.mqttStep2b.body') }}
          </p>
        </div>
        <button
          type="button"
          @click="exit"
          class="w-full bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-200 font-medium py-2.5 px-6 rounded-lg transition-colors text-sm"
        >
          {{ t('wizard.mqttStep2b.cta') }}
        </button>
        <button
          type="button"
          @click="goBack"
          class="mt-4 flex items-center gap-1.5 text-sm font-medium text-gray-500 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 transition-colors mx-auto"
        >
          ← {{ t('wizard.back') }}
        </button>
      </div>

    </div>
  </div>
</template>
