const axios = require('axios');

function flatten(value, prefix, out) {
  if (value == null || typeof value !== 'object' || Array.isArray(value)) {
    if (prefix) out[prefix] = value;
    return out;
  }
  for (const [key, child] of Object.entries(value)) {
    const next = prefix ? `${prefix}.${key}` : key;
    flatten(child, next, out);
  }
  return out;
}

function pick(envValue, configured, fallback) {
  if (envValue != null && String(envValue).trim() !== '') return envValue;
  if (configured != null && String(configured).trim() !== '') return configured;
  return fallback;
}

async function readConfigServer(configServerUrl) {
  const url = `${String(configServerUrl).replace(/\/$/, '')}/ms-interview/default`;
  const response = await axios.get(url, { timeout: 2000, validateStatus: (status) => status === 200 });
  const merged = {};
  const sources = [...(response.data.propertySources || [])].reverse();
  for (const source of sources) {
    Object.assign(merged, flatten(source.source || {}, '', {}));
  }
  return merged;
}

async function loadConfig() {
  const configServerUrl = process.env.CONFIG_SERVER_URL || 'http://localhost:8888';
  let remote = {};
  try {
    remote = await readConfigServer(configServerUrl);
    console.log(`Config Server loaded from ${configServerUrl}`);
  } catch (error) {
    console.warn(`Config Server unreachable (${error.message}). Using environment defaults.`);
  }

  return {
    port: Number(pick(process.env.PORT, remote['server.port'], 8084)),
    mongodbUri: pick(
      process.env.MONGODB_URI,
      remote['app.mongodb.uri'] || remote['spring.data.mongodb.uri'],
      'mongodb://localhost:27017/interview_db',
    ),
    rabbitmqUrl: pick(
      process.env.RABBITMQ_URL,
      remote['app.rabbitmq.url'],
      'amqp://guest:guest@localhost:5672',
    ),
    applicationServiceUrl: pick(
      process.env.APPLICATION_SERVICE_URL,
      remote['app.application-service-url'],
      'http://localhost:8083',
    ),
    eurekaHost: pick(process.env.EUREKA_HOST, remote['eureka.host'], 'localhost'),
    eurekaPort: Number(pick(process.env.EUREKA_PORT, remote['eureka.port'], 8761)),
    instanceHost: process.env.EUREKA_INSTANCE_HOST || 'localhost',
    configServerUrl,
    enforceRecruiter: process.env.ENFORCE_RECRUITER === 'true',
    serviceName: 'ms-interview',
  };
}

module.exports = { loadConfig };
