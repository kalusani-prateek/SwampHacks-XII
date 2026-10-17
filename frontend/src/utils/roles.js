// User roles. There is no separate admin: supervisors hold every management
// privilege (PlanIt Dashboard + Manage panel), while crew members view sites,
// get alerts, report hazards, read briefings and use the assistant.
// The backend stores this in users.role and checks it on every request (docs/API.md).
export const ROLES = {
  CREW: 'crew',
  SUPERVISOR: 'supervisor',
};

/** True if `user` has one of the `allowed` roles (or no restriction given). */
export function hasRole(user, allowed) {
  if (!allowed || allowed.length === 0) return true;
  return Boolean(user && allowed.includes(user.role));
}
