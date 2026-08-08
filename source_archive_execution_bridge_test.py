from __future__ import annotations

import subprocess
import unittest
from types import SimpleNamespace

from capture_archivebox import ARCHIVEBOX_MODE_DOCKER_COMPOSE, build_archivebox_command_plan
from source_archive_execution_bridge import (
    ArchiveExecutionStatus,
    ArchiveProviderKind,
    build_archivebox_default_execution_plans,
    build_archive_dns_diagnostic_result,
    build_archive_today_check_request,
    build_archive_today_submit_request,
    build_wayback_cdx_request,
    build_wayback_availability_request,
    build_wayback_submit_request,
    execute_archive_http_request,
    execute_archivebox_command,
    interpret_archive_today_check_response,
    interpret_wayback_availability_response,
    interpret_wayback_cdx_response,
)


class SourceArchiveExecutionBridgeTest(unittest.TestCase):
    def test_wayback_request_builder_and_fake_client_execution(self) -> None:
        request = build_wayback_availability_request("https://example.invalid/story")
        self.assertIn("archive.org/wayback/available", request.url)

        def fake_client(req):
            self.assertEqual(req.provider, ArchiveProviderKind.WAYBACK)
            return {"status": 200, "body": '{"archived_snapshots":{}}', "archive_url": "https://web.archive.org/web/1/example"}

        result = execute_archive_http_request(request, http_client=fake_client)
        self.assertEqual(result.status, ArchiveExecutionStatus.SUCCESS)
        self.assertEqual(result.http_status, 200)
        self.assertTrue(result.external_call_performed_by_fake_client)

    def test_submit_requires_explicit_approval(self) -> None:
        request = build_wayback_submit_request("https://example.invalid/story")
        result = execute_archive_http_request(request, http_client=lambda req: {"status": 200})
        self.assertEqual(result.status, ArchiveExecutionStatus.APPROVAL_REQUIRED)

        approved = build_archive_today_submit_request(
            "https://example.invalid/story",
            explicit_submit_granted=True,
        )
        submitted = execute_archive_http_request(approved, http_client=lambda req: {"status": 200, "body": "started"})
        self.assertEqual(submitted.status, ArchiveExecutionStatus.SUBMISSION_STARTED)

    def test_archive_today_challenge_becomes_user_handoff(self) -> None:
        request = build_archive_today_check_request("https://example.invalid/story")
        result = execute_archive_http_request(
            request,
            http_client=lambda req: {"status": 200, "body": "captcha challenge"},
        )
        self.assertEqual(result.status, ArchiveExecutionStatus.CHALLENGE_USER_HANDOFF)
        self.assertTrue(result.challenge_required)

    def test_dns_diagnostic_is_metadata_only(self) -> None:
        result = build_archive_dns_diagnostic_result(
            provider=ArchiveProviderKind.ARCHIVE_TODAY,
            mirror="archive.ph",
            note="mirror list configured",
        )
        self.assertEqual(result.status, ArchiveExecutionStatus.DNS_DIAGNOSTIC)
        self.assertIn("metadata only", result.warnings[0])

    def test_archivebox_command_wrapper_uses_injected_runner(self) -> None:
        plan = build_archivebox_command_plan(
            mode=ARCHIVEBOX_MODE_DOCKER_COMPOSE,
            url="https://example.invalid/story",
        )
        blocked = execute_archivebox_command(plan, approval_granted=False)
        self.assertEqual(blocked.status, ArchiveExecutionStatus.APPROVAL_REQUIRED)

        calls: list[list[str]] = []

        def runner(command, **kwargs):
            calls.append(command)
            return SimpleNamespace(returncode=0, stdout="ok token", stderr="")

        result = execute_archivebox_command(plan, runner=runner, approval_granted=True)
        self.assertEqual(result.status, ArchiveExecutionStatus.SUCCESS)
        self.assertEqual(calls[0][0], "docker")

    def test_archivebox_dependency_and_timeout_are_classified(self) -> None:
        plan = build_archivebox_command_plan(
            mode=ARCHIVEBOX_MODE_DOCKER_COMPOSE,
            url="https://example.invalid/story",
        )
        missing = execute_archivebox_command(
            plan,
            runner=lambda *args, **kwargs: (_ for _ in ()).throw(FileNotFoundError()),
            approval_granted=True,
        )
        self.assertEqual(missing.status, ArchiveExecutionStatus.DEPENDENCY_NOT_FOUND)

        timeout = execute_archivebox_command(
            plan,
            runner=lambda *args, **kwargs: (_ for _ in ()).throw(subprocess.TimeoutExpired("archivebox", 1)),
            approval_granted=True,
            timeout_seconds=1,
        )
        self.assertEqual(timeout.status, ArchiveExecutionStatus.TIMEOUT)

    def test_wayback_and_archive_today_interpretations_cover_found_not_found_multiple_and_format_changes(self) -> None:
        availability = build_wayback_availability_request("https://example.invalid/story")
        found = execute_archive_http_request(
            availability,
            http_client=lambda req: {
                "status": 200,
                "body": '{"archived_snapshots":{"closest":{"available":true,"url":"https://web.archive.org/web/1/example"}}}',
            },
        )
        self.assertEqual(interpret_wayback_availability_response(found).status, ArchiveExecutionStatus.SUCCESS)
        not_found = execute_archive_http_request(
            availability,
            http_client=lambda req: {"status": 200, "body": '{"archived_snapshots":{}}'},
        )
        self.assertEqual(interpret_wayback_availability_response(not_found).status, ArchiveExecutionStatus.NOT_FOUND)
        changed = execute_archive_http_request(
            availability,
            http_client=lambda req: {"status": 200, "body": '<html>changed</html>'},
        )
        self.assertEqual(interpret_wayback_availability_response(changed).status, ArchiveExecutionStatus.FORMAT_CHANGED)

        cdx = execute_archive_http_request(
            build_wayback_cdx_request("https://example.invalid/story"),
            http_client=lambda req: {
                "status": 200,
                "body": '[["urlkey","timestamp","original"],["x","20260101000000","https://example.invalid/story"],["x","20260202000000","https://example.invalid/story"]]',
            },
        )
        self.assertEqual(interpret_wayback_cdx_response(cdx).status, ArchiveExecutionStatus.MULTIPLE_RESULTS)

        archive_today_missing = execute_archive_http_request(
            build_archive_today_check_request("https://example.invalid/story"),
            http_client=lambda req: {"status": 404, "body": "not found"},
        )
        self.assertEqual(interpret_archive_today_check_response(archive_today_missing).status, ArchiveExecutionStatus.NOT_FOUND)

    def test_archivebox_default_plans_cover_modes_profiles_and_cancel(self) -> None:
        plans = build_archivebox_default_execution_plans("https://example.invalid/story")
        self.assertEqual(len(plans), 12)
        profiles = {plan.profile for plan in plans}
        self.assertEqual(profiles, {"light", "balanced", "full"})
        cancelled = execute_archivebox_command(
            plans[0],
            runner=lambda *args, **kwargs: SimpleNamespace(returncode=0),
            approval_granted=True,
            cancel_requested=True,
        )
        self.assertEqual(cancelled.status, ArchiveExecutionStatus.CANCELLED)


if __name__ == "__main__":
    unittest.main()
