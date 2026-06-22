<script setup>
import { ref, computed, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRoute, useRouter } from 'vue-router';
import { api } from '../services/api.js';
import InfoTooltip from '../components/InfoTooltip.vue';
import EntityPicker from '../components/EntityPicker.vue';
import SetupWizard from '../components/SetupWizard.vue';
import MqttSetupWizard from '../components/MqttSetupWizard.vue';

const { t } = useI18n();
const route = useRoute();
const router = useRouter();

const entities = ref({ weather: [], power: [], energy: [] });
const config = ref({
  weather_entity: '',
  power_entity: '',
  energy_entity: '',
  cost_per_kwh: null,
  annual_basic_price: null,
  mqtt_opt_in: false,
  mqtt_host: '',
  mqtt_port: 8883,
  mqtt_user: '',
  mqtt_password: '',
  mqtt_topic: '',
});
const loading = ref(true);
const saving = ref(false);
const savedAt = ref(null);
const lastSavedConfig = ref(null);
const error = ref(null);
const confirmOptOut = ref(false);
const confirmReset = ref(false);
const resetting = ref(false);
const appVersion = ref(null);
const showWizard = ref(false);
const showMqttWizard = ref(false);
const activeTab = ref('sensors');

const TABS = [
  { key: 'sensors', label: () => t('settings.tabSensors') },
  { key: 'preferences', label: () => t('settings.tabPreferences') },
  { key: 'system', label: () => t('settings.tabSystem') },
];

const isDirty = computed(() => {
  if (!lastSavedConfig.value) return false;
  return JSON.stringify(config.value) !== lastSavedConfig.value;
});

const savedLabel = computed(() => {
  if (!savedAt.value || isDirty.value) return null;
  return t('settings.savedAt', {
    time: savedAt.value.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
  });
});

const fetchData = async () => {
  try {
    loading.value = true;
    const [entitiesRes, configRes] = await Promise.all([
      api.getEntities(),
      api.getConfig(),
    ]);
    entities.value = entitiesRes;
    config.value = configRes;
  } catch (err) {
    error.value = err.message;
  } finally {
    loading.value = false;
  }
};

const saveConfig = async () => {
  try {
    saving.value = true;
    error.value = null;
    await api.saveConfig(config.value);
    savedAt.value = new Date();
    lastSavedConfig.value = JSON.stringify(config.value);
  } catch (err) {
    error.value = err.message;
  } finally {
    saving.value = false;
  }
};

const handleOptOut = async () => {
  try {
    saving.value = true;
    error.value = null;
    await api.optOut(config.value);
    config.value.mqtt_opt_in = false;
    confirmOptOut.value = false;
  } catch (err) {
    error.value = err.message;
  } finally {
    saving.value = false;
  }
};

const handleReset = async () => {
  resetting.value = true;
  try {
    await api.resetConfig();
    localStorage.removeItem('topas_onboarding_done');
    localStorage.removeItem('topas_guided_done');
    localStorage.removeItem('topas_is_beta_tester');
    router.push('/welcome');
  } catch (err) {
    error.value = err.message;
    resetting.value = false;
    confirmReset.value = false;
  }
};

const handleWizardFinish = async (cfg) => {
  showWizard.value = false;
  if (Object.keys(cfg).length > 0) {
    try {
      await api.saveConfig(cfg);
      config.value = { ...config.value, ...cfg };
      savedAt.value = new Date();
      lastSavedConfig.value = JSON.stringify(config.value);
    } catch (err) {
      error.value = err.message;
    }
  }
  router.push('/');
};

const handleWizardExit = () => {
  showWizard.value = false;
};

const handleMqttWizardFinish = async (mqttCfg) => {
  showMqttWizard.value = false;
  try {
    await api.saveConfig(mqttCfg);
    config.value = { ...config.value, ...mqttCfg };
    savedAt.value = new Date();
    lastSavedConfig.value = JSON.stringify(config.value);
  } catch (err) {
    error.value = err.message;
  }
};

const handleMqttWizardExit = () => {
  showMqttWizard.value = false;
};

onMounted(async () => {
  await fetchData();
  try {
    const v = await api.getVersion();
    appVersion.value = v.current;
  } catch {
    // version display is non-critical
  }

  // Trigger initial config wizard if guided=true or first visit with no power entity
  if (
    route.query.guided === 'true' ||
    (!localStorage.getItem('topas_guided_done') && !config.value.power_entity)
  ) {
    showWizard.value = true;
  }

  // Trigger MQTT wizard after opt-in redirect
  if (route.query['mqtt-wizard'] === 'true' && config.value.mqtt_opt_in) {
    showMqttWizard.value = true;
  }
});
</script>

