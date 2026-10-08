const path = require('path');
require('dotenv').config({ path: path.join(__dirname, '../../.env') });
const mongoose = require('mongoose');
const { Recommendation } = require('../models');

async function main() {
  await mongoose.connect(process.env.MONGODB_URI || 'mongodb://127.0.0.1:27017/wellness_db');
  console.log('Connected to DB');

  const all = await Recommendation.find().sort({ updatedAt: -1 });
  const seen = new Set();
  const toDelete = [];

  for (const doc of all) {
    const key = `${doc.userId}_${doc.recDate}_${doc.recType}`;
    if (seen.has(key)) {
      toDelete.push(doc._id);
    } else {
      seen.add(key);
    }
  }

  console.log('Found', toDelete.length, 'historical duplicate recommendation records to purge.');
  if (toDelete.length > 0) {
    const delRes = await Recommendation.deleteMany({ _id: { $in: toDelete } });
    console.log('Deleted legacy duplicates:', delRes.deletedCount);
  }

  await Recommendation.syncIndexes();
  const indexes = await Recommendation.collection.indexes();
  console.log('Current registered indexes:');
  for (const idx of indexes) {
    console.log(' - Name:', idx.name, 'Keys:', JSON.stringify(idx.key), 'Unique:', idx.unique);
  }

  await mongoose.disconnect();
  console.log('Done!');
}

main().catch((err) => {
  console.error('Error:', err);
  process.exit(1);
});
