"""Travel Planner API: PostgreSQL transactions and optimistic versions."""
import os
import re
from contextlib import asynccontextmanager
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from uuid import UUID

import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, Response

DB = os.getenv('DATABASE_URL', 'postgresql://traveler:traveler@localhost:5432/traveler')
pool = ConnectionPool(DB, min_size=1, max_size=20, open=False, kwargs={'row_factory': dict_row})
PLAN_FIELDS = ('title', 'description', 'start_date', 'end_date', 'budget', 'currency', 'is_public')
LOC_FIELDS = ('name', 'address', 'latitude', 'longitude', 'arrival_date', 'departure_date', 'budget', 'notes')

@asynccontextmanager
async def lifespan(app):
    pool.open(wait=True)
    with pool.connection() as conn:
        conn.execute(Path('docs/schema.sql').read_text(encoding='utf-8'))
    yield
    pool.close()

app = FastAPI(title='TravelerAPI', lifespan=lifespan)

@app.exception_handler(HTTPException)
async def error_handler(request, exc):
    if isinstance(exc.detail, dict):
        return JSONResponse(exc.detail, status_code=exc.status_code)
    return JSONResponse({'error': exc.detail}, status_code=exc.status_code)

@app.exception_handler(Exception)
async def internal_error(request, exc):
    return JSONResponse({'error': 'Internal error'}, status_code=500)

def fail(message='Validation error'):
    raise HTTPException(400, 'Validation error: ' + message)

def ident(value):
    try: return UUID(value)
    except (ValueError, TypeError): fail('invalid id')

def integer(value):
    if type(value) is not int or value <= 0: fail('version or order must be a positive integer')
    return value

def validate(data, kind, creation=False):
    fields = PLAN_FIELDS if kind == 'plan' else LOC_FIELDS
    if not isinstance(data, dict) or any(k not in (*fields, 'version', 'visit_order') for k in data): fail('unknown field')
    if creation and ('title' if kind == 'plan' else 'name') not in data: fail('name required')
    for key in ('title', 'name'):
        if key in data and (not isinstance(data[key], str) or not data[key].strip() or len(data[key]) > 200): fail(key)
    for key in ('description', 'address', 'notes'):
        if key in data and data[key] is not None and not isinstance(data[key], str): fail(key)
    if 'currency' in data and (not isinstance(data['currency'], str) or not re.fullmatch('[A-Z]{3}', data['currency'])): fail('currency')
    if 'is_public' in data and type(data['is_public']) is not bool: fail('is_public')
    for key in ('budget', 'latitude', 'longitude'):
        if key in data and data[key] is not None:
            try: number = Decimal(str(data[key]))
            except InvalidOperation: fail(key)
            if type(data[key]) is bool or not number.is_finite(): fail(key)
            if key == 'budget' and (number < 0 or number > Decimal('99999999.99') or number.as_tuple().exponent < -2): fail(key)
            if key == 'latitude' and not -90 <= number <= 90: fail(key)
            if key == 'longitude' and not -180 <= number <= 180: fail(key)
    for key in ('start_date', 'end_date', 'arrival_date', 'departure_date'):
        if key in data and data[key] is not None:
            try:
                if not isinstance(data[key], str): raise ValueError()
                (date.fromisoformat if key in ('start_date', 'end_date') else datetime.fromisoformat)(data[key].replace('Z', '+00:00'))
            except ValueError: fail(key)
    if 'version' in data: integer(data['version'])
    if 'visit_order' in data: integer(data['visit_order'])

def check_range(data, kind):
    a,b = ('start_date','end_date') if kind == 'plan' else ('arrival_date','departure_date')
    if data.get(a) is not None and data.get(b) is not None:
        parse = date.fromisoformat if kind == 'plan' else datetime.fromisoformat
        left = parse(data[a].replace('Z', '+00:00')) if isinstance(data[a], str) else data[a]
        right = parse(data[b].replace('Z', '+00:00')) if isinstance(data[b], str) else data[b]
        if left > right: fail('invalid date range')

def serial(row):
    if row is None: return None
    return {k: str(v) if isinstance(v, (UUID, Decimal)) and not isinstance(v, Decimal) else float(v) if isinstance(v, Decimal) else v.isoformat().replace('+00:00','Z') if isinstance(v, datetime) else v.isoformat() if isinstance(v, date) else v for k,v in row.items()}

async def payload(request):
    try: data = await request.json()
    except Exception: fail('invalid JSON')
    return data

def row_or_404(row):
    if row is None: raise HTTPException(404, 'Resource not found')
    return row

def update(cur, table, id_value, data, fields, version=None):
    changes = [k for k in fields if k in data]
    if not changes: fail('no fields to update')
    sql = f"UPDATE {table} SET " + ', '.join(f'{k}=%s' for k in changes) + ', version=version+1 WHERE id=%s'
    values = [data[k] for k in changes] + [id_value]
    if version is not None:
        sql += ' AND version=%s'
        values.append(version)
    return cur.execute(sql + ' RETURNING *', values).fetchone()

@app.get('/health')
def health():
    try:
        with pool.connection() as conn: conn.execute('SELECT 1')
        return {'status': 'ok'}
    except Exception: raise HTTPException(503, 'Health check failed')

@app.get('/api/travel-plans')
def plans(limit: int = 50, offset: int = 0):
    if not 1 <= limit <= 100 or offset < 0: fail('pagination')
    with pool.connection() as conn:
        return [serial(r) for r in conn.execute('SELECT * FROM travel_plans ORDER BY created_at, id LIMIT %s OFFSET %s', (limit,offset)).fetchall()]

