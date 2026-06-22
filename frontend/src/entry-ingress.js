import { createApp } from 'vue';
import App from './App.vue';
import router from './router';
import i18n, { setLocale } from './i18n';
import { initTheme } from './composables/useTheme.js';
import './style.css';

// Apply persisted theme + language before mount to avoid a flash of the wrong state.
initTheme();
setLocale(i18n.global.locale.value);

const app = createApp(App);
app.use(router);
app.use(i18n);
app.mount('#app');
