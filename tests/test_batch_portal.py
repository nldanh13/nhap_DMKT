from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import json
import tempfile
import unittest

from approved_package import REQUIRED_FIELDS, seal_local_package
from batch_portal import preflight, run_batch, select_services

ROOT = Path(__file__).resolve().parents[1]
SERVICES = json.loads((ROOT / "data" / "services.json").read_text(encoding="utf-8"))


class ApprovedBatchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.approved = self.root / "local_approved"
        self.approved.mkdir()
        self.out = self.root / "reports"
        self.pdf = self.approved / "qtkt_signed.pdf"
        self.pdf.write_bytes(b"%PDF-1.4\nMock signed document for offline testing\n%%EOF\n")

    def write_approved(self, records):
        for item in records:
            form = item["form_decision"]
            codes = form["codes"]
            if len(codes) != 1:
                continue
            code = codes[0]
            body = {field: "Nội dung kiểm thử, không dùng để điều trị"
                    for field in REQUIRED_FIELDS}
            body["drugs"] = ""
            body["support_personnel"] = ""
            data = {
                "schema_version": 1, "procedure_id": item["id"],
                "catalog_code": code,
                "approval": {
                    "issuer": "BỆNH VIỆN", "decision_number": "123/QĐ-BV",
                    "decision_date": "2026-01-01",
                    "approved_title": item["technical_catalog"]["annex1"]["name"],
                    "approved_by": "Người ký", "attested_by": "Người đối chiếu",
                    "signed_pdf": self.pdf.name, "signed_pdf_sha256": "",
                },
                "content": body, "content_sha256": "",
            }
            path = self.approved / f"{item['id']}.approved-qtkt.json"
            path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            seal_local_package(path)

    def report(self):
        files = list(self.out.glob("qtkt_batch_*.json"))
        self.assertEqual(len(files), 1)
        return json.loads(files[0].read_text(encoding="utf-8"))

    def test_scope_counts_and_lab_exclusion(self):
        self.assertEqual(len(SERVICES), 13)
        self.assertEqual(len(select_services(SERVICES, "casts")), 8)
        self.assertEqual(len(select_services(SERVICES, "clinical")), 11)
        self.assertEqual(len(select_services(SERVICES, "all")), 13)
        self.assertTrue(all(r["id"].startswith("bot_") for r in select_services(SERVICES, "casts")))

    def test_unsupported_laboratory_blocks_all_scope(self):
        records=select_services(SERVICES, "all")
        self.write_approved(records)
        tested=preflight(records, self.approved)
        labs=[x for x in tested if "duong_mau" in x["id"]]
        self.assertEqual(len(labs), 2)
        self.assertTrue(all(x["status"] == "BLOCKED" for x in labs))

    def test_missing_any_approved_package_does_not_launch_browser(self):
        casts=select_services(SERVICES, "casts")
        self.write_approved(casts[:-1])
        executed=[]
        result=run_batch(SERVICES, self.approved, "casts", save=True,
                         ask=lambda _: "LƯU TẤT CẢ 8",
                         invoke=lambda *a,**kw: executed.append((a,kw)),
                         report_dir=self.out)
        self.assertEqual(result, 2)
        self.assertFalse(executed)
        self.assertEqual(self.report()["result"], "PREFLIGHT_BLOCKED")

    def test_check_only_preflights_without_browser_or_consent(self):
        self.write_approved(select_services(SERVICES, "casts"))
        result=run_batch(SERVICES, self.approved, "casts", save=False,
                         ask=lambda _: self.fail("No confirmation in dry run"),
                         invoke=lambda *a,**kw: self.fail("No browser in dry run"),
                         report_dir=self.out)
        self.assertEqual(result, 0)
        self.assertEqual(self.report()["result"], "CHECK_ONLY")

    def test_cancellation_prevents_every_save(self):
        self.write_approved(select_services(SERVICES, "casts"))
        result=run_batch(SERVICES, self.approved, "casts", save=True,
                         ask=lambda _: "LƯU",
                         invoke=lambda *a,**kw: self.fail("Browser must not run"),
                         report_dir=self.out)
        self.assertEqual(result, 1)
        self.assertEqual(self.report()["result"], "CANCELLED")

    def test_one_confirmation_runs_all_approved_casts(self):
        casts=select_services(SERVICES, "casts")
        self.write_approved(casts)
        invocations=[]
        prompts=[]
        def ask(prompt):
            prompts.append(prompt)
            return "LƯU TẤT CẢ 8"
        def invoke(args, **kwargs):
            invocations.append((args, kwargs))
            return SimpleNamespace(returncode=0)
        result=run_batch(SERVICES, self.approved, "casts", save=True, ask=ask,
                         invoke=invoke, report_dir=self.out)
        self.assertEqual(result, 0)
        self.assertEqual(len(prompts), 1)
        self.assertEqual(len(invocations), 8)
        for (argv, opts), item in zip(invocations, casts):
            self.assertEqual(argv[argv.index("--id")+1], item["id"])
            self.assertIn("--save", argv)
            self.assertTrue(Path(argv[argv.index("--approved-package")+1]).is_file())
            self.assertEqual(opts["env"]["DMKT_BATCH_SAVE_CONFIRMED_ID"], item["id"])
            self.assertEqual(len(opts["env"]["DMKT_BATCH_SAVE_CONFIRMED_SHA256"]), 64)
        result_doc=self.report()
        self.assertEqual(result_doc["result"], "ALL_SAVED_CONFIRMED")
        self.assertEqual(len(result_doc["items"]), 8)
        self.assertTrue(all(r["status"] == "SAVED_CONFIRMED_BY_PORTAL" for r in result_doc["items"]))
        self.assertNotIn("sha256", str(result_doc))
        self.assertNotIn("content", str(result_doc))

    def test_error_stops_all_following_records(self):
        self.write_approved(select_services(SERVICES, "casts"))
        calls=[]
        def invoke(*a, **kw):
            calls.append(a)
            return SimpleNamespace(returncode=5 if len(calls)==3 else 0)
        result=run_batch(SERVICES, self.approved, "casts", save=True,
                         ask=lambda _: "LƯU TẤT CẢ 8", invoke=invoke,
                         report_dir=self.out)
        self.assertEqual(result, 1)
        self.assertEqual(len(calls), 3)
        report=self.report()
        self.assertEqual(report["result"], "STOPPED_ON_ERROR")
        self.assertEqual(report["items"][2]["status"], "FAILED_OR_UNCONFIRMED")
        self.assertTrue(all(r["status"] == "NOT_ATTEMPTED" for r in report["items"][3:]))

    def test_cannot_select_duplicate_registry_ids(self):
        one=select_services(SERVICES,"casts")[0]
        with self.assertRaisesRegex(ValueError, "trùng"):
            select_services([one,one], "casts")


if __name__ == "__main__":
    unittest.main()
