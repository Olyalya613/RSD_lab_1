import {optionsFor,setupSuite,teardownSuite,runJourney,summary} from './utils/scenario.js';
export const options=optionsFor('stress');
for (const n of [100,200,400,600,1000]) {
  options.thresholds[`http_req_duration{phase:hold-${n}}`]=['p(95)<200'];
  options.thresholds[`http_req_failed{phase:hold-${n}}`]=['rate<0.01'];
}
// k6 exit 99 records failed SLOs without interrupting recovery measurements.

export function setup() {return setupSuite('stress');}
export default function(data) {runJourney('stress',data);}
export function teardown(data) {teardownSuite('stress',data);}
export function handleSummary(data) {return summary('stress',data);}
