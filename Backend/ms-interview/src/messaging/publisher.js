const amqp = require('amqplib');

const EXCHANGE = 'jobboard.events';
const QUEUES = {
  'interview.scheduled': 'interview.scheduled',
  'interview.cancelled': 'interview.cancelled',
};

function createPublisher(config, runtime) {
  let connection;
  let channel;

  async function connect() {
    try {
      connection = await amqp.connect(config.rabbitmqUrl);
      connection.on('error', (error) => {
        runtime.rabbitmq = 'degraded';
        console.warn(`RabbitMQ connection error: ${error.message}`);
      });
      connection.on('close', () => {
        runtime.rabbitmq = 'degraded';
        channel = null;
      });
      channel = await connection.createChannel();
      await channel.assertExchange(EXCHANGE, 'topic', { durable: true });
      for (const [routingKey, queue] of Object.entries(QUEUES)) {
        await channel.assertQueue(queue, { durable: true });
        await channel.bindQueue(queue, EXCHANGE, routingKey);
      }
      runtime.rabbitmq = 'connected';
      console.log('RabbitMQ publisher ready (jobboard.events)');
    } catch (error) {
      runtime.rabbitmq = 'degraded';
      console.warn(`RabbitMQ unavailable (${error.message}). Events stay eventually consistent.`);
    }
  }

  async function publish(routingKey, payload) {
    try {
      if (!channel) {
        console.warn(`Event ${payload.eventType} ${payload.eventId} not published (RabbitMQ down).`);
        return { published: false };
      }
      channel.publish(EXCHANGE, routingKey, Buffer.from(JSON.stringify(payload)), {
        contentType: 'application/json',
        persistent: true,
        messageId: payload.eventId,
      });
      return { published: true };
    } catch (error) {
      runtime.rabbitmq = 'degraded';
      console.warn(`Event ${payload.eventType} ${payload.eventId} not published: ${error.message}`);
      return { published: false };
    }
  }

  async function close() {
    try {
      if (channel) await channel.close();
      if (connection) await connection.close();
    } catch (error) {
      console.warn(`RabbitMQ close: ${error.message}`);
    }
  }

  return { connect, publish, close };
}

module.exports = { createPublisher };
