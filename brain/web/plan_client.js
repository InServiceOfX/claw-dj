// Typed-by-contract browser client for the plan and reusable-bunch APIs.
// Mutations never retry: a decision made against a stale revision must be
// reviewed against a fresh Arrange snapshot before it is applied again.

/** @typedef {{slug:string, display_name:string, status:'wip'|'ready'|'archived', stale?:boolean, rev?:string}} Plan */
/** @typedef {{slug:string, tracks:Array<object>, notes:Array<object>, segments:Array<object>, bunches:Array<object>, rev:string, revs:object, stale:boolean, staleness:object, artifact:object|null}} Arrange */

const revisions = new Map();
const arrangeControllers = new Map();

export class PlanApiError extends Error {
  constructor(status, payload, response) {
    super(payload?.message || payload?.summary || payload?.error || response.statusText || `HTTP ${status}`);
    this.name = 'PlanApiError';
    this.status = status;
    this.payload = payload || {};
    this.response = response;
  }
}

export class PlanConflictError extends PlanApiError {
  constructor(payload, response) {
    super(409, payload, response);
    this.name = 'PlanConflictError';
  }
}

function announceConflict(error) {
  document.dispatchEvent(new CustomEvent('clawdj:plan-conflict', {
    detail: {error, payload: error.payload},
  }));
}

async function decode(response) {
  if (response.status === 204) return null;
  const type = response.headers.get('content-type') || '';
  if (type.includes('application/json')) return response.json();
  const text = await response.text();
  return text ? {message: text} : {};
}

async function request(path, options = {}, {allowConflict = false} = {}) {
  const response = await fetch(path, options);
  const payload = await decode(response);
  if (!response.ok) {
    const error = response.status === 409
      ? new PlanConflictError(payload, response)
      : new PlanApiError(response.status, payload, response);
    if (response.status === 409 && !allowConflict) announceConflict(error);
    throw error;
  }
  return payload;
}

function json(method, body, signal) {
  return {
    method,
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(body),
    signal,
  };
}

function remember(slug, payload) {
  if (slug && payload?.rev) revisions.set(slug, payload.rev);
  return payload;
}

function baseRev(slug) {
  const value = revisions.get(slug);
  if (!value) throw new Error('Refresh this plan before changing it.');
  return value;
}

function withBase(slug, body = {}) {
  return {...body, base_rev: baseRev(slug)};
}

export function currentRevision(slug) {
  return revisions.get(slug) || null;
}

export function forgetRevision(slug) {
  revisions.delete(slug);
}

export async function listPlans({status} = {}) {
  const query = status ? `?${new URLSearchParams({status})}` : '';
  return (await request(`/api/plans${query}`)).plans;
}

export async function createPlan(displayName) {
  return request('/api/plans', json('POST', {display_name: displayName}));
}

export async function getActivePlan() {
  const plan = await request('/api/plans/active');
  return remember(plan.slug, plan);
}

export async function setActivePlan(slug) {
  if (!currentRevision(slug)) await getPlan(slug);
  const plan = await request('/api/plans/active', json('POST', withBase(slug, {slug})));
  return remember(slug, plan);
}

export async function getPlan(slug) {
  const detail = await request(`/api/plans/${encodeURIComponent(slug)}`);
  remember(slug, detail);
  return detail;
}

export async function renamePlan(slug, displayName) {
  return remember(slug, await request(`/api/plans/${encodeURIComponent(slug)}`, json('POST', withBase(slug, {display_name: displayName}))));
}

export async function duplicatePlan(slug, displayName) {
  return request(`/api/plans/${encodeURIComponent(slug)}/duplicate`, json('POST', withBase(slug, {display_name: displayName})));
}

export async function deletePlan(slug) {
  await request(`/api/plans/${encodeURIComponent(slug)}`, json('POST', withBase(slug, {action: 'delete'})));
  forgetRevision(slug);
}

export async function setStatus(slug, status) {
  return remember(slug, await request(`/api/plans/${encodeURIComponent(slug)}`, json('POST', withBase(slug, {status}))));
}

