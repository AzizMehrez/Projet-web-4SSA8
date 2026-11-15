const express = require('express');

function asyncRoute(handler) {
  return (req, res, next) => Promise.resolve(handler(req, res, next)).catch(next);
}

function createInterviewRouter(service, requireRecruiter) {
  const router = express.Router();

  router.get('/', asyncRoute(async (req, res) => {
    res.json(await service.list(req.query));
  }));

  router.get('/:id', asyncRoute(async (req, res) => {
    res.json(await service.getById(req.params.id));
  }));

  router.post('/', requireRecruiter, asyncRoute(async (req, res) => {
    res.status(201).json(await service.schedule(req.body));
  }));

  router.patch('/:id/status', requireRecruiter, asyncRoute(async (req, res) => {
    if (!req.body || req.body.status !== 'CANCELLED') {
      return res.status(400).json({
        status: 400,
        error: 'VALIDATION',
        message: 'status must be CANCELLED',
      });
    }
    const result = await service.cancel(req.params.id, req.body.reason);
    return res.json(result.interview);
  }));

  router.patch('/:id', requireRecruiter, asyncRoute(async (req, res) => {
    if (!req.body || req.body.status !== 'CANCELLED') {
      return res.status(400).json({
        status: 400,
        error: 'VALIDATION',
        message: 'status must be CANCELLED',
      });
    }
    const result = await service.cancel(req.params.id, req.body.reason);
    return res.json(result.interview);
  }));

  router.delete('/:id', requireRecruiter, asyncRoute(async (req, res) => {
    await service.cancel(req.params.id, req.query.reason);
    res.status(204).send();
  }));

  return router;
}

module.exports = { createInterviewRouter };
