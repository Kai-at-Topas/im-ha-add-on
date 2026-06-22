// Central API client. Uses RELATIVE paths (no leading slash) so requests resolve
// against the document's base URL — required for HA Ingress, which serves the
// add-on under a path-prefixed URL. In dev, Vite proxies /api to the backend.

async function request(path, options = {}) {
  const response = await fetch(path, options);
  if (!response.ok) {
    throw new Error(`Request to ${path} failed with status ${response.status}`);
  }
  // Some endpoints may return empty bodies; guard JSON parsing.
  const text = await response.text();
  return text ? JSON.parse(text) : null;
}

function postJson(path, body) {
  return request(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
}

export const api = {
  getConfig({ noCache = false } = {}) {
    if (noCache) {
      return request(`api/config?t=${Date.now()}`, {
        cache: 'no-store',
        headers: { Pragma: 'no-cache', 'Cache-Control': 'no-cache' },
      });
    }
    return request('api/config');
  },

  saveConfig(config) {
    return postJson('api/config', config);
  },

  acceptOptIn() {
    return postJson('api/config/optin');
  },

  optOut(config) {
    return postJson('api/config', { ...config, mqtt_opt_in: false });
  },

  getEntities() {
    return request('api/ha/entities');
  },

  getState() {
    return request('api/ha/state');
  },

  getHistory(hours = 24) {
    return request(`api/ha/history?hours=${hours}`);
  },

  getForecast(type = 'daily') {
    return request(`api/ha/forecast?type=${type}`);
  },

  getEnergyStats() {
    return request('api/ha/energy/stats');
  },

  getEnergyHourly(days = 7) {
    return request(`api/ha/energy/hourly?days=${days}`);
  },

  getProfile() {
    return request('api/ha/profile');
  },

  getLocation() {
    return request('api/ha/location');
  },

  getTime() {
    return request('api/ha/time');
  },

  getVersion() {
    return request('api/version');
  },

  resetConfig() {
    return postJson('api/config/reset');
  },
};

export default api;
