"""Analyze real k6 JSON/GZIP streams; never synthesize benchmark numbers."""
import argparse
import csv
import gzip
import json
import math
from array import array
from collections import defaultdict
from datetime import datetime
from pathlib import Path

NAMES = ('smoke','load','stress','spike','endurance')

def quantile(values, q=.95):
    if not values: return None
    values=sorted(values); pos=(len(values)-1)*q; lo=math.floor(pos); hi=math.ceil(pos)
    return values[lo] + (values[hi]-values[lo])*(pos-lo)

def group():
    return {'durations':array('d'),'errors':0.0,'requests':0,'conflicts':0,'target':0,'first':float('inf'),'last':0.0}

def stats(g):
    d=g['durations']; n=g['requests']
    return {'requests':n,'avg_ms':sum(d)/len(d) if d else None,'p95_ms':quantile(d),
            'error_rate':g['errors']/n if n else None,'expected_conflicts':g['conflicts'],
            'configured_vus':g['target'],'first_time':None if math.isinf(g['first']) else g['first'],'last_time':g['last']}

def within_slo(row):
    return row['requests']>=20 and row['p95_ms'] is not None and row['p95_ms']<200 and row['error_rate'] is not None and row['error_rate']<.01

def analyze(folder,name):
    summary_file=folder/f'{name}-summary.json'
    if not summary_file.exists(): return {'test':name,'status':'not_run'}
    summary=json.loads(summary_file.read_text(encoding='utf-8-sig'))
    if summary.get('verificationOnly'): return {'test':name,'status':'verification_only'}
    streams=[folder/f'{name}-metrics.json.gz',folder/f'{name}-metrics.json']
    stream=next((p for p in streams if p.exists()),None)
    if not stream: return {'test':name,'status':'missing_stream','summary':summary}
    phases=defaultdict(group); windows=defaultdict(group); recovery=defaultdict(group); vus=[]
    reader=gzip.open if stream.suffix=='.gz' else open
    with reader(stream,'rt',encoding='utf-8-sig') as handle:
        for line in handle:
            point=json.loads(line)
            if point.get('type')!='Point':continue
            metric=point.get('metric'); data=point['data']; tags=data.get('tags') or {}; v=float(data['value'])
            timestamp=datetime.fromisoformat(data['time'].replace('Z','+00:00')).timestamp()
            if metric=='vus': vus.append((timestamp,int(v)));continue
            if tags.get('measured')!='true':continue
            phase=tags.get('phase','unknown'); target=int(tags.get('target_vus','0'))
            groups=[phases[phase],windows[int(timestamp//30)]]
            if phase=='recovery':groups.append(recovery[int(timestamp//5)])
            for g in groups:
                g['target']=target;g['first']=min(g['first'],timestamp);g['last']=max(g['last'],timestamp)
                if metric=='http_req_duration':g['durations'].append(v)
                elif metric=='http_req_failed':g['requests']+=1;g['errors']+=v
                elif metric=='optimistic_conflict_count':g['conflicts']+=int(v)
    rows={phase:stats(g) for phase,g in phases.items()}
    for r in rows.values():
        r['observed_max_vus']=max((n for t,n in vus if r['first_time'] is not None and r['first_time']<=t<=r['last_time']),default=None)
    measured=group()
    for g in phases.values():
        measured['durations'].extend(g['durations']);measured['requests']+=g['requests'];measured['errors']+=g['errors'];measured['conflicts']+=g['conflicts']
    result={'test':name,'status':'measured','summary':summary,'overall':stats(measured),'phases':rows,
            'observed_max_vus':max((n for _,n in vus),default=None),
            'timeline':[{'time':k*30,**stats(g)} for k,g in sorted(windows.items())],
            'exit_code':int((folder/f'{name}-exit-code.txt').read_text().strip()) if (folder/f'{name}-exit-code.txt').exists() else None}
    duration_ms=summary.get('summary',{}).get('state',{}).get('testRunDurationMs')
    planned_ms=sum(x['seconds'] for x in summary.get('phases',[]))*1000
    result['planned_duration_seconds']=planned_ms/1000
    result['recorded_duration_seconds']=duration_ms/1000 if duration_ms is not None else None
    if duration_ms is not None and duration_ms + 1000 < planned_ms:
        result['status']='incomplete'
    if result['exit_code'] not in (None,0,99):result['status']='incomplete'
    if name=='load':
        holds=[r for phase,r in rows.items() if phase.startswith('hold-') or phase=='peak']
        acceptable=[r['configured_vus'] for r in holds if within_slo(r) and r['observed_max_vus'] is not None and r['observed_max_vus']>=r['configured_vus']]
        result['largest_tested_vus_within_slo']=max(acceptable,default=None)
        result['peak']=rows.get('peak')
    if name=='stress':
        holds=sorted((r for phase,r in rows.items() if phase.startswith('hold-')),key=lambda r:r['configured_vus'])
        degraded=next((r['configured_vus'] for r in holds if r['requests']>=20 and not within_slo(r)),None)
        broken=next((r['configured_vus'] for r in holds if r['requests']>=20 and (r['error_rate']>=.05 or r['p95_ms']>=2000)),None)
        result.update(degradation_vus=degraded,operational_breaking_point_vus=broken,recovered_within_slo=within_slo(rows.get('recovery',stats(group()))))
    if name=='spike':
        baseline=rows.get('baseline'); rebound=rows.get('recovery'); delay=None
        cap=max(200,1.2*baseline['p95_ms']) if baseline and baseline['p95_ms'] is not None else 200
        stable=0; previous=None
        for idx,g in sorted(recovery.items()):
            r=stats(g)
            ok=r['requests']>=5 and r['p95_ms'] is not None and r['p95_ms']<=cap and r['error_rate']<.01
            stable=stable+1 if ok and (previous is None or idx==previous+1) else (1 if ok else 0)
            previous=idx
            if stable>=3 and rebound:
                delay=max(0,(idx+1)*5-rebound['first_time']);break
        result.update(recovery_seconds=delay,recovery_p95_limit_ms=cap,spike=rows.get('spike'))
    if name=='endurance':
        steady=phases.get('steady'); first=array('d'); last=array('d')
        if steady:
            start=steady['first'];end=steady['last']
            for k,g in windows.items():
                if k*30>=start and (k+1)*30<=start+300:first.extend(g['durations'])
                if k*30>=end-300 and (k+1)*30<=end:last.extend(g['durations'])
        a=quantile(first);b=quantile(last)
        result.update(first_five_minutes_p95_ms=a,last_five_minutes_p95_ms=b,p95_growth_ratio=b/a if a and b is not None else None)
    return result

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--results',type=Path,default=Path(__file__).resolve().parents[1]/'tests/performance-tests/results');args=parser.parse_args()
    args.results.mkdir(parents=True,exist_ok=True)
    results=[analyze(args.results,name) for name in NAMES]
    (args.results/'analysis.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
    with (args.results/'phase-metrics.csv').open('w',newline='',encoding='utf-8-sig') as handle:
        fields=['test','phase','configured_vus','observed_max_vus','requests','avg_ms','p95_ms','error_rate','expected_conflicts']
        writer=csv.DictWriter(handle,fieldnames=fields);writer.writeheader()
        for result in results:
            for phase,row in result.get('phases',{}).items():writer.writerow({'test':result['test'],'phase':phase,**{f:row.get(f) for f in fields if f not in ('test','phase')}})
    print(args.results/'analysis.json')

if __name__=='__main__':main()
