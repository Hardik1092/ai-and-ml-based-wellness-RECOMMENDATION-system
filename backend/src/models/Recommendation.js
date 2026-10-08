const mongoose = require('mongoose');

const recommendationSchema = new mongoose.Schema({
  userId: { type: mongoose.Schema.Types.ObjectId, ref: 'User', required: true },
  recDate: { type: String, required: true },
  recType: { type: String, required: true },
  foodIds: { type: [String], default: [] },
  activityIds: { type: [String], default: [] },
  summary: { type: String, default: '' },
  mlPrediction: { type: String, default: null },
  mlConfidence: { type: Number, default: null },
  source: { type: String, default: 'hybrid' },
  payload: { type: mongoose.Schema.Types.Mixed, default: null },
}, { timestamps: true });

recommendationSchema.index({ userId: 1, recDate: 1, recType: 1 }, { unique: true });

recommendationSchema.methods.toPublic = function toPublic() {
  return {
    recommendation_id: String(this._id),
    date: this.recDate,
    type: this.recType,
    food_ids: this.foodIds || [],
    activity_ids: this.activityIds || [],
    summary: this.summary,
    ml_prediction: this.mlPrediction,
    ml_confidence: this.mlConfidence,
    source: this.source,
    created_at: this.createdAt ? this.createdAt.toISOString() : null,
  };
};

module.exports = mongoose.model('Recommendation', recommendationSchema);
