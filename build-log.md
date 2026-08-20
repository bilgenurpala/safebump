# SafeBump Build Log

This log records design and build evidence as it occurred. It is not a reconstructed success story.

## 2026-08-15 — SB-01: Project setup and baseline

### What happened

- Created a separate public `safebump` repository so future branch and rollback operations cannot move the internship repository underneath the agent itself.
- Copied the existing BE-02 FastAPI and SQLite project into `target/`. This is reused internship work, not a newly written backend.
- Created an isolated `.venv` on Ubuntu 26.04 LTS with Python 3.14.4 and installed the four pinned direct requirements.
- Ran the six target tests successfully with exit code 0.

### Friction and evidence

Repository setup was delayed by GitHub device-login and remote-desktop access friction. Work continued directly in the Linux environment rather than treating Windows results as Linux evidence.

The baseline was green but not warning-free: pytest reported one `StarletteDeprecationWarning` involving the freshly resolved transitive Starlette dependency and HTTPX. The warning predates any SafeBump upgrade and is recorded as baseline evidence, not hidden as a clean run.

### Decision

Keep BE-02 as the target because it provides four direct pins, six fast deterministic tests, SQLite, and no API key requirement. Do not claim a warning-free baseline or cross-platform support.

## 2026-08-15 — SB-02: Manual tool inspection

### What happened

Ran the planned tools manually before implementation:

- `pip list --outdated` reported newer versions for FastAPI, pip, `pydantic_core`, pytest, and Uvicorn.
- `pip check` reported no broken requirements.
- `pytest` passed all six tests with the existing warning.
- `git status` showed an unborn local `master` branch and the untracked `target/` copy.
- `pip-audit` was installed in a separate `.tools-venv` to avoid contaminating the target environment.
- `pip-audit -r target/requirements.txt` found one known vulnerability: `PYSEC-2026-1845` in `pytest==8.4.2`, with `9.0.3` listed as a fixed version.

### What changed

Separated the audit tool environment from the target environment. This preserves the meaning of target `pip check` and outdated-package output.

### Decision

Treat outdated discovery, vulnerability prioritization, compatibility checking, and behavioral testing as different signals. The pytest finding is security-priority input, but its major-version fix must still go to human approval.

## 2026-08-15 — SB-03: Decision rules and guardrails

### What changed

- Defined security finding > patch > minor as the review order while keeping every major release behind approval.
- Made pytest success and a clean `pip check` jointly required for a local keep.
- Expanded rollback from “restore the pin” to restoring the pin, Git state, target environment, and baseline checks.
- Added default-branch, dirty-tree, path, attempt, command-timeout, total-runtime, remote-action, and honesty guardrails.

### Design correction

The initial core-job wording treated passing tests as the only gate and used “only if” in a way that did not fully express the deterministic two-way decision. The specification now states both the keep and rollback paths and distinguishes bounded evidence from a claim of complete safety.

## 2026-08-15 — SB-04: Pre-build evaluations

### What happened

Defined five observable cases before agent code: compatible patch keep, test-failure rollback, major security-fix approval, `pip check` conflict despite passing tests, and blocked push/PR without approval.

### What changed

Each case now names a fixture, expected behavior, and evidence. The cases do not accept “worked well” as a result and do not duplicate the same gate: test failure and dependency conflict are evaluated independently.

### Limitation

The fixtures are specifications, not completed eval runs. Results must not be claimed until the implementation executes them.

## 2026-08-15 — SB-05: Platform and final design review

### Decision

Selected a scripted Python agent over n8n and a Claude Project. The safety-critical work is local CLI, filesystem, exit-code, branch, timeout, and rollback control; adding a visual or model-driven orchestration layer would not remove that implementation burden.

### Scope review

The MVP remains one Linux target, direct `==` pins, patch/minor automation, major approval, two verification gates, rollback, and a local report. Multi-repository operation, scheduling, npm, direct transitive upgrades, automatic remote actions, and merge remain excluded to preserve the ten-hour build target.

### Submission state

