import argparse,json,os,platform,subprocess
from importlib.metadata import version
from pathlib import Path
import psycopg
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
data=json.loads(a.output.read_text(encoding='utf-8-sig')) if a.output.exists() else {}
url=os.getenv('DATABASE_URL','postgresql://traveler_lab2:traveler_lab2_dev@127.0.0.1:5432/traveler_lab2')
with psycopg.connect(url) as conn:
    data['postgresql_version']=conn.execute('SELECT version()').fetchone()[0]
    data['isolation']=conn.execute('SHOW default_transaction_isolation').fetchone()[0]
    data['postgres_max_connections']=conn.execute('SHOW max_connections').fetchone()[0]
data['python_version']=platform.python_version()
data['dependencies']={name:version(name) for name in ['fastapi','uvicorn','psycopg','psycopg-pool']}
a.output.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
