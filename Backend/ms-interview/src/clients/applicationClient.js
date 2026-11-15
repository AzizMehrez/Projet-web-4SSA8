const axios = require('axios');
const CircuitBreaker = require('opossum');
const { HttpError } = require('../httpError');

const ATTEMPTS = 3;
const TIMEOUT_MS = 2000;

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function isRetryable(error) {
  if (error.retryable === true) return true;
  if (error.retryable === false) return false;
  return true;
}

function createApplicationClient(config) {
  const baseUrl = String(config.applicationServiceUrl).replace(/\/$/, '');

  async function fetchOnce(applicationId) {
    const url = `${baseUrl}/api/applications/${encodeURIComponent(applicationId)}`;
    const response = await axios.get(url, {
      timeout: TIMEOUT_MS,
      validateStatus: () => true,
    });
    if (response.status === 404) return { exists: false };
    if (response.status >= 200 && response.status < 300) return { exists: true };
    const error = new Error(`ms-application responded ${response.status}`);
    error.retryable = response.status >= 500;
    throw error;
  }

  async function fetchWithRetries(applicationId) {
    let lastError;
    for (let attempt = 1; attempt <= ATTEMPTS; attempt += 1) {
      try {
        return await fetchOnce(applicationId);
      } catch (error) {
        lastError = error;
        if (!isRetryable(error) || attempt === ATTEMPTS) break;
        await delay(200 * attempt);
      }
    }
    throw lastError;
  }

  const breaker = new CircuitBreaker(fetchWithRetries, {
    timeout: ATTEMPTS * TIMEOUT_MS + 2000,
    errorThresholdPercentage: 50,
    volumeThreshold: 3,
    resetTimeout: 15000,
    rollingCountTimeout: 20000,
  });

  async function assertExists(applicationId) {
    try {
      const result = await breaker.fire(applicationId);
      if (!result.exists) {
        throw new HttpError(404, 'Application not found', 'APPLICATION_NOT_FOUND');
      }
    } catch (error) {
      if (error instanceof HttpError) throw error;
      throw new HttpError(503, 'Application service unavailable', 'APPLICATION_UNAVAILABLE');
    }
  }

  function state() {
    if (breaker.opened) return 'open';
    if (breaker.halfOpen) return 'half-open';
    return 'closed';
  }

  return { assertExists, state };
}

module.exports = { createApplicationClient };
