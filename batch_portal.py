"""Batch preflight and run for hospital-approved clinical QTKT records.

All selected records must pass preflight before *any* browser is launched.
No hospital signatures, patient data or clinical prose go into the batch report.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Callable

from approved_package import load_approved_package
from review_submission import DATA as REVIEW_DATA, load_and_validate_review_item

ROOT = Path(__file__).resolve().parent
SERVICES_PATH = ROOT / "data" / "services.json"
DEFAULT_APPROVED_DIR = ROOT / "local_approved"
REPORT_DIR = ROOT / "output"


def select_services(services: list[dict], scope: str) -> list[dict]:
    """Keep the registry order and never silently substitute a procedure ID."""
    if scope == "casts":
        selected = [item for item in services if item["id"].startswith("bot_")]
    elif scope == "clinical":
        selected = [item for item in services if str(item.get("form_template", "")).startswith("Lâm sàng")]
    elif scope == "all":
        selected = list(services)
    else:
        raise ValueError("Phạm vi không được hỗ trợ.")
    if len({item["id"] for item in selected}) != len(selected):
        raise ValueError("Danh sách dịch vụ có ID bị trùng; từ chối chạy hàng loạt.")
    if not selected:
        raise ValueError("Không có dịch vụ trong nhóm đã chọn.")
    return selected


def package_file(approved_dir: Path, procedure_id: str) -> Path:
    if not procedure_id or not all(c.isascii() and (c.isalnum() or c == "_") for c in procedure_id):
        raise ValueError("ID dịch vụ không hợp lệ.")
    return approved_dir / (procedure_id + ".approved-qtkt.json")


def initialize_templates(selected: list[dict], approved_dir: Path) -> tuple[int, int]:
    """Create invalid-by-design starter JSON files; NEVER use a clinical draft as a source."""
    from approved_package import CLINICAL_FIELDS, OPTIONAL_FIELDS

    approved_dir.mkdir(parents=True, exist_ok=True)
    created = skipped = 0
    for item in selected:
        if not str(item.get("form_template", "")).startswith("Lâm sàng"):
            print(f"  Không tạo cho biểu mẫu xét nghiệm: {item['id']}")
            skipped += 1
            continue
        codes = item.get("form_decision", {}).get("codes", [])
        if len(codes) != 1:
            print(f"  Không có một mã PL1 duy nhất: {item['id']}")
            skipped += 1
            continue
        path = package_file(approved_dir, item["id"])
        if path.exists():
            print(f"  Đã tồn tại, không ghi đè: {path.name}")
            skipped += 1
            continue
        starter = {
            "schema_version": 1,
            "procedure_id": item["id"],
            "catalog_code": codes[0],
            "approval": {
                "issuer": "BỆNH VIỆN",
                "decision_number": "__SỐ QUYẾT ĐỊNH BỆNH VIỆN__",
                "decision_date": "YYYY-MM-DD",
                "approved_title": item["technical_catalog"]["annex1"]["name"],
                "approved_by": "__NGƯỜI PHÊ DUYỆT__",
                "attested_by": "__NGƯỜI ĐỐI CHIẾU PDF VỚI JSON__",
                "signed_pdf": item["id"] + "-QTKT-da-ky.pdf",
                "signed_pdf_sha256": "",
                "serial_number": "",
                "writer": "", "reviewer": "", "approver_title": "",
            },
            "content": {
                key: ("" if key in OPTIONAL_FIELDS else "__NHẬP NGUYÊN VĂN TỪ HỒ SƠ BỆNH VIỆN__")
                for key in CLINICAL_FIELDS
            },
            "content_sha256": "",
        }
        with path.open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(starter, ensure_ascii=False, indent=2) + "\n")
        created += 1
        print(f"  Đã tạo khung nhập, CHƯA ĐƯỢC DUYỆT: {path.name}")
    return created, skipped


def preflight(selected: list[dict], approved_dir: Path) -> list[dict]:
    """Validate all local packages offline; do not touch Selenium or the portal."""
    results = []
    for item in selected:
        pid = item["id"]
        record = {"id": pid, "service": item["service"], "status": "BLOCKED", "reason": ""}
        try:
            if not str(item.get("form_template", "")).startswith("Lâm sàng"):
                raise ValueError("Biểu mẫu xét nghiệm dùng QĐ 3376; bộ lưu đã duyệt hiện chỉ hỗ trợ mẫu lâm sàng.")
            form = item.get("form_decision", {})
            codes = form.get("codes", [])
            if form.get("annex") != "PL1" or len(codes) != 1:
                raise ValueError("Dịch vụ không có duy nhất một mã PL1; cần kiểm tra danh mục.")
            if not item.get("technical_catalog", {}).get("annex1", {}).get("name"):
                raise ValueError("Thiếu tên kỹ thuật trong PL1.")
            path = package_file(approved_dir, pid)
            data = load_approved_package(
                path, pid, codes[0], item["technical_catalog"]["annex1"]["name"]
            )
            record.update(
                status="READY", reason="", path=str(path),
                code=codes[0], sha256=data["content_sha256"],
                decision=data["approval"]["decision_number"]
            )
        except (ValueError, KeyError, OSError, json.JSONDecodeError) as exc:
            record["reason"] = str(exc)
        results.append(record)
    return results


def write_report(rows: list[dict], *, scope: str, consent: bool, result: str,
                 report_dir: Path = REPORT_DIR) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now()
    path = report_dir / f"qtkt_batch_{now:%Y%m%d_%H%M%S_%f}.json"
    allowed = {"id", "service", "code", "status", "reason"}
    summary = [{k: v for k, v in row.items() if k in allowed} for row in rows]
    document = {
        "created_at": now.isoformat(timespec="seconds"),
        "scope": scope,
        "consent_to_save": consent,
        "result": result,
        "items": summary,
    }
    path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def run_batch(services: list[dict], approved_dir: Path, scope: str,
              *, save: bool, ask: Callable[[str], str] = input,
              invoke: Callable[..., object] = subprocess.run,
              report_dir: Path = REPORT_DIR) -> int:
    selected = select_services(services, scope)
    records = preflight(selected, approved_dir)
    for i, row in enumerate(records, 1):
        label = "ĐỦ HỒ SƠ" if row["status"] == "READY" else "CHƯA ĐỦ"
        print(f"[{i}/{len(records)}] {row['id']}: {label}")
        if row["status"] != "READY":
            print("  Lý do:", row["reason"])
    if any(row["status"] != "READY" for row in records):
        print("DỪNG TRƯỚC KHI ĐĂNG NHẬP: phải đủ hồ sơ đã phê duyệt cho TOÀN BỘ nhóm.")
        print("Không tự lấy nội dung từ data/clinical_drafts.json để lưu.")
        report = write_report(records, scope=scope, consent=False, result="PREFLIGHT_BLOCKED",
                              report_dir=report_dir)
        print("Báo cáo:", report)
        return 2
    if not save:
        print(f"Đã kiểm tra đủ {len(records)} hồ sơ. Đây là chạy thử, KHÔNG kết nối hoặc lưu lên website.")
        report = write_report(records, scope=scope, consent=False, result="CHECK_ONLY",
                              report_dir=report_dir)
        print("Báo cáo:", report)
        return 0

    phrase = f"LƯU TẤT CẢ {len(records)}"
    confirmation = ask(
        f"Đã đối chiếu {len(records)} QTKT với PDF bệnh viện ký duyệt. "
        f"Cho phép chương trình lưu lần lượt? Nhập đúng {phrase}: "
    ).strip()
    if confirmation != phrase:
        print("Đã hủy. Không đăng nhập và không lưu bản nào.")
        report = write_report(records, scope=scope, consent=False, result="CANCELLED",
                              report_dir=report_dir)
        print("Báo cáo:", report)
        return 1

    for i, row in enumerate(records, 1):
        pid = row["id"]
        print(f"\nBắt đầu [{i}/{len(records)}]: {pid}")
        env = dict(os.environ)
        env["DMKT_BATCH_SAVE_CONFIRMED_ID"] = pid
        env["DMKT_BATCH_SAVE_CONFIRMED_SHA256"] = row["sha256"]
        try:
            outcome = invoke(
                [sys.executable, str(ROOT / "autofill_portal.py"), "--id", pid,
                 "--approved-package", row["path"], "--save"],
                cwd=ROOT, env=env, check=False,
            )
            exit_code = outcome.returncode
        except Exception as exc:
            exit_code = 1
            row["reason"] = f"Không khởi chạy được phiên trình duyệt ({type(exc).__name__})."
        if exit_code:
            row["status"] = "FAILED_OR_UNCONFIRMED"
            if not row["reason"]:
                row["reason"] = f"Chrome/Selenium không xác nhận lưu (exit code {exit_code})."
            for later in records[i:]:
                later["status"] = "NOT_ATTEMPTED"
            report = write_report(records, scope=scope, consent=True,
                                  result="STOPPED_ON_ERROR", report_dir=report_dir)
            print("DỪNG NGAY sau lỗi. Kiểm tra cổng trước khi thử lại để tránh trùng.")
            print("Báo cáo:", report)
            return 1
        row["status"] = "SAVED_CONFIRMED_BY_PORTAL"
        print(f"Đã xác nhận lưu thành công [{i}/{len(records)}]: {pid}")

    report = write_report(records, scope=scope, consent=True,
                          result="ALL_SAVED_CONFIRMED", report_dir=report_dir)
    print(f"HOÀN TẤT: Cổng đã xác nhận lưu {len(records)}/{len(records)} QTKT.")
    print("Báo cáo:", report)
    return 0


def preflight_review(selected: list[dict], *, data_dir: Path = REVIEW_DATA) -> list[dict]:
    """Check all eight clinical drafts without pretending hospital approval."""
    procedures = json.loads((data_dir / "procedures.json").read_text(encoding="utf-8"))["procedures"]
    records = []
    for item in selected:
        result = {"id": item["id"], "service": item["service"],
                  "status": "BLOCKED", "reason": ""}
        try:
            draft, check = load_and_validate_review_item(
                item, procedures.get(item["id"], {}), data_dir=data_dir
            )
            result.update(
                code=check["code"], digest=check["digest"],
                missing=check["missing"], critical_missing=check["critical_missing"],
                status="READY_WITH_GAPS" if check["missing"] else "READY_FOR_REVIEW"
            )
        except (ValueError, KeyError, OSError, json.JSONDecodeError) as exc:
            result["reason"] = str(exc)
        records.append(result)
    return records


def run_review_batch(services: list[dict], *, save: bool,
                     ask: Callable[[str], str] = input,
                     invoke: Callable[..., object] = subprocess.run,
                     report_dir: Path = REPORT_DIR,
                     data_dir: Path = REVIEW_DATA) -> int:
    selected = select_services(services, "casts")
    if len(selected) != 8:
        print("Danh sách 8 nắn bó bột không còn đúng; dừng trước khi lưu.")
        return 2
    records = preflight_review(selected, data_dir=data_dir)
    for i, row in enumerate(records, 1):
        print(f"[{i}/8] {row['id']}: {row['status']}")
        if row.get("missing"):
            print("  Các mục chưa đủ nội dung:", ", ".join(row["missing"]))
        if row.get("critical_missing"):
            print("  CẢNH BÁO THIẾU NỘI DUNG CỐT LÕI:", ", ".join(row["critical_missing"]))
        if row["status"] == "BLOCKED":
            print("  Lý do:", row["reason"])
    if any(r["status"] == "BLOCKED" for r in records):
        print("DỪNG: chưa đủ dữ liệu cơ bản để nhập; không mở Chrome.")
        path = write_report(records, scope="casts_for_review", consent=False,
                            result="REVIEW_PREFLIGHT_BLOCKED", report_dir=report_dir)
        print("Báo cáo:", path)
        return 2
    if not save:
        print("KIỂM TRA BẢN NHÁP: không mở Chrome, không bấm Lưu.")
        path = write_report(records, scope="casts_for_review", consent=False,
                            result="REVIEW_CHECK_ONLY", report_dir=report_dir)
        print("Báo cáo:", path)
        return 0

    phrase = "LƯU 8 BẢN NHÁP CHỜ DUYỆT"
    print("CẢNH BÁO: nội dung đang là bản dự thảo. Lưu không có nghĩa được phê duyệt.")
    print("Chương trình chỉ để cờ 'Đang triển khai' BỎ CHỌN. Các ô không có căn cứ được để trống.")
    confirmation = ask(
        "Bạn xác nhận trên cổng này nút Lưu chỉ ghi hồ sơ để người khác duyệt, "
        f"và chấp nhận các mục chưa hoàn thiện? Nhập đúng {phrase}: "
    ).strip()
    if confirmation != phrase:
        print("Đã hủy, chưa đăng nhập cổng.")
        path = write_report(records, scope="casts_for_review", consent=False,
                            result="REVIEW_CANCELLED", report_dir=report_dir)
        print("Báo cáo:", path)
        return 1

    for i, row in enumerate(records, 1):
        pid = row["id"]
        env = dict(os.environ)
        env["DMKT_BATCH_REVIEW_ID"] = pid
        env["DMKT_BATCH_REVIEW_SHA256"] = row["digest"]
        print(f"\nĐang nhập bản nháp [{i}/8]: {pid}")
        try:
            response = invoke(
                [sys.executable, str(ROOT / "autofill_portal.py"),
                 "--id", pid, "--submit-for-review", "--save"],
                cwd=ROOT, env=env, check=False,
            )
            exit_code = response.returncode
        except Exception as exc:
            exit_code = 1
            row["reason"] = f"Chưa chạy được Chrome/Selenium ({type(exc).__name__})."
        if exit_code:
            row["status"] = "FAILED_OR_UNCONFIRMED"
            if not row["reason"]:
                row["reason"] = f"Không xác nhận lưu trên cổng (exit code {exit_code})."
            for pending in records[i:]:
                pending["status"] = "NOT_ATTEMPTED"
            path = write_report(records, scope="casts_for_review", consent=True,
                                result="REVIEW_STOPPED_ON_ERROR", report_dir=report_dir)
            print("DỪNG tại mục lỗi. Kiểm tra trên website trước khi chạy lại để tránh trùng.")
            print("Báo cáo:", path)
            return 1
        row["status"] = "SAVED_TO_PORTAL_UNAPPROVED"
        print(f"Cổng đã xác nhận lưu bản nháp [{i}/8]: {pid}. Chưa có xác nhận phê duyệt.")
    path = write_report(records, scope="casts_for_review", consent=True,
                        result="REVIEW_ALL_SAVED_UNAPPROVED", report_dir=report_dir)
    print("Đã lưu 8 bản lên cổng. Trạng thái duyệt do bộ phận có thẩm quyền quản lý.")
    print("Báo cáo:", path)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Kiểm tra hoặc lưu lần lượt các QTKT đã phê duyệt; dừng nếu thiếu bất kỳ hồ sơ nào."
    )
    parser.add_argument("--scope", choices=("casts", "clinical", "all"), default="casts",
                        help="casts=8 nắn bó bột; clinical=11 lâm sàng; all=13 (xét nghiệm chưa hỗ trợ)")
    parser.add_argument("--approved-dir", type=Path, default=DEFAULT_APPROVED_DIR)
    parser.add_argument("--save", action="store_true", help="Cho phép lưu sau một lần xác nhận toàn bộ danh sách")
    parser.add_argument("--for-review", action="store_true",
                        help="8 QTKT bản nháp để người khác duyệt; KHÔNG yêu cầu quyết định phê duyệt đã ban hành")
    parser.add_argument("--init-templates", action="store_true",
                        help="Tạo khung JSON cho từng dịch vụ, không tự lấy dữ liệu nháp và không tự lưu")
    args = parser.parse_args(argv)
    if args.save and args.init_templates:
        parser.error("--init-templates không thể dùng cùng --save.")
    if args.for_review and (args.init_templates or args.scope != "casts"):
        parser.error("--for-review chỉ dùng cho 8 QTKT nắn bó bột, không dùng --init-templates/--scope khác.")
    services = json.loads(SERVICES_PATH.read_text(encoding="utf-8"))
    if args.for_review:
        return run_review_batch(services, save=args.save)
    if args.init_templates:
        chosen = select_services(services, args.scope)
        created, skipped = initialize_templates(chosen, args.approved_dir.resolve())
        print(f"Đã tạo {created} khung; bỏ qua {skipped}. TẤT CẢ khung còn phải nhập từ PDF bệnh viện.")
        return 0
    return run_batch(services, args.approved_dir.resolve(), args.scope, save=args.save)


if __name__ == "__main__":
    raise SystemExit(main())