The design documents are ready for public-link verification. Portal submission, GitHub issue closure, and board movement must occur only after the files are pushed and the public links are checked.

## 2026-08-16 — SB-06: Observe

### What I tried

Implemented the read-only observation slice using JSON output from `pip list --outdated` and `pip-audit`. The script reads the four direct pins from `target/requirements.txt`, merges outdated and vulnerability evidence, classifies version changes, and sorts findings by security status, patch, minor, major, and unchanged packages.

### What broke

The first verification exposed that the local repository had been initialized without fetching or attaching to the existing remote history. Both `safebump.py` and the entire `target/` directory appeared untracked. The package scan worked, but the planned Git rollback could not have safely restored an untracked target.

### What I changed

Fetched `origin/main`, preserved the local files outside the repository, recreated the local `main` branch from `origin/main`, and created `feat/sb-06-observe` from the tracked baseline. I restored only `safebump.py`; the target now comes from the committed remote baseline.

### Evidence and decision

The observation run reported the vulnerable pytest major upgrade first, followed by the FastAPI and Uvicorn minor upgrades and the unchanged HTTPX pin. `git diff -- target` remained empty, the run stayed on `feat/sb-06-observe`, and the agent source hash remained unchanged. No dependency was installed or upgraded.

## 2026-08-16 — SB-07: One loop without a decision

### What I tried

Added a fixed one-package workflow for FastAPI `0.139.0` to `0.141.1`. The workflow checks the controller branch and tracked working tree, creates a package-specific branch, updates the direct pin, installs the candidate, runs pytest, prints the exit code and test evidence, and then restores the baseline pin and environment.

### What broke

The first run stopped before creating a branch because `safebump.py` still contained uncommitted changes. The clean-working-tree guard reported the tracked source modification, so no target file or dependency was changed.

The first successful run also exposed a branch-naming defect. `canonicalize_name()` was applied to the version as well as the package name, producing `safebump/fastapi-0-141-1` instead of the intended `safebump/fastapi-0.141.1`.

### What I changed

Committed the workflow implementation before retrying. I then separated package-name normalization from version normalization so package names remain canonical while version dots remain readable in branch names.

### Evidence and result

The corrected run created `safebump/fastapi-0.141.1`, installed FastAPI `0.141.1`, and captured pytest exit code `0`. All six tests passed with the existing `StarletteDeprecationWarning`. The result recorded `decision` as `null` because this slice does not choose whether to keep or roll back based on the test result.

The fixed cleanup sequence restored `target/requirements.txt` and the target environment to FastAPI `0.139.0`, returned to `feat/sb-07-one-loop`, and deleted the temporary package branch. Baseline pytest and `pip check` both returned exit code `0`.

## 2026-08-16 — SB-08: Decide

### What I tried

Extended the one-package workflow into a multi-package decision loop. Each eligible direct dependency receives its own branch and verification cycle. A candidate is kept only when both pytest and `pip check` return exit code `0`. Major upgrades are routed to human approval without installation, and unchanged packages are skipped.

### Normal run

The agent prioritized the vulnerable pytest upgrade first but did not install pytest `9.1.1` because it crosses a major-version boundary. It recorded `human_approval_required` even though the package had a known vulnerability.

FastAPI `0.141.1` and Uvicorn `0.52.3` each passed all six tests and produced a clean `pip check`, so the agent kept them on separate local branches. HTTPX was already current and was skipped. The controller branch and its baseline environment were restored between package attempts.

### Controlled failure

I explicitly approved a controlled major-version demo using HTTPX `1.0.dev3`. The candidate installed and `pip check` returned exit code `0`, but pytest failed during test collection with exit code `2`. Starlette's test client expected `httpx.BaseTransport`, which was absent from the candidate version.

This was important because package metadata alone reported no broken requirements while the application could not start its tests. The agent chose `rollback`, restored `httpx==0.28.1`, reinstalled the declared baseline, and reran both verification gates.

### Rollback evidence

