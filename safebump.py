import argparse
import hashlib
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from packaging.utils import canonicalize_name
from packaging.version import Version


REPO_ROOT = Path(__file__).resolve().parent
TARGET_DIR = REPO_ROOT / "target"
REQUIREMENTS_PATH = TARGET_DIR / "requirements.txt"
TARGET_PYTHON = REPO_ROOT / ".venv" / "bin" / "python"
PIP_AUDIT = REPO_ROOT / ".tools-venv" / "bin" / "pip-audit"
SOURCE_PATH = Path(__file__).resolve()
REPORTS_DIR = REPO_ROOT / "reports"
COMMAND_TIMEOUT_SECONDS = 600
RUN_TIMEOUT_SECONDS = 2700
MAX_ATTEMPTS = 4
VERIFIED_TESTS = [
    "test_seed_runs_once",
    "test_read_endpoints",
    "test_create_and_persist_task",
    "test_update_and_delete_task",
    "test_update_and_delete_unknown_task",
    "test_update_validation",
]
UNVERIFIED_AREAS = [
    "application behavior outside the six target tests",
    "production traffic and deployment behavior",
    "performance, concurrency, and load behavior",
    "security properties not represented by pip-audit",
    "platforms other than Ubuntu 26.04 LTS with Python 3.14.4",
]


class RunLimits:
    def __init__(
        self,
        max_attempts: int = MAX_ATTEMPTS,
        run_timeout_seconds: int = RUN_TIMEOUT_SECONDS,
    ) -> None:
        self.max_attempts = max_attempts
        self.deadline = time.monotonic() + run_timeout_seconds
        self.attempts = 0

    def remaining_seconds(self) -> int:
        remaining = int(self.deadline - time.monotonic())

        if remaining <= 0:
            raise TimeoutError("The total run time limit was reached")

        return remaining

    def begin_attempt(self) -> None:
        if self.attempts >= self.max_attempts:
            raise RuntimeError(
                f"The package attempt limit of {self.max_attempts} was reached"
            )

        self.remaining_seconds()
        self.attempts += 1


RUN_LIMITS: RunLimits | None = None


def run_command(
    args: list[str],
    accepted_exit_codes: set[int],
) -> subprocess.CompletedProcess[str]:
    timeout = COMMAND_TIMEOUT_SECONDS

    if RUN_LIMITS is not None:
        timeout = min(timeout, RUN_LIMITS.remaining_seconds())

    result = subprocess.run(
        args,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )

    if result.returncode not in accepted_exit_codes:
        message = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(
            f"Command failed with exit code {result.returncode}: "
            f"{' '.join(args)}\n{message}"
        )

    return result


def read_direct_dependencies() -> dict[str, dict[str, str]]:
    dependencies = {}

    for raw_line in REQUIREMENTS_PATH.read_text(
        encoding="utf-8"
    ).splitlines():
        line = raw_line.strip()

        if not line or line.startswith("#") or "==" not in line:
            continue

        name, version = line.split("==", maxsplit=1)
        normalized_name = canonicalize_name(name.strip())

        dependencies[normalized_name] = {
            "name": name.strip(),
            "current_version": version.strip(),
        }

    return dependencies


def collect_outdated_packages() -> dict[str, dict[str, str]]:
    result = run_command(
        [
            str(TARGET_PYTHON),
            "-m",
            "pip",
            "list",
            "--outdated",
            "--format=json",
            "--disable-pip-version-check",
        ],
        {0},
    )
    packages = json.loads(result.stdout)

    return {
        canonicalize_name(package["name"]): package
        for package in packages
    }


def collect_audit_results() -> dict[str, list[dict[str, object]]]:
    result = run_command(
        [
            str(PIP_AUDIT),
            "-r",
            str(REQUIREMENTS_PATH),
            "--format",
            "json",
            "--progress-spinner",
            "off",
        ],
        {0, 1},
    )

    payload = json.loads(result.stdout)
    dependencies = payload.get("dependencies", payload)
    findings = {}

    for dependency in dependencies:
        name = canonicalize_name(dependency["name"])
        vulnerabilities = []

        for vulnerability in dependency.get("vulns", []):
            vulnerabilities.append(
                {
                    "id": vulnerability["id"],
                    "fix_versions": vulnerability.get(
                        "fix_versions",
                        [],
                    ),
                }
            )

        findings[name] = vulnerabilities

    return findings