<template>
  <!-- Initial config wizard overlay -->
  <SetupWizard
    v-if="showWizard"
    :entities="entities"
    :initial-config="config"
    @finish="handleWizardFinish"
    @exit="handleWizardExit"
  />

  <!-- MQTT post-opt-in wizard overlay -->
  <MqttSetupWizard
    v-if="showMqttWizard"
    :initial-config="config"
    @finish="handleMqttWizardFinish"
    @exit="handleMqttWizardExit"
  />

  <div class="max-w-2xl mx-auto px-4 sm:px-6 py-8">
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-2xl font-bold text-gray-900 dark:text-white">{{ t('settings.title') }}</h1>
      <router-link to="/" class="text-blue-600 dark:text-blue-400 hover:underline text-sm">
        {{ t('nav.backToDashboard') }}
      </router-link>
    </div>

    <!-- Tab navigation -->
    <div class="flex gap-1 mb-6 bg-gray-100 dark:bg-gray-800 rounded-lg p-1 border border-gray-200 dark:border-gray-700">
      <button
        v-for="tab in TABS"
        :key="tab.key"
        type="button"
        @click="activeTab = tab.key"
        :class="[
          'flex-1 py-2 px-3 rounded-md text-sm font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500',
          activeTab === tab.key
            ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm'
            : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200',
        ]"
      >
        {{ tab.label() }}
      </button>
    </div>

    <div v-if="loading" class="text-center py-10">
      <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto"></div>
      <p class="mt-4 text-gray-500 dark:text-gray-400">{{ t('common.loading') }}</p>
    </div>

    <div v-else class="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-6 border border-gray-200 dark:border-gray-700">
      <!-- Error banner (always visible regardless of tab) -->
      <div v-if="error" class="mb-6 p-4 bg-red-50 dark:bg-red-900/40 border border-red-400 dark:border-red-600 text-red-700 dark:text-red-200 rounded-md">
        {{ error }}
      </div>

      <!-- ── Tab: General ── -->
      <form v-if="activeTab === 'sensors'" @submit.prevent="saveConfig" class="space-y-6">
        <!-- Sensors section title -->
        <h3 class="text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">
          {{ t('settings.entitiesTitle') }}
        </h3>

        <!-- Power entity — required -->
        <div>
          <div class="flex items-center gap-2 mb-1">
            <span class="text-sm font-medium text-gray-700 dark:text-gray-300">{{ t('settings.powerEntity') }}</span>
            <span class="text-xs font-semibold text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/30 px-1.5 py-0.5 rounded">{{ t('settings.requiredBadge') }}</span>
          </div>
          <EntityPicker
            v-model="config.power_entity"
            :candidates="entities.power"
            :help-text="t('settings.powerHelp')"
            role="power"
          />
        </div>

        <!-- Energy entity — optional -->
        <div>
          <div class="flex items-center gap-2 mb-1">
            <span class="text-sm font-medium text-gray-700 dark:text-gray-300">{{ t('settings.energyEntity') }}</span>
            <span class="text-xs font-medium text-gray-500 dark:text-gray-400 bg-gray-100 dark:bg-gray-700 px-1.5 py-0.5 rounded">{{ t('settings.optionalBadge') }}</span>
          </div>
          <EntityPicker
            v-model="config.energy_entity"
            :candidates="entities.energy"
            :help-text="t('settings.energyHelp')"
            role="energy"
            :clearable="true"
          />
          <p class="mt-1.5 text-xs text-gray-400 dark:text-gray-500 italic">{{ t('settings.energyIntegratedNote') }}</p>
        </div>

        <!-- Weather entity — optional -->
        <div>
          <div class="flex items-center gap-2 mb-1">
            <span class="text-sm font-medium text-gray-700 dark:text-gray-300">{{ t('settings.weatherEntity') }}</span>
            <span class="text-xs font-medium text-gray-500 dark:text-gray-400 bg-gray-100 dark:bg-gray-700 px-1.5 py-0.5 rounded">{{ t('settings.optionalBadge') }}</span>
          </div>
          <EntityPicker
            v-model="config.weather_entity"
            :candidates="entities.weather"
            :help-text="t('settings.weatherHelp')"
            role="weather"
            :clearable="true"
          />
        </div>

        <!-- Electricity pricing -->
        <div class="pt-2 border-t border-gray-200 dark:border-gray-700">
          <h3 class="text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-4 mt-4">
            {{ t('settings.pricingTitle') }}
          </h3>
          <div class="grid grid-cols-2 gap-4">
            <!-- Working price -->
            <div>
              <label class="flex items-center gap-2 text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                {{ t('settings.costPerKwh') }}
                <InfoTooltip :text="t('settings.costPerKwhHelp')" />
              </label>
              <div class="relative">
                <span class="absolute inset-y-0 left-3 flex items-center text-gray-500 dark:text-gray-400 text-sm select-none">€</span>
                <input
                  v-model.number="config.cost_per_kwh"
                  type="number"
                  min="0"
                  step="0.001"
                  :placeholder="t('settings.costPerKwhPlaceholder')"
                  class="w-full bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md py-2 pl-8 pr-3 text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
            <!-- Grundpreis -->
            <div>
              <label class="flex items-center gap-2 text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                {{ t('settings.annualBasicPrice') }}
                <InfoTooltip :text="t('settings.annualBasicPriceHelp')" />
              </label>
              <div class="relative">
                <span class="absolute inset-y-0 left-3 flex items-center text-gray-500 dark:text-gray-400 text-sm select-none">€</span>
                <input
                  v-model.number="config.annual_basic_price"
                  type="number"
                  min="0"
                  step="0.01"
                  :placeholder="t('settings.annualBasicPricePlaceholder')"
                  class="w-full bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md py-2 pl-8 pr-3 text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
          </div>
        </div>

        <!-- Save button -->
        <div class="pt-2">
          <button
            type="submit"
            :disabled="saving"
            class="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-4 rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
          >
            {{ saving ? t('common.saving') : t('settings.saveConfig') }}
          </button>
          <p v-if="savedLabel" class="mt-2 text-xs text-center text-green-600 dark:text-green-400">
            ✓ {{ savedLabel }}
          </p>
          <p v-else-if="isDirty && lastSavedConfig" class="mt-2 text-xs text-center text-amber-600 dark:text-amber-400">
            {{ t('settings.unsavedChanges') }}
          </p>
        </div>
      </form>

      <!-- ── Tab: Privacy ── -->
      <form v-else-if="activeTab === 'preferences'" @submit.prevent="saveConfig" class="space-y-6">
        <!-- Privacy & data synchronization -->
        <div>
          <h3 class="text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-3">
            {{ t('settings.privacyTitle') }}
          </h3>
          <p class="text-gray-500 dark:text-gray-400 text-sm mb-4">{{ t('settings.privacyBody') }}</p>

          <!-- Opted out: link to consent page -->
          <template v-if="!config.mqtt_opt_in">
            <router-link
              to="/opt-in"
              class="block w-full text-center bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-md transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {{ t('settings.optIn') }}
            </router-link>
          </template>

          <!-- Opted in: status + MQTT config form + inline revoke confirmation -->
          <template v-else>
            <p class="mb-4 inline-flex items-center gap-2 text-sm font-medium text-green-700 dark:text-green-300">
              <span class="h-2 w-2 rounded-full bg-green-500"></span>
              {{ t('settings.optInActive') }}
            </p>

            <!-- MQTT configuration fields -->
            <div class="mt-4 mb-6 space-y-3">
              <h4 class="text-sm font-semibold text-gray-700 dark:text-gray-300">
                {{ t('settings.mqttTitle') }}
              </h4>
              <!-- Host + Port -->
              <div class="grid grid-cols-3 gap-3">
                <div class="col-span-2">
                  <label class="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
                    {{ t('settings.mqttHost') }}
                  </label>
                  <input
                    v-model="config.mqtt_host"
                    type="text"
                    :placeholder="t('settings.mqttHostPlaceholder')"
                    class="w-full bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md py-2 px-3 text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                  />
                </div>
                <div>
                  <label class="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
                    {{ t('settings.mqttPort') }}
                  </label>
                  <input
                    v-model.number="config.mqtt_port"
                    type="number"
                    min="1"
                    max="65535"
                    placeholder="8883"
                    class="w-full bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md py-2 px-3 text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                  />
                </div>
              </div>
              <!-- Username -->
              <div>
                <label class="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
                  {{ t('settings.mqttUser') }}
                </label>
                <input
                  v-model="config.mqtt_user"
                  type="text"
                  autocomplete="username"
                  class="w-full bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md py-2 px-3 text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                />
              </div>
              <!-- Password -->
              <div>
                <label class="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
                  {{ t('settings.mqttPassword') }}
                </label>
                <input
                  v-model="config.mqtt_password"
                  type="password"
                  autocomplete="current-password"
                  class="w-full bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md py-2 px-3 text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                />
              </div>
            </div>

            <!-- Revoke button -->
            <button
              v-if="!confirmOptOut"
              type="button"
              @click="confirmOptOut = true"
              :disabled="saving"
              class="w-full bg-transparent border border-red-500 text-red-600 dark:text-red-400 hover:bg-red-500 hover:text-white font-medium py-2 px-4 rounded-md transition-colors disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-red-500"
            >
              {{ t('settings.optOut') }}
            </button>

            <!-- Inline revoke confirmation -->
            <div v-else class="rounded-lg border border-red-300 dark:border-red-700 bg-red-50 dark:bg-red-900/20 p-4">
              <p class="text-sm text-red-700 dark:text-red-300 mb-3">
                {{ t('settings.optOutConfirmBody') }}
              </p>
              <div class="flex gap-3">
                <button
                  type="button"
                  @click="handleOptOut"
                  :disabled="saving"
                  class="flex-1 bg-red-600 hover:bg-red-700 text-white font-medium py-2 px-3 rounded-md transition-colors text-sm disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-red-500"
                >
                  {{ saving ? t('common.saving') : t('settings.optOutConfirmYes') }}
                </button>
                <button
                  type="button"
                  @click="confirmOptOut = false"
                  :disabled="saving"
                  class="flex-1 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-200 font-medium py-2 px-3 rounded-md transition-colors text-sm disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-gray-400"
                >
                  {{ t('common.cancel') }}
                </button>
              </div>
            </div>


            <!-- Save button — only visible when opted in and MQTT fields are shown -->
            <div class="pt-4">
              <button
                type="submit"
                :disabled="saving"
                class="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-4 rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
              >
                {{ saving ? t('common.saving') : t('settings.saveConfig') }}
              </button>
              <p v-if="savedLabel" class="mt-2 text-xs text-center text-green-600 dark:text-green-400">
                ✓ {{ savedLabel }}
              </p>
              <p v-else-if="isDirty && lastSavedConfig" class="mt-2 text-xs text-center text-amber-600 dark:text-amber-400">
                {{ t('settings.unsavedChanges') }}
              </p>
            </div>
          </template>
        </div>
      </form>

      <!-- ── Tab: System ── -->
      <div v-else-if="activeTab === 'system'" class="space-y-8">
        <!-- About / version -->
        <div>
          <h3 class="text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-3">
            {{ t('settings.aboutTitle') }}
          </h3>
          <p v-if="appVersion" class="text-sm text-gray-500 dark:text-gray-400">
            {{ t('settings.version') }} {{ appVersion }}
          </p>
        </div>

        <!-- Factory Reset -->
        <div class="pt-6 border-t border-gray-200 dark:border-gray-700">
          <h3 class="text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-2">
            {{ t('settings.resetTitle') }}
          </h3>
          <p class="text-sm text-gray-500 dark:text-gray-400 mb-4">{{ t('settings.resetBody') }}</p>

          <button
            v-if="!confirmReset"
            type="button"
            @click="confirmReset = true"
            :disabled="resetting"
            class="w-full bg-transparent border border-red-500 text-red-600 dark:text-red-400 hover:bg-red-500 hover:text-white font-medium py-2 px-4 rounded-md transition-colors disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-red-500"
          >
            {{ t('settings.resetButton') }}
          </button>

          <div v-else class="rounded-lg border border-red-300 dark:border-red-700 bg-red-50 dark:bg-red-900/20 p-4">
            <p class="text-sm text-red-700 dark:text-red-300 mb-3">{{ t('settings.resetConfirmBody') }}</p>
            <div class="flex gap-3">
              <button
                type="button"
                @click="handleReset"
                :disabled="resetting"
                class="flex-1 bg-red-600 hover:bg-red-700 text-white font-medium py-2 px-3 rounded-md transition-colors text-sm disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-red-500"
              >
                {{ resetting ? t('common.saving') : t('settings.resetConfirmYes') }}
              </button>
              <button
                type="button"
                @click="confirmReset = false"
                :disabled="resetting"
                class="flex-1 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-200 font-medium py-2 px-3 rounded-md transition-colors text-sm disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-gray-400"
              >
                {{ t('common.cancel') }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
