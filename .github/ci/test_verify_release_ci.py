from copy import deepcopy
from unittest import TestCase

from verify_release_ci import REQUIRED_JOBS, checkout_shas, verify_run

BASE = "1" * 40
HEAD = "2" * 40
CHECKOUT = "3" * 40


def log(sha):
    return (
        "2026-11-28T02:00:00Z [command]/usr/bin/git log -1 --format=%H\n"
        f"2026-11-28T02:00:00Z {sha}\n"
    ).encode()


class VerifyReleaseCITests(TestCase):
    def setUp(self):
        self.run = dict(
            id=1, path=".github/workflows/ci.yml", event="pull_request", head_sha=HEAD,
            status="completed", conclusion="success", run_attempt=2,
            html_url="https://example.com/runs/1",
            pull_requests=[dict(number=4, head=dict(sha=HEAD), base=dict(sha=BASE))],
        )
        self.jobs = [
            dict(
                id=index, name=name, status="completed", conclusion="success",
                run_attempt=2, html_url=f"https://example.com/jobs/{index}",
                steps=[dict(name="Checkout without confidential fixtures", conclusion="success")],
            )
            for index, name in enumerate(sorted(REQUIRED_JOBS), start=1)
        ]

    def verify(self, jobs=None, read_log=lambda _: log(CHECKOUT), **overrides):
        options = dict(checkout=CHECKOUT, pr=4, head=HEAD, base=BASE)
        options.update(overrides)
        return verify_run(self.run, self.jobs if jobs is None else jobs, read_log, **options)

    def test_exact_proposed_merge(self):
        receipt = self.verify()
        self.assertTrue(receipt["gate_passed"])
        self.assertEqual(len(receipt["jobs"]), 7)
        self.assertTrue(all(len(job["log_sha256"]) == 64 for job in receipt["jobs"]))

    def test_push_receipt(self):
        self.run.update(event="push", head_sha=CHECKOUT)
        self.assertTrue(self.verify(pr=None, head=None, base=None)["gate_passed"])
        with self.assertRaisesRegex(ValueError, "Push run"):
            self.verify(pr=None, head=None, base=None, checkout=HEAD)

    def test_stale_pr_base_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "head and base"):
            self.verify(base=CHECKOUT)

    def test_incomplete_or_wrong_attempt_jobs_are_rejected(self):
        for field, value in (("conclusion", "skipped"), ("run_attempt", 1), ("steps", [])):
            with self.subTest(field=field):
                jobs = deepcopy(self.jobs)
                jobs[0][field] = value
                with self.assertRaisesRegex(ValueError, "Required jobs"):
                    self.verify(jobs=jobs)
        with self.assertRaisesRegex(ValueError, "Required jobs"):
            self.verify(jobs=self.jobs[:-1])

    def test_wrong_or_ambiguous_checkout_is_rejected(self):
        for payload in (log(HEAD), log(CHECKOUT) + log(HEAD), b""):
            with self.subTest(payload=payload), self.assertRaisesRegex(ValueError, "checkout"):
                self.verify(read_log=lambda _: payload)

    def test_printed_sha_without_checkout_command_is_not_evidence(self):
        self.assertEqual(checkout_shas(f"2026-11-28T02:00:00Z {CHECKOUT}\n".encode()), [])

    def test_merged_pr_without_current_api_association(self):
        self.run["pull_requests"] = []
        with self.assertRaisesRegex(ValueError, "expected parents"):
            self.verify(parents=[HEAD, BASE])
        with self.assertRaisesRegex(ValueError, "Missing PR merge ref"):
            self.verify(parents=[BASE, HEAD])
        fetch = (
            f"2026-11-28T02:00:00Z [command]/usr/bin/git -c protocol.version=2 "
            f"fetch --no-tags origin +{CHECKOUT}:refs/remotes/pull/4/merge\n"
        ).encode()
        evidence = fetch + log(CHECKOUT)
        receipt = self.verify(read_log=lambda _: evidence, parents=[BASE, HEAD])
        self.assertTrue(receipt["gate_passed"])