def classify_change(
    current_version: str,
    latest_version: str,
) -> str:
    current = Version(current_version)
    latest = Version(latest_version)

    if latest.major != current.major:
        return "major"

    if latest.minor != current.minor:
        return "minor"

    if latest.micro != current.micro:
        return "patch"

    return "none"


def priority_key(
    package: dict[str, object],
) -> tuple[int, str]:
    if package["has_vulnerability"]:
        priority = 0
    else:
        priority = {
            "patch": 1,
            "minor": 2,
            "major": 3,
            "none": 4,
        }[package["change_type"]]

    return priority, str(package["name"]).lower()


def observe() -> list[dict[str, object]]:
    direct_dependencies = read_direct_dependencies()
    outdated_packages = collect_outdated_packages()
    audit_results = collect_audit_results()
    observations = []

    for normalized_name, dependency in direct_dependencies.items():
        outdated = outdated_packages.get(normalized_name)
        current_version = dependency["current_version"]
        latest_version = (
            outdated["latest_version"]
            if outdated
            else current_version
        )
        vulnerabilities = audit_results.get(normalized_name, [])

        observations.append(
            {
                "name": dependency["name"],
                "current_version": current_version,
                "latest_version": latest_version,
                "change_type": classify_change(
                    current_version,
                    latest_version,
                ),
                "has_vulnerability": bool(vulnerabilities),
                "vulnerabilities": vulnerabilities,
            }
        )

    return sorted(observations, key=priority_key)


def git_output(args: list[str]) -> str:
    result = run_command(["git", *args], {0})
    return result.stdout.strip()


def require_safe_branch() -> str:
    branch = git_output(["branch", "--show-current"])

    if not branch:
        raise RuntimeError("Detached HEAD is not allowed")

    if branch in {"main", "master"}:
        raise RuntimeError(
            f"Refusing to run on default branch: {branch}"
        )

    return branch


def require_clean_worktree() -> None:
    status = git_output(
        [
            "status",
            "--porcelain",
            "--untracked-files=no",
        ]
    )

    if status:
        raise RuntimeError(
            "Tracked working tree changes must be committed first:\n"
            f"{status}"
        )


def source_hash() -> str:
    return hashlib.sha256(SOURCE_PATH.read_bytes()).hexdigest()


def normalize_package_component(value: str) -> str:
    return canonicalize_name(value)


def normalize_version_component(value: str) -> str:
    normalized = str(Version(value))

    return "".join(
        character
        for character in normalized
        if character.isalnum() or character in {"-", "."}
    )


def build_upgrade_branch(
    package_name: str,
    candidate_version: str,
) -> str:
    package = normalize_package_component(package_name)
    version = normalize_version_component(candidate_version)

    return f"safebump/{package}-{version}"


def replace_requirement_pin(
    package_name: str,
    current_version: str,
    candidate_version: str,
) -> None:
    original = REQUIREMENTS_PATH.read_text(encoding="utf-8")
    old_pin = f"{package_name}=={current_version}"
    new_pin = f"{package_name}=={candidate_version}"

    if original.count(old_pin) != 1:
        raise RuntimeError(
            f"Expected exactly one requirement pin for {old_pin}"
        )

    REQUIREMENTS_PATH.write_text(
        original.replace(old_pin, new_pin),
        encoding="utf-8",
    )


def install_candidate(
    package_name: str,
    candidate_version: str,
) -> None:
    run_command(
        [
            str(TARGET_PYTHON),
            "-m",
            "pip",
            "install",
            f"{package_name}=={candidate_version}",
        ],
        {0},
    )


def run_pytest() -> subprocess.CompletedProcess[str]:
    return run_command(
        [
            str(TARGET_PYTHON),
            "-m",
            "pytest",
            str(TARGET_DIR),
            "-q",
        ],
        set(range(256)),
    )


def run_pip_check() -> subprocess.CompletedProcess[str]:
    return run_command(
        [
            str(TARGET_PYTHON),
            "-m",
            "pip",
            "check",
        ],
        set(range(256)),
    )


