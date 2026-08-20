import time
import unittest
from datetime import datetime, timezone

import safebump


class RunLimitsTests(unittest.TestCase):
    def test_attempt_limit_stops_second_attempt(self) -> None:
        limits = safebump.RunLimits(max_attempts=1, run_timeout_seconds=60)
        limits.begin_attempt()

        with self.assertRaisesRegex(RuntimeError, "attempt limit"):
            limits.begin_attempt()

    def test_expired_run_limit_stops_work(self) -> None:
        limits = safebump.RunLimits(max_attempts=1, run_timeout_seconds=60)
        limits.deadline = time.monotonic() - 1

        with self.assertRaisesRegex(TimeoutError, "time limit"):
            limits.remaining_seconds()


class ApprovalGateTests(unittest.TestCase):
    def test_unapproved_push_is_not_executed(self) -> None:
        result = safebump.remote_action_result("push", False)

        self.assertEqual(result["decision"], "awaiting_human_approval")
        self.assertFalse(result["executed"])

    def test_merge_is_never_executed(self) -> None:
        result = safebump.remote_action_result("merge", True)

        self.assertEqual(result["decision"], "blocked")
        self.assertFalse(result["executed"])


class HonestyReportTests(unittest.TestCase):
    def test_failed_run_does_not_claim_tests_ran(self) -> None:
        now = datetime.now(timezone.utc)
        report = safebump.render_report(
            started_at=now,
            finished_at=now,
            controller_branch=None,
            results=[],
            status="failed",
            error="guard stopped the run",
            remote_action=None,
        )

        self.assertIn("test suite was not completed", report)
        self.assertNotIn("`test_seed_runs_once`", report)

    def test_successful_pytest_lists_bounded_coverage(self) -> None:
        now = datetime.now(timezone.utc)
        report = safebump.render_report(
            started_at=now,
            finished_at=now,
            controller_branch="feat/test",
            results=[{"pytest_exit_code": 0}],
            status="completed",
            error=None,
            remote_action=None,
        )

        self.assertIn("`test_seed_runs_once`", report)
        self.assertIn("production traffic", report)


if __name__ == "__main__":
    unittest.main()
