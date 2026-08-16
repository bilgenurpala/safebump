import json
import subprocess
from pathlib import Path

from packaging.utils import canonicalize_name
from packaging.version import Version


REPO_ROOT = Path(__file__).resolve().parent
TARGET_DIR = REPO_ROOT / "target"
REQUIREMENTS_PATH = TARGET_DIR / "requirements.txt"
TARGET_PYTHON = REPO_ROOT / ".venv" / "bin" / "python"
PIP_AUDIT = REPO_ROOT / ".tools-venv" / "bin" / "pip-audit"


def run_command(args: list[str], accepted_exit_codes: set[int]) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        args,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )

    if result.returncode not in accepted_exit_codes:
        message = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(
            f"Command failed with exit code {result.returncode}: {' '.join(args)}\n{message}"
        )

    return result


def read_direct_dependencies() -> dict[str, dict[str, str]]:
    dependencies = {}

    for raw_line in REQUIREMENTS_PATH.read_text(encoding="utf-8").splitlines():
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
                    "fix_versions": vulnerability.get("fix_versions", []),
                }
            )

        findings[name] = vulnerabilities

    return findings


def classify_change(current_version: str, latest_version: str) -> str:
    current = Version(current_version)
    latest = Version(latest_version)

    if latest.major != current.major:
        return "major"

    if latest.minor != current.minor:
        return "minor"

    if latest.micro != current.micro:
        return "patch"

    return "none"


def priority_key(package: dict[str, object]) -> tuple[int, str]:
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


def print_observations(observations: list[dict[str, object]]) -> None:
    print(json.dumps(observations, indent=2))


def main() -> None:
    observations = observe()
    print_observations(observations)


if __name__ == "__main__":
    main()