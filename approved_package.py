"""Validate an explicitly approved hospital QTKT package before Selenium may save it.

The checksums detect local changes; they DO NOT authenticate a hospital signature
or prove that transcribed fields match the signed original. A human must verify both.
"""
from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
import re
import unicodedata

CLINICAL_FIELDS = (
    "overview", "indications", "contraindications", "precautions",
    "personnel", "support_personnel", "drugs", "supplies", "equipment",
    "patient", "records", "duration_hours", "location",
    "preprocedure_checks", "steps", "during_procedure_events",
    "post_procedure_events", "late_complications", "references",
)
OPTIONAL_FIELDS = {"support_personnel", "drugs"}
REQUIRED_FIELDS = set(CLINICAL_FIELDS) - OPTIONAL_FIELDS
APPROVAL_FIELDS = {
    "issuer", "decision_number", "decision_date", "approved_title",
    "approved_by", "attested_by", "signed_pdf", "signed_pdf_sha256",
}
PLACEHOLDER = re.compile(r"(?i)(?:__|\bTODO\b|CHỜ THẨM ĐỊNH|\[BỔ SUNG|\[ĐỀ XUẤT|NHẬP TỪ QUY TRÌNH|CHƯA CÓ NGUỒN)")


def _normalized_title(value: str) -> str:
    value = re.sub(r"\s*\[bột liền\]\s*", "", value, flags=re.IGNORECASE)
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


