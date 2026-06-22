<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { formatNumber } from '../utils/format.js';
import { useHaTimezone } from '../composables/useHaTimezone.js';

const props = defineProps({
  points: { type: Array, default: () => [] },
  unit: { type: String, default: '' },
  color: { type: String, default: '#3b82f6' },
});

const { t, locale } = useI18n();
const { timeZone } = useHaTimezone();

const H = 260;
const PAD = { top: 16, right: 14, bottom: 28, left: 52 };

const containerRef = ref(null);
const svgRef = ref(null);
const width = ref(600);
const hoverIndex = ref(null);

let ro = null;
onMounted(() => {
  if (containerRef.value) {
    width.value = containerRef.value.clientWidth || 600;
    ro = new ResizeObserver((entries) => {
      width.value = entries[0].contentRect.width;
    });
    ro.observe(containerRef.value);
  }
});
onUnmounted(() => ro && ro.disconnect());

const valid = computed(() => (props.points || []).filter((p) => p.value !== null && p.value !== undefined));

const bounds = computed(() => {
  const pts = valid.value;
  if (!pts.length) return null;
  const times = pts.map((p) => new Date(p.time).getTime());
  const values = pts.map((p) => p.value);
  const minV = Math.min(...values);
  const maxV = Math.max(...values);
  return {
    minT: Math.min(...times),
    maxT: Math.max(...times),
    minV,
    maxV,
    spanT: Math.max(1, Math.max(...times) - Math.min(...times)),
    spanV: maxV - minV || 1,
  };
});

const plotW = computed(() => Math.max(1, width.value - PAD.left - PAD.right));
const plotH = H - PAD.top - PAD.bottom;

function sx(time) {
  const b = bounds.value;
  return PAD.left + ((new Date(time).getTime() - b.minT) / b.spanT) * plotW.value;
}
function sy(value) {
  const b = bounds.value;
  return PAD.top + ((b.maxV - value) / b.spanV) * plotH;
}

const coords = computed(() => {
  if (!bounds.value) return [];
  return valid.value.map((p) => [sx(p.time), sy(p.value)]);
});

