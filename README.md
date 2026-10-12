# TravelerAPI Lab 3

Read START_HERE_LAB3_UA.md for the Windows workflow.

Lab 3 adds a non-root multi-stage Dockerfile, PostgreSQL/API Compose stack, private .env generation, Hurl verification, Docker monitoring and k6 comparison with the user's actual published Lab 2 results.

The API and all five k6 scenarios are unchanged from lab2-corrected. Baseline measurements are preserved in results/baseline with source commit and file hashes. Docker measurements go to results/docker; they are not supplied until a real run.

Compose files:
- docker-compose.yml: full stack with health checks, private database network, named storage, CPU/RAM limits, log rotation and read-only non-root API.
- docker-compose.benchmark.yml: removes per-container caps for native comparison; Docker Desktop's VM-wide resources still apply.
- docker-compose.dev.yml: bind mounts and reload, only for development.

Run setup-env.ps1, start-stack.ps1, check-stack.ps1, collect-monitoring.ps1, run-performance.ps1, then container/build-report.py. k6 remains on Windows. The report uses actual measurements and never manufactures Docker numbers or screenshots.

Publish the local lab3-docker branch with git push -u origin lab3-docker. The repository has no extra outer project directory.
