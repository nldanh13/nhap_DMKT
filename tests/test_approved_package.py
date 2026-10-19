from __future__ import annotations

from datetime import date
import json
from pathlib import Path
import tempfile
import unittest

from approved_package import (
    CLINICAL_FIELDS, OPTIONAL_FIELDS, REQUIRED_FIELDS,
    load_approved_package, seal_local_package,
)


class ApprovedPackageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.pdf = self.root / "quyet-dinh-da-ky.pdf"
        self.pdf.write_bytes(b"%PDF-1.4\nTest fixture only\n%%EOF\n")
        self.path = self.root / "approved.json"
        self.content = {key: "Noi dung da duoc nguoi phu trach doi chieu."
                        for key in REQUIRED_FIELDS}
        for key in OPTIONAL_FIELDS:
            self.content[key] = ""
        self.payload = {
            "schema_version": 1,
            "procedure_id": "bot_trat_khuyu",
            "catalog_code": "10.1000",
            "approval": {
                "issuer": "BỆNH VIỆN",
                "decision_number": "123/QĐ-BV",
                "decision_date": "2026-01-02",
                "approved_title": "Nắn, bó bột trật khớp khuỷu",
                "approved_by": "Người có thẩm quyền",
                "attested_by": "Người đã đối chiếu PDF",
                "signed_pdf": "quyet-dinh-da-ky.pdf",
                "signed_pdf_sha256": "",
            },
            "content": self.content,
            "content_sha256": "",
        }
        self.write()

    def write(self):
        self.path.write_text(json.dumps(self.payload, ensure_ascii=False), encoding="utf-8")

    def seal(self):
        seal_local_package(self.path)
        self.payload = json.loads(self.path.read_text(encoding="utf-8"))

    def load(self, *, pid="bot_trat_khuyu", code="10.1000",
             title="Nắn, bó bột trật khớp khuỷu"):
        return load_approved_package(self.path, pid, code, title)

    def test_sealed_package_passes(self):
        self.seal()
        result = self.load()
        self.assertEqual(result["approval"]["decision_number"], "123/QĐ-BV")
        self.assertEqual(set(CLINICAL_FIELDS), set(result["content"]))
        self.assertEqual(len(result["content_sha256"]), 64)

    def test_checksums_do_not_count_as_signature_proof(self):
        self.seal()
        self.pdf.write_bytes(b"%PDF-1.4\nAltered document\n")
        with self.assertRaisesRegex(ValueError, "PDF đã bị thay đổi"):
            self.load()

    def test_json_tampering_fails_closed(self):
        self.seal()
        self.payload["content"]["steps"] += " CHANGED"
        self.write()
        with self.assertRaisesRegex(ValueError, "JSON đã bị thay đổi"):
            self.load()

    def test_wrong_service_and_code_are_rejected(self):
        self.seal()
        with self.assertRaisesRegex(ValueError, "Mã ID hoặc mã danh mục"):
            self.load(pid="bot_xuong_got")
        with self.assertRaisesRegex(ValueError, "Mã ID hoặc mã danh mục"):
            self.load(code="10.1999")

    def test_wrong_approved_title_rejected(self):
        self.seal()
        with self.assertRaisesRegex(ValueError, "Tên quy trình"):
            self.load(title="Nắn, bó bột trật khớp cổ chân")

    def test_missing_critical_field_rejected(self):
        self.payload["content"].pop("steps")
        self.write()
        with self.assertRaisesRegex(ValueError, "Thiếu mục QTKT bắt buộc"):
            self.seal()

    def test_blank_critical_field_rejected(self):
        self.payload["content"]["steps"] = ""
        self.write()
        with self.assertRaisesRegex(ValueError, "còn trống"):
            self.seal()

    def test_placeholder_field_rejected(self):
        self.payload["content"]["steps"] = "[BỔ SUNG] nội dung"
        self.write()
        with self.assertRaisesRegex(ValueError, "ghi chú chưa hoàn thiện"):
            self.seal()

    def test_wrong_issuer_rejected(self):
        self.payload["approval"]["issuer"] = "BỘ Y TẾ"
        self.write()
        with self.assertRaisesRegex(ValueError, "BỆNH VIỆN"):
            self.seal()

    def test_moh_catalog_decision_is_not_hospital_approval(self):
        self.payload["approval"]["decision_number"] = "3116/QĐ-BYT"
        self.write()
        with self.assertRaisesRegex(ValueError, "phải của bệnh viện"):
            self.seal()

    def test_future_approval_date_rejected(self):
        self.payload["approval"]["decision_date"] = str(date.today().year + 1) + "-12-31"
        self.write()
        with self.assertRaisesRegex(ValueError, "tương lai"):
            self.seal()

    def test_requires_local_pdf(self):
        self.payload["approval"]["signed_pdf"] = "khong-co.pdf"
        self.write()
        with self.assertRaisesRegex(ValueError, "Không tìm được file PDF"):
            self.seal()

    def test_optional_drugs_and_support_can_be_blank(self):
        self.seal()
        result = self.load()
        self.assertEqual(result["content"]["drugs"], "")
        self.assertEqual(result["content"]["support_personnel"], "")


if __name__ == "__main__":
    unittest.main()