const linePath = computed(() =>
  coords.value.length ? 'M' + coords.value.map((c) => `${c[0].toFixed(1)},${c[1].toFixed(1)}`).join(' L') : ''
);
const areaPath = computed(() => {
  const c = coords.value;
  if (c.length < 2) return '';
  return (
    'M' +
    c.map((p) => `${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(' L') +
    ` L${c[c.length - 1][0].toFixed(1)},${PAD.top + plotH} L${c[0][0].toFixed(1)},${PAD.top + plotH} Z`
  );
});

// Axis ticks
const yTicks = computed(() => {
  const b = bounds.value;
  if (!b) return [];
  return [b.maxV, (b.maxV + b.minV) / 2, b.minV].map((v) => ({
    y: sy(v),
    label: formatNumber(v, locale.value),
  }));
});
const xTicks = computed(() => {
  const b = bounds.value;
  if (!b) return [];
  return [b.minT, (b.minT + b.maxT) / 2, b.maxT].map((time) => ({
    x: sx(time),
    label: fmtTime(time),
  }));
});

function fmtTime(time) {
  return new Date(time).toLocaleString(locale.value, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    ...(timeZone.value ? { timeZone: timeZone.value } : {}),
  });
}

function onMove(e) {
  const b = bounds.value;
  if (!b || !svgRef.value) return;
  const rect = svgRef.value.getBoundingClientRect();
  const x = e.clientX - rect.left;
  // nearest point by x
  let best = 0;
  let bestDist = Infinity;
  coords.value.forEach((c, i) => {
    const d = Math.abs(c[0] - x);
    if (d < bestDist) {
      bestDist = d;
      best = i;
    }
  });
  hoverIndex.value = best;
}
function onLeave() {
  hoverIndex.value = null;
}

const hover = computed(() => {
  if (hoverIndex.value === null || !coords.value[hoverIndex.value]) return null;
  const p = valid.value[hoverIndex.value];
  const [x, y] = coords.value[hoverIndex.value];
  return {
    x,
    y,
    value: formatNumber(p.value, locale.value),
    time: fmtTime(p.time),
    // clamp tooltip horizontally inside the plot
    tipX: Math.min(Math.max(x, PAD.left + 60), width.value - 60),
  };
});

// Current-time dashed line — only shown when now falls within the chart range
const nowX = computed(() => {
  const b = bounds.value;
  if (!b) return null;
  const now = Date.now();
  if (now <= b.minT || now >= b.maxT) return null;
  return PAD.left + ((now - b.minT) / b.spanT) * plotW.value;
});
</script>

<template>
  <div ref="containerRef" class="relative w-full select-none">
    <div v-if="valid.length < 2" class="h-40 flex items-center justify-center text-sm text-gray-400 dark:text-gray-500">
      {{ t('detail.noData') }}
    </div>

    <template v-else>
      <svg
        ref="svgRef"
        :viewBox="`0 0 ${width} ${H}`"
        :width="width"
        :height="H"
        class="overflow-visible"
        @mousemove="onMove"
        @mouseleave="onLeave"
      >
        <!-- grid + y axis -->
        <g>
          <line
            v-for="(tk, i) in yTicks"
            :key="'gy' + i"
            :x1="PAD.left" :x2="width - PAD.right" :y1="tk.y" :y2="tk.y"
            class="stroke-gray-200 dark:stroke-gray-700" stroke-width="1"
          />
          <text
            v-for="(tk, i) in yTicks"
            :key="'ty' + i"
            :x="PAD.left - 8" :y="tk.y + 3" text-anchor="end"
            class="fill-gray-400 dark:fill-gray-500 text-[10px]"
          >{{ tk.label }}</text>
        </g>

        <!-- x axis labels -->
        <text
          v-for="(tk, i) in xTicks"
          :key="'tx' + i"
          :x="tk.x" :y="H - 8"
          :text-anchor="i === 0 ? 'start' : i === xTicks.length - 1 ? 'end' : 'middle'"
          class="fill-gray-400 dark:fill-gray-500 text-[10px]"
        >{{ tk.label }}</text>

        <!-- series -->
        <path :d="areaPath" :fill="color" fill-opacity="0.12" />
        <path :d="linePath" :stroke="color" fill="none" stroke-width="2" stroke-linejoin="round" stroke-linecap="round" />

        <!-- current-time marker -->
        <line
          v-if="nowX !== null"
          :x1="nowX" :x2="nowX" :y1="PAD.top" :y2="PAD.top + plotH"
          class="stroke-blue-400 dark:stroke-blue-500"
          stroke-width="1.5" stroke-dasharray="5 3" opacity="0.7"
        />

        <!-- crosshair + marker -->
        <g v-if="hover">
          <line :x1="hover.x" :x2="hover.x" :y1="PAD.top" :y2="PAD.top + plotH" class="stroke-gray-300 dark:stroke-gray-600" stroke-width="1" stroke-dasharray="3 3" />
          <circle :cx="hover.x" :cy="hover.y" r="4" :fill="color" stroke="white" stroke-width="1.5" />
        </g>
      </svg>

      <!-- tooltip -->
      <div
        v-if="hover"
        class="pointer-events-none absolute -translate-x-1/2 -translate-y-full rounded-md bg-gray-900 dark:bg-gray-700 text-white text-xs px-2 py-1 shadow-lg whitespace-nowrap"
        :style="{ left: hover.tipX + 'px', top: hover.y - 8 + 'px' }"
      >
        <div class="font-semibold tabular-nums">{{ hover.value }} {{ unit }}</div>
        <div class="text-gray-300 dark:text-gray-300">{{ hover.time }}</div>
      </div>
    </template>
  </div>
</template>
