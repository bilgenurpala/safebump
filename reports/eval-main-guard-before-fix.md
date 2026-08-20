# SafeBump Run Report

- Started: `2026-08-20T07:54:40.517441+00:00`
- Finished: `2026-08-20T07:54:40.519042+00:00`
- Duration: `0.00 seconds`
- Controller branch: `unavailable`
- Run status: `failed`
- Package attempts: `0/4`

## Package Decisions

No package decision completed.
## Approval Gate

No remote action was requested or executed.

## Honesty and Coverage Boundary

The defined checks provide bounded evidence, not proof of complete safety.

Verified by the target test suite:

- `test_seed_runs_once`
- `test_read_endpoints`
- `test_create_and_persist_task`
- `test_update_and_delete_task`
- `test_update_and_delete_unknown_task`
- `test_update_validation`

Not verified by this run:

- application behavior outside the six target tests
- production traffic and deployment behavior
- performance, concurrency, and load behavior
- security properties not represented by pip-audit
- platforms other than Ubuntu 26.04 LTS with Python 3.14.4

## Run Error

`RuntimeError: Refusing to run on default branch: main`
