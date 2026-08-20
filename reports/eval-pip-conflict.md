# SafeBump Run Report

- Started: `2026-08-20T08:19:22.963302+00:00`
- Finished: `2026-08-20T08:19:40.720523+00:00`
- Duration: `17.76 seconds`
- Controller branch: `codex/sb-09-11-build-agent`
- Run status: `completed`
- Package attempts: `1/4`

## Package Decisions

### uvicorn

- Attempted: `0.52.3 -> 0.52.4`
- Change type: `patch`
- Decision: `rollback`
- Reason: pip check exited with 1: safebump-conflict-fixture 1.0.0 has requirement uvicorn<0.52.4, but you have uvicorn 0.52.4.
- Pytest exit code: `0`
- pip check exit code: `1`
- Branch: `safebump/eval-pip-conflict`

#### Pytest evidence

```text
......                                                                   [100%]
=============================== warnings summary ===============================
.venv/lib/python3.14/site-packages/fastapi/testclient.py:1
  /mnt/Data/Projects/safebump/.venv/lib/python3.14/site-packages/fastapi/testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
6 passed, 1 warning in 0.24s
```

#### pip check evidence

```text
safebump-conflict-fixture 1.0.0 has requirement uvicorn<0.52.4, but you have uvicorn 0.52.4.
```

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
