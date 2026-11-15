require('dotenv').config();

const express = require('express');
const mongoose = require('mongoose');
const { loadConfig } = require('./config');
const { connectMongo } = require('./db');
const { createApplicationClient } = require('./clients/applicationClient');
const { createPublisher } = require('./messaging/publisher');
const { registerWithEureka } = require('./eureka');
const { createRequireRecruiter } = require('./middleware/requireRecruiter');
const { createInterviewService } = require('./services/interviewService');
const { createInterviewRouter } = require('./routes/interviews');

function healthPayload(runtime, applicationClient) {
  const mongoUp = mongoose.connection.readyState === 1;
  return {
    status: mongoUp ? 'UP' : 'DOWN',
    service: 'ms-interview',
    mongo: mongoUp ? 'connected' : 'disconnected',
    rabbitmq: runtime.rabbitmq,
    eureka: runtime.eureka,
    circuitBreaker: applicationClient.state(),
  };
}

function buildApp(runtime, applicationClient, service, config) {
  const app = express();
  app.disable('x-powered-by');
  app.use(express.json());

  app.get(['/health', '/actuator/health'], (_req, res) => {
    const body = healthPayload(runtime, applicationClient);
    res.status(body.status === 'UP' ? 200 : 503).json(body);
  });

  app.use('/api/interviews', createInterviewRouter(service, createRequireRecruiter(config)));

  app.use((req, res) => {
    res.status(404).json({ status: 404, error: 'NOT_FOUND', message: `No route ${req.method} ${req.path}` });
  });

  app.use((error, _req, res, _next) => {
    const invalidJson = error instanceof SyntaxError && error.status === 400;
    const status = invalidJson ? 400 : (error.status || 500);
    if (status >= 500) console.error(error);
    res.status(status).json({
      status,
      error: invalidJson ? 'VALIDATION' : (error.code || 'ERROR'),
      message: status >= 500 ? 'Internal error' : (invalidJson ? 'Invalid JSON body' : error.message),
    });
  });

  return app;
}

async function start() {
  const config = await loadConfig();
  await connectMongo(config.mongodbUri);

  const runtime = { rabbitmq: 'down', eureka: 'down' };
  const applicationClient = createApplicationClient(config);
  const publisher = createPublisher(config, runtime);
  const service = createInterviewService({ applicationClient, publisher });
  const app = buildApp(runtime, applicationClient, service, config);

  const server = await new Promise((resolve, reject) => {
    const listening = app.listen(config.port, '0.0.0.0');
    listening.once('listening', () => resolve(listening));
    listening.once('error', reject);
  });
  console.log(`ms-interview listening on 0.0.0.0:${config.port}`);

  await publisher.connect();
  const eurekaClient = registerWithEureka(config, runtime);

  async function shutdown() {
    server.close();
    try {
      if (eurekaClient) eurekaClient.stop();
    } catch (error) {
      console.warn(`Eureka stop: ${error.message}`);
    }
    await publisher.close();
    await mongoose.disconnect();
    process.exit(0);
  }

  process.on('SIGINT', shutdown);
  process.on('SIGTERM', shutdown);
  return server;
}

if (require.main === module) {
  start().catch((error) => {
    console.error(`ms-interview failed to start: ${error.message}`);
    process.exit(1);
  });
}

module.exports = { start, buildApp };
