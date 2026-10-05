const hold = (label, seconds, target) => ({label, seconds, target});
const loadPeak = Number(__ENV.LOAD_VUS || 100);
const spikePeak = Number(__ENV.SPIKE_VUS || 1000);
export const VERIFY = __ENV.VERIFY === '1';
export const PROFILES = {
  smoke: [hold('warmup',5,2),hold('steady',10,2),hold('cooldown',5,0)],
  load: [hold('ramp-10',15,10),hold('hold-10',30,10),hold('ramp-50',15,50),hold('hold-50',30,50),hold('ramp-peak',30,loadPeak),hold('peak',120,loadPeak),hold('cooldown',30,0)],
  stress: [100,200,400,600,1000].flatMap(n => [hold(`ramp-${n}`,30,n),hold(`hold-${n}`,60,n)]).concat([hold('recovery-ramp',15,10),hold('recovery',60,10),hold('cooldown',15,0)]),
  spike: [hold('warmup',10,10),hold('baseline',30,10),hold('spike-ramp',2,spikePeak),hold('spike',30,spikePeak),hold('drop',2,10),hold('recovery',60,10),hold('cooldown',10,0)],
  endurance: [hold('warmup',60,100),hold('steady',1680,100),hold('cooldown',60,0)], // Exactly 30 minutes.
};
for (const p of Object.values(PROFILES)) for (const x of p) {
  if (!Number.isInteger(x.target) || x.target < 0 || x.target > 5000) throw new Error('VU targets must be integers in 0..5000');
}
export function profile(name) {
  return PROFILES[name].map(x => VERIFY ? {...x,seconds:x.target===0?1:2,target:Math.min(x.target,5)} : {...x});
}