def _pdf_path(package_path: Path, value: str) -> Path:
    if not value.strip():
        raise ValueError("Thiếu đường dẫn PDF quyết định / quy trình đã phê duyệt.")
    path = Path(value)
    path = path if path.is_absolute() else package_path.parent / path
    path = path.resolve()
    if not path.is_file() or path.suffix.lower() != ".pdf":
        raise ValueError(f"Không tìm được file PDF đã phê duyệt: {path}")
    with path.open("rb") as f:
        if f.read(5) != b"%PDF-":
            raise ValueError("Tệp chứng cứ không phải PDF hợp lệ.")
    return path


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _sha256_content(data: dict) -> str:
    canonical = {key: value for key, value in data.items() if key != "content_sha256"}
    return hashlib.sha256(json.dumps(
        canonical, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")).hexdigest()


def _validate_structure(data: dict, procedure_id: str, catalog_code: str, expected_title: str) -> None:
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise ValueError("Gói dữ liệu phải có schema_version = 1.")
    if data.get("procedure_id") != procedure_id or data.get("catalog_code") != catalog_code:
        raise ValueError("Mã ID hoặc mã danh mục không khớp dịch vụ đang nhập.")
    approval = data.get("approval")
    fields = data.get("content")
    if not isinstance(approval, dict) or not isinstance(fields, dict):
        raise ValueError("Thiếu đối tượng approval hoặc content.")
    missing = APPROVAL_FIELDS - set(approval)
    if missing:
        raise ValueError("Thiếu trường thông tin quyết định: " + ", ".join(sorted(missing)))
    if approval["issuer"] != "BỆNH VIỆN":
        raise ValueError("Cơ quan ban hành phải là BỆNH VIỆN, không dùng số quyết định BYT thay thế.")
    if "QĐ-BYT" in str(approval.get("decision_number", "")).upper():
        raise ValueError("Số quyết định ban hành QTKT phải của bệnh viện, không dùng QĐ-BYT.")
    for k in ("decision_number", "approved_title", "approved_by", "attested_by", "signed_pdf"):
        if not isinstance(approval[k], str) or not approval[k].strip() or PLACEHOLDER.search(approval[k]):
            raise ValueError(f"Chưa có thông tin bệnh viện hợp lệ: approval.{k}")
    for key in ("serial_number", "writer", "writer_title", "reviewer",
                "reviewer_title", "approver_title"):
        value = approval.get(key)
        if value is not None and (
            not isinstance(value, str) or PLACEHOLDER.search(value)
        ):
            raise ValueError(f"Thông tin người viết/xem xét/duyệt hoặc STT không hợp lệ: approval.{key}")
    if _normalized_title(approval["approved_title"]) != _normalized_title(expected_title):
        raise ValueError("Tên quy trình được duyệt không khớp tên kỹ thuật trong danh mục.")
    try:
        issued = date.fromisoformat(approval["decision_date"])
    except (TypeError, ValueError) as exc:
        raise ValueError("Ngày quyết định phải có dạng YYYY-MM-DD.") from exc
    if issued > date.today():
        raise ValueError("Ngày quyết định ban hành không thể nằm trong tương lai.")
    unknown = set(fields) - set(CLINICAL_FIELDS)
    if unknown:
        raise ValueError("Trường nội dung không được biểu mẫu hỗ trợ: " + ", ".join(sorted(unknown)))
    missing_content = REQUIRED_FIELDS - set(fields)
    if missing_content:
        raise ValueError("Thiếu mục QTKT bắt buộc: " + ", ".join(sorted(missing_content)))
    for key in CLINICAL_FIELDS:
        value = fields.get(key, "")
        if not isinstance(value, str):
            raise ValueError(f"Trường content.{key} phải là văn bản.")
        if key in REQUIRED_FIELDS and not value.strip():
            raise ValueError(f"Trường content.{key} còn trống: yêu cầu đúng bản bệnh viện đã duyệt.")
        if PLACEHOLDER.search(value):
            raise ValueError(f"Trường content.{key} chứa ghi chú chưa hoàn thiện.")
    if not isinstance(approval["signed_pdf_sha256"], str) or not re.fullmatch(
        r"[a-f0-9]{64}", approval["signed_pdf_sha256"]
    ):
        raise ValueError("Thiếu mã SHA256 hợp lệ cho PDF bệnh viện.")
    if not isinstance(data.get("content_sha256"), str) or not re.fullmatch(
        r"[a-f0-9]{64}", data["content_sha256"]
    ):
        raise ValueError("Gói chưa được khóa checksum nội dung.")


def load_approved_package(path: Path, procedure_id: str, catalog_code: str, expected_title: str) -> dict:
    """Read and verify one *locally attested* approved package; no connection to DMKT."""
    path = Path(path).resolve()
    if not path.is_file():
        raise ValueError(f"Không tồn tại gói dữ liệu đã duyệt: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    _validate_structure(data, procedure_id, catalog_code, expected_title)
    pdf = _pdf_path(path, data["approval"]["signed_pdf"])
    if _sha256_file(pdf) != data["approval"]["signed_pdf_sha256"]:
        raise ValueError("File PDF đã bị thay đổi so với SHA256 trong gói.")
    if _sha256_content(data) != data["content_sha256"]:
        raise ValueError("Nội dung JSON đã bị thay đổi sau khi người phụ trách chốt.")
    return data


def seal_local_package(path: Path) -> str:
    """Compute tamper-detection checksums only; never marks a draft as approved."""
    path = Path(path).resolve()
    data = json.loads(path.read_text(encoding="utf-8"))
    approval = data.get("approval")
    if not isinstance(approval, dict):
        raise ValueError("Không tìm thấy thông tin approval.")
    pdf = _pdf_path(path, approval.get("signed_pdf", ""))
    actual = _sha256_file(pdf)
    prior = approval.get("signed_pdf_sha256")
    if prior and prior != actual:
        raise ValueError("PDF khác SHA256 cũ. Không tự thay dấu vân tay chứng cứ.")
    approval["signed_pdf_sha256"] = actual
    data["content_sha256"] = _sha256_content(data)
    data_path_code = data.get("catalog_code", "")
    data_title = approval.get("approved_title", "")
    _validate_structure(data, data.get("procedure_id", ""), data_path_code, data_title)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return data["content_sha256"]


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description="Kiểm tra checksum gói QTKT bệnh viện đã ban hành (không tự phê duyệt).")
    cli.add_argument("path", type=Path)
    cli.add_argument("--seal-checksums", action="store_true",
                     help="Tính checksum sau khi đã đối chiếu thủ công với PDF ký duyệt")
    args = cli.parse_args()
    if not args.seal_checksums:
        cli.error("Chỉ hỗ trợ --seal-checksums, không tự chứng thực phê duyệt.")
    digest = seal_local_package(args.path)
    print("Đã tính checksum chống thay đổi, KHÔNG xác nhận tính hợp lệ của chữ ký:", digest)
