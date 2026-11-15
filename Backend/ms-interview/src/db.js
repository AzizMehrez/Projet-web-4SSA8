const mongoose = require('mongoose');

async function connectMongo(uri) {
  const attempts = 5;
  for (let attempt = 1; attempt <= attempts; attempt += 1) {
    try {
      await mongoose.connect(uri, {
        serverSelectionTimeoutMS: 4000,
        dbName: 'interview_db',
      });
      console.log('MongoDB connected (interview_db)');
      return;
    } catch (error) {
      if (attempt === attempts) throw error;
      console.warn(`MongoDB not ready (${attempt}/${attempts}): ${error.message}`);
      await new Promise((resolve) => setTimeout(resolve, 2000));
    }
  }
}

module.exports = { connectMongo };
