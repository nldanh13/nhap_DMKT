from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import json
import tempfile
import unittest

from batch_portal import preflight_review, run_review_batch, select_services
from review_submission import draft_digest, load_review_draft, validate_review_item

ROOT = Path(__file__).resolve().parents[1]
SERVICES = json.loads((ROOT / "data/services.json").read_text(encoding="utf-8"))
PROCEDURES = json.loads((ROOT / "data/procedures.json").read_text(encoding="utf-8"))["procedures"]
CASTS = select_services(SERVICES, "casts")


class ReviewSubmissionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.reports = Path(self.temp.name) / "reports"

    def read_report(self):
        found = list(self.reports.glob("qtkt_batch_*.json"))
        self.assertEqual(len(found), 1)
        return json.loads(found[0].read_text(encoding="utf-8"))

    def test_eight_drafts_are_unapproved_and_have_review_warnings(self):
        self.assertEqual(len(CASTS), 8)
        rows = preflight_review(CASTS)
        self.assertEqual(len(rows), 8)
        self.assertTrue(all(row["status"].startswith("READY") for row in rows))
        for item, row in zip(CASTS, rows):
            self.assertEqual(row["code"], item["form_decision"]["codes"][0])
            self.assertTrue(PROCEDURES[item["id"]]["requires_clinical_review"])
            self.assertFalse(PROCEDURES[item["id"]]["approved_for_auto_save"])
            self.assertEqual(len(row["digest"]), 64)
        ankle = next(row for row in rows if row["id"] == "bot_trat_co_chan")
        self.assertIn("steps", ankle["missing"])
        self.assertIn("steps", ankle["critical_missing"])

    def test_mutation_changes_digest_without_granting_approval(self):
        draft = load_review_draft("bot_trat_khuyu")
        mutated = deepcopy(draft)
        mutated["steps"] += "\nBước không xác minh"
        self.assertNotEqual(draft_digest(draft), draft_digest(mutated))

    def test_wrong_status_blocks_unapproved_review_submission(self):
        item = CASTS[0]
        draft = load_review_draft(item["id"])
        entry = deepcopy(PROCEDURES[item["id"]])
        entry["requires_clinical_review"] = False
        with self.assertRaisesRegex(ValueError, "không được đánh dấu"):
            validate_review_item(item, entry, draft)
        entry["requires_clinical_review"] = True
        entry["approved_for_auto_save"] = True
        with self.assertRaisesRegex(ValueError, "tự lưu"):
            validate_review_item(item, entry, draft)

    def test_review_dry_run_does_not_open_chrome(self):
        result = run_review_batch(
            SERVICES, save=False, report_dir=self.reports,
            ask=lambda prompt: self.fail("Check-only must not ask confirmation"),
            invoke=lambda *a, **kw: self.fail("Check-only must not invoke Selenium"),
        )
        self.assertEqual(result, 0)
        report = self.read_report()
        self.assertEqual(report["scope"], "casts_for_review")
        self.assertEqual(report["result"], "REVIEW_CHECK_ONLY")
        self.assertFalse(report["consent_to_save"])

    def test_declining_confirmation_does_not_write(self):
        result = run_review_batch(
            SERVICES, save=True, report_dir=self.reports,
            ask=lambda prompt: "LƯU TẤT CẢ 8",
            invoke=lambda *a, **kw: self.fail("Wrong phrase must not invoke browser"),
        )
        self.assertEqual(result, 1)
        self.assertEqual(self.read_report()["result"], "REVIEW_CANCELLED")

    def test_one_confirmation_submits_eight_unapproved_drafts(self):
        prompts, invoked = [], []
        def ask(prompt):
            prompts.append(prompt)
            return "LƯU 8 BẢN NHÁP CHỜ DUYỆT"
        def invoke(argv, **kwargs):
            invoked.append((argv, kwargs))
            return SimpleNamespace(returncode=0)
        status = run_review_batch(
            SERVICES, save=True, report_dir=self.reports,
            ask=ask, invoke=invoke,
        )
        self.assertEqual(status, 0)
        self.assertEqual(len(prompts), 1)
        self.assertEqual(len(invoked), 8)
        for (argv, kw), item in zip(invoked, CASTS):
            self.assertEqual(argv[argv.index("--id") + 1], item["id"])
            self.assertIn("--submit-for-review", argv)
            self.assertIn("--save", argv)
            self.assertNotIn("--approved-package", argv)
            self.assertEqual(kw["env"]["DMKT_BATCH_REVIEW_ID"], item["id"])
            self.assertEqual(len(kw["env"]["DMKT_BATCH_REVIEW_SHA256"]), 64)
        result = self.read_report()
        self.assertEqual(result["result"], "REVIEW_ALL_SAVED_UNAPPROVED")
        self.assertTrue(all(row["status"] == "SAVED_TO_PORTAL_UNAPPROVED"
                            for row in result["items"]))
        self.assertNotIn("content", str(result))
        self.assertNotIn("decision_number", str(result))

    def test_error_stops_following_drafts(self):
        attempts=[]
        def invoke(*args,**kwargs):
            attempts.append(args)
            return SimpleNamespace(returncode=9 if len(attempts)==3 else 0)
        status=run_review_batch(
            SERVICES, save=True, report_dir=self.reports,
            ask=lambda _: "LƯU 8 BẢN NHÁP CHỜ DUYỆT", invoke=invoke,
        )
        self.assertEqual(status, 1)
        self.assertEqual(len(attempts), 3)
        items=self.read_report()["items"]
        self.assertEqual(items[2]["status"], "FAILED_OR_UNCONFIRMED")
        self.assertTrue(all(x["status"] == "NOT_ATTEMPTED" for x in items[3:]))

    def test_review_uses_eight_only(self):
        self.assertEqual(len(CASTS), 8)
        self.assertNotIn("duong_mau_noi_tru", {x["id"] for x in CASTS})


if __name__ == "__main__":
    unittest.main()
