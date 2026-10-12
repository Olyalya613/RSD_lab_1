"""Record effective Docker settings; never save inspect/config environment secrets."""
import argparse,hashlib,json,platform,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def run(*args):return subprocess.check_output(args,cwd=ROOT,text=True,encoding='utf-8').strip()
def fingerprint():
    files=[ROOT/'app.py',ROOT/'docs/schema.sql',ROOT/'requirements.lock.txt',*sorted((ROOT/'tests/performance-tests').rglob('*.js'))]
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--profile',choices=['benchmark','limited'],default='benchmark');a=p.parse_args()
    compose=['docker','compose','-f','docker-compose.yml']
    if a.profile=='benchmark':compose+=['-f','docker-compose.benchmark.yml']
    config=json.loads(run(*compose,'config','--format','json'))
    info=json.loads(run('docker','info','--format','{{json .}}'))
    # Feed Python through stdin to avoid Windows quoting and exposing connection URL.
    code="""import json,os,platform,psycopg,hashlib
from pathlib import Path
from importlib.metadata import version
with psycopg.connect(os.environ['DATABASE_URL']) as c:
 d={'postgresql_version':c.execute('SELECT version()').fetchone()[0],
 'isolation':c.execute('SHOW default_transaction_isolation').fetchone()[0],
 'postgres_max_connections':c.execute('SHOW max_connections').fetchone()[0],
 'postgres_encoding':c.execute('SHOW server_encoding').fetchone()[0],
 'postgres_collation':c.execute('SELECT datcollate FROM pg_database WHERE datname=current_database()').fetchone()[0]}
d['python_version']=platform.python_version()
d['runtime_fingerprints']={name:hashlib.sha256((Path('/app')/name).read_bytes()).hexdigest() for name in ['app.py','docs/schema.sql','requirements.lock.txt']}
d['api_sha256']=d['runtime_fingerprints']['app.py']
d['dependencies']={n:version(n) for n in ['fastapi','uvicorn','psycopg','psycopg-pool']}
print(json.dumps(d))
"""
    api=json.loads(subprocess.check_output([*compose,'exec','-T','web','python','-'],input=code,cwd=ROOT,text=True,encoding='utf-8'))
    data=json.loads(a.output.read_text(encoding='utf-8-sig')) if a.output.exists() else {}
    data.update(api);data.update(execution='Docker Desktop Linux containers; host k6',profile=a.profile,docker_version=run('docker','version','--format','{{.Server.Version}}'),docker_os=info.get('OperatingSystem'),docker_cpus=info.get('NCPU'),docker_ram_gb=round(info.get('MemTotal',0)/1024**3,2),workers=1,db_pool_max=20,api_sha256=api['api_sha256'],source_fingerprints={**fingerprint(),**api['runtime_fingerprints']},git_head=run('git','rev-parse','HEAD') if __import__('shutil').which('git') else 'unavailable')
    data['containers']={}
    for service in ['web','postgres']:
        cid=run(*compose,'ps','-q',service)
        if not cid:raise RuntimeError(service+' is not running')
        inspected=json.loads(run('docker','inspect',cid))[0]
        data['containers'][service]={'id':cid,'image_id':inspected['Image'],'image_reference':inspected['Config']['Image'],'user':inspected['Config'].get('User'),'nano_cpus':inspected['HostConfig'].get('NanoCpus'),'memory_bytes':inspected['HostConfig'].get('Memory'),'read_only':inspected['HostConfig'].get('ReadonlyRootfs'),'command':inspected['Config'].get('Cmd')}
    data['compose_sha256']={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in ['Dockerfile','docker-compose.yml','docker-compose.benchmark.yml']}
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Recorded environment without credentials:',a.output)
if __name__=='__main__':main()