def failure_detail(result: subprocess.CompletedProcess[str]) -> str:
    output = "\n".join(
        part.strip()
        for part in [result.stdout, result.stderr]
        if part.strip()
    )
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    markers = ("error", "failed", "incompatible", "requires", "conflict")

    for line in lines:
        if line.startswith("E   "):
            return line.removeprefix("E   ").strip()

    for line in reversed(lines):
        if any(marker in line.lower() for marker in markers):
            return line

    return lines[-1] if lines else "no command output was captured"


def restore_baseline_environment() -> None:
    run_command(
        [
            str(TARGET_PYTHON),
            "-m",
            "pip",
            "install",
            "--force-reinstall",
            "-r",
            str(REQUIREMENTS_PATH),
        ],
        {0},
    )


def restore_requirement_file() -> None:
    run_command(
        [
            "git",
            "restore",
            "--source",
            "HEAD",
            "--",
            str(REQUIREMENTS_PATH.relative_to(REPO_ROOT)),
        ],
        {0},
    )


def verify_restored_baseline() -> dict[str, object]:
    pytest_result = run_pytest()
    pip_check_result = run_pip_check()

    return {
        "pytest_exit_code": pytest_result.returncode,
        "pip_check_exit_code": pip_check_result.returncode,
        "verified": (
            pytest_result.returncode == 0
            and pip_check_result.returncode == 0
        ),
        "pytest_stdout": pytest_result.stdout.strip(),
        "pytest_stderr": pytest_result.stderr.strip(),
        "pip_check_stdout": pip_check_result.stdout.strip(),
        "pip_check_stderr": pip_check_result.stderr.strip(),
    }


def commit_kept_requirement(
    package_name: str,
    candidate_version: str,
) -> str:
    relative_path = str(
        REQUIREMENTS_PATH.relative_to(REPO_ROOT)
    )

    run_command(
        [
            "git",
            "add",
            "--",
            relative_path,
        ],
        {0},
    )
    run_command(
        [
            "git",
            "commit",
            "-m",
            f"feat: upgrade {package_name} to {candidate_version}",
        ],
        {0},
    )

    return git_output(["rev-parse", "--short", "HEAD"])


def return_to_controller(
    controller_branch: str,
) -> None:
    run_command(
        [
            "git",
            "switch",
            controller_branch,
        ],
        {0},
    )


def delete_upgrade_branch(
    upgrade_branch: str,
) -> None:
    run_command(
        [
            "git",
            "branch",
            "-d",
            upgrade_branch,
        ],
        {0},
    )


def restore_controller_environment() -> None:
    restore_baseline_environment()

    pytest_result = run_pytest()
    pip_check_result = run_pip_check()

    if pytest_result.returncode != 0:
        raise RuntimeError(
            "Controller baseline pytest failed after restoration"
        )

    if pip_check_result.returncode != 0:
        raise RuntimeError(
            "Controller baseline pip check failed after restoration"
        )


def approval_result(
    package: dict[str, object],
) -> dict[str, object]:
    return {
        "package": package["name"],
        "previous_version": package["current_version"],
        "candidate_version": package["latest_version"],
        "change_type": package["change_type"],
        "has_vulnerability": package["has_vulnerability"],
        "vulnerabilities": package["vulnerabilities"],
        "decision": "human_approval_required",
        "reason": (
            "Major upgrades are not installed automatically, "
            "including security-priority upgrades."
        ),
        "branch": None,
        "install_attempted": False,
    }


def skipped_result(
    package: dict[str, object],
) -> dict[str, object]:
    return {
        "package": package["name"],
        "previous_version": package["current_version"],
        "candidate_version": package["latest_version"],
        "change_type": package["change_type"],
        "decision": "skip",
        "reason": "The direct dependency is already current.",
        "branch": None,
        "install_attempted": False,
    }


