<script setup>
defineProps({
  text: { type: String, required: true },
});
</script>

<template>
  <span class="relative inline-flex items-center group align-middle">
    <button
      type="button"
      :aria-label="text"
      :title="text"
      class="inline-flex items-center justify-center h-4 w-4 rounded-full border border-gray-400 dark:border-gray-500 text-[10px] font-bold text-gray-500 dark:text-gray-400 cursor-help focus:outline-none focus:ring-2 focus:ring-blue-500"
    >
      i
    </button>
    <span
      role="tooltip"
      class="pointer-events-none absolute left-1/2 bottom-full mb-2 -translate-x-1/2 w-56 rounded-md bg-gray-900 dark:bg-gray-700 text-white text-xs leading-snug p-2 opacity-0 group-hover:opacity-100 group-focus-within:opacity-100 transition-opacity z-20 shadow-lg"
    >
      {{ text }}
    </span>
  </span>
</template>
