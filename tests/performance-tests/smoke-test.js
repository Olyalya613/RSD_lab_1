import {optionsFor,setupSuite,teardownSuite,runJourney,summary} from './utils/scenario.js';
export const options=optionsFor('smoke');
export function setup() {return setupSuite('smoke');}
export default function(data) {runJourney('smoke',data);}
export function teardown(data) {teardownSuite('smoke',data);}
export function handleSummary(data) {return summary('smoke',data);}
