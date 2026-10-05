import {optionsFor,setupSuite,teardownSuite,runJourney,summary} from './utils/scenario.js';
export const options=optionsFor('spike');
for (const phase of ['baseline','spike','recovery']) {
  options.thresholds[`http_req_duration{phase:${phase}}`]=['p(95)<200'];
  options.thresholds[`http_req_failed{phase:${phase}}`]=['rate<0.01'];
}
// 10 to 1000 VUs in 2 seconds, then recovery at 10 VUs.

export function setup() {return setupSuite('spike');}
export default function(data) {runJourney('spike',data);}
export function teardown(data) {teardownSuite('spike',data);}
export function handleSummary(data) {return summary('spike',data);}
