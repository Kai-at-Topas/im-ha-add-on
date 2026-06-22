<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { formatNumber } from '../utils/format.js';
import { useHaTimezone } from '../composables/useHaTimezone.js';

const props = defineProps({
  today: { type: Array, default: () => [] },    // 24 values (avg W per hour)
  yesterday: { type: Array, default: () => [] }, // 24 values
  unit: { type: String, default: 'W' },
  decimals: { type: Number, default: 0 },
  todayLabel: { type: String, default: 'Today' },
  yesterdayLabel: { type: String, default: 'Yesterday' },
});

const { locale } = useI18n();
const { timeZone } = useHaTimezone();

const H = 220;
const PAD = { top: 12, right: 8, bottom: 32, left: 40 };
const BAR_GAP = 0.1; // fraction of group width used as gap between groups
const INNER_GAP = 2;  // px between the two bars in a group

const containerRef = ref(null);
const width = ref(600);
let ro = null;

onMounted(() => {
  if (containerRef.value) {
    width.value = containerRef.value.clientWidth || 600;
    ro = new ResizeObserver((entries) => { width.value = entries[0].contentRect.width; });
    ro.observe(containerRef.value);
  }
});
onUnmounted(() => ro && ro.disconnect());

const plotW = computed(() => Math.max(1, width.value - PAD.left - PAD.right));
const plotH = computed(() => H - PAD.top - PAD.bottom);

const maxVal = computed(() => {
  const all = [...props.today, ...props.yesterday].filter((v) => v !== null);
  return Math.max(...all, 0.001);
});

// Each hour group occupies groupW pixels; two bars fill the interior
const groupW = computed(() => plotW.value / 24);
const barW = computed(() => Math.max(1, (groupW.value * (1 - BAR_GAP)) / 2 - INNER_GAP / 2));

function barX(hour, isToday) {
  const groupLeft = PAD.left + hour * groupW.value + groupW.value * (BAR_GAP / 2);
  return isToday ? groupLeft : groupLeft + barW.value + INNER_GAP;
}

function barH(value) {
  if (value === null) return 0;
  return (value / maxVal.value) * plotH.value;
}
function barY(value) {
  return PAD.top + plotH.value - barH(value);
}

// Y axis ticks
const yTicks = computed(() => {
  const m = maxVal.value;
  return [0, m / 2, m].map((v) => ({
    y: PAD.top + plotH.value - (v / m) * plotH.value,
    label: formatNumber(v, locale.value, props.decimals),
  }));
});

// Hover
const hoveredHour = ref(null);
function onMove(e) {
  const rect = containerRef.value?.getBoundingClientRect();
  if (!rect) return;
  const x = e.clientX - rect.left - PAD.left;
  const hour = Math.floor(x / groupW.value);
  hoveredHour.value = (hour >= 0 && hour < 24) ? hour : null;
}
function onLeave() { hoveredHour.value = null; }

const tooltip = computed(() => {
  const h = hoveredHour.value;
  if (h === null) return null;
  const tVal = props.today[h] ?? null;
  const yVal = props.yesterday[h] ?? null;
  const x = PAD.left + h * groupW.value + groupW.value / 2;
  return {
    x,
    hour: h,
    today: tVal !== null ? formatNumber(tVal, locale.value, props.decimals) : 'N/A',
    yesterday: yVal !== null ? formatNumber(yVal, locale.value, props.decimals) : 'N/A',
  };
});

const HOUR_LABELS = [0, 4, 8, 12, 16, 20];

// Current-time dashed line (fractional hour position into today's bars).
// Uses HA's timezone when known so the line matches the (HA-tz) buckets even
// when the viewer's device is in another timezone; otherwise browser-local.
const nowLineX = computed(() => {
  const now = new Date();
  let nowHour;
  if (timeZone.value) {
    const parts = new Intl.DateTimeFormat('en-GB', {
      timeZone: timeZone.value, hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
    }).formatToParts(now);
    const hh = Number(parts.find((p) => p.type === 'hour').value);
    const mm = Number(parts.find((p) => p.type === 'minute').value);
    nowHour = hh + mm / 60;
  } else {
    nowHour = now.getHours() + now.getMinutes() / 60;
  }
  return PAD.left + nowHour * groupW.value;
});
</script>

