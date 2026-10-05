# Verification scope

The archive contains actual verification logs, not invented benchmark results.

## Correctness verification

- Python 3.12 and dependencies from requirements.lock.txt.
- A real local PostgreSQL 16.6 process, listening on 127.0.0.1:55432.
- A real local Uvicorn process on 127.0.0.1:4567, one worker.
- No Docker processes were used for these checks.
- 20 unittest checks: five validation, four analyzer, eleven real HTTP/PostgreSQL concurrency checks.
- The concurrency suite uses barriers, multiple HTTP clients, and an actual held database row lock. It verifies database waiting through pg_stat_activity instead of assuming requests overlap.
- test_single_snapshot_while_writer_commits repeatedly reads the API while a separate database connection atomically updates the plan and its locations.

This execution sandbox exposes only UID 0 and does not allow switching to an unprivileged Unix UID. The scratch-only PostgreSQL verification build therefore disabled the initdb/postgres root-start guard. SQL, MVCC, locking and transaction engine code were unchanged. The test cluster used trust authentication on loopback and was stopped after testing. This build and its database are NOT included in the delivered project. On Windows install the standard PostgreSQL 16 release and run the supplied native scripts.

## Hurl verification

All five Hurl files passed: 69 HTTP requests, zero failed files. The new ordering.hurl checks collection-token enforcement and conflict reporting. See verification-hurl.txt.

## k6 verification

The five scripts are exercised with VERIFY=1, real HTTP and the same PostgreSQL cluster. Their reduced stage lengths and maximum of five users are only functional verification. Telemetry is disabled. See verification-k6-*.txt.

The numerical values in these logs are NOT Windows baseline measurements and must not be copied into the report's performance tables. The analyzer excludes verificationOnly results. No successful 30-minute Endurance measurement is claimed before the user runs the full profile.

## Repeat locally

Use START_HERE_UA.md for the exact Windows commands. Set TEST_DATABASE_URL and TEST_API_URL to the database and API you started, then run test_concurrency.py. Use a separate local lab database and do not run this suite during k6 measurements.
