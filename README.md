# SafeBump

SafeBump is a guarded, local Python agent designed to upgrade pinned dependencies in a single target project one package at a time. It validates every attempted upgrade with the target project's tests and dependency-compatibility check, then keeps or rolls back the change according to explicit rules.

The project was built during the [FlyRank AI internship](https://github.com/bilgenurpala/flyrank-internship) as a capstone agent. Its initial target is a disclosed copy of the internship's BE-02 FastAPI and SQLite project rather than a newly created backend.

## Status

SafeBump is in the design phase. The specification and five pre-build evaluation cases were defined before any agent implementation was written.

## Repository Structure

```text
.
|-- README.md
|-- build-log.md
|-- evals.md
|-- spec.md
`-- target/
    |-- database.py
    |-- main.py
    |-- requirements.txt
    |-- test_main.py
    |-- docs/
    `-- sql/
```

## Baseline

The target was installed in an isolated virtual environment on Ubuntu 26.04 LTS with Python 3.14.4.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r target/requirements.txt
python -m pytest target/ -q
python -m pip check
```

Observed baseline:

- `pytest`: 6 passed, 1 existing `StarletteDeprecationWarning`
- `pip check`: no broken requirements found
- `pip-audit`: one known vulnerability in `pytest==8.4.2` (`PYSEC-2026-1845`), fixed in `9.0.3`

The audit finding is a prioritization input, not proof that an upgrade is safe. Because the available fix is a major upgrade, SafeBump must request human approval rather than apply it automatically.

## Design Documents

- [Agent specification](spec.md)
- [Pre-build evaluation cases](evals.md)
- [Build log](build-log.md)

## Limitations

- No agent implementation exists yet.
- The design covers one local Python project with pinned direct dependencies.
- Major upgrades, automatic push, automatic pull requests, merging, scheduling, multiple repositories, npm, and direct transitive-dependency upgrades are outside the MVP.
- Passing tests and `pip check` provide bounded evidence; they do not prove all application behavior or security properties.
- The baseline resolves unpinned transitive dependencies, so a fresh installation may change over time.
- Ubuntu 26.04 LTS with Python 3.14.4 is the only verified environment. Windows and macOS are untested.

## License

No license has been selected yet.

