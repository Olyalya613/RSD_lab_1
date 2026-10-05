import {optionsFor,setupSuite,teardownSuite,runJourney,summary} from './utils/scenario.js';
export const options=optionsFor('load');
options.thresholds['http_req_duration{phase:peak}']=['p(95)<200'];
options.thresholds['http_req_failed{phase:peak}']=['rate<0.01'];
// The analyzer reports the largest tested plateau that satisfies both SLOs.

export function setup() {return setupSuite('load');}
export default function(data) {runJourney('load',data);}
export function teardown(data) {teardownSuite('load',data);}
export function handleSummary(data) {return summary('load',data);}
