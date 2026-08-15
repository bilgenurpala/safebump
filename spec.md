# SafeBump Agent Specification

## Core Job

SafeBump upgrades pinned Python packages in the target project's `requirements.txt` one at a time, keeps an upgrade when the target test suite passes and `pip check` reports no dependency conflicts, and otherwise restores the previous pin and environment state.

## User and Usage

The primary user is the developer maintaining the target Python project. The agent is run manually when reviewing outdated or vulnerable direct dependencies, not continuously or on an unverified schedule.

## Job Done

A run is complete when SafeBump has inspected the target's pinned direct dependencies, prioritized eligible candidates, attempted each permitted candidate at most once on a non-default branch, verified each attempt, restored failed attempts, and produced a Markdown report that distinguishes observed evidence from unverified behavior. Push, pull-request creation, major upgrades, and merge remain pending unless a human explicitly approves the relevant action.

## Scope

### Included in the MVP

- One local target repository
- Direct packages pinned with `==` in `target/requirements.txt`
- Security findings, patch upgrades, and minor upgrades
- One package per branch and verification cycle
- Keep-or-roll-back decisions based on `pytest` and `pip check`
- A local Markdown report and explicit approval gates

### Excluded from the MVP

- Automatic major upgrades
- Direct transitive-dependency upgrades
- Automatic push, pull-request creation, or merge
- Multiple repositories, scheduling, npm, lockfile generation, or dependency-resolution repair
- Claims of full application compatibility or vulnerability remediation

This scope is intended to fit approximately ten implementation hours by keeping the target, package format, toolchain, and decision policy fixed.

## Target and Data Sources

The target is `target/`, a disclosed copy of the FlyRank internship BE-02 project. It is a FastAPI and SQLite service with four pinned direct dependencies and six deterministic tests. SafeBump reads:

- `target/requirements.txt` for direct pins
- installed package metadata in the target virtual environment
- package-index metadata returned by pip when checking available versions
- vulnerability advisories returned by `pip-audit`
- the target test suite and process exit codes
- Git branch, diff, and working-tree state

Network access is required for package-index and vulnerability-advisory lookups and for installing an attempted version. The target tests themselves require neither an API key nor network access after the environment is installed.

## Verified Development Environment

This is the environment in which the target baseline and design tools were actually verified; it is not a cross-platform compatibility claim.

| Item | Verified value |
|---|---|
| Operating system | Ubuntu 26.04 LTS (Resolute Raccoon) |
| Python | 3.14.4 |
| Target environment | Repository-local `.venv` |
| Audit tool environment | Separate repository-local `.tools-venv` |
| Target baseline | 6 tests passed with 1 warning; exit code 0 |
| Dependency consistency | `pip check`: no broken requirements found |

The baseline warning is a `StarletteDeprecationWarning` produced in the freshly resolved baseline environment before any agent upgrade. Because `starlette` is transitive and unpinned, this warning cannot be attributed to a SafeBump change and the exact resolved baseline may vary on a future clean installation.

## Tools and Access Plan

| Tool or data source | Purpose | Access plan | Failure or decision meaning |
|---|---|---|---|
| `python -m pip list --outdated` | Discover installed packages with newer releases | Run locally inside the target `.venv`; uses the configured package index | A lookup/network failure stops discovery; the output is not a safety decision |
| `pip-audit` | Identify known advisories and suggested fixed versions | Run from `.tools-venv` against `target/requirements.txt`; uses the vulnerability service and package metadata | Findings raise priority; tool/network failure is reported as unknown, not as “no vulnerabilities” |
| `python -m pip check` | Verify installed dependency requirements are mutually compatible | Run locally inside the target `.venv` after an attempted install | Exit code 0 is required to keep an upgrade; nonzero triggers rollback |
| `python -m pytest target/ -q` | Exercise the target project's six behavioral tests | Run locally from the repository root inside the target `.venv` | Exit code 0 is required to keep an upgrade; nonzero triggers rollback |
| `git` | Inspect state, create isolated branches, show diffs, and restore failed attempts | Invoke the local CLI with argument lists in the target repository | Dirty/default-branch or unexpected-state checks stop mutation; push and merge require approval |
| File system | Read pins and write the local report | Restrict paths to the configured repository and `target/requirements.txt` | Missing, malformed, symlinked-outside-root, or out-of-scope paths stop the run |

### Why all three pip checks are needed

`pip list --outdated` answers what newer versions exist. It does not identify known vulnerabilities and does not prove that versions are compatible. `pip-audit` answers whether known advisories affect declared packages and supplies fix information when known. It does not prove application behavior and an unavailable advisory service is not a clean result. `pip check` answers whether the installed environment's declared dependency requirements are consistent. It does not search for newer versions, known vulnerabilities, or behavioral regressions. Discovery, security prioritization, and post-install consistency are separate questions, so none of these commands replaces the other two.

