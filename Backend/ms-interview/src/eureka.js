const os = require('os');
const { Eureka } = require('eureka-js-client');

function guessIp() {
  const interfaces = os.networkInterfaces();
  for (const entries of Object.values(interfaces)) {
    for (const entry of entries || []) {
      if (entry.family === 'IPv4' && !entry.internal) return entry.address;
    }
  }
  return '127.0.0.1';
}

function registerWithEureka(config, runtime) {
  const hostName = config.instanceHost;
  const ipAddr = hostName === 'localhost' ? '127.0.0.1' : guessIp();
  const port = config.port;
  const client = new Eureka({
    instance: {
      app: 'ms-interview',
      instanceId: `${hostName}:ms-interview:${port}`,
      hostName,
      ipAddr,
      statusPageUrl: `http://${hostName}:${port}/health`,
      healthCheckUrl: `http://${hostName}:${port}/health`,
      homePageUrl: `http://${hostName}:${port}/`,
      port: { $: port, '@enabled': true },
      securePort: { $: 443, '@enabled': false },
      vipAddress: 'ms-interview',
      dataCenterInfo: {
        '@class': 'com.netflix.appinfo.InstanceInfo$DefaultDataCenterInfo',
        name: 'MyOwn',
      },
    },
    eureka: {
      host: config.eurekaHost,
      port: config.eurekaPort,
      servicePath: '/eureka/apps/',
      fetchRegistry: false,
      registerWithEureka: true,
      maxRetries: 3,
      requestRetryDelay: 2000,
    },
  });

  try {
    client.start((error) => {
      if (error) {
        runtime.eureka = 'degraded';
        console.warn(`Eureka registration failed: ${error.message || error}`);
        return;
      }
      runtime.eureka = 'registered';
      console.log('Registered with Eureka as ms-interview');
    });
  } catch (error) {
    runtime.eureka = 'degraded';
    console.warn(`Eureka client failed: ${error.message}`);
    return null;
  }

  return client;
}

module.exports = { registerWithEureka };
