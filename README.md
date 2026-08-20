# SafeBump

SafeBump is a guarded, local Python agent designed to upgrade pinned dependencies in a single target project one package at a time. It validates every attempted upgrade with the target project's tests and dependency-compatibility check, then keeps or rolls back the change according to explicit rules.

The project was built during the [FlyRank AI internship](https://github.com/bilgenurpala/flyrank-internship) as a capstone agent. Its initial target is a disclosed copy of the internship's BE-02 FastAPI and SQLite project rather than a newly created backend.

## Status

SafeBump has a working end-to-end agent loop. It observes direct dependency updates and vulnerability findings, routes major versions to approval, attempts eligible upgrades on isolated branches, runs pytest and `pip check`, keeps or rolls back the candidate, and writes a bounded-evidence Markdown report. All five pre-written evaluation cases have been exercised on Ubuntu 26.04 LTS with Python 3.14.4.

## Architecture

```text
requirements + package index + audit findings
                    |
                    v
           prioritize one candidate
                    |
       major -------+------- patch/minor
         |                       |
     approval             branch + install
                                 |
                         pytest + pip check
                            |          |
                           keep     rollback
                            \          /
                             Markdown report
                                  |
                         remote approval gate
```

## Repository Structure

```text
.
|-- README.md
|-- build-log.md
|-- eval-fixtures/
|-- evals.md
|-- reports/
|-- raw-runs/
|-- safebump.py
|-- spec.md
|-- test_safebump.py
`-- target/
    |-- database.py
    |-- main.py
    |-- requirements.txt
    |-- test_main.py
    |-- docs/
    `-- sql/
```

## Setup

SafeBump is verified on Ubuntu 26.04 LTS with Python 3.14.4. Run it from a non-default branch because the default-branch guard intentionally stops on `main` and `master`.

```bash
git clone https://github.com/bilgenurpala/safebump.git
cd safebump
git switch -c local/safebump-run
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r target/requirements.txt
python -m pip install packaging
python3 -m venv .tools-venv
.tools-venv/bin/python -m pip install pip-audit
python safebump.py
```

Every run writes a timestamped file under `reports/`. To select the path explicitly:

```bash
python safebump.py --report reports/my-run.md
```

Run the deterministic guardrail tests with:

```bash
python -m unittest -v test_safebump.py
python -m pytest target/ -q
python -m pip check
```

SafeBump does not push, open pull requests, or merge. A remote request without explicit approval is recorded but not executed:

```bash
python safebump.py --request-remote-action push
```

## Evaluation Results

| Case | Expected | Observed | Result |
|---|---|---|:---:|
| EVAL-01 | Keep a safe patch | Uvicorn `0.52.4` kept after 6 tests and clean `pip check` | Pass |
| EVAL-02 | Roll back a test-breaking candidate | HTTPX `1.0.dev3` caused a `BaseTransport` collection error; `0.28.1` restored | Pass |
| EVAL-03 | Route a major security fix to approval | Vulnerable pytest `8.4.2` remained unchanged; major candidate was not installed | Pass |
| EVAL-04 | Reject a dependency conflict despite green tests | 6 tests passed, `pip check` failed, and Uvicorn `0.52.3` was restored | Pass |
| EVAL-05 | Block an unapproved remote action | Push remained local and no remote ref was created | Pass |

See [the complete expected-versus-observed record](evals.md), an [example successful report](reports/eval-unapproved-push.md), an [example rollback report](reports/eval-test-rollback.md), and the [unedited terminal logs](raw-runs/).

## Observed Baseline

Observed baseline:

- `pytest`: 6 passed, 1 existing `StarletteDeprecationWarning`
- `pip check`: no broken requirements found
- `pip-audit`: one known vulnerability in `pytest==8.4.2` (`PYSEC-2026-1845`), fixed in `9.0.3`

The audit finding is a prioritization input, not proof that an upgrade is safe. Because the available fix is a major upgrade, SafeBump must request human approval rather than apply it automatically.

## Project Evidence

- [Agent specification](spec.md)
- [Evaluation cases and results](evals.md)
- [Build log](build-log.md)
- [Run reports](reports/)
- [Raw terminal records](raw-runs/)

## Limitations

- The implementation covers one local Python project with direct `==` pins.
- Major upgrades, automatic push, automatic pull requests, merging, scheduling, multiple repositories, npm, and direct transitive-dependency upgrades are outside the MVP.
- Passing tests and `pip check` provide bounded evidence; they do not prove all application behavior or security properties.
- The baseline resolves unpinned transitive dependencies, so a fresh installation may change over time.
- Ubuntu 26.04 LTS with Python 3.14.4 is the only verified environment. Windows and macOS are untested.
- Kept upgrades remain on local branches for human review; SafeBump does not publish or merge them.

## License

SafeBump is released under the [MIT License](LICENSE).

