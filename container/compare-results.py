"""Compare actual analyzed streams with preserved Lab 2 results; no invented values."""
import argparse,importlib.util,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
NAMES=('smoke','load','stress','spike','endurance')
def read(path,default):return json.loads(path.read_text(encoding='utf-8-sig')) if path.exists() else default
def version_number(value):
    found=re.search(r'(?:PostgreSQL\s+|Python\s+|\bv)(\d+\.\d+(?:\.\d+)?)',str(value))
    return found.group(1) if found else str(value).split()[0] if value else None
def percentage_change(before,after):
    if before is None or after is None or before==0:return None
    return 100*(after-before)/before

def conditions(bmeta,dmeta,provenance):
    dmeta = dict(dmeta)
    dmeta['source_fingerprints'] = {
        key.replace('\\', '/'): value
        for key, value in dmeta.get('source_fingerprints', {}).items()
    }
    failures=[];notes=[]
    for key in ('cpu','logical_processors','python_version','isolation','workers','db_pool_max','postgres_max_connections'):
        if key not in bmeta or key not in dmeta:notes.append('Не зафіксовано обидва значення '+key)
        elif str(bmeta[key])!=str(dmeta[key]):failures.append('Відрізняється '+key)
    for key in ('postgresql_version','k6_version'):
        if bmeta.get(key) and dmeta.get(key) and version_number(bmeta[key])!=version_number(dmeta[key]):failures.append('Відрізняється '+key)
    if bmeta.get('dependencies') and dmeta.get('dependencies') and bmeta['dependencies']!=dmeta['dependencies']:failures.append('Відрізняються залежності API')
    if provenance.get('api_sha256') and dmeta.get('api_sha256') and provenance['api_sha256']!=dmeta['api_sha256']:failures.append('Відрізняється app.py')
    if provenance.get('scenario_sha256') and dmeta.get('source_fingerprints'):
        for name,digest in provenance['scenario_sha256'].items():
            if dmeta['source_fingerprints'].get(name)!=digest:failures.append('Змінено сценарій '+name)
    for name,digest in provenance.get('runtime_fingerprints',{}).items():
        if dmeta.get('source_fingerprints') and dmeta['source_fingerprints'].get(name)!=digest:failures.append('Відрізняється '+name)
    if not dmeta.get('source_fingerprints'):notes.append('Немає відбитків коду контейнерного запуску')
    for name,c in dmeta.get('containers',{}).items():
        if c.get('nano_cpus',0) or c.get('memory_bytes',0):notes.append('Є додаткові CPU/RAM обмеження контейнера '+name)
    notes.append('Windows native порівнюється з Linux у Docker Desktop; результат включає ОС, мережу, сховище та VM-wide обмеження.')
    return failures,notes

def compare(baseline,docker,bmeta,dmeta,provenance):
    b={x['test']:x for x in baseline};d={x['test']:x for x in docker}
    failures,notes=conditions(bmeta,dmeta,provenance)
    rows=[]
    for name in NAMES:
        before=b.get(name,{'test':name,'status':'not_run'});after=d.get(name,{'test':name,'status':'not_run'})
        problems=list(failures)
        bs=before.get('summary',{});ds=after.get('summary',{})
        ready=before.get('status')=='measured' and after.get('status')=='measured'
        if ready:
            if bs.get('phases')!=ds.get('phases'):problems.append('Відрізняються тривалість або VU профілю')
            if bs.get('thinkSeconds')!=ds.get('thinkSeconds'):problems.append('Відрізняється think time')
            if bs.get('verificationOnly') or ds.get('verificationOnly'):problems.append('Короткий VERIFY запуск')
            if bs.get('baseUrl')!=ds.get('baseUrl'):problems.append('Відрізняється адреса тестування')
        status='ready' if ready and not problems else 'different_conditions' if ready else 'awaiting_docker' if before.get('status')=='measured' else 'awaiting_baseline'
        old=before.get('overall',{});new=after.get('overall',{})
        delta={}
        if status=='ready':
            for key in ('avg_ms','p95_ms'):delta[key+'_percent']=percentage_change(old.get(key),new.get(key))
            if old.get('error_rate') is not None and new.get('error_rate') is not None:delta['errors_percentage_points']=100*(new['error_rate']-old['error_rate'])
        rows.append({'test':name,'comparison_status':status,'baseline_status':before.get('status'),'docker_status':after.get('status'),'baseline':old,'docker':new,'delta':delta,'problems':problems})
    return {'rows':rows,'environment_problems':failures,'method_notes':notes,'baseline_meta':bmeta,'docker_meta':dmeta}

def main():
    p=argparse.ArgumentParser();p.add_argument('--baseline',type=Path,default=ROOT/'results/baseline');p.add_argument('--docker',type=Path,default=ROOT/'results/docker');p.add_argument('--output',type=Path,default=ROOT/'results/comparison.json');a=p.parse_args()
    spec=importlib.util.spec_from_file_location('lab2_analysis',ROOT/'native/analyze-results.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    # Native raw streams were not committed, so preserve the actual published analysis.
    baseline=read(a.baseline/'analysis.json',[])
    docker=[module.analyze(a.docker,name) for name in NAMES]
    a.docker.mkdir(parents=True,exist_ok=True)
    (a.docker/'analysis.json').write_text(json.dumps(docker,ensure_ascii=False,indent=2),encoding='utf-8')
    result=compare(baseline,docker,read(a.baseline/'run-meta.json',{}),read(a.docker/'run-meta.json',{}),read(a.baseline/'provenance.json',{}))
    for index,name in enumerate(NAMES):
        per_test=read(a.docker/f'{name}-environment.json',None)
        if per_test is not None:
            one=compare(baseline,docker,read(a.baseline/'run-meta.json',{}),per_test,read(a.baseline/'provenance.json',{}))
            result['rows'][index]=one['rows'][index]
            result['rows'][index]['docker_environment']=per_test
    result['baseline_source']=read(a.baseline/'provenance.json',{})
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print(a.output)
if __name__=='__main__':main()