The manual design-phase run observed newer direct versions for FastAPI, pytest, and Uvicorn. It also found `PYSEC-2026-1845` in `pytest==8.4.2`, with `9.0.3` listed as the fixed version. Because this crosses a major-version boundary, the security priority does not override the human-approval rule.

## Draft Operating Instructions

1. Confirm that the configured path is the intended repository, the working tree is in an expected state, and the current branch is not `main` or `master` before changing a pin.
2. Read only direct `==` pins from `target/requirements.txt`; do not select pip itself or unpinned transitive packages as direct targets.
3. Collect outdated-version and audit evidence. Prioritize known security findings first, then patch releases, then minor releases. Route every major release to human approval without installing it automatically.
4. Create a dedicated branch for one eligible package and record the starting commit, pin, and environment state.
5. Change only that direct pin, install the candidate, and run the fixed verification commands.
6. Keep the attempt only when both pytest and `pip check` exit successfully. Otherwise restore the previous pin, restore the target environment from the restored requirements, re-run the baseline checks, and record the failing evidence.
7. Produce a Markdown report containing the candidate, reason for priority, commands, exit codes, decision, rollback result, warnings, and anything that could not be verified.
8. Ask for explicit human approval before a major upgrade, push, or pull-request action. Never merge.

## Decision Rules

### Prioritization

1. A direct dependency with a known vulnerability
2. A patch upgrade
3. A minor upgrade
4. A major upgrade, which is reported for approval and never attempted automatically

Security priority determines review order, not permission. A security fix that requires a major upgrade remains behind the major-upgrade approval gate.

### Keep or Roll Back

| Pytest | `pip check` | Decision |
|---|---|---|
| Pass | Clean | Keep the local branch change and report bounded success |
| Fail | Clean or not run | Roll back and record the test failure |
| Pass | Conflict | Roll back and record the dependency conflict |
| Tool error or timeout | Any | Treat verification as incomplete, roll back, and report uncertainty |

Rollback means restoring the previous requirements pin and Git state, restoring the target environment from that baseline, and confirming that baseline pytest and `pip check` results are recovered. Merely editing the requirements file back is not a complete rollback.

## Guardrails and Approval Gates

- Never modify dependencies while on `main` or `master`.
- Stop before mutation if the working tree contains unexpected changes.
- Attempt one package at a time on a dedicated branch.
- Attempt each selected candidate at most once per run.
- Allow at most four package attempts in one run.
- Apply a ten-minute timeout to each external command and a forty-five-minute limit to the full run.
- Never install a major upgrade without explicit human approval.
- Never push or create a pull request without explicit human approval for that action.
- Never merge.
- Never treat missing audit data, a timed-out check, or a tool error as a clean result.
- Report the exact checks that passed, warnings that remained, and areas the test suite did not cover. Use language such as “the defined checks passed” rather than claiming complete safety.

Local edits and disposable branches are reversible when their starting state is recorded. A published branch, pull request, merge, or major-version migration can affect other people or require broader review, so those operations are not autonomous.

## Platform Decision

SafeBump will be implemented as a scripted Python agent. Its tools are local CLI programs and files, and Python can invoke them with explicit argument lists, capture exit codes and timeouts, enforce path and branch checks, and implement deterministic rollback without a paid service.

An n8n workflow would make the sequence visible, but local Git branches, virtual environments, subprocess exit codes, and filesystem rollback would require shell-heavy custom nodes. That adds an orchestration layer without reducing the risky implementation work. A Claude Project with connectors would help with explanation and report drafting, but it would depend on model-driven tool selection for a safety-sensitive loop and would not provide the same deterministic local execution boundary. The Python path is therefore the smallest platform that matches the job and demonstrates the intended backend capability.

The trade-off is maintenance: subprocess behavior, pip output, advisory availability, and package formats can change. The MVP limits that maintenance burden by supporting one verified Linux environment, direct `==` pins, fixed commands, and explicit failure-closed rules.

## Pre-Build Evaluation Plan

Five measurable cases were defined in [evals.md](evals.md) before implementation. Each case specifies its fixture, observable behavior, and verification evidence. Passing those cases will demonstrate conformance to this specification, not universal dependency safety.

## Known Limitations

- The six tests cover the BE-02 behavior represented in `test_main.py`; they do not prove every runtime path.
- `pip check` verifies declared dependency compatibility, not semantic application compatibility.
- `pip-audit` depends on known advisories and available data; absence of a finding is not proof of absence.
- Unpinned transitive dependencies make fresh baseline resolution time-dependent.
- Only Ubuntu 26.04 LTS and Python 3.14.4 have been verified. Windows and macOS are untested.

