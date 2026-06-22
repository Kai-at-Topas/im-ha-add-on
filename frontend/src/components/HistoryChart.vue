<script setup>
import { computed } from 'vue';

const props = defineProps({
  points: { type: Array, default: () => [] },
  color: { type: String, default: '#3b82f6' },
});

const W = 300;
const H = 80;
const PAD = 4;

const coords = computed(() => {
  const pts = props.points || [];
  if (pts.length < 2) return null;

  const times = pts.map((p) => new Date(p.time).getTime());
  const values = pts.map((p) => p.value);
  const minT = Math.min(...times);
  const maxT = Math.max(...times);
  const minV = Math.min(...values);
  const maxV = Math.max(...values);
  const spanT = maxT - minT || 1;
  const spanV = maxV - minV || 1;

  return pts.map((p) => {
    const x = PAD + ((new Date(p.time).getTime() - minT) / spanT) * (W - 2 * PAD);
    const y = H - PAD - ((p.value - minV) / spanV) * (H - 2 * PAD);
    return [Number(x.toFixed(2)), Number(y.toFixed(2))];
  });
});

const linePath = computed(() =>
  coords.value ? 'M' + coords.value.map((c) => c.join(',')).join(' L') : ''
);

const areaPath = computed(() => {
  if (!coords.value) return '';
  const c = coords.value;
  return (
    'M' +
    c.map((p) => p.join(',')).join(' L') +
    ` L${c[c.length - 1][0]},${H - PAD} L${c[0][0]},${H - PAD} Z`
  );
});
</script>

<template>
  <svg
    v-if="linePath"
    :viewBox="`0 0 ${W} ${H}`"
    preserveAspectRatio="none"
    class="w-full h-20"
  >
    <path :d="areaPath" :fill="color" fill-opacity="0.12" />
    <path
      :d="linePath"
      :stroke="color"
      fill="none"
      stroke-width="2"
      stroke-linejoin="round"
      stroke-linecap="round"
      vector-effect="non-scaling-stroke"
    />
  </svg>
  <div v-else class="h-20 flex items-center justify-center text-xs text-gray-400 dark:text-gray-500">
    —
  </div>
</template>
