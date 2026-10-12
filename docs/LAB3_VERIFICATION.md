# Lab 3 preparation checks

Docker Engine is not available in the preparation environment. No docker build, container startup, container Hurl run, docker stats measurement or Docker performance run is claimed.

Actual preparation checks:
- Docker Compose v2.39.0 config --quiet accepted base, benchmark and development configuration with locally generated .env.
- Python validation/analyzer/comparison suites: 17 passed, 11 real PostgreSQL concurrency checks skipped because no running test API/database is configured for this turn. Eight of the passed tests are new Lab 3 comparison checks.
- API and k6 files match the published Lab 2 code; CAS fixes are preserved.
- Python sources compile. PowerShell files are parsed with the PowerShell language parser.

The original Lab 2 verification logs are historical correctness evidence, not Docker run logs. Actual Windows baseline results are separately preserved in results/baseline from public commit 4fa48edf2e5dfdcf78325acde264215e86164117. Docker screenshots and measurements must be produced using START_HERE_LAB3_UA.md.
