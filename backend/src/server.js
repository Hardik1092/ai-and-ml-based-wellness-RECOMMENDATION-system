const mongoose = require('mongoose');
const { createApp } = require('./app');
const { connectDb } = require('./config/db');
const { env } = require('./config/env');

async function main() {
  await connectDb();
  const app = createApp();
  const server = app.listen(env.port, env.host, () => {
    console.log(`Wellness API listening on http://${env.host}:${env.port}`);
  });

  const shutdown = (signal) => {
    console.log(`Received ${signal}. Shutting down gracefully...`);
    server.close(async () => {
      console.log('HTTP server closed.');
      try {
        await mongoose.connection.close();
        console.log('MongoDB connection closed.');
        process.exit(0);
      } catch (err) {
        console.error('Error closing MongoDB connection:', err);
        process.exit(1);
      }
    });

    setTimeout(() => {
      console.error('Forced shutdown after timeout.');
      process.exit(1);
    }, 10000).unref();
  };

  process.on('SIGTERM', () => shutdown('SIGTERM'));
  process.on('SIGINT', () => shutdown('SIGINT'));
}

main().catch((err) => {
  console.error('Failed to start server', err);
  process.exit(1);
});
