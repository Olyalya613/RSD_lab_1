# TravelerAPI Lab 2

Native Windows Python + PostgreSQL + k6. Start with **START_HERE_UA.md**.

The repository root directly contains app.py, docs, native and tests. There is no outer traveler-lab directory and no Docker launch configuration.

Correctness changes:
- Blocking psycopg runs in synchronous FastAPI handlers in its thread pool.
- Location field updates use SQL compare-and-swap without a parent lock.
- Plan plus locations are read by one SQL statement with a consistent snapshot.
- Membership and ordering use travel_plans.order_version. Reordering requires both version and order_version. Append/delete/reorder advance the collection token.
- Real HTTP/PostgreSQL concurrency tests are in tests/test_concurrency.py.

Five k6 profiles are in tests/performance-tests. The Endurance profile lasts 30 minutes; VERIFY=1 is only a short code check and is excluded from baseline reports.

Run native/build-report.py after real measurements to regenerate the Word report. Missing measurements are explicitly marked. Verification logs in docs are correctness evidence, not Windows performance results.

Publish the included Git history with git push -u origin lab2-corrected. Never use GitHub Upload files to publish the local commit history.
