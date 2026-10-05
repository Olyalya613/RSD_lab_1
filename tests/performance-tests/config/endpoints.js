export const BASE_URL = (__ENV.API_URL || 'http://localhost:4567').replace(/\/$/, '');
export const ENDPOINTS = {
  TRAVEL_PLANS: `${BASE_URL}/api/travel-plans`,
  TRAVEL_PLAN_BY_ID: id => `${BASE_URL}/api/travel-plans/${id}`,
  LOCATIONS_FOR_PLAN: id => `${BASE_URL}/api/travel-plans/${id}/locations`,
  LOCATION_BY_ID: id => `${BASE_URL}/api/locations/${id}`,
  HEALTH: `${BASE_URL}/health`,
};
export const DEFAULT_HEADERS = {'Content-Type': 'application/json'};
export const DEFAULT_THRESHOLDS = {
  'http_req_duration{measured:true}': ['p(95)<200'],
  'http_req_failed{measured:true}': ['rate<0.01'],
  checks: ['rate>0.99'],
};
export const SMOKE_THRESHOLDS = {'http_req_failed': ['rate==0'], checks: ['rate==1']};
export const STRESS_THRESHOLDS = DEFAULT_THRESHOLDS;
export const THINK_TIME = {MIN: 1, MAX: 3};
export const RETRY_CONFIG = {MAX_RETRIES: 0, RETRY_DELAY: 0};