def attempt_candidate(
    package_name: str,
    current_version: str,
    candidate_version: str,
    change_type: str,
    has_vulnerability: bool,
    vulnerabilities: list[dict[str, object]],
    upgrade_branch_override: str | None = None,
) -> dict[str, object]:
    if RUN_LIMITS is None:
        raise RuntimeError("Run limits must be initialized")

    RUN_LIMITS.begin_attempt()
    controller_branch = require_safe_branch()
    require_clean_worktree()
    initial_source_hash = source_hash()
    upgrade_branch = upgrade_branch_override or build_upgrade_branch(
        package_name,
        candidate_version,
    )
    branch_created = False
    returned_to_controller = False

    try:
        run_command(
            [
                "git",
                "switch",
                "-c",
                upgrade_branch,
            ],
            {0},
        )
        branch_created = True

        replace_requirement_pin(
            package_name,
            current_version,
            candidate_version,
        )
        install_candidate(
            package_name,
            candidate_version,
        )

        pytest_result = run_pytest()
        pip_check_result = run_pip_check()
        should_keep = (
            pytest_result.returncode == 0
            and pip_check_result.returncode == 0
        )

        result = {
            "package": package_name,
            "previous_version": current_version,
            "candidate_version": candidate_version,
            "change_type": change_type,
            "has_vulnerability": has_vulnerability,
            "vulnerabilities": vulnerabilities,
            "branch": upgrade_branch,
            "pytest_exit_code": pytest_result.returncode,
            "pytest_stdout": pytest_result.stdout.strip(),
            "pytest_stderr": pytest_result.stderr.strip(),
            "pip_check_exit_code": pip_check_result.returncode,
            "pip_check_stdout": pip_check_result.stdout.strip(),
            "pip_check_stderr": pip_check_result.stderr.strip(),
        }

        if should_keep:
            commit_hash = commit_kept_requirement(
                package_name,
                candidate_version,
            )
            result.update(
                {
                    "decision": "keep",
                    "reason": (
                        "Pytest passed and pip check reported "
                        "no dependency conflicts."
                    ),
                    "commit": commit_hash,
                    "rollback": None,
                }
            )

            return_to_controller(controller_branch)
            returned_to_controller = True
            restore_controller_environment()
        else:
            reasons = []

            if pytest_result.returncode != 0:
                reasons.append(
                    f"pytest exited with "
                    f"{pytest_result.returncode}: "
                    f"{failure_detail(pytest_result)}"
                )

            if pip_check_result.returncode != 0:
                reasons.append(
                    f"pip check exited with "
                    f"{pip_check_result.returncode}: "
                    f"{failure_detail(pip_check_result)}"
                )

            restore_requirement_file()
            restore_baseline_environment()
            rollback = verify_restored_baseline()

            result.update(
                {
                    "decision": "rollback",
                    "reason": "; ".join(reasons),
                    "commit": None,
                    "rollback": rollback,
                }
            )

            return_to_controller(controller_branch)
            returned_to_controller = True
            delete_upgrade_branch(upgrade_branch)

        final_source_hash = source_hash()
        result["source_hash_before"] = initial_source_hash
        result["source_hash_after"] = final_source_hash
        result["source_unchanged"] = (
            initial_source_hash == final_source_hash
        )

        if not result["source_unchanged"]:
            raise RuntimeError(
                "Agent source changed during the package attempt"
            )

        print(json.dumps(result, indent=2))
        return result
    except Exception:
        if branch_created and not returned_to_controller:
            restore_requirement_file()
            restore_baseline_environment()
            return_to_controller(controller_branch)

            if upgrade_branch in git_output(
                ["branch", "--format=%(refname:short)"]
            ).splitlines():
                delete_upgrade_branch(upgrade_branch)

        raise


def run_normal_candidates(
    observations: list[dict[str, object]],
) -> list[dict[str, object]]:
    results = []

    for package in observations:
        change_type = str(package["change_type"])

        if change_type == "major":
            result = approval_result(package)
        elif change_type == "none":
            result = skipped_result(package)
        else:
            result = attempt_candidate(
                package_name=str(package["name"]),
                current_version=str(
                    package["current_version"]
                ),
                candidate_version=str(
                    package["latest_version"]
                ),
                change_type=change_type,
                has_vulnerability=bool(
                    package["has_vulnerability"]
                ),
                vulnerabilities=list(
                    package["vulnerabilities"]
                ),
            )

        if change_type in {"major", "none"}:
            print(json.dumps(result, indent=2))

        results.append(result)

    return results


