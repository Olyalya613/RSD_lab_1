import http from 'k6/http';
import {check, sleep} from 'k6';
import {Rate, Counter} from 'k6/metrics';
import {ENDPOINTS, DEFAULT_HEADERS} from '../config/endpoints.js';

export const errorRate = new Rate('api_errors');
export const conflictRate = new Rate('optimistic_lock_conflicts');
export const conflictCount = new Counter('optimistic_conflict_count');
export const unexpectedCount = new Counter('unexpected_responses');
let context = {phase: 'other', target_vus: '0', measured: 'false'};
let contextProvider = null;
const knownLocations = new Map(); // Separate map per virtual user.
export function setContext(tags) { context = {...tags}; contextProvider = null; }
export function setContextProvider(provider) { contextProvider = provider; }
export function parse(response) {
  try { return JSON.parse(response.body); } catch (_) { return null; }
}
export function request(method, url, body = null, expected = [200], type = 'read') {
  if (contextProvider) context = contextProvider();
  const statuses = Array.isArray(expected) ? expected : [expected];
  const endpoint = url.replace(/\/[0-9a-f-]{36}/g, '/:id').split('?')[0];
  const tags = {...context, type, endpoint, name: `${method} ${endpoint}`};
  const r = http.request(method, url, body === null ? null : JSON.stringify(body), {
    headers: DEFAULT_HEADERS, tags, timeout: '10s',
    responseCallback: http.expectedStatuses(...statuses),
  });
  const passed = check(r, {[`${method} expected ${statuses.join('/')}`]: x => statuses.includes(x.status)}, tags);
  errorRate.add(!passed, tags);
  if (!passed) unexpectedCount.add(1, tags);
  if (method === 'PUT') {
    conflictRate.add(r.status === 409, tags); // Include non-conflicts in denominator.
    if (r.status === 409) conflictCount.add(1, tags);
  }
  return r;
}
function object(r, expected) {
  if (r.status !== expected) return null;
  const value = parse(r);
  check(value, {'response is JSON object': v => v !== null && typeof v === 'object' && !Array.isArray(v)}, context);
  return value;
}
export function checkHealth() {
  const r = request('GET', ENDPOINTS.HEALTH);
  return check(r, {'health status is ok': x => x.status === 200 && parse(x)?.status === 'ok'}, context);
}
export function createTravelPlan(data) {
  const p = object(request('POST', ENDPOINTS.TRAVEL_PLANS, data, 201, 'write'), 201);
  if (p) check(p, {'plan UUID and version': x => /^[0-9a-f-]{36}$/.test(x.id) && x.version === 1}, context);
  return p;
}
export function getTravelPlan(id) {
  const p = object(request('GET', ENDPOINTS.TRAVEL_PLAN_BY_ID(id)), 200);
  if (p) {
    check(p, {'plan has locations': x => Array.isArray(x.locations)}, context);
    for (const loc of p.locations || []) knownLocations.set(loc.id, loc);
  }
  return p;
}
export function listTravelPlans() {
  const r = request('GET', `${ENDPOINTS.TRAVEL_PLANS}?limit=50&offset=0`);
  const p = parse(r);
  check(r, {'plan list is array': x => x.status === 200 && Array.isArray(p)}, context);
  return r.status === 200 && Array.isArray(p) ? p : null;
}
export function updateTravelPlan(id, data, allowConflict = false) {
  const r = request('PUT', ENDPOINTS.TRAVEL_PLAN_BY_ID(id), data, allowConflict ? [200,409] : [200], 'write');
  if (r.status === 409) return {conflict: true, body: parse(r)};
  const p = object(r, 200);
  if (p) check(p, {'plan version increments': x => x.version === data.version + 1}, context);
  return p;
}
export function deleteTravelPlan(id) {
  const ok = request('DELETE', ENDPOINTS.TRAVEL_PLAN_BY_ID(id), null, 204, 'write').status === 204;
  for (const [lid,loc] of knownLocations) if (loc.travel_plan_id === id) knownLocations.delete(lid);
  return ok;
}
export function verifyPlanDeleted(id) {
  return request('GET', ENDPOINTS.TRAVEL_PLAN_BY_ID(id), null, 404).status === 404;
}
export function addLocation(planId, data) {
  const loc = object(request('POST', ENDPOINTS.LOCATIONS_FOR_PLAN(planId), data, 201, 'write'), 201);
  if (loc) {
    check(loc, {'location version and order': x => x.version === 1 && x.visit_order >= 1 && x.travel_plan_id === planId}, context);
    knownLocations.set(loc.id, loc);
  }
  return loc;
}
export function updateLocation(id, data, allowConflict = false) {
  const patch = {...data};
  if (patch.version === undefined) {
    const known = knownLocations.get(id);
    if (known) {
      const parent = getTravelPlan(known.travel_plan_id);
      const latest = parent?.locations.find(x => x.id === id);
      if (latest) patch.version = latest.version;
    }
  }
  const r = request('PUT', ENDPOINTS.LOCATION_BY_ID(id), patch, allowConflict ? [200,409] : [200], 'write');
  if (r.status === 409) return {conflict: true, body: parse(r)};
  const loc = object(r, 200);
  if (loc) {
    check(loc, {'location version increments': x => x.version === patch.version + 1}, context);
    knownLocations.set(id,loc);
  }
  return loc;
}
export function deleteLocation(id) {
  knownLocations.delete(id);
  return request('DELETE', ENDPOINTS.LOCATION_BY_ID(id), null, 204, 'write').status === 204;
}
export function testValidation(method,url,data) {
  return request(method,url,data,400,'write').status === 400;
}
export function thinkTime(min = 1,max = 3) {sleep(min + Math.random() * (max-min));}
