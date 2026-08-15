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