def remote_action_result(
    action: str,
    approved: bool,
) -> dict[str, object]:
    if action == "merge":
        return {
            "action": action,
            "decision": "blocked",
            "reason": "SafeBump never merges.",
            "executed": False,
        }

    if not approved:
        return {
            "action": action,
            "decision": "awaiting_human_approval",
            "reason": (
                f"Explicit approval for {action} was not supplied."
            ),
            "executed": False,
        }

    return {
        "action": action,
        "decision": "approved_but_not_executed",
        "reason": (
            "The MVP records approval but does not implement remote "
            "mutation. Run the reviewed Git or GitHub command manually."
        ),
        "executed": False,
    }


def render_report(
    started_at: datetime,
    finished_at: datetime,
    controller_branch: str | None,
    results: list[dict[str, object]],
    status: str,
    error: str | None,
    remote_action: dict[str, object] | None,
) -> str:
    elapsed = (finished_at - started_at).total_seconds()
    tests_verified = any(
        result.get("pytest_exit_code") == 0
        for result in results
    )
    lines = [
        "# SafeBump Run Report",
        "",
        f"- Started: `{started_at.isoformat()}`",
        f"- Finished: `{finished_at.isoformat()}`",
        f"- Duration: `{elapsed:.2f} seconds`",
        f"- Controller branch: `{controller_branch or 'unavailable'}`",
        f"- Run status: `{status}`",
        f"- Package attempts: `{RUN_LIMITS.attempts if RUN_LIMITS else 0}/{RUN_LIMITS.max_attempts if RUN_LIMITS else MAX_ATTEMPTS}`",
        "",
        "## Package Decisions",
        "",
    ]

    if not results:
        lines.append("No package decision completed.")

    for result in results:
        lines.extend(
            [
                f"### {result.get('package', 'Unknown package')}",
                "",
                f"- Attempted: `{result.get('previous_version', 'unknown')} -> {result.get('candidate_version', 'unknown')}`",
                f"- Change type: `{result.get('change_type', 'unknown')}`",
                f"- Decision: `{result.get('decision', 'unknown')}`",
                f"- Reason: {result.get('reason', 'No reason recorded.')}",
                f"- Pytest exit code: `{result.get('pytest_exit_code', 'not run')}`",
                f"- pip check exit code: `{result.get('pip_check_exit_code', 'not run')}`",
                f"- Branch: `{result.get('branch') or 'none'}`",
                "",
            ]
        )

        if result.get("pytest_stdout") or result.get("pytest_stderr"):
            lines.extend(
                [
                    "#### Pytest evidence",
                    "",
                    "```text",
                    str(
                        result.get("pytest_stdout")
                        or result.get("pytest_stderr")
                    ),
                    "```",
                    "",
                ]
            )

        if result.get("pip_check_stdout") or result.get("pip_check_stderr"):
            lines.extend(
                [
                    "#### pip check evidence",
                    "",
                    "```text",
                    str(
                        result.get("pip_check_stdout")
                        or result.get("pip_check_stderr")
                    ),
                    "```",
                    "",
                ]
            )

    lines.extend(["## Approval Gate", ""])

    if remote_action is None:
        lines.append("No remote action was requested or executed.")
    else:
        lines.extend(
            [
                f"- Requested action: `{remote_action['action']}`",
                f"- Decision: `{remote_action['decision']}`",
                f"- Executed: `{str(remote_action['executed']).lower()}`",
                f"- Reason: {remote_action['reason']}",
            ]
        )

    lines.extend(
        [
            "",
            "## Honesty and Coverage Boundary",
            "",
            "The defined checks provide bounded evidence, not proof of complete safety.",
            "",
        ]
    )

    if tests_verified:
        lines.extend(
            [
                "Verified by the target test suite:",
                "",
                *[f"- `{test}`" for test in VERIFIED_TESTS],
            ]
        )
    else:
        lines.append("The target test suite was not completed successfully in this run.")

    lines.extend(
        [
            "",
            "Not verified by this run:",
            "",
            *[f"- {area}" for area in UNVERIFIED_AREAS],
        ]
    )

    if error:
        lines.extend(["", "## Run Error", "", f"`{error}`"])

    return "\n".join(lines) + "\n"


def write_report(content: str, output: Path | None) -> Path:
    REPORTS_DIR.mkdir(exist_ok=True)
    report_path = output or REPORTS_DIR / (
        datetime.now(timezone.utc).strftime("run-%Y%m%dT%H%M%SZ.md")
    )
    resolved = report_path.resolve()

    if not resolved.is_relative_to(REPO_ROOT):
        raise RuntimeError("Report path must stay inside the repository")

    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(content, encoding="utf-8")
    return resolved


