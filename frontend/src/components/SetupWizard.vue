<script setup>
import { ref, computed } from 'vue';
import { useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import EntityPicker from './EntityPicker.vue';

const props = defineProps({
  entities: { type: Object, default: () => ({ weather: [], power: [], energy: [] }) },
  initialConfig: { type: Object, default: () => ({}) },
});

const emit = defineEmits(['finish', 'exit']);

const { t } = useI18n();
const router = useRouter();

const TOTAL_STEPS = 5;
const currentStep = ref(1);

const powerEntity = ref(props.initialConfig.power_entity || '');
const energyEntity = ref(props.initialConfig.energy_entity || '');
const weatherEntity = ref(props.initialConfig.weather_entity || '');
const costPerKwh = ref(props.initialConfig.cost_per_kwh ?? null);
const annualBasicPrice = ref(props.initialConfig.annual_basic_price ?? null);

const progressPct = computed(() => ((currentStep.value - 1) / TOTAL_STEPS) * 100);

const canGoNext = computed(() => {
  if (currentStep.value === 1) return !!powerEntity.value;
  return true;
});

function next() {
  if (currentStep.value < TOTAL_STEPS) currentStep.value++;
}

function back() {
  if (currentStep.value > 1) currentStep.value--;
}

function skip() {
  if (currentStep.value === 2) energyEntity.value = '';
  if (currentStep.value === 3) weatherEntity.value = '';
  if (currentStep.value < TOTAL_STEPS) currentStep.value++;
}

function exit() {
  localStorage.setItem('topas_guided_done', 'true');
  emit('exit');
}

function finish() {
  const cfg = {};
  if (powerEntity.value) cfg.power_entity = powerEntity.value;
  if (energyEntity.value) cfg.energy_entity = energyEntity.value;
  if (weatherEntity.value) cfg.weather_entity = weatherEntity.value;
  if (costPerKwh.value != null) cfg.cost_per_kwh = costPerKwh.value;
  if (annualBasicPrice.value != null) cfg.annual_basic_price = annualBasicPrice.value;
  localStorage.setItem('topas_guided_done', 'true');
  emit('finish', cfg);
}

const summaryItems = computed(() => [
  { label: t('settings.powerEntity'), value: powerEntity.value || null },
  { label: t('settings.energyEntity'), value: energyEntity.value || null },
  { label: t('settings.weatherEntity'), value: weatherEntity.value || null },
  { label: t('settings.costPerKwh'), value: costPerKwh.value != null ? `€ ${costPerKwh.value}` : null },
  { label: t('settings.annualBasicPrice'), value: annualBasicPrice.value != null ? `€ ${annualBasicPrice.value}` : null },
]);
</script>

<template>
  <!-- Full-screen overlay -->
  <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm px-4">
    <div class="w-full max-w-lg bg-white dark:bg-gray-800 rounded-xl shadow-xl border border-gray-200 dark:border-gray-700 overflow-hidden">

      <!-- Header: progress bar + exit link -->
      <div class="px-6 pt-5 pb-4 border-b border-gray-100 dark:border-gray-700">
        <div class="flex items-center justify-between mb-3">
          <span class="text-xs font-medium text-gray-500 dark:text-gray-400">
            {{ t('wizard.stepOf', { current: currentStep, total: TOTAL_STEPS }) }}
          </span>
          <button
            @click="exit"
            class="text-xs text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
          >
            {{ t('wizard.exitWizard') }}
          </button>
        </div>
        <!-- Progress bar -->
        <div class="w-full bg-gray-100 dark:bg-gray-700 rounded-full h-1.5">
          <div
            class="bg-blue-500 h-1.5 rounded-full transition-all duration-300"
            :style="{ width: progressPct + '%' }"
          ></div>
        </div>
      </div>

      <!-- Step content -->
      <div class="px-6 py-6">

        <!-- Step 1: Power sensor (required) -->
        <div v-if="currentStep === 1">
          <h2 class="text-lg font-bold text-gray-900 dark:text-white mb-1">
            {{ t('wizard.step1.title') }}
          </h2>
          <p class="text-sm text-gray-500 dark:text-gray-400 mb-5">
            {{ t('wizard.step1.description') }}
          </p>
          <EntityPicker
            v-model="powerEntity"
            :candidates="entities.power"
            :help-text="t('settings.powerHelp')"
            role="power"
          />
          <p v-if="!powerEntity" class="mt-2 text-xs text-amber-600 dark:text-amber-400">
            {{ t('wizard.step1.required') }}
          </p>
        </div>

        <!-- Step 2: Energy sensor (optional) -->
        <div v-else-if="currentStep === 2">
          <h2 class="text-lg font-bold text-gray-900 dark:text-white mb-1">
            {{ t('wizard.step2.title') }}
          </h2>
          <p class="text-sm text-gray-500 dark:text-gray-400 mb-5">
            {{ t('wizard.step2.description') }}
          </p>
          <EntityPicker
            v-model="energyEntity"
            :candidates="entities.energy"
            :help-text="t('settings.energyHelp')"
            role="energy"
            :clearable="true"
          />
        </div>

        <!-- Step 3: Weather (optional) -->
        <div v-else-if="currentStep === 3">
          <h2 class="text-lg font-bold text-gray-900 dark:text-white mb-1">
            {{ t('wizard.step3.title') }}
          </h2>
          <p class="text-sm text-gray-500 dark:text-gray-400 mb-5">
            {{ t('wizard.step3.description') }}
          </p>
          <EntityPicker
            v-model="weatherEntity"
            :candidates="entities.weather"
            :help-text="t('settings.weatherHelp')"
            role="weather"
            :clearable="true"
          />
        </div>

        <!-- Step 4: Electricity price (optional) -->
        <div v-else-if="currentStep === 4">
          <h2 class="text-lg font-bold text-gray-900 dark:text-white mb-1">
            {{ t('wizard.step4.title') }}
          </h2>
          <p class="text-sm text-gray-500 dark:text-gray-400 mb-5">
            {{ t('wizard.step4.description') }}
          </p>
          <div class="space-y-4">
            <!-- Working price -->
            <div>
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                {{ t('settings.costPerKwh') }}
              </label>
              <div class="relative w-full">
                <span class="absolute inset-y-0 left-3 flex items-center text-gray-500 dark:text-gray-400 text-sm select-none">€</span>
                <input
                  v-model.number="costPerKwh"
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
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                {{ t('settings.annualBasicPrice') }}
              </label>
              <div class="relative w-full">
                <span class="absolute inset-y-0 left-3 flex items-center text-gray-500 dark:text-gray-400 text-sm select-none">€</span>
                <input
                  v-model.number="annualBasicPrice"
                  type="number"
                  min="0"
                  step="0.01"
                  :placeholder="t('settings.annualBasicPricePlaceholder')"
                  class="w-full bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md py-2 pl-8 pr-3 text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <p class="mt-1 text-xs text-gray-400 dark:text-gray-500">{{ t('wizard.step4.grundpreisNote') }}</p>
            </div>
          </div>
        </div>

        <!-- Step 5: Done / summary -->
        <div v-else-if="currentStep === 5">
          <div class="text-center mb-5">
            <div class="text-3xl mb-2">✅</div>
            <h2 class="text-lg font-bold text-gray-900 dark:text-white mb-2">
              {{ t('wizard.step5.title') }}
            </h2>
            <p class="text-sm text-gray-500 dark:text-gray-400">
              {{ t('wizard.step5.body') }}
            </p>
          </div>
          <!-- Summary list -->
          <ul class="space-y-1.5 mb-2">
            <li
              v-for="item in summaryItems"
              :key="item.label"
              class="flex items-center justify-between text-sm"
            >
              <span class="text-gray-500 dark:text-gray-400">{{ item.label }}</span>
              <span
                :class="item.value ? 'text-gray-900 dark:text-white font-mono text-xs' : 'text-gray-300 dark:text-gray-600 text-xs italic'"
              >
                {{ item.value || t('wizard.step5.notSet') }}
              </span>
            </li>
          </ul>
        </div>

      </div>

      <!-- Footer: navigation buttons -->
      <div class="px-6 pb-6 flex items-center gap-3">
        <!-- Back -->
        <button
          v-if="currentStep > 1 && currentStep < 5"
          type="button"
          @click="back"
          class="text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition-colors"
        >
          {{ t('wizard.back') }}
        </button>
        <div class="flex-1"></div>

        <!-- Step 1-4: skip optional steps -->
        <button
          v-if="currentStep >= 2 && currentStep <= 4"
          type="button"
          @click="skip"
          class="text-sm text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
        >
          {{ t('wizard.skip') }}
        </button>

        <!-- Step 1-4: next -->
        <button
          v-if="currentStep < 5"
          type="button"
          @click="next"
          :disabled="!canGoNext"
          class="bg-blue-600 hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed text-white font-semibold py-2 px-5 rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
        >
          {{ t('wizard.next') }}
        </button>

        <!-- Step 5: finish -->
        <button
          v-if="currentStep === 5"
          type="button"
          @click="finish"
          class="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2.5 px-5 rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
        >
          {{ t('wizard.step5.cta') }}
        </button>
      </div>

    </div>
  </div>
</template>
