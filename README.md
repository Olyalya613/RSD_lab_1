# TravelerAPI

REST API for collaborative travel planning. Python 3.12, FastAPI, psycopg 3, PostgreSQL 16. No sign-in or GUI.

## Start

Install Docker Desktop, start the engine, then run `docker compose up --build` in this directory. The API listens at `http://localhost:4567`, interactive documentation at `/docs`, health at `/health`. Database schema is created at startup. To clear local data: `docker compose down -v` (deletes the database volume). Docker Compose uses a development-only database password; change it before remote deployment.

Alternatively, start PostgreSQL locally, create database `traveler`, set `DATABASE_URL=postgresql://user:password@localhost:5432/traveler`, install `pip install -r requirements.txt`, and run `uvicorn app:app --port 4567`.

## Tests

Install Hurl; run `hurl --test ./tests/ --variables-file ./tests/variables.properties` with API and DB running. Hurl scripts are integration tests; the race script checks stale versions sequentially. For true simultaneous requests, run a separate concurrency load test. The tests were updated to include location versions after the v4 extension. The original tests assume `host=http://127.0.0.1:4567`.

## Concurrency

Plan update uses conditional `UPDATE ... WHERE id = %s AND version = %s` and returns HTTP 409 for a stale version. Location insertion and reordering lock the parent row with `FOR UPDATE`, serializing changes within a plan. A deferred unique constraint on `(travel_plan_id, visit_order)` protects the database; reordering shifts the intervening positions. Location PUT requires its own `version`; a stale request receives 409. The old Hurl tests lacking the version were adapted. DELETE endpoints intentionally have no version precondition, as in the supplied contract.

`GET /api/travel-plans/{id}` returns location versions. `PUT /api/locations/{id}` requires `version`, plus changed fields. `visit_order` is optional and selects an occupied position, shifting intervening locations. `POST` assigns the next order. Untrusted strings are returned as JSON; the server does not render HTML. Queries use parameters.

## Files

- `app.py`: REST endpoints, validation, transactions and version checks.
- `docs/schema.sql`: PostgreSQL constraints, keys and indexes.
- `docs/travel_api_swagger.json`: provided OpenAPI with version and port update.
- `tests/*.hurl`: CRUD, validation, ordering and stale-version scenarios.
- `compose.yaml`, `Dockerfile`, `requirements.txt`: setup and dependencies.

The PDF's 95th percentile latency and 1000 simultaneous user targets require measurements on a specified machine and production deployment; they are not asserted without benchmarks.