def run_failure_demo() -> dict[str, object]:
    return attempt_candidate(
        package_name="httpx",
        current_version="0.28.1",
        candidate_version="1.0.dev3",
        change_type="major",
        has_vulnerability=False,
        vulnerabilities=[],
    )


def install_conflict_fixture() -> None:
    run_command(
        [
            str(TARGET_PYTHON),
            "-m",
            "pip",
            "install",
            "--no-deps",
            str(REPO_ROOT / "eval-fixtures" / "pip-conflict"),
        ],
        {0},
    )


def uninstall_conflict_fixture() -> None:
    run_command(
        [
            str(TARGET_PYTHON),
            "-m",
            "pip",
            "uninstall",
            "--yes",
            "safebump-conflict-fixture",
        ],
        {0},
    )


def run_pip_conflict_demo() -> dict[str, object]:
    install_conflict_fixture()

    try:
        baseline_check = run_pip_check()

        if baseline_check.returncode != 0:
            raise RuntimeError(
                "The conflict fixture did not start from a clean baseline: "
                f"{failure_detail(baseline_check)}"
            )

        return attempt_candidate(
            package_name="uvicorn",
            current_version="0.52.3",
            candidate_version="0.52.4",
            change_type="patch",
            has_vulnerability=False,
            vulnerabilities=[],
            upgrade_branch_override="safebump/eval-pip-conflict",
        )
    finally:
        uninstall_conflict_fixture()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--approve-major-demo",
        action="store_true",
    )
    parser.add_argument(
        "--eval-pip-conflict-demo",
        action="store_true",
    )
    parser.add_argument(
        "--request-remote-action",
        choices=["push", "pr", "merge"],
    )
    parser.add_argument(
        "--approve-remote-action",
        action="store_true",
    )
    parser.add_argument("--report", type=Path)
    parser.add_argument("--max-attempts", type=int, default=MAX_ATTEMPTS)
    parser.add_argument(
        "--run-timeout-seconds",
        type=int,
        default=RUN_TIMEOUT_SECONDS,
    )
    return parser.parse_args()


def main() -> None:
    global RUN_LIMITS
    args = parse_args()
    started_at = datetime.now(timezone.utc)
    RUN_LIMITS = RunLimits(
        max_attempts=args.max_attempts,
        run_timeout_seconds=args.run_timeout_seconds,
    )
    controller_branch = None
    results = []
    status = "failed"
    error = None
    remote_action = remote_action_result(
        args.request_remote_action,
        args.approve_remote_action,
    ) if args.request_remote_action else None

    try:
        if args.max_attempts < 1 or args.run_timeout_seconds < 1:
            raise RuntimeError("Attempt and run-time limits must be positive")

        controller_branch = require_safe_branch()
        require_clean_worktree()
        initial_source_hash = source_hash()
        observations = observe()

        print(
            json.dumps(
                {
                    "controller_branch": controller_branch,
                    "source_hash": initial_source_hash,
                    "observations": observations,
                },
                indent=2,
            )
        )

        if args.approve_major_demo and args.eval_pip_conflict_demo:
            raise RuntimeError("Select only one controlled eval demo")

        if args.approve_major_demo:
            results = [run_failure_demo()]
        elif args.eval_pip_conflict_demo:
            results = [run_pip_conflict_demo()]
        else:
            results = run_normal_candidates(observations)

        final_source_hash = source_hash()
        status = "completed"
        summary = {
            "controller_branch": require_safe_branch(),
            "results": results,
            "remote_action": remote_action,
            "source_hash_before": initial_source_hash,
            "source_hash_after": final_source_hash,
            "source_unchanged": initial_source_hash == final_source_hash,
        }
        print(json.dumps(summary, indent=2))
    except Exception as caught:
        error = f"{type(caught).__name__}: {caught}"
        raise
    finally:
        finished_at = datetime.now(timezone.utc)
        report = render_report(
            started_at=started_at,
            finished_at=finished_at,
            controller_branch=controller_branch,
            results=results,
            status=status,
            error=error,
            remote_action=remote_action,
        )
        report_path = write_report(report, args.report)
        print(f"Report: {report_path}")


if __name__ == "__main__":
    main()
