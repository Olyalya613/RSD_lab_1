import {check,sleep,randomSeed} from 'k6';
import exec from 'k6/execution';
import {ENDPOINTS,BASE_URL,DEFAULT_THRESHOLDS,SMOKE_THRESHOLDS} from '../config/endpoints.js';
import {profile,VERIFY} from '../config/profiles.js';
import {generateTravelPlan,generateLocation} from './data-generator.js';
import {setContext,setContextProvider,checkHealth,createTravelPlan,getTravelPlan,listTravelPlans,addLocation,updateTravelPlan,updateLocation,deleteLocation,deleteTravelPlan,verifyPlanDeleted,request,parse} from './api-client.js';

export function optionsFor(name) {
  return {
    scenarios: {users:{executor:'ramping-vus',startVUs:0,stages:profile(name).map(x => ({duration:`${x.seconds}s`,target:x.target})),gracefulRampDown:'10s',gracefulStop:'10s'}},
    thresholds:name==='smoke'?SMOKE_THRESHOLDS:DEFAULT_THRESHOLDS,
    summaryTrendStats:['avg','min','med','max','p(90)','p(95)','p(99)'],
    userAgent:'TravelerAPI-Lab2-k6',
  };
}
function tagPhase(name) {
  const elapsed=(Date.now()-exec.scenario.startTime)/1000;
  let end=0; const phases=profile(name); let phase=phases[phases.length-1];
  for (const candidate of phases) {end+=candidate.seconds;if (elapsed < end) {phase=candidate;break;}}
  return {test:name,phase:phase.label,target_vus:String(phase.target),measured:'true'};
}
export function setupSuite(name) {
  setContext({test:name,phase:'setup',target_vus:'0',measured:'false'});
  if (!checkHealth()) throw new Error(`API unavailable at ${BASE_URL}. Start native API and PostgreSQL before k6.`);
  if (name==='smoke') return {ids:[]};
  const ids=[];
  try {
    for(let i=0;i<10;i++) {
      const p=createTravelPlan({...generateTravelPlan(),title:`K6 seed ${name} ${i}`});
      if(!p) throw new Error('Cannot create seed plan');
      ids.push(p.id);
      if(!addLocation(p.id,generateLocation()) || !addLocation(p.id,generateLocation())) throw new Error('Cannot create seed locations');
    }
  } catch(e) {for(const id of ids) deleteTravelPlan(id);throw e;}
  return {ids};
}
export function teardownSuite(name,data) {
  setContext({test:name,phase:'teardown',target_vus:'0',measured:'false'});
  for (const id of data?.ids || []) deleteTravelPlan(id);
}
function smokeJourney() {
  listTravelPlans();
  const p=createTravelPlan(generateTravelPlan());if(!p)return;
  try {
    getTravelPlan(p.id);
    const a=addLocation(p.id,generateLocation());const b=addLocation(p.id,generateLocation());
    const changed=updateTravelPlan(p.id,{title:'Updated plan',version:p.version});
    if(changed) request('PUT',ENDPOINTS.TRAVEL_PLAN_BY_ID(p.id),{budget:10,version:p.version},409,'write');
    if(a) {
      const changedLoc=updateLocation(a.id,{notes:'Tickets booked',version:a.version});
      if(changedLoc) {
        const stale=request('PUT',ENDPOINTS.LOCATION_BY_ID(a.id),{budget:10,version:a.version},409,'write');
        check(stale,{'stale location has current_version':x=>parse(x)?.current_version===changedLoc.version});
        const beforeOrder=getTravelPlan(p.id);
        if(beforeOrder) {
          updateLocation(a.id,{visit_order:2,version:changedLoc.version,order_version:beforeOrder.order_version});
          const afterOrder=getTravelPlan(p.id);
          const neighbour=afterOrder?.locations.find(x=>x.id===b?.id);
          if(neighbour) {
            const staleOrder=request('PUT',ENDPOINTS.LOCATION_BY_ID(neighbour.id),{visit_order:2,version:neighbour.version,order_version:beforeOrder.order_version},409,'write');
            check(staleOrder,{'stale collection has current_order_version':x=>parse(x)?.current_order_version===afterOrder.order_version});
          }
        }
      }
    }
    const ordered=getTravelPlan(p.id);
    check(ordered,{'location orders are unique':x=>!!x && new Set(x.locations.map(l=>l.visit_order)).size===x.locations.length});
    if(b) deleteLocation(b.id);
  } finally {deleteTravelPlan(p.id);verifyPlanDeleted(p.id);}
}
function ownedWrite() {
  const p=createTravelPlan(generateTravelPlan());if(!p)return;
  try {
    const loc=addLocation(p.id,generateLocation());
    getTravelPlan(p.id);
    updateTravelPlan(p.id,{budget:1250.50,version:p.version});
    if(loc) updateLocation(loc.id,{notes:'Booked',version:loc.version});
  } finally {deleteTravelPlan(p.id);}
}
export function runJourney(name,data) {
  if (__ITER === 0) randomSeed(42 + __VU);
  setContextProvider(() => tagPhase(name));
  if(name==='smoke') smokeJourney();
  else {
    const id=data.ids[Math.floor(Math.random()*data.ids.length)];
    const choice=Math.random();
    if(choice < .70) {listTravelPlans();getTravelPlan(id);}
    else if(choice < .90) ownedWrite();
    else {
      const p=getTravelPlan(id);
      if(p) {
        updateTravelPlan(id,{description:'Shared edit',version:p.version},true);
        const loc=p.locations[0];
        if(loc) updateLocation(loc.id,{notes:'Shared notes',version:loc.version},true);
      }
    }
  }
  sleep(Number(__ENV.THINK_SECONDS || .5));
}
export function summary(name,data) {
  const metrics=data.metrics || {};
  const vals=key=>metrics[key]?.values || {};
  const dur=vals('http_req_duration{measured:true}');
  const actualDur=Object.keys(dur).length?dur:vals('http_req_duration');
  const err=vals('http_req_failed{measured:true}');
  const actualErr=Object.keys(err).length?err:vals('http_req_failed');
  const lines=[`TEST: ${name}${VERIFY?' (VERIFICATION ONLY, NOT BASELINE)':''}`,
    `avg response: ${Number(actualDur.avg||0).toFixed(2)} ms`,
    `http_req_duration p95: ${Number(actualDur['p(95)']||0).toFixed(2)} ms`,
    `http_req_failed rate: ${(100*Number(actualErr.rate||0)).toFixed(3)}%`,
    `checks passed: ${(100*Number(vals('checks').rate||0)).toFixed(2)}%`,
    `requests: ${vals('http_reqs').count||0}; requests/s: ${Number(vals('http_reqs').rate||0).toFixed(2)}`,
    `expected optimistic conflicts: ${vals('optimistic_conflict_count').count||0}`,
    `BASE_URL: ${BASE_URL}`];
  const result={test:name,verificationOnly:VERIFY,baseUrl:BASE_URL,thinkSeconds:Number(__ENV.THINK_SECONDS || .5),phases:profile(name),summary:data};
  return {stdout:lines.join('\n')+'\n', [`${__ENV.RESULTS_DIR || 'results'}/${name}-summary.json`]:JSON.stringify(result,null,2)};
}
