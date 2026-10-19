"""Preflight for unapproved clinical drafts submitted for a separate review.

These checks never mark a procedure as approved. The SHA256 only protects a
batch against accidentally submitting different local data after preflight.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
REVIEW_FIELDS = (
    "overview", "indications", "contraindications", "precautions",
    "personnel", "drugs", "supplies", "equipment", "patient", "records",
    "duration_hours", "location", "preprocedure_checks", "steps",
    "during_procedure_events", "post_procedure_events", "late_complications",
    "references",
)
HIGH_RISK_MISSING = ("overview", "indications", "steps", "references")


def draft_digest(record: dict) -> str:
    """Digest clinical content, including the fields intentionally left blank."""
    raw = json.dumps(
        record, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def load_review_draft(procedure_id: str, *, data_dir: Path = DATA) -> dict:
    document = json.loads((data_dir / "clinical_drafts.json").read_text(encoding="utf-8"))
    draft = document["procedures"].get(procedure_id)
    if not isinstance(draft, dict):
        raise ValueError(f"Không có bản nháp chuyên môn cho {procedure_id}.")
    return draft


def validate_review_item(item: dict, procedure: dict, draft: dict) -> dict:
    """Validate identity and provide warnings; no hospital approval is implied."""
    pid = item["id"]
    if not pid.startswith("bot_") or not str(item.get("form_template", "")).startswith("Lâm sàng"):
        raise ValueError("Chế độ gửi duyệt chỉ cho 8 kỹ thuật nắn, bó bột mẫu lâm sàng.")
    if not procedure.get("requires_clinical_review", False):
        raise ValueError("Kỹ thuật không được đánh dấu là bản nháp cần duyệt.")
    if procedure.get("approved_for_auto_save", False):
        raise ValueError("Bản nháp lại được đánh dấu tự lưu đã duyệt; cần kiểm tra dữ liệu.")
    codes = item.get("form_decision", {}).get("codes", [])
    if item.get("form_decision", {}).get("annex") != "PL1" or len(codes) != 1:
        raise ValueError("Mã PL1 của dịch vụ không phải duy nhất.")
    if not isinstance(draft.get("overview"), str) or not draft["overview"].strip():
        raise ValueError("Thiếu nội dung Đại cương, không thể nhập bản nháp.")
    if not isinstance(draft.get("references"), str) or not draft["references"].strip():
        raise ValueError("Chưa có tài liệu tham khảo, không thể gửi duyệt.")
    if not all(isinstance(draft.get(key, ""), str) for key in REVIEW_FIELDS):
        raise ValueError("Dữ liệu bản nháp có trường không phải văn bản.")
    missing = [key for key in REVIEW_FIELDS if not draft.get(key, "").strip()]
    return {
        "id": pid,
        "code": codes[0],
        "digest": draft_digest(draft),
        "missing": missing,
        "critical_missing": [key for key in HIGH_RISK_MISSING if key in missing],
    }


def load_and_validate_review_item(item: dict, procedure: dict,
                                  *, data_dir: Path = DATA) -> tuple[dict, dict]:
    draft = load_review_draft(item["id"], data_dir=data_dir)
    return draft, validate_review_item(item, procedure, draft)
