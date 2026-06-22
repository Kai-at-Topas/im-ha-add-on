<script setup>
import { ref, computed, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { api } from '../services/api.js';
import { formatNumber, adaptiveDecimals, formatPower } from '../utils/format.js';
import { useEntityState } from '../composables/useEntityState.js';
import { useHistory } from '../composables/useHistory.js';
import { useEnergyStats } from '../composables/useEnergyStats.js';
import { useHaTimezone } from '../composables/useHaTimezone.js';
import WeatherCard from '../components/WeatherCard.vue';
import MetricTile from '../components/MetricTile.vue';
import StatCard from '../components/StatCard.vue';
import ConsumptionCard from '../components/ConsumptionCard.vue';
import DetailModal from '../components/DetailModal.vue';
import DetailChart from '../components/DetailChart.vue';
import WeatherForecast from '../components/WeatherForecast.vue';
import HourlyForecastStrip from '../components/HourlyForecastStrip.vue';
import HeatmapChart from '../components/HeatmapChart.vue';
import HourlyBarsChart from '../components/HourlyBarsChart.vue';

const { t, locale } = useI18n();

const { state, loading, error, lastUpdated } = useEntityState();
const { stats, loading: statsLoading } = useEnergyStats();
const { timeZone } = useHaTimezone();

const RANGES = [
  { key: '6h', hours: 6 },
  { key: '24h', hours: 24 },
  { key: '7d', hours: 168 },
];
const hours = ref(24);
const { history } = useHistory(hours);

// Greeting name + opt-in status (config is needed on mount for the opt-in gate;
// the greeting name is non-blocking).
const userName = ref('');
const optedIn = ref(false);

onMounted(async () => {
  try {
    const [config, profile] = await Promise.all([
      api.getConfig(),
      api.getProfile(),
    ]);
    optedIn.value = config.mqtt_opt_in === true;
    userName.value = profile?.name || '';
  } catch { /* fallback to defaults */ }
});


const greeting = computed(() =>
  userName.value ? t('dashboard.greeting', { name: userName.value }) : t('dashboard.greetingPlain')
);

const allUnconfigured = computed(
  () => state.value && ['weather', 'power', 'energy'].every((k) => state.value[k]?.status === 'unconfigured')
);

const updatedLabel = computed(() =>
  lastUpdated.value
    ? lastUpdated.value.toLocaleTimeString(locale.value, timeZone.value ? { timeZone: timeZone.value } : {})
    : ''
);

const powerPoints = computed(() => history.value?.power?.points ?? null);
const energyPoints = computed(() => history.value?.energy?.points ?? null);

const energyUnit = computed(() => stats.value?.energy?.unit ?? 'kWh');
const powerUnit = computed(() => stats.value?.power?.unit ?? 'W');
const hasCost = computed(() => !!stats.value?.cost?.per_kwh);
const statsUnconfigured = computed(() => stats.value?.status === 'unconfigured');

// ── Row 1: live power, sign-aware ───────────────────────────────────────────
// Negative = solar export (green, no minus); positive = grid usage (neutral).
// Auto-scaled to kW once past 1000 W.
const powerDisplay = computed(() => {
  const p = state.value?.power;
  if (p?.status !== 'ok' || typeof p.value !== 'number') {
    return { title: t('energy.gridUsage'), valueText: null, unit: null, colorClass: null };
  }
  const exporting = p.value < 0;
  const { value, unit } = formatPower(Math.abs(p.value), locale.value);
  return {
    title: exporting ? t('energy.gridExport') : t('energy.gridUsage'),
    valueText: value,
    unit,
    colorClass: exporting
      ? 'text-emerald-600 dark:text-emerald-400'
      : 'text-gray-900 dark:text-white',
  };
});

// Walk powerPoints backwards to find when the current export run started.
// Returns a Date (first sample in the unbroken negative streak) or null.
const exportSince = computed(() => {
  const pts = powerPoints.value;
  if (!pts || pts.length === 0) return null;
  if (pts[pts.length - 1].value >= 0) return null;
  let i = pts.length - 2;
  while (i >= 0 && pts[i].value < 0) i--;
  return new Date(pts[i + 1].time);
});

// Phantom/contextual subtext line on the Grid tile so its sparkline lines up
// with the Meter Reading tile (which always carries a subtext line).
const powerSubtext = computed(() => {
  const p = state.value?.power;
  if (p?.status === 'ok' && typeof p.value === 'number' && p.value < 0) {
    if (exportSince.value) {
      const timeStr = exportSince.value.toLocaleTimeString(locale.value, {
        hour: '2-digit',
        minute: '2-digit',
        ...(timeZone.value ? { timeZone: timeZone.value } : {}),
      });
      return t('energy.exportSince', { time: timeStr });
    }
    return t('energy.exportActive');
  }
  return ' '; // non-breaking space keeps the line height for alignment
});

// ── Data-collection hint (first 7 days in integrated mode) ──────────────────
const daysOfData = computed(() => {
  if (stats.value?.energy_source !== 'integrated') return Infinity;
  const since = stats.value?.energy?.since_timestamp;
  if (!since) return 0;
  return (Date.now() - new Date(since).getTime()) / 86400000;
});
const showDataHint = computed(() => daysOfData.value < 7);

// ── Row 1: meter reading subtext (start-of-month + month-to-date delta) ──────
const meterSubtext = computed(() => {
  // When energy is derived by integrating the power sensor, show the since date
  if (stats.value?.energy_source === 'integrated') {
    const sinceTsRaw = stats.value?.energy?.since_timestamp;
    if (sinceTsRaw) {
      const sinceDate = new Date(sinceTsRaw).toLocaleDateString(locale.value, {
        month: 'short',
        day: 'numeric',
        ...(timeZone.value ? { timeZone: timeZone.value } : {}),
      });
      return t('energy.meterSubIntegrated', { date: sinceDate });
    }
    return t('energy.meterSubIntegratedFallback');
  }

  const total = state.value?.energy?.value;
  const thisMonth = stats.value?.energy?.this_month;
  if (typeof total !== 'number' || typeof thisMonth !== 'number') return null;
  const start = formatNumber(total - thisMonth, locale.value, 0);
  const diff = formatNumber(thisMonth, locale.value, adaptiveDecimals(thisMonth));
  return t('energy.meterSub', { start, diff });
});

// ── Row 2: annual estimate subtext (LTS-aware) ──────────────────────────────
const annualSubtext = computed(() => {
  const pct = stats.value?.energy?.vs_last_year_pct;
  if (pct !== null && pct !== undefined) {
    const sign = pct > 0 ? '+' : '';
    return t('stats.vsLastYear', { pct: `${sign}${formatNumber(pct, locale.value, 0)}` });
  }
  return t('stats.basedOnPreviousMonths');
});

// ── Row 4: Min/Max → peak export vs peak grid usage (kW, with times) ─────────
const minMaxLines = computed(() => {
  const pwr = stats.value?.power;
  const min = pwr?.min_today; // most negative → peak export
  const max = pwr?.max_today; // most positive → peak grid usage
  const exportP = typeof min === 'number' && min < 0 ? formatPower(Math.abs(min), locale.value) : null;
  const gridP = typeof max === 'number' && max > 0 ? formatPower(max, locale.value) : null;
  return [
    {
      label: t('stats.maxExport'),
      valueText: exportP?.value ?? null,
      unit: exportP?.unit,
      sub: exportP ? fmtTime(pwr?.min_time) : null,
      colorClass: 'text-emerald-600 dark:text-emerald-400',
    },
    {
      label: t('stats.maxGridUsage'),
      valueText: gridP?.value ?? null,
      unit: gridP?.unit,
      sub: gridP ? fmtTime(pwr?.max_time) : null,
      colorClass: 'text-gray-900 dark:text-white',
    },
  ];
});

// ── Detail modal ──────────────────────────────────────────────────────────────
const activeDetail = ref(null);
const weatherTab = ref('hourly'); // 'hourly' | 'daily'
const comparisonTab = ref('hourly'); // 'hourly' | 'heatmap'

// Hourly power data fetched lazily when the consumption modal opens
const hourlyData = ref(null);
const hourlyLoading = ref(false);
const hourlyError = ref(null);

function setWeatherTab(tab) {
  weatherTab.value = tab;
}

async function openDetail(type) {
  if (type === 'weather') {
    weatherTab.value = 'hourly';
    activeDetail.value = 'weather';
    return;
  }
  if (type === 'consumption') {
    if (!optedIn.value) {
      activeDetail.value = 'lockedComparison';
      return;
    }
    comparisonTab.value = 'hourly';
    activeDetail.value = 'consumption';
    if (!hourlyData.value) {
      hourlyLoading.value = true;
      hourlyError.value = null;
      try {
        hourlyData.value = await api.getEnergyHourly(7);
      } catch (e) {
        hourlyError.value = e.message;
      } finally {
        hourlyLoading.value = false;
      }
    }
    return;
  }
  activeDetail.value = type;
}

function closeDetail() { activeDetail.value = null; }

// Hourly slices for comparison charts
const todayHours = computed(() => {
  if (!hourlyData.value?.days?.length) return Array(24).fill(null);
  return hourlyData.value.days[hourlyData.value.days.length - 1].hours;
});
const yesterdayHours = computed(() => {
  if (!hourlyData.value?.days?.length || hourlyData.value.days.length < 2) return Array(24).fill(null);
  return hourlyData.value.days[hourlyData.value.days.length - 2].hours;
});
const heatmapDays = computed(() => hourlyData.value?.days ?? []);
const hourlyUnit = computed(() => hourlyData.value?.unit ?? 'W');

// Min/max times formatted in HA's timezone when known (else browser-local).
function fmtTime(isoStr) {
  if (!isoStr) return '—';
  return new Date(isoStr).toLocaleTimeString(locale.value, {
    hour: '2-digit',
    minute: '2-digit',
    ...(timeZone.value ? { timeZone: timeZone.value } : {}),
  });
}

const detailTitle = computed(() => {
  const map = {
    weather: t('weather.title'),
    power: t('energy.power'),
    energy: t('energy.total'),
    consumption: t('stats.consumptionTitle'),
    minmax: t('stats.minMax'),
    lockedComparison: t('detail.viewDetails'),
  };
  return map[activeDetail.value] ?? '';
});
</script>

<template>
  <div class="max-w-5xl mx-auto px-4 sm:px-6 py-8">

    <!-- Header -->
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-2xl font-bold text-gray-900 dark:text-white">{{ greeting }}</h1>
      <span v-if="updatedLabel" class="text-xs text-gray-400 dark:text-gray-500">
        {{ t('dashboard.lastUpdated') }}: {{ updatedLabel }}
      </span>
    </div>

    <!-- Initial loading -->
    <div v-if="loading" class="text-center py-20">
      <div class="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-500 mx-auto"></div>
      <p class="mt-4 text-gray-500 dark:text-gray-400">{{ t('dashboard.loading') }}</p>
    </div>

    <!-- Error -->
    <div
      v-else-if="error"
      class="rounded-lg p-4 bg-red-50 dark:bg-red-900/30 border border-red-300 dark:border-red-700 text-red-700 dark:text-red-200"
    >
      {{ t('common.error') }}: {{ error }}
    </div>

    <!-- No entities configured -->
    <div v-else-if="allUnconfigured" class="text-center py-20">
      <p class="text-gray-700 dark:text-gray-200 font-medium">{{ t('dashboard.notConfigured') }}</p>
      <p class="mt-2 text-gray-500 dark:text-gray-400">{{ t('dashboard.configurePrompt') }}</p>
      <router-link
        to="/settings"
        class="inline-flex mt-6 items-center px-4 py-2 rounded-md bg-blue-600 hover:bg-blue-700 text-white font-medium transition-colors"
      >
        {{ t('dashboard.goToSettings') }}
      </router-link>
    </div>

    <template v-else>
      <!-- ── Data-collection hint ── -->
      <div
        v-if="showDataHint"
        class="mt-6 p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-700 rounded-xl"
      >
        <p class="text-sm font-medium text-blue-800 dark:text-blue-200 mb-1">
          {{ t('dashboard.dataHintTitle') }}
        </p>
        <p class="text-sm text-blue-700 dark:text-blue-300 leading-relaxed">
          {{ t('dashboard.dataHintBody') }}
        </p>
      </div>
      <!-- ── Row 1: Weather · Power · Total Energy ── -->
      <div class="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
        <MetricTile
          icon="power"
          :title="powerDisplay.title"
          :metric="state.power"
          :value-text="powerDisplay.valueText"
          :value-unit="powerDisplay.unit"
          :value-color-class="powerDisplay.colorClass"
          :subtext="powerSubtext"
          :history="powerPoints"
          color="#f59e0b"
          clickable
          @open="openDetail('power')"
          class="card-enter"
          style="animation-delay: 60ms"
        />
        <MetricTile
          icon="activity"
          :title="t('energy.meterReading')"
          :metric="state.energy"
          :subtext="meterSubtext"
          :history="energyPoints"
          color="#10b981"
          clickable
          @open="openDetail('energy')"
          class="card-enter"
          style="animation-delay: 120ms"
        />
        <WeatherCard
          :weather="state.weather"
          clickable
          @open="openDetail('weather')"
          class="card-enter"
          style="animation-delay: 0ms"
        />
      </div>

      <!-- ── Row 2: Period summary ── -->
      <div class="grid gap-6 sm:grid-cols-3 mt-6">
        <StatCard
          :title="t('stats.today')"
          :value="stats?.energy?.today ?? null"
          :unit="energyUnit"
          :decimals="adaptiveDecimals(stats?.energy?.today)"
          :cost-value="hasCost ? (stats?.cost?.today ?? null) : null"
          :cost-extra="hasCost ? (stats?.cost?.today_grundpreis ?? null) : null"
          :sub-value="stats?.energy?.yesterday_so_far ?? null"
          :sub-label="t('stats.yesterdayAtThisTime')"
          :sub-unit="energyUnit"
          :loading="statsLoading"
          variant="energy"
          icon="clock"
          class="card-enter"
          style="animation-delay: 0ms"
        />
        <StatCard
          :title="t('stats.thisMonth')"
          :value="stats?.energy?.this_month ?? null"
          :unit="energyUnit"
          :cost-value="hasCost ? (stats?.cost?.this_month ?? null) : null"
          :cost-extra="hasCost ? (stats?.cost?.this_month_grundpreis ?? null) : null"
          :sub-value="stats?.energy?.month_end_estimate ?? null"
          :sub-label="t('stats.monthEndEstimate')"
          :sub-unit="energyUnit"
          :loading="statsLoading"
          variant="energy"
          :decimals="0"
          class="card-enter"
          style="animation-delay: 60ms"
        />
        <StatCard
          :title="t('stats.annualEstimate')"
          :value="stats?.energy?.annual_estimate ?? null"
          :unit="energyUnit"
          :cost-value="hasCost ? (stats?.cost?.annual_estimate ?? null) : null"
          :cost-extra="hasCost ? (stats?.cost?.annual_grundpreis ?? null) : null"
          :sub-value="null"
          :sub-label="annualSubtext"
          :loading="statsLoading"
          variant="energy"
          :decimals="0"
          prefix="~"
          icon="trending-up"
          class="card-enter"
          style="animation-delay: 120ms"
        />
      </div>

      <!-- ── Row 3: Consumption comparison ── -->
      <template v-if="!statsUnconfigured">
        <div class="mt-6">
          <ConsumptionCard
            :today="stats?.energy?.today ?? null"
            :yesterday="stats?.energy?.yesterday ?? null"
            :thirty-day-avg="stats?.energy?.daily_avg ?? null"
            :thirty-day-avg-days="stats?.energy?.daily_avg_days ?? null"
            :unit="energyUnit"
            :loading="statsLoading"
            clickable
            @open="openDetail('consumption')"
            class="card-enter"
            style="animation-delay: 0ms"
          />
        </div>

        <!-- ── Row 4: Power analysis — locked teaser until opted in ── -->
        <div class="grid gap-6 sm:grid-cols-2 mt-6">
          <StatCard
            :title="t('stats.baseLoad')"
            :value="stats?.power?.base_load ?? null"
            :unit="powerUnit"
            :empty-text="t('stats.calculatedNightly')"
            :description="optedIn ? t('detail.baseLoadDescription') : null"
            :loading="statsLoading"
            variant="power"
            icon="moon"
            :locked="!optedIn"
            :clickable="!optedIn"
            @open="openDetail('lockedComparison')"
            class="card-enter"
            style="animation-delay: 0ms"
          />
          <StatCard
            :title="t('stats.minMax')"
            :lines="minMaxLines"
            :loading="statsLoading"
            variant="power"
            icon="scale"
            :locked="!optedIn"
            clickable
            @open="openDetail(optedIn ? 'minmax' : 'lockedComparison')"
            class="card-enter"
            style="animation-delay: 60ms"
          />
        </div>
      </template>
    </template>

    <!-- ── Detail modals ── -->
    <DetailModal v-if="activeDetail" :title="detailTitle" @close="closeDetail">

      <!-- Weather → hourly strip + 7-day forecast tabs -->
      <template v-if="activeDetail === 'weather'">
        <div class="flex gap-1 mb-4 p-1 bg-gray-100 dark:bg-gray-900/60 rounded-lg">
          <button
            type="button"
            @click="setWeatherTab('hourly')"
            :class="['flex-1 flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-colors',
              weatherTab === 'hourly'
                ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm'
                : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200']"
          >
            {{ t('forecast.hourlyTab') }}
          </button>
          <button
            type="button"
            @click="setWeatherTab('daily')"
            :class="['flex-1 flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-colors',
              weatherTab === 'daily'
                ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm'
                : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200']"
          >
            {{ t('forecast.dailyTab') }}
          </button>
        </div>
        <div class="h-[28rem] overflow-y-auto">
          <HourlyForecastStrip v-if="weatherTab === 'hourly'" />
          <WeatherForecast v-else />
        </div>
      </template>

      <!-- Power → chart + range selector -->
      <template v-else-if="activeDetail === 'power'">
        <div class="flex items-center justify-between mb-4">
          <span class="text-xs text-gray-400 dark:text-gray-500">{{ t('dashboard.history') }}</span>
          <div class="inline-flex rounded-md border border-gray-300 dark:border-gray-600 overflow-hidden">
            <button
              v-for="r in RANGES" :key="r.key" type="button"
              @click="hours = r.hours"
              :class="['px-3 py-1 text-xs font-medium transition-colors',
                hours === r.hours ? 'bg-blue-600 text-white' : 'bg-transparent text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700']"
            >{{ t(`dashboard.range.${r.key}`) }}</button>
          </div>
        </div>
        <DetailChart :points="powerPoints || []" :unit="state.power?.unit || 'W'" color="#f59e0b" />
        <div class="mt-4 rounded-lg bg-gray-50 dark:bg-gray-900/40 p-3 flex gap-2">
          <svg class="h-4 w-4 flex-shrink-0 mt-0.5 text-gray-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>
          <p class="text-xs text-gray-500 dark:text-gray-400">{{ t('detail.powerDescription') }}</p>
        </div>
      </template>

      <!-- Energy → chart + range selector -->
      <template v-else-if="activeDetail === 'energy'">
        <div class="flex items-center justify-between mb-4">
          <span class="text-xs text-gray-400 dark:text-gray-500">{{ t('dashboard.history') }}</span>
          <div class="inline-flex rounded-md border border-gray-300 dark:border-gray-600 overflow-hidden">
            <button
              v-for="r in RANGES" :key="r.key" type="button"
              @click="hours = r.hours"
              :class="['px-3 py-1 text-xs font-medium transition-colors',
                hours === r.hours ? 'bg-blue-600 text-white' : 'bg-transparent text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700']"
            >{{ t(`dashboard.range.${r.key}`) }}</button>
          </div>
        </div>
        <DetailChart :points="energyPoints || []" :unit="state.energy?.unit || 'kWh'" color="#10b981" />
        <div class="mt-4 rounded-lg bg-gray-50 dark:bg-gray-900/40 p-3 flex gap-2">
          <svg class="h-4 w-4 flex-shrink-0 mt-0.5 text-gray-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>
          <p class="text-xs text-gray-500 dark:text-gray-400">{{ t('detail.energyDescription') }}</p>
        </div>
      </template>

      <!-- Consumption → tabbed: hourly bar chart + heatmap (both in W) -->
      <template v-else-if="activeDetail === 'consumption'">
        <div class="flex gap-1 mb-4 p-1 bg-gray-100 dark:bg-gray-900/60 rounded-lg">
          <button
            type="button"
            @click="comparisonTab = 'hourly'"
            :class="['flex-1 px-3 py-1.5 rounded-md text-sm font-medium transition-colors',
              comparisonTab === 'hourly'
                ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm'
                : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200']"
          >
            {{ t('detail.hourlyTab') }}
          </button>
          <button
            type="button"
            @click="comparisonTab = 'heatmap'"
            :class="['flex-1 px-3 py-1.5 rounded-md text-sm font-medium transition-colors',
              comparisonTab === 'heatmap'
                ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm'
                : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200']"
          >
            {{ t('detail.heatmapTab') }}
          </button>
        </div>

        <div v-if="hourlyLoading" class="flex items-center justify-center py-16">
          <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-emerald-500"></div>
        </div>
        <div v-else-if="hourlyError" class="text-center text-sm text-red-500 py-8">{{ hourlyError }}</div>
        <template v-else-if="comparisonTab === 'hourly'">
          <p class="text-xs text-gray-400 dark:text-gray-500 mb-4">{{ t('detail.hourlyDescription') }}</p>
          <HourlyBarsChart
            :today="todayHours"
            :yesterday="yesterdayHours"
            :unit="hourlyUnit"
            :today-label="t('stats.today')"
            :yesterday-label="t('stats.yesterday')"
          />
        </template>
        <template v-else>
          <p class="text-xs text-gray-400 dark:text-gray-500 mb-4">{{ t('detail.heatmapDescription') }}</p>
          <HeatmapChart :days="heatmapDays" :unit="hourlyUnit" />
        </template>
      </template>

      <!-- Locked: comparison details require opt-in -->
      <template v-else-if="activeDetail === 'lockedComparison'">
        <div class="flex flex-col items-center gap-4 py-8 text-center">
          <svg class="h-10 w-10 text-gray-300 dark:text-gray-600" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
          <p class="text-sm text-gray-500 dark:text-gray-400 max-w-xs">{{ t('settings.privacyBody') }}</p>
          <router-link to="/settings" class="text-sm font-medium text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300" @click="closeDetail">
            {{ t('dashboard.goToSettings') }} →
          </router-link>
        </div>
      </template>

      <!-- Min / Max with timestamps -->
      <template v-else-if="activeDetail === 'minmax'">
        <div class="rounded-lg bg-gray-50 dark:bg-gray-900/40 p-4 flex gap-3 mb-6">
          <svg class="h-5 w-5 flex-shrink-0 mt-0.5 text-amber-500" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>
          <p class="text-sm text-gray-600 dark:text-gray-300">{{ t('detail.minMaxDescription') }}</p>
        </div>
        <div class="grid grid-cols-2 gap-4 text-center">
          <div class="rounded-xl border border-gray-200 dark:border-gray-700 p-4">
            <p class="text-xs text-gray-400 mb-1">{{ t('stats.maxExport') }}</p>
            <p class="text-2xl font-semibold text-emerald-600 dark:text-emerald-400 tabular-nums">
              {{ minMaxLines[0].valueText ?? '—' }} <span class="text-base text-gray-400">{{ minMaxLines[0].unit }}</span>
            </p>
            <p class="text-xs text-gray-400 mt-1">{{ minMaxLines[0].sub ?? fmtTime(stats?.power?.min_time) }}</p>
          </div>
          <div class="rounded-xl border border-gray-200 dark:border-gray-700 p-4">
            <p class="text-xs text-gray-400 mb-1">{{ t('stats.maxGridUsage') }}</p>
            <p class="text-2xl font-semibold text-gray-900 dark:text-white tabular-nums">
              {{ minMaxLines[1].valueText ?? '—' }} <span class="text-base text-gray-400">{{ minMaxLines[1].unit }}</span>
            </p>
            <p class="text-xs text-gray-400 mt-1">{{ minMaxLines[1].sub ?? fmtTime(stats?.power?.max_time) }}</p>
          </div>
        </div>
      </template>

    </DetailModal>
  </div>
</template>