@app.post('/api/travel-plans', status_code=201)
async def create_plan(request: Request):
    d=await payload(request); validate(d,'plan',True); check_range(d,'plan')
    keys=[k for k in PLAN_FIELDS if k in d]
    with pool.connection() as conn:
        row=conn.execute('INSERT INTO travel_plans (' + ','.join(keys) + ') VALUES (' + ','.join(['%s']*len(keys)) + ') RETURNING *', [d[k] for k in keys]).fetchone()
    return serial(row)

@app.get('/api/travel-plans/{id}')
def get_plan(id: str):
    pid=ident(id)
    with pool.connection() as conn:
        row=row_or_404(conn.execute('SELECT * FROM travel_plans WHERE id=%s',(pid,)).fetchone())
        locs=conn.execute('SELECT * FROM locations WHERE travel_plan_id=%s ORDER BY visit_order',(pid,)).fetchall()
        return {**serial(row), 'locations': [serial(r) for r in locs]}

@app.put('/api/travel-plans/{id}')
async def put_plan(id: str, request: Request):
    pid=ident(id); d=await payload(request); validate(d,'plan')
    if 'version' not in d: fail('version required')
    with pool.connection() as conn:
        with conn.cursor() as cur:
            current=row_or_404(cur.execute('SELECT * FROM travel_plans WHERE id=%s',(pid,)).fetchone())
            check_range({**current,**d},'plan')
            row=update(cur,'travel_plans',pid,d,PLAN_FIELDS,d['version'])
            if row is None:
                current=row_or_404(cur.execute('SELECT version FROM travel_plans WHERE id=%s',(pid,)).fetchone())
                raise HTTPException(409, {'error':'Conflict: resource modified', 'current_version':current['version']})
    return serial(row)

@app.delete('/api/travel-plans/{id}', status_code=204)
def delete_plan(id: str):
    with pool.connection() as conn:
        row=conn.execute('DELETE FROM travel_plans WHERE id=%s RETURNING id',(ident(id),)).fetchone()
        row_or_404(row)
    return Response(status_code=204)

@app.post('/api/travel-plans/{id}/locations', status_code=201)
async def create_location(id: str, request: Request):
    pid=ident(id); d=await payload(request); validate(d,'location',True); check_range(d,'location')
    if 'visit_order' in d: fail('order assigned automatically')
    with pool.connection() as conn:
        with conn.cursor() as cur:
            row_or_404(cur.execute('SELECT id FROM travel_plans WHERE id=%s FOR UPDATE',(pid,)).fetchone())
            order=cur.execute('SELECT COALESCE(MAX(visit_order),0)+1 AS n FROM locations WHERE travel_plan_id=%s',(pid,)).fetchone()['n']
            keys=[k for k in LOC_FIELDS if k in d]
            row=cur.execute('INSERT INTO locations (travel_plan_id,visit_order,'+','.join(keys)+') VALUES (%s,%s,'+','.join(['%s']*len(keys))+') RETURNING *',[pid,order]+[d[k] for k in keys]).fetchone()
    return serial(row)

@app.put('/api/locations/{id}')
async def put_location(id: str, request: Request):
    lid=ident(id); d=await payload(request); validate(d,'location')
    with pool.connection() as conn:
        with conn.cursor() as cur:
            existing=row_or_404(cur.execute('SELECT * FROM locations WHERE id=%s',(lid,)).fetchone())
            if 'version' not in d: fail('version required')
            row_or_404(cur.execute('SELECT id FROM travel_plans WHERE id=%s FOR UPDATE',(existing['travel_plan_id'],)).fetchone())
            existing=row_or_404(cur.execute('SELECT * FROM locations WHERE id=%s FOR UPDATE',(lid,)).fetchone())
            if existing['version'] != d['version']:
                raise HTTPException(409,{'error':'Conflict: resource modified','current_version':existing['version']})
            check_range({**existing,**d},'location')
            if 'visit_order' in d and d['visit_order'] != existing['visit_order']:
                target=d['visit_order']; old=existing['visit_order']; pid=existing['travel_plan_id']
                max_order=cur.execute('SELECT MAX(visit_order) AS n FROM locations WHERE travel_plan_id=%s',(pid,)).fetchone()['n']
                if target > max_order: fail('order exceeds number of locations')
                if target < old:
                    cur.execute('UPDATE locations SET visit_order=visit_order+1, version=version+1 WHERE travel_plan_id=%s AND visit_order >= %s AND visit_order < %s',(pid,target,old))
                else:
                    cur.execute('UPDATE locations SET visit_order=visit_order-1, version=version+1 WHERE travel_plan_id=%s AND visit_order > %s AND visit_order <= %s',(pid,old,target))
                cur.execute('UPDATE locations SET visit_order=%s WHERE id=%s',(target,lid))
            row=update(cur,'locations',lid,d,LOC_FIELDS + ('visit_order',))
    return serial(row)

@app.delete('/api/locations/{id}', status_code=204)
def delete_location(id: str):
    lid=ident(id)
    with pool.connection() as conn:
        with conn.cursor() as cur:
            existing=row_or_404(cur.execute('SELECT travel_plan_id FROM locations WHERE id=%s',(lid,)).fetchone())
            row_or_404(cur.execute('SELECT id FROM travel_plans WHERE id=%s FOR UPDATE',(existing['travel_plan_id'],)).fetchone())
            row_or_404(cur.execute('DELETE FROM locations WHERE id=%s RETURNING id',(lid,)).fetchone())
    return Response(status_code=204)