<template>
  <div ref="containerRef" class="relative w-full select-none" @mousemove="onMove" @mouseleave="onLeave">
    <svg :viewBox="`0 0 ${width} ${H}`" :width="width" :height="H" class="overflow-visible">
      <!-- Y gridlines + labels -->
      <g>
        <line
          v-for="(tk, i) in yTicks" :key="'gy' + i"
          :x1="PAD.left" :x2="width - PAD.right" :y1="tk.y" :y2="tk.y"
          class="stroke-gray-200 dark:stroke-gray-700" stroke-width="1"
        />
        <text
          v-for="(tk, i) in yTicks" :key="'ty' + i"
          :x="PAD.left - 6" :y="tk.y + 4" text-anchor="end"
          class="fill-gray-400 dark:fill-gray-500 text-[9px]"
        >{{ tk.label }}</text>
      </g>

      <!-- Hour group hover highlight -->
      <rect
        v-if="hoveredHour !== null"
        :x="PAD.left + hoveredHour * groupW"
        :y="PAD.top"
        :width="groupW"
        :height="plotH"
        class="fill-gray-100 dark:fill-gray-700/40"
        rx="2"
      />

      <!-- Bars -->
      <g v-for="h in 24" :key="h">
        <!-- Today bar (amber) -->
        <rect
          v-if="today[h - 1] !== null"
          :x="barX(h - 1, true)"
          :y="barY(today[h - 1])"
          :width="barW"
          :height="barH(today[h - 1])"
          rx="2"
          class="fill-amber-400 dark:fill-amber-500 transition-opacity duration-150"
          :opacity="hoveredHour !== null && hoveredHour !== h - 1 ? 0.4 : 1"
        />
        <!-- Yesterday bar (emerald) -->
        <rect
          v-if="yesterday[h - 1] !== null"
          :x="barX(h - 1, false)"
          :y="barY(yesterday[h - 1])"
          :width="barW"
          :height="barH(yesterday[h - 1])"
          rx="2"
          class="fill-emerald-400 dark:fill-emerald-500 transition-opacity duration-150"
          :opacity="hoveredHour !== null && hoveredHour !== h - 1 ? 0.4 : 1"
        />
      </g>

      <!-- Current-time dashed line -->
      <line
        :x1="nowLineX" :x2="nowLineX" :y1="PAD.top" :y2="PAD.top + plotH"
        class="stroke-blue-400 dark:stroke-blue-500"
        stroke-width="1.5" stroke-dasharray="5 3" opacity="0.7"
      />

      <!-- X axis hour labels -->
      <text
        v-for="h in HOUR_LABELS" :key="'xl' + h"
        :x="PAD.left + h * groupW + groupW / 2"
        :y="H - 8"
        text-anchor="middle"
        class="fill-gray-400 dark:fill-gray-500 text-[9px]"
      >{{ h }}:00</text>
    </svg>

    <!-- Tooltip -->
    <div
      v-if="tooltip"
      class="pointer-events-none absolute -translate-x-1/2 -translate-y-full rounded-lg bg-gray-900 dark:bg-gray-700 text-white text-xs px-3 py-2 shadow-xl whitespace-nowrap"
      :style="{ left: tooltip.x + 'px', top: PAD.top + 'px' }"
    >
      <div class="font-semibold mb-1">{{ String(tooltip.hour).padStart(2, '0') }}:00</div>
      <div class="flex items-center gap-2">
        <span class="h-2 w-2 rounded-full bg-amber-400 flex-shrink-0" />
        {{ todayLabel }}: {{ tooltip.today }} {{ unit }}
      </div>
      <div class="flex items-center gap-2 mt-0.5">
        <span class="h-2 w-2 rounded-full bg-emerald-400 flex-shrink-0" />
        {{ yesterdayLabel }}: {{ tooltip.yesterday }} {{ unit }}
      </div>
    </div>

    <!-- Legend -->
    <div class="flex items-center gap-4 mt-2 justify-center text-xs text-gray-500 dark:text-gray-400">
      <span class="flex items-center gap-1.5">
        <span class="h-2.5 w-2.5 rounded-sm bg-amber-400" /> {{ todayLabel }}
      </span>
      <span class="flex items-center gap-1.5">
        <span class="h-2.5 w-2.5 rounded-sm bg-emerald-400" /> {{ yesterdayLabel }}
      </span>
    </div>
  </div>
</template>
