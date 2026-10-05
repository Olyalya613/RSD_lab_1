import {optionsFor,setupSuite,teardownSuite,runJourney,summary} from './utils/scenario.js';
export const options=optionsFor('endurance');
options.thresholds['http_req_duration{phase:steady}']=['p(95)<200'];
options.thresholds['http_req_failed{phase:steady}']=['rate<0.01'];
// Default schedule: 60s warmup + 1680s steady + 60s cooldown = 30min.
// VERIFY=1 is solely a short code verification, not an endurance measurement.

export function setup() {return setupSuite('endurance');}
export default function(data) {runJourney('endurance',data);}
export function teardown(data) {teardownSuite('endurance',data);}
export function handleSummary(data) {return summary('endurance',data);}
