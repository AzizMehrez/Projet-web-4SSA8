function rolesFromBearer(authorization) {
  if (!authorization || !authorization.toLowerCase().startsWith('bearer ')) return [];
  const parts = authorization.slice(7).trim().split('.');
  if (parts.length < 2) return [];
  try {
    const payload = JSON.parse(Buffer.from(parts[1], 'base64url').toString('utf8'));
    const realmRoles = payload.realm_access && Array.isArray(payload.realm_access.roles)
      ? payload.realm_access.roles
      : [];
    const flatRoles = Array.isArray(payload.roles) ? payload.roles : [];
    return [...realmRoles, ...flatRoles].map(String);
  } catch {
    return [];
  }
}

function collectRoles(req) {
  const header = req.get('x-roles') || req.get('x-user-roles') || '';
  const fromHeader = header.split(/[,\s]+/).filter(Boolean);
  return [...fromHeader, ...rolesFromBearer(req.get('authorization'))];
}

function createRequireRecruiter(config) {
  return function requireRecruiter(req, res, next) {
    const roles = collectRoles(req);
    const allowed = roles.some((role) => role === 'ROLE_RECRUITER' || role === 'RECRUITER');
    if (roles.length === 0 && !config.enforceRecruiter) return next();
    if (!allowed) {
      return res.status(403).json({
        status: 403,
        error: 'FORBIDDEN',
        message: 'ROLE_RECRUITER is required. The API Gateway validates the Keycloak JWT.',
      });
    }
    return next();
  };
}

module.exports = { createRequireRecruiter };
