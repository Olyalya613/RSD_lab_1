import argparse,hashlib,json,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--project',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
root=a.project.resolve();files=[root/'app.py',root/'docs/schema.sql',root/'requirements.lock.txt',*sorted((root/'tests/performance-tests').rglob('*.js'))]
hashes={str(x.relative_to(root)):hashlib.sha256(x.read_bytes()).hexdigest() for x in files if x.exists()}
try:head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
except (OSError,subprocess.SubprocessError):head='unavailable'
value={'source_project':str(root),'source_commit':head,'api_sha256':hashes.get('app.py'),'scenario_sha256':{name:h for name,h in hashes.items() if name.endswith('.js')},'runtime_fingerprints':{name:hashes.get(name) for name in ['app.py','docs/schema.sql','requirements.lock.txt']},'files':{x.name:hashlib.sha256(x.read_bytes()).hexdigest() for x in a.output.parent.iterdir() if x.is_file() and x!=a.output},'limitations':'Hashes were recorded at import; they are not proof of a clean worktree during the original native measurement.'}
a.output.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