After restoration, all six tests passed with the existing warning, `pip check` returned exit code `0`, and the rollback result recorded `verified: true`. The failed `safebump/httpx-1.0.dev3` branch was deleted. The FastAPI and Uvicorn keep branches remained available, while the controller requirements stayed at the original baseline.

The agent source SHA-256 remained `8178dcebf59cf92759aa36d0067c4221fcd07f9fbcb474d63ea9aaf79952de56` before and after the run.

### Decision boundary

The verification policy is deterministic rather than model-generated. The agent is not valuable because it invents a safety judgment; it is valuable because observed tool results change its next action. Passing tests and a clean dependency check lead to a local keep, failed or incomplete verification leads to rollback, and a major-version boundary leads to human approval.

## 2026-08-20 — SB-09: Markdown run reports

### What I tried

Added a Markdown report for every completed or stopped run. The report records start and finish times, duration, attempted packages, versions, branches, command exit codes, keep/rollback/approval decisions, concrete command output, the remote-action gate, and the coverage boundary.

### What broke

The first default-branch break test correctly stopped on `main`, but its report still listed all six tests under “Verified by the target test suite.” Pytest had never run because the branch guard stopped first. That made the report internally dishonest even though the guard itself worked.

The first improved rollback report also selected pytest's final `1 warning, 1 error` summary as its reason. The full evidence contained the real `AttributeError` involving `httpx.BaseTransport`, but the decision summary was still too generic for SB-09.

### What I changed

Made coverage reporting conditional on an observed successful pytest exit code. A guard-stopped run now says the target suite was not completed. Changed failure extraction to prefer pytest's concrete `E` exception line, so the HTTPX rollback reason names the absent `BaseTransport` API.

### Evidence

The before/after main reports and before/after rollback reports remain in `reports/`; matching unedited terminal sessions remain in `raw-runs/`. The final HTTPX report records the exact collection exception, and the restored baseline records 6 passed plus a clean `pip check`.

## 2026-08-20 — SB-10: Guardrails, approval gate, and honesty layer

### Implemented guardrails

- Refuse `main`, `master`, detached HEAD, and tracked dirty working trees before package mutation.
- Limit a run to four package attempts, ten minutes per command, and forty-five minutes in total.
- Record push and PR requests as awaiting explicit approval; never execute merge.
- Keep remote actions outside the automatic agent loop.
- Report only checks that actually ran and list behavior the six tests cannot verify.

### Break attempts

- Renamed a disposable clone branch to `main`; SafeBump exited `1` before observation or mutation and still wrote a failure report.
- Requested push without approval; the report recorded `executed: false`, and `git ls-remote` confirmed no matching remote branch.
- Exercised the second-attempt boundary and an expired run deadline through the deterministic guardrail tests; both raised and all seven unit tests passed on Linux.
- The main break attempt exposed the false coverage claim described in SB-09. It was fixed and rerun rather than hidden.

### Honesty boundary

A successful target run names the six tests that passed but still excludes production traffic, deployment behavior, load/concurrency, security properties outside the audit, and untested platforms. A stopped run no longer inherits those success claims.

## 2026-08-20 — SB-11: Five executed evaluations

### Results

- EVAL-01 passed: Uvicorn `0.52.4` was kept locally after 6 tests and clean dependency metadata.
- EVAL-02 passed after the report-reason fix: HTTPX `1.0.dev3` failed collection because `httpx.BaseTransport` was missing; `0.28.1` was restored and both baseline gates passed.
- EVAL-03 passed: vulnerable pytest `8.4.2` remained unchanged because the available candidate crossed a major boundary and required approval.
- EVAL-04 passed: a controlled local fixture produced a real Uvicorn metadata conflict. All 6 tests passed, `pip check` returned `1`, the candidate was rolled back, and the clean baseline was reverified.
- EVAL-05 passed: an unapproved push request performed no remote mutation.

### Raw evidence and limitation

The Linux terminal sessions are preserved without editing in `raw-runs/`; generated reports are preserved in `reports/`. The core dependency run completed without mid-run hand editing. The eval fixtures are controlled demonstrations for failure paths; they do not expand the supported production scope beyond one pinned Python target.
