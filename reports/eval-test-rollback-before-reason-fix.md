# SafeBump Run Report

- Started: `2026-08-20T08:12:09.957606+00:00`
- Finished: `2026-08-20T08:12:26.336172+00:00`
- Duration: `16.38 seconds`
- Controller branch: `codex/sb-09-11-build-agent`
- Run status: `completed`
- Package attempts: `1/4`

## Package Decisions

### httpx

- Attempted: `0.28.1 -> 1.0.dev3`
- Change type: `major`
- Decision: `rollback`
- Reason: pytest exited with 2: 1 warning, 1 error in 0.25s
- Pytest exit code: `2`
- pip check exit code: `0`
- Branch: `safebump/httpx-1.0.dev3`

#### Pytest evidence

```text
==================================== ERRORS ====================================
_____________________ ERROR collecting target/test_main.py _____________________
target/test_main.py:4: in <module>
    from fastapi.testclient import TestClient
.venv/lib/python3.14/site-packages/fastapi/testclient.py:1: in <module>
    from starlette.testclient import TestClient as TestClient  # noqa
    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.venv/lib/python3.14/site-packages/starlette/testclient.py:207: in <module>
    class _TestClientTransport(httpx.BaseTransport):
                               ^^^^^^^^^^^^^^^^^^^
E   AttributeError: module 'httpx' has no attribute 'BaseTransport'. Did you mean: 'Transport'?
=============================== warnings summary ===============================
.venv/lib/python3.14/site-packages/fastapi/testclient.py:1
  /mnt/Data/Projects/safebump/.venv/lib/python3.14/site-packages/fastapi/testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ============================
ERROR target/test_main.py - AttributeError: module 'httpx' has no attribute '...
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
1 warning, 1 error in 0.25s
```

#### pip check evidence

```text
No broken requirements found.
```

## Approval Gate

No remote action was requested or executed.

## Honesty and Coverage Boundary

The defined checks provide bounded evidence, not proof of complete safety.

The target test suite was not completed successfully in this run.

Not verified by this run:

- application behavior outside the six target tests
- production traffic and deployment behavior
- performance, concurrency, and load behavior
- security properties not represented by pip-audit
- platforms other than Ubuntu 26.04 LTS with Python 3.14.4
