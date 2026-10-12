"""Generate a local .env, without printing or overwriting credentials."""
import secrets
from pathlib import Path
from urllib.parse import quote
ROOT=Path(__file__).resolve().parents[1]
def main():
    target=ROOT/'.env'
    if target.exists():
        print('.env already exists; retained unchanged.');return
    example=(ROOT/'.env.example').read_text(encoding='utf-8')
    password=secrets.token_urlsafe(30)
    example=example.replace('POSTGRES_PASSWORD=REPLACE_WITH_YOUR_PASSWORD','POSTGRES_PASSWORD='+password)
    example=example.replace(':REPLACE_WITH_YOUR_PASSWORD@',':'+quote(password,safe='')+'@')
    with target.open('x',encoding='utf-8',newline='\n') as handle:handle.write(example)
    print('.env created. Credentials were not printed.')
if __name__=='__main__':main()