export async function refreshPlan(slug, {signal} = {}) {
  arrangeControllers.get(slug)?.abort();
  const controller = new AbortController();
  arrangeControllers.set(slug, controller);
  const abort = () => controller.abort();
  signal?.addEventListener('abort', abort, {once: true});
  try {
    const snapshot = await request(`/api/plans/${encodeURIComponent(slug)}/arrange`, {signal: controller.signal});
    return remember(slug, snapshot);
  } finally {
    signal?.removeEventListener('abort', abort);
    if (arrangeControllers.get(slug) === controller) arrangeControllers.delete(slug);
  }
}

export async function fetchJournal(slug, limit = 50) {
  const query = new URLSearchParams({limit: String(limit)});
  return (await request(`/api/plans/${encodeURIComponent(slug)}/journal?${query}`)).entries;
}

export async function setOrder(slug, trackIds) {
  return remember(slug, await request(`/api/plans/${encodeURIComponent(slug)}/order`, json('POST', withBase(slug, {track_ids: trackIds}))));
}

export async function moveBunch(slug, bunchId, toIndex) {
  return remember(slug, await request(`/api/plans/${encodeURIComponent(slug)}/order`, json('POST', withBase(slug, {move_bunch: bunchId, to_index: toIndex}))));
}

export async function addTracks(slug, {add = [], remove = []}) {
  return remember(slug, await request(`/api/plans/${encodeURIComponent(slug)}/tracks`, json('POST', withBase(slug, {add, remove}))));
}

export async function setNote(slug, trackId, note, author = 'human') {
  return remember(slug, await request(`/api/plans/${encodeURIComponent(slug)}/notes`, json('POST', withBase(slug, {track_id: trackId, note, author}))));
}

export async function clearNote(slug, trackId) {
  return remember(slug, await request(`/api/plans/${encodeURIComponent(slug)}/notes`, json('POST', withBase(slug, {track_id: trackId, clear: true}))));
}

export async function setTransition(slug, patch) {
  return remember(slug, await request(`/api/plans/${encodeURIComponent(slug)}/transitions`, json('POST', withBase(slug, patch))));
}

export async function clearTransition(slug, fromTrackId, toTrackId) {
  return setTransition(slug, {from_track_id: fromTrackId, to_track_id: toTrackId, clear: true});
}

export async function listPlanBunches(slug) {
  return (await request(`/api/plans/${encodeURIComponent(slug)}/bunches`)).activations;
}

export async function setBunchActivation(slug, bunchId, enabled, region = undefined, {allowConflict = false} = {}) {
  const body = withBase(slug, {bunch_id: bunchId, enabled});
  if (region !== undefined) body.region = region;
  return remember(slug, await request(`/api/plans/${encodeURIComponent(slug)}/bunches`, json('POST', body), {allowConflict}));
}

export async function createAndActivateBunch(slug, {label, track_ids, ordered = true}) {
  let created;
  try {
    created = await request('/api/bunches', json('POST', {label, track_ids, ordered}));
  } catch (error) {
    return {created: null, activated: false, conflict: null, stage: 'library-create-failed', error};
  }
  try {
    const activation = await setBunchActivation(slug, created.bunch_id, true, undefined, {allowConflict: true});
    return {created, activated: activation.activation, conflict: null, stage: 'activated'};
  } catch (error) {
    if (error instanceof PlanConflictError) {
      return {created, activated: false, conflict: error.payload, stage: 'activation-conflicted'};
    }
    return {created, activated: false, conflict: null, stage: 'activation-failed', error};
  }
}

export function deactivateBunch(slug, bunchId) {
  return setBunchActivation(slug, bunchId, false);
}

export async function listBunches({trackId} = {}) {
  const query = trackId ? `?${new URLSearchParams({track_id: trackId})}` : '';
  return (await request(`/api/bunches${query}`)).bunches;
}

export function getBunch(bunchId) {
  return request(`/api/bunches/${encodeURIComponent(bunchId)}`);
}

export function updateBunch(bunchId, patch) {
  return request(`/api/bunches/${encodeURIComponent(bunchId)}`, json('POST', patch));
}

export async function archiveBunch(bunchId) {
  const result = await request(`/api/bunches/${encodeURIComponent(bunchId)}`, json('POST', {action: 'archive'}));
  for (const slug of result.affected_slugs || []) forgetRevision(slug);
  return result;
}
