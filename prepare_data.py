"""Export the bundled, offline-reviewed service data to UTF-8 CSV files."""
from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
OUT = ROOT / "output"
OUT.mkdir(exist_ok=True)

services = json.loads((DATA / "services.json").read_text(encoding="utf-8"))
sources = json.loads((DATA / "sources.json").read_text(encoding="utf-8"))
procedures = json.loads((DATA / "procedures.json").read_text(encoding="utf-8"))["procedures"]

columns = ["id", "Tên dịch vụ", "Người thực hiện", "Khoa/đơn vị", "Mẫu quy trình", "Ghi chú mẫu", "Căn cứ phân công", "Mẫu đã chọn hiện hành", "Mã PL01 khuyến nghị", "Ghi chú chọn mã", "Mã PL01", "Tên kỹ thuật PL01", "Mức khớp PL01", "Mã PL02", "Tên kỹ thuật PL02", "Mức khớp PL02", "Thời điểm áp dụng danh mục", "Văn bản nguồn", "Tên kỹ thuật nguồn", "Trang PDF index (0-based)", "Mức độ khớp QTKT", "Ghi chú đối chiếu", "Tổng quan dự thảo", "Chỉ định dự thảo", "Chống chỉ định dự thảo", "Chuẩn bị dự thảo", "Các bước dự thảo", "Theo dõi/biến chứng dự thảo", "Việc cần bệnh viện xác nhận", "URL nguồn"]
path = OUT / "Danh_sach_13_dich_vu_va_du_lieu_nguon.csv"
with path.open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=columns)
    writer.writeheader()
    for item in services:
        details = procedures.get(item["id"], {})
        fields = details.get("form_fields", {})
        source_ids = details.get("source_ids") or ([item["source_id"]] if item.get("source_id") else [])
        source_list = [sources[k] for k in source_ids if k in sources]
        source_list += [sources[k] for k in ("tt23", "tt25") if k in sources]
        source_list += [sources[k] for k in item.get("form_decision", {}).get("template_source_ids", []) if k in sources]
        catalog = item.get("technical_catalog", {})
        pl1 = catalog.get("annex1", {})
        pl2 = catalog.get("annex2", {})
        writer.writerow({
            "id": item["id"],
            "Tên dịch vụ": item["service"],
            "Người thực hiện": item["performer"],
            "Khoa/đơn vị": item["department"],
            "Mẫu quy trình": item.get("form_template", ""),
            "Ghi chú mẫu": item.get("form_template_note", ""),
            "Căn cứ phân công": item.get("assignment_basis", ""),
            "Mẫu đã chọn hiện hành": item.get("form_decision", {}).get("annex", "PL1"),
            "Mã PL01 khuyến nghị": "; ".join(item.get("form_decision", {}).get("codes", [])),
            "Ghi chú chọn mã": item.get("form_decision", {}).get("code_decision_note", ""),
            "Mã PL01": pl1.get("code") or "Chưa xác định",
            "Tên kỹ thuật PL01": pl1.get("name") or "Chưa tìm thấy khớp",
            "Mức khớp PL01": pl1.get("match", ""),
            "Mã PL02": pl2.get("code") or "Chưa xác định",
            "Tên kỹ thuật PL02": pl2.get("name") or "Chưa tìm thấy khớp",
            "Mức khớp PL02": pl2.get("match", ""),
            "Thời điểm áp dụng danh mục": catalog.get("annex_status", ""),
            "Văn bản nguồn": "; ".join(x.get("decision", "") for x in source_list),
            "Tên kỹ thuật nguồn": item.get("source_procedure") or "Chưa tìm thấy quy trình khớp trực tiếp",
            "Trang PDF index (0-based)": ", ".join(map(str, item.get("pdf_pages", []))),
            "Mức độ khớp QTKT": details.get("match_status", item.get("match", "")),
            "Ghi chú đối chiếu": item.get("note", ""),
            "Tổng quan dự thảo": fields.get("overview", ""),
            "Chỉ định dự thảo": fields.get("indications", ""),
            "Chống chỉ định dự thảo": fields.get("contraindications", ""),
            "Chuẩn bị dự thảo": fields.get("preparation", ""),
            "Các bước dự thảo": fields.get("steps", ""),
            "Theo dõi/biến chứng dự thảo": fields.get("risks_followup", ""),
            "Việc cần bệnh viện xác nhận": fields.get("local_confirmation", ""),
            "URL nguồn": "; ".join(x.get("url", "") for x in source_list),
        })

print(f"Đã tạo dữ liệu CSV dùng Excel: {path}")
print("Dữ liệu nguồn, dự thảo chuyên môn và ghi chú giới hạn đã được đóng gói sẵn; không cần tải PDF để xuất CSV.")
