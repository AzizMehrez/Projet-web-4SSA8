const mongoose = require('mongoose');

// Remote identifier only. This service does not own Application, Job, or Candidate.
const interviewSchema = new mongoose.Schema(
  {
    applicationId: { type: String, required: true, index: true },
    meetingUrl: { type: String },
    notes: { type: String },
    slot: {
      start: { type: Date, required: true },
      end: { type: Date, required: true },
    },
    status: {
      type: String,
      enum: ['SCHEDULED', 'CANCELLED'],
      default: 'SCHEDULED',
      required: true,
    },
  },
  { collection: 'interviews' },
);

interviewSchema.set('toJSON', {
  virtuals: true,
  versionKey: false,
  transform(_doc, ret) {
    ret.id = String(ret._id);
    delete ret._id;
    return ret;
  },
});

module.exports = mongoose.model('Interview', interviewSchema);
