const { randomUUID } = require('crypto');
const mongoose = require('mongoose');
const Interview = require('../models/interview');
const { HttpError } = require('../httpError');

function readSlot(body) {
  const startRaw = body.slot && body.slot.start ? body.slot.start : body.slotStart;
  const endRaw = body.slot && body.slot.end ? body.slot.end : body.slotEnd;
  if (!startRaw || !endRaw) {
    throw new HttpError(400, 'slot.start and slot.end are required', 'VALIDATION');
  }
  const start = new Date(startRaw);
  const end = new Date(endRaw);
  if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) {
    throw new HttpError(400, 'slot.start and slot.end must be ISO-8601 dates', 'VALIDATION');
  }
  if (end <= start) {
    throw new HttpError(400, 'slot.end must be after slot.start', 'VALIDATION');
  }
  return { start, end };
}

function toDto(doc) {
  return {
    id: doc.id,
    applicationId: doc.applicationId,
    meetingUrl: doc.meetingUrl || null,
    notes: doc.notes || null,
    slot: {
      start: doc.slot.start.toISOString(),
      end: doc.slot.end.toISOString(),
    },
    status: doc.status,
  };
}

async function findOrThrow(id) {
  if (!mongoose.isValidObjectId(id)) {
    throw new HttpError(404, 'Interview not found', 'NOT_FOUND');
  }
  const interview = await Interview.findById(id);
  if (!interview) throw new HttpError(404, 'Interview not found', 'NOT_FOUND');
  return interview;
}

function createInterviewService({ applicationClient, publisher }) {
  return {
    async schedule(body) {
      if (body == null || typeof body !== 'object') {
        throw new HttpError(400, 'JSON body is required', 'VALIDATION');
      }
      if (body.applicationId == null || String(body.applicationId).trim() === '') {
        throw new HttpError(400, 'applicationId is required', 'VALIDATION');
      }
      const applicationId = String(body.applicationId).trim();
      const slot = readSlot(body);

      await applicationClient.assertExists(applicationId);

      const interview = await Interview.create({
        applicationId,
        meetingUrl: body.meetingUrl == null ? undefined : String(body.meetingUrl),
        notes: body.notes == null ? undefined : String(body.notes),
        slot,
        status: 'SCHEDULED',
      });

      await publisher.publish('interview.scheduled', {
        eventId: randomUUID(),
        eventType: 'InterviewScheduled',
        interviewId: interview.id,
        applicationId: interview.applicationId,
        slot: {
          start: interview.slot.start.toISOString(),
          end: interview.slot.end.toISOString(),
        },
        meetingUrl: interview.meetingUrl || null,
        occurredAt: new Date().toISOString(),
      });

      return toDto(interview);
    },

    async getById(id) {
      return toDto(await findOrThrow(id));
    },

    async list(query) {
      const page = Math.max(0, Number(query.page) || 0);
      const size = Math.min(100, Math.max(1, Number(query.size) || 20));
      const filter = {};
      if (query.applicationId != null && String(query.applicationId).trim() !== '') {
        filter.applicationId = String(query.applicationId).trim();
      }
      const docs = await Interview.find(filter)
        .sort({ 'slot.start': 1 })
        .skip(page * size)
        .limit(size);
      return docs.map(toDto);
    },

    async cancel(id, reason) {
      const interview = await findOrThrow(id);
      if (interview.status === 'CANCELLED') return { interview: toDto(interview), alreadyCancelled: true };

      interview.status = 'CANCELLED';
      await interview.save();

      await publisher.publish('interview.cancelled', {
        eventId: randomUUID(),
        eventType: 'InterviewCancelled',
        interviewId: interview.id,
        applicationId: interview.applicationId,
        reason: reason == null || String(reason).trim() === '' ? null : String(reason),
        occurredAt: new Date().toISOString(),
      });

      return { interview: toDto(interview), alreadyCancelled: false };
    },
  };
}

module.exports = { createInterviewService };
