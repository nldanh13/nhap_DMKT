from __future__ import annotations

import argparse
import base64
import ctypes
from ctypes import wintypes
from getpass import getpass
import json
import os
import re
import sys
import time
import traceback
import unicodedata
from datetime import date, datetime
from pathlib import Path

from approved_package import CLINICAL_FIELDS, REQUIRED_FIELDS, load_approved_package

from selenium import webdriver
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
services = json.loads((DATA / "services.json").read_text(encoding="utf-8"))
sources = json.loads((DATA / "sources.json").read_text(encoding="utf-8"))
all_procedures = json.loads((DATA / "procedures.json").read_text(encoding="utf-8"))["procedures"]
config_path = ROOT / "selectors.json"
login_config_path = ROOT / "login.json"

parser = argparse.ArgumentParser(
    description="Điền trước biểu mẫu để người dùng kiểm tra; mặc định KHÔNG tự lưu."
)
parser.add_argument("--id", help="ID dịch vụ trong data/services.json")
parser.add_argument("--inspect", action="store_true", help="Chỉ liệt kê các trường biểu mẫu")
parser.add_argument("--draft-preview", action="store_true", help="Điền bản NHÁP chưa thẩm định vào biểu mẫu để kiểm tra, KHÔNG LƯU")
parser.add_argument("--save", action="store_true", help="Chỉ lưu sau khi đã kiểm tra và xác nhận rõ ràng.")
parser.add_argument("--approved-package", type=Path, help="JSON dữ liệu QTKT chính thức kèm thông tin quyết định và dấu vân tay PDF đã ký.")
args = parser.parse_args()
if args.draft_preview and (args.save or args.inspect or args.approved_package):
    parser.error("--draft-preview không thể dùng cùng --save, --inspect hoặc --approved-package")
if args.approved_package and (not args.save or args.inspect or not args.id):
    parser.error("--approved-package yêu cầu --id và --save; không dùng cùng --inspect")
if args.save and not args.approved_package:
    parser.error("--save bắt buộc có --approved-package trỏ tới dữ liệu QTKT bệnh viện đã phê duyệt.")

if args.id:
    matches = [x for x in services if x["id"] == args.id]
    if not matches:
        sys.exit(f"Không có ID: {args.id}")
    item = matches[0]
else:
    for i, x in enumerate(services, 1):
        p = all_procedures.get(x["id"], {})
        print(f"{i:2}. {x['service']} [{x['id']}] — {x['performer']} — {p.get('match_status', x['match'])}")
    try:
        n = int(input("Chọn dịch vụ cần tạo quy trình: "))
        item = services[n - 1]
    except (ValueError, IndexError):
        sys.exit("Lựa chọn không hợp lệ.")

selectors = json.loads(config_path.read_text(encoding="utf-8"))
procedure = all_procedures.get(item["id"], {})
form_fields = procedure.get("form_fields", {})
source_ids = procedure.get("source_ids") or ([item["source_id"]] if item.get("source_id") else [])
source_list = [sources[k] for k in source_ids if k in sources]
catalog_sources = [sources[k] for k in ("tt23", "tt25") if k in sources]
template_sources = [sources[k] for k in item.get("form_decision", {}).get("template_source_ids", []) if k in sources]
# Keep the "Tài liệu tham khảo" field bibliographic: exclude catalog notes, page indexes,
# and match-status commentary, which belong in the review dataset rather than the citation list.
reference_sources = []
seen_reference_ids = set()
for source in source_list + catalog_sources:
    citation = source.get("reference_citation")
    if citation and citation not in seen_reference_ids:
        reference_sources.append(citation)
        seen_reference_ids.add(citation)
source_text = "\n".join(
    f"{index}. {citation}" for index, citation in enumerate(reference_sources, 1)
)

values = {
    "service": item["service"],
    "template_type": item.get("form_template"),
    "specialty": item.get("department"),
    "catalog_annex": item.get("form_decision", {}).get("annex", "PL1"),
    "issuing_authority": item.get("form_decision", {}).get("issuing_authority", "BỆNH VIỆN"),
    "section6_title": item.get("form_decision", {}).get("section6_title", "CÁC BƯỚC TIẾN HÀNH"),
    # Chưa có quyết định triển khai của bệnh viện nên luôn bỏ chọn cờ này.
    "deployment_flag": False,
    "performer": item["performer"],
    "department": item["department"],
    "assignment_basis": item.get("assignment_basis", ""),
    "source": source_text,
    **form_fields,
}

# Trong mẫu lâm sàng, ô 5.1 cần chức danh và số lượng nhân lực, không ghi tên
# cá nhân được phân công. Với 8 bản dự thảo, chỉ điền nhân lực trong preview.
if procedure.get("requires_clinical_review", False):
    values["performer"] = None


def separate_personnel(personnel: str) -> tuple[str, str]:
    """Split staffing by role and quantity; do not append any person's name."""
    direct, marker, support = personnel.partition("\nNhân lực hỗ trợ:")
    direct = direct.removeprefix("Nhân lực trực tiếp:").strip()
    return direct, support.strip() if marker else ""


approved_package = None
if args.approved_package:
    codes_expected = list(dict.fromkeys(item.get("form_decision", {}).get("codes", [])))
    if len(codes_expected) != 1 or item.get("form_decision", {}).get("annex") != "PL1":
        parser.error("Chế độ lưu dữ liệu đã duyệt yêu cầu chính xác một mã danh mục PL1.")
    try:
        approved_package = load_approved_package(
            args.approved_package,
            item["id"], codes_expected[0], item["technical_catalog"]["annex1"]["name"],
        )
    except (ValueError, OSError, KeyError, json.JSONDecodeError) as exc:
        parser.error(f"Không thể xác nhận bộ hồ sơ đã duyệt: {exc}")

    # NEVER inherit editorial fields from a generated draft for an approved save.
    for key in CLINICAL_FIELDS:
        values[key] = None
    values.update(approved_package["content"])
    values["performer"] = approved_package["content"]["personnel"]
    values["support_personnel"] = approved_package["content"].get("support_personnel") or None
    values["source"] = approved_package["content"]["references"]
    approval = approved_package["approval"]
    values.update(
        issuing_authority=approval["issuer"],
        decision_number=approval["decision_number"],
        issue_date=date.fromisoformat(approval["decision_date"]).strftime("%d/%m/%Y"),
        serial_number=approval.get("serial_number"),
        writer=approval.get("writer"),
        writer_title=approval.get("writer_title"),
        reviewer=approval.get("reviewer"),
        reviewer_title=approval.get("reviewer_title"),
        approver=approval["approved_by"],
        approver_title=approval.get("approver_title"),
        deployment_flag=False,
    )
    print(f"Đã xác minh checksum gói và PDF: {item['id']} — {approval['decision_number']}")
    print("Lưu ý: checksum không xác minh chữ ký hoặc độ chính xác chuyển nội dung PDF; người phụ trách phải kiểm tra.")
if args.draft_preview:
    draft = json.loads((DATA / "clinical_drafts.json").read_text(encoding="utf-8"))["procedures"].get(item["id"])
    if not draft or not procedure.get("requires_clinical_review", False):
        parser.error("Chỉ dùng --draft-preview cho các QTKT có dữ liệu nháp cần thẩm định")
    print("CẢNH BÁO: Đây là BẢN NHÁP chưa được bệnh viện phê duyệt. Không sử dụng làm quy trình chính thức.")
    if input("Chỉ xem trước trong biểu mẫu, KHÔNG LƯU. Nhập XEM để tiếp tục: ").strip() != "XEM":
        raise SystemExit("Đã hủy điền bản nháp.")
    direct, support = separate_personnel(draft["personnel"])
    values.update(performer=direct or None, support_personnel=support or None,
                  source=draft.get("references") or None)


def visible(driver, selector: str) -> bool:
    return bool(driver.execute_script("""
      return Array.from(document.querySelectorAll(arguments[0]))
        .some(e => e.getClientRects().length && getComputedStyle(e).visibility !== 'hidden');
    """, selector))


def protect_password(password: str) -> str:
    """Mã hóa bằng Windows DPAPI, chỉ tài khoản Windows hiện tại giải mã được."""
    if os.name != "nt":
        return ""

    class DataBlob(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]

    raw = password.encode("utf-8")
    source_buffer = (ctypes.c_byte * len(raw)).from_buffer_copy(raw)
    source = DataBlob(len(raw), ctypes.cast(source_buffer, ctypes.POINTER(ctypes.c_byte)))
    encrypted = DataBlob()
    crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    crypt32.CryptProtectData.argtypes = [
        ctypes.POINTER(DataBlob), wintypes.LPCWSTR, ctypes.POINTER(DataBlob),
        wintypes.LPVOID, wintypes.LPVOID, wintypes.DWORD, ctypes.POINTER(DataBlob),
    ]
    crypt32.CryptProtectData.restype = wintypes.BOOL
    kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    kernel32.LocalFree.restype = ctypes.c_void_p
    ok = crypt32.CryptProtectData(
        ctypes.byref(source), None, None, None, None, 0, ctypes.byref(encrypted)
    )
    if not ok:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        return base64.b64encode(ctypes.string_at(encrypted.pbData, encrypted.cbData)).decode("ascii")
    finally:
        kernel32.LocalFree(encrypted.pbData)


def unprotect_password(encoded: str) -> str:
    if os.name != "nt" or not encoded:
        return ""

    class DataBlob(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]

    raw = base64.b64decode(encoded)
    source_buffer = (ctypes.c_byte * len(raw)).from_buffer_copy(raw)
    source = DataBlob(len(raw), ctypes.cast(source_buffer, ctypes.POINTER(ctypes.c_byte)))
    decrypted = DataBlob()
    crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    crypt32.CryptUnprotectData.argtypes = [
        ctypes.POINTER(DataBlob), ctypes.POINTER(wintypes.LPWSTR), ctypes.POINTER(DataBlob),
        wintypes.LPVOID, wintypes.LPVOID, wintypes.DWORD, ctypes.POINTER(DataBlob),
    ]
    crypt32.CryptUnprotectData.restype = wintypes.BOOL
    kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    kernel32.LocalFree.restype = ctypes.c_void_p
    ok = crypt32.CryptUnprotectData(
        ctypes.byref(source), None, None, None, None, 0, ctypes.byref(decrypted)
    )
    if not ok:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        return ctypes.string_at(decrypted.pbData, decrypted.cbData).decode("utf-8")
    finally:
        kernel32.LocalFree(decrypted.pbData)


def load_login_settings() -> tuple[str, str, str]:
    try:
        saved = json.loads(login_config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        saved = {}

    username = str(saved.get("username", "")).strip()
    unit = str(saved.get("unit", "")).strip() or str(item["department"])
    protected = str(saved.get("password_protected", ""))
    if not username:
        username = input("Họ tên tài khoản đăng nhập: ").strip()
    if not username:
        sys.exit("Chưa nhập họ tên tài khoản.")

    password = ""
    if protected:
        try:
            password = unprotect_password(protected)
        except Exception:
            print("Không giải mã được mật khẩu đã lưu trên máy này; vui lòng nhập lại.")
    if not password:
        password = getpass("Mật khẩu (ký tự không hiển thị): ")
        if not password:
            sys.exit("Chưa nhập mật khẩu.")
        if os.name == "nt":
            protected = protect_password(password)
            print("Mật khẩu đã được mã hóa và lưu trong login.json trên tài khoản Windows này.")
        else:
            protected = ""
            print("Mật khẩu không được lưu trên hệ điều hành này; lần chạy sau sẽ hỏi lại.")

    login_config_path.write_text(json.dumps({
        "username": username,
        "unit": unit,
        "password_protected": protected,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return username, password, unit


def perform_login(driver, username: str, password: str, unit: str) -> None:
    WebDriverWait(driver, 30, poll_frequency=0.25).until(lambda d: d.execute_script(
        "return !!document.querySelector('#loginRole') && document.querySelectorAll('#loginRole option').length > 1"
    ))

    def unit_key(value: str) -> str:
        value = unicodedata.normalize("NFKD", value)
        value = "".join(ch for ch in value if not unicodedata.combining(ch))
        return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()

    wanted = unit_key(unit)
    # Lấy option trực tiếp từ DOM. Value CTCH trong biểu mẫu hiện tại được rút gọn
    # thành `khoa-ngoai-chan-thuong-chinh-hinh-than-k`, nên ưu tiên mã này.
    dom_options = driver.execute_script("""
      return Array.from(document.querySelectorAll('#loginRole option')).map(o => ({
        text: (o.textContent || '').trim(), value: o.getAttribute('value') || ''
      }));
    """)
    known_values = {
        "khoa ngoai chan thuong chinh hinh than kinh": "khoa-ngoai-chan-thuong-chinh-hinh-than-k",
    }
    preferred_value = known_values.get(wanted)
    matching_indices = [i for i, o in enumerate(dom_options)
                        if preferred_value and o["value"] == preferred_value]
    if not matching_indices:
        matching_indices = [i for i, o in enumerate(dom_options) if unit_key(o["text"]) == wanted]
    if not matching_indices:
        # Một số nhãn có dấu nối/khoảng trắng khác nhau; chấp nhận khớp đủ các từ
        # đặc trưng khi chỉ còn duy nhất một lựa chọn phù hợp.
        words = set(wanted.split()) - {"khoa", "phong", "trung", "tam", "to"}
        matching_indices = [i for i, o in enumerate(dom_options)
                            if words and words.issubset(set(unit_key(o["text"]).split()))]
    if len(matching_indices) != 1:
        available = "; ".join(o["text"] for o in dom_options)
        raise RuntimeError(f"Không tìm được duy nhất đơn vị “{unit}” trong danh sách đăng nhập. Đơn vị trên trang: {available}")
    # Chọn theo chỉ số để không phụ thuộc vào value bị rút gọn hoặc Selenium
    # không đọc được thuộc tính value của option.
    def choose_login_unit(d):
        try:
            select = Select(d.find_element(By.ID, "loginRole"))
            select.select_by_index(matching_indices[0])
            selected_unit = select.first_selected_option.text.strip()
            return selected_unit if unit_key(selected_unit) == wanted else False
        except StaleElementReferenceException:
            return False

    selected_unit = WebDriverWait(driver, 15, poll_frequency=0.2).until(choose_login_unit)
    if unit_key(selected_unit) != wanted:
        raise RuntimeError(f"Đơn vị đăng nhập chưa đúng. Đã chọn: {selected_unit}")
    set_text_fresh(driver, "#loginName", username, "tên đăng nhập")
    set_text_fresh(driver, "#loginPass", password, "mật khẩu")
    click_unique(driver, "#loginBtn", "Đăng nhập")

    def login_finished(d):
        return d.execute_script("""
      const login = document.querySelector('.loginbox, #loginBox, #login');
      const tab = document.querySelector('[data-tab="qt"]');
      const shown = e => !!e && !!e.getClientRects().length && getComputedStyle(e).visibility !== 'hidden';
      const error = document.querySelector('#loginErr');
      if (error && shown(error) && error.textContent.trim()) return 'ERROR:' + error.textContent.trim();
      return shown(tab) && (!login || !shown(login)) ? 'OK' : false;
    """)

    try:
        result = WebDriverWait(driver, 30, poll_frequency=0.25).until(login_finished)
    except TimeoutException as exc:
        raise RuntimeError("Đăng nhập chưa hoàn tất trong 30 giây; kiểm tra họ tên, mật khẩu hoặc thông báo trên trang.") from exc
    if result != "OK":
        raise RuntimeError(f"Trang từ chối đăng nhập: {result.removeprefix('ERROR:')}")


def click_unique(driver, selector: str, label: str, timeout: int = 20):
    """Retry the entire lookup: elements can become stale even during visibility checks."""
    def click_fresh(d):
        try:
            elements = [
                e for e in d.find_elements(By.CSS_SELECTOR, selector)
                if e.is_displayed() and e.is_enabled()
            ]
            if len(elements) > 1:
                raise RuntimeError(f"Không xác định duy nhất nút {label}: tìm thấy {len(elements)} nút.")
            if not elements:
                return False
            elements[0].click()
            return True
        except StaleElementReferenceException:
            # SPA rerendered while checking/clicking: acquire a new element next poll.
            return False

    WebDriverWait(driver, timeout, poll_frequency=0.2).until(click_fresh)


def set_text_fresh(driver, selector: str, value: str, label: str, timeout: int = 15) -> None:
    """Reacquire the input when the app rerenders, including during visibility checks."""
    value = str(value)

    def replace(d):
        try:
            elements = [
                e for e in d.find_elements(By.CSS_SELECTOR, selector)
                if e.is_displayed() and e.is_enabled()
            ]
            if len(elements) > 1:
                raise RuntimeError(f"Không xác định duy nhất trường {label}: tìm thấy {len(elements)} trường.")
            if not elements:
                return False
            el = elements[0]
            el.clear()
            el.send_keys(value)
            return True
        except StaleElementReferenceException:
            return False

    WebDriverWait(driver, timeout, poll_frequency=0.2).until(replace)


def read_selector_values(driver, selector: str) -> list[dict]:
    """Read current DOM values atomically, avoiding WebElement references across rerenders."""
    return driver.execute_script("""
      const selector = arguments[0];
      return Array.from(document.querySelectorAll(selector))
        .filter(e => e.getClientRects().length)
        .map(e => ({tag:e.tagName.toLowerCase(), type:(e.type||'').toLowerCase(),
          value:('value' in e ? e.value : (e.innerText || e.textContent || '')),
          checked:!!e.checked,
          selectedText:e.tagName === 'SELECT' && e.selectedIndex >= 0
            ? e.options[e.selectedIndex].text.trim() : ''}));
    """, selector)


def select_picker_row(driver, code_or_name: str, *, exact: bool = True) -> None:
    """Chọn một dòng chính xác trong bộ chọn của trang và xác nhận nó đã được áp dụng."""
    set_text_fresh(driver, "#mdPickSearch", code_or_name, "tìm trong danh sách", timeout=20)

    def click_matching_row(d):
        rows = d.find_elements(By.CSS_SELECTOR, "#mdPickTbl tbody tr[data-i]")
        matched = []
        for row in rows:
            try:
                cells = [c.text.strip() for c in row.find_elements(By.CSS_SELECTOR, "td")]
                if (exact and code_or_name in cells) or (
                    not exact and any(code_or_name.casefold() == c.casefold() for c in cells)
                ):
                    matched.append(row)
            except StaleElementReferenceException:
                return False
        if len(matched) > 1:
            raise RuntimeError(f"Danh sách có nhiều dòng khớp “{code_or_name}”; không tự chọn.")
        if not matched:
            return False
        try:
            matched[0].click()
            return True
        except StaleElementReferenceException:
            return False

    WebDriverWait(driver, 20, poll_frequency=0.2).until(click_matching_row)
    WebDriverWait(driver, 15).until(lambda d: not visible(d, "#mdPick.on"))


def selected_code_values(driver) -> list[str]:
    return driver.execute_script("""
      const box = document.querySelector('#qfKT');
      return box ? Array.from(box.querySelectorAll('tbody tr'))
        .map(row => row.cells && row.cells[1] ? row.cells[1].innerText.trim() : '')
        .filter(Boolean) : [];
    """)


def choose_codes(driver) -> list[str]:
    codes = list(dict.fromkeys(item.get("form_decision", {}).get("codes", [])))
    if not codes:
        raise RuntimeError("Dịch vụ chưa có mã kỹ thuật PL1 được xác định; dừng trước khi lưu.")

    current_annex = read_selector_values(driver, "#qfLoaiMa")
    if len(current_annex) != 1:
        raise RuntimeError("Không tìm thấy duy nhất ô chọn phụ lục mã kỹ thuật.")
    if driver.execute_script("return document.querySelector('#qfLoaiMa').value") != "PL1":
        def choose_pl1(d):
            try:
                el = d.find_element(By.ID, "qfLoaiMa")
                Select(el).select_by_value("PL1")
                return True
            except StaleElementReferenceException:
                return False
        WebDriverWait(driver, 10, poll_frequency=0.2).until(choose_pl1)
        WebDriverWait(driver, 10, poll_frequency=0.2).until(
            lambda d: d.execute_script("return document.querySelector('#qfLoaiMa')?.value") == "PL1"
        )

    for code in codes:
        if code in selected_code_values(driver):
            continue
        click_unique(driver, "#qfThemKT", "Chọn kỹ thuật")
        select_picker_row(driver, code, exact=True)
        if code not in selected_code_values(driver):
            raise RuntimeError(f"Trang chưa xác nhận đã thêm mã kỹ thuật {code}; dừng trước khi lưu.")

    selected = selected_code_values(driver)
    if set(selected) != set(codes):
        raise RuntimeError(f"Mã kỹ thuật trên biểu mẫu không khớp. Cần {codes}, hiện có {selected}; dừng trước khi lưu.")
    return codes


def choose_department(driver) -> None:
    expected = str(item.get("department", "")).strip()
    if not expected:
        return
    if expected in driver.execute_script("return document.querySelector('#qfDV')?.innerText || ''"):
        return
    click_unique(driver, "#qfThemDV", "Thêm đơn vị thực hiện")
    select_picker_row(driver, expected, exact=False)
    if expected not in driver.execute_script("return document.querySelector('#qfDV')?.innerText || ''"):
        raise RuntimeError(f"Chưa xác nhận đơn vị thực hiện {expected}; dừng trước khi lưu.")


def fill_fields(driver) -> tuple[list[str], list[str], dict[str, str]]:
    field_selectors = dict(selectors)
    if args.approved_package:
        field_selectors.update({
            "decision_number": '[data-qf="qdBV"]',
            "issue_date": '[data-qf="ngayBH"]',
            "serial_number": '[data-qf="sttQT"]',
            "writer": '[data-qf="nguoiViet"]',
            "writer_title": '[data-qf="cdViet"]',
            "reviewer": '[data-qf="nguoiKiemTra"]',
            "reviewer_title": '[data-qf="cdKiemTra"]',
            "approver": '[data-qf="nguoiPheDuyet"]',
            "approver_title": '[data-qf="cdPheDuyet"]',
        })
    is_xn = str(item.get("form_template", "")).startswith("Xét nghiệm")
    if is_xn:
        # Mẫu QĐ 3376 dùng bộ tên trường khác mẫu lâm sàng.
        field_selectors.update({
            "performer": '[data-qf="xnNguoiTH"]',
            "overview": '[data-qf="xnMucDich"]',
            "indications": '[data-qf="xnPhamVi"]',
            "contraindications": '[data-qf="xnKtTruoc"]',
            "preparation": '[data-qf="xnThietBi"]',
            "consumables": '[data-qf="xnHoaChat"]',
            "pre_test_checks": '[data-qf="xnKtTruoc"]',
            "instrument_setup": '[data-qf="xnChuanBi"]',
            "responsibilities": '[data-qf="xnTrachNhiem"]',
            "abbreviations": '[data-qf="xnVietTat"]',
            "sample": '[data-qf="xnMauBP"]',
            "location": '[data-qf="diaDiem"]',
            "steps": '[data-qf="xnCacBuoc"]',
        })
        # Mẫu xét nghiệm không có ô Chống chỉ định riêng; không đổ nội dung này
        # vào ô Kiểm tra trước khi thực hiện.
        field_selectors.pop("contraindications", None)
        field_selectors.pop("section6_title", None)

    filled, skipped = [], []
    allowed_fields = set(field_selectors) if (args.draft_preview or args.approved_package) else set(procedure.get("autofill_fields", []))
    for key, selector in field_selectors.items():
        if not selector or key not in values or values[key] is None or values[key] == "":
            continue
        if allowed_fields and key not in allowed_fields and key not in {
            "service", "performer", "technical_name", "template_type", "specialty",
            "catalog_annex", "issuing_authority", "section6_title", "deployment_flag",
        }:
            continue
        try:
            def fill_fresh(d):
                try:
                    elements = [e for e in d.find_elements(By.CSS_SELECTOR, selector)
                                if e.is_displayed() and e.is_enabled()]
                    if len(elements) > 1:
                        raise RuntimeError(f"{key}: selector khớp {len(elements)} trường")
                    if not elements:
                        return False
                    el = elements[0]
                    if el.tag_name.lower() == "input" and el.get_attribute("type") == "checkbox":
                        if el.is_selected() != bool(values[key]):
                            el.click()
                    elif el.tag_name.lower() == "select":
                        select = Select(el)
                        if key == "catalog_annex":
                            select.select_by_value(str(values[key]))
                        else:
                            select.select_by_visible_text(str(values[key]))
                    else:
                        el.clear()
                        el.send_keys(str(values[key]))
                    return True
                except StaleElementReferenceException:
                    return False

            WebDriverWait(driver, 12, poll_frequency=0.2).until(fill_fresh)
            filled.append(key)
            print(f"  Đã điền: {key}")
        except TimeoutException:
            skipped.append(f"{key}: phần tử liên tục tải lại hoặc không sẵn sàng")
        except Exception as exc:
            skipped.append(f"{key}: không điền được ({type(exc).__name__})")
    return filled, skipped, field_selectors


def verify_fields(driver, filled: list[str], field_selectors: dict[str, str]) -> None:
    for key in filled:
        selector = field_selectors[key]
        current = read_selector_values(driver, selector)
        if len(current) != 1:
            raise RuntimeError(f"Trường {key} không còn xuất hiện duy nhất (tìm thấy {len(current)}); dừng trước khi lưu.")
        el = current[0]
        expected = values[key]
        if el["tag"] == "input" and el["type"] == "checkbox":
            actual = el["checked"]
        elif el["tag"] == "select" and key != "catalog_annex":
            actual = el["selectedText"].strip()
        else:
            actual = el["value"]
        if key == "deployment_flag":
            if actual:
                raise RuntimeError("Cờ Đang triển khai vẫn đang bật; dừng trước khi lưu.")
        elif key == "catalog_annex":
            if actual != str(expected):
                raise RuntimeError("Phụ lục kỹ thuật không đúng PL1; dừng trước khi lưu.")
        elif key == "service":
            if str(actual or "").strip().casefold() != str(expected).strip().casefold():
                raise RuntimeError("Tên quy trình trên biểu mẫu chưa khớp dịch vụ đã chọn.")
        elif str(actual or "").strip() != str(expected).strip():
            raise RuntimeError(f"Giá trị trường {key} chưa khớp; dừng trước khi lưu.")


def report_draft_preview_state(driver, filled: list[str], field_selectors: dict[str, str]) -> None:
    """Read actual DOM properties (not HTML attributes) without printing medical content."""
    wanted = {key: field_selectors[key] for key in filled}
    state = driver.execute_script("""
        const wanted = arguments[0];
        const inputs = {};
        for (const [key, selector] of Object.entries(wanted)) {
            const elements = Array.from(document.querySelectorAll(selector))
                .filter(e => e.getClientRects().length);
            if (elements.length !== 1) {
                inputs[key] = null;
                continue;
            }
            const el = elements[0];
            inputs[key] = {
                length: String(el.value ?? el.textContent ?? '').length,
                checked: el.type === 'checkbox' ? !!el.checked : null
            };
        }
        const checkbox = document.querySelector('#qfDanhDauTT');
        const save = document.querySelector('#qfLuu');
        return {
            inputs,
            deployment_checked: checkbox ? !!checkbox.checked : null,
            save_disabled: save ? !!save.disabled : null
        };
    """, wanted)
    missing = [key for key, item_state in state["inputs"].items() if item_state is None]
    if missing:
        raise RuntimeError("Không còn tìm thấy duy nhất các ô: " + ", ".join(missing))
    if state["deployment_checked"] is not False:
        raise RuntimeError("Ô 'Đang triển khai' không ở trạng thái bỏ chọn.")
    if state["save_disabled"] is not True:
        raise RuntimeError("Nút 'Lưu' chưa bị vô hiệu hóa. Không tiếp tục bản nháp.")
    print("KIỂM TRA TRỰC TIẾP TỪ CHROME (không cần mở Console):")
    for key, item_state in state["inputs"].items():
        if key not in {"deployment_flag", "template_type", "catalog_annex", "section6_title"}:
            print(f"  {key}: {item_state['length']} ký tự")
    print("  Đang triển khai: KHÔNG đánh dấu")
    print("  Nút Lưu: ĐÃ VÔ HIỆU HÓA")


def find_existing_procedure(driver):
    """Tìm bản có sẵn để cập nhật, tránh tạo thêm quy trình trùng tên."""
    set_text_fresh(driver, "#dmSearch", item["service"], "tìm quy trình hiện có")
    time.sleep(0.4)
    matched = driver.execute_script("""
      const target = arguments[0].trim().toLocaleLowerCase();
      return Array.from(document.querySelectorAll('#dmTbl tbody tr')).filter(row =>
        Array.from(row.cells || []).some(cell => cell.innerText.trim().toLocaleLowerCase() === target)
      ).length;
    """, item["service"])
    if matched > 1:
        raise RuntimeError(f"Có nhiều quy trình trùng tên “{item['service']}”; không thể chọn bản cần sửa an toàn.")
    if matched == 0:
        set_text_fresh(driver, "#dmSearch", "", "xóa tìm kiếm")
    return matched == 1


def click_edit_existing(driver) -> None:
    def click_edit(d):
        rows = d.find_elements(By.CSS_SELECTOR, "#dmTbl tbody tr")
        matched = []
        for row in rows:
            try:
                cells = [c.text.strip() for c in row.find_elements(By.CSS_SELECTOR, "td")]
                if any(cell.casefold() == item["service"].strip().casefold() for cell in cells):
                    matched.append(row)
            except StaleElementReferenceException:
                return False
        if len(matched) != 1:
            return False
        try:
            buttons = matched[0].find_elements(By.CSS_SELECTOR, "button[data-xem]")
            if len(buttons) != 1 or buttons[0].text.strip().casefold() != "sửa":
                raise RuntimeError(f"Đã tìm thấy “{item['service']}” nhưng tài khoản không có nút Sửa duy nhất.")
            buttons[0].click()
            return True
        except StaleElementReferenceException:
            return False
    WebDriverWait(driver, 15, poll_frequency=0.2).until(click_edit)


def wait_for_success(driver) -> str:
    deadline = time.time() + 30
    last_toast = ""
    while time.time() < deadline:
        state = driver.execute_script("""
          const toast = document.querySelector('#toast');
          const info = document.querySelector('#mdInfo');
          return {toast: toast && toast.getClientRects().length ? toast.innerText.trim() : '',
            infoHidden: !!info && !info.getClientRects().length};
        """)
        last_toast = (state or {}).get("toast", "") or last_toast
        if last_toast in {"Đã thêm quy trình vào danh mục.", "Đã lưu thay đổi."}:
            return last_toast
        if last_toast and ("không lưu" in last_toast.casefold() or "không có quyền" in last_toast.casefold()):
            raise RuntimeError(f"Trang báo lỗi khi lưu: {last_toast}")
        if (state or {}).get("infoHidden") and last_toast:
            if "đã thêm quy trình" in last_toast.casefold() or "đã lưu thay đổi" in last_toast.casefold():
                return last_toast
        time.sleep(0.25)
    raise TimeoutException("Đã bấm Lưu nhưng trang chưa hiện thông báo xác nhận thành công trong 30 giây.")


def save_debug_bundle(driver, error: BaseException, step: str) -> Path | None:
    """Write local diagnostics without saving password field values."""
    folder = ROOT / "debug"
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    bundle = folder / stamp
    try:
        bundle.mkdir(parents=True, exist_ok=True)
        try:
            # Never leave a typed password in a debug screenshot or HTML snapshot.
            snapshot = driver.execute_script("""
              const clone = document.documentElement.cloneNode(true);
              clone.querySelectorAll('input[type=password]').forEach(e => { e.value = ''; e.removeAttribute('value'); });
              return '<!doctype html>\\n' + clone.outerHTML;
            """)
        except Exception:
            snapshot = "Không thể tạo snapshot HTML đã ẩn mật khẩu; không lưu DOM gốc vì có thể chứa thông tin nhạy cảm."
        (bundle / "page.html").write_text(snapshot, encoding="utf-8")
        try:
            driver.save_screenshot(str(bundle / "screenshot.png"))
        except Exception:
            pass
        try:
            browser_logs = driver.get_log("browser")
        except Exception as log_error:
            browser_logs = [{"message": f"Không đọc được console log: {log_error}"}]
        (bundle / "browser_console.json").write_text(
            json.dumps(browser_logs, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        details = (
            f"Thời điểm: {datetime.now().isoformat(timespec='seconds')}\\n"
            f"Dịch vụ: {item.get('service', '')} [{item.get('id', '')}]\\n"
            f"Bước cuối: {step}\\n"
            f"URL: {driver.current_url}\\n"
            f"Lỗi: {type(error).__name__}: {error}\\n\\n"
            f"Traceback:\\n{traceback.format_exc()}\\n"
        )
        (bundle / "error.txt").write_text(details, encoding="utf-8")
        return bundle
    except Exception as debug_error:
        print(f"Không tạo được gói debug: {debug_error}")
        return None


options = webdriver.ChromeOptions()
options.add_argument("--start-maximized")
options.set_capability("goog:loggingPrefs", {"browser": "ALL"})
username, password, login_unit = load_login_settings()
driver = webdriver.Chrome(options=options)
driver.get("https://quan-ly-dmkt.lhtran0701.workers.dev/")
current_step = "Khởi tạo trình duyệt"

try:
    current_step = "Đăng nhập"
    print("Đang đăng nhập...")
    perform_login(driver, username, password, login_unit)
    password = ""
    print("Đăng nhập thành công; chương trình đang mở biểu mẫu.")

    current_step = "Mở danh sách quy trình kỹ thuật"
    click_unique(driver, '[data-tab="qt"]', "Quy trình kỹ thuật")
    WebDriverWait(driver, 20).until(EC.visibility_of_element_located((By.ID, "qtThem")))
    current_step = "Tìm dịch vụ đã có để cập nhật hoặc tạo mới"
    existing = find_existing_procedure(driver)
    if existing and args.approved_package:
        raise RuntimeError("Đã có QTKT cùng tên trên cổng; chế độ nhập đã duyệt không tự ghi đè. Hãy kiểm tra bản hiện có trước khi quyết định cập nhật.")
    if existing:
        current_step = "Mở biểu mẫu sửa quy trình hiện có"
        click_edit_existing(driver)
        save_message = "Đã lưu thay đổi."
    else:
        current_step = "Mở biểu mẫu thêm quy trình"
        click_unique(driver, "#qtThem", "Thêm quy trình")
        save_message = "Đã thêm quy trình vào danh mục."
    current_step = "Chờ biểu mẫu sẵn sàng"
    WebDriverWait(driver, 20).until(EC.visibility_of_element_located((By.ID, "qfLuu")))
    if args.inspect:
        current_step = "Kiểm tra cấu trúc biểu mẫu đã mở"
        print("Đang đọc các ô nhập của biểu mẫu QTKT...")
        fields = driver.execute_script("""
          return Array.from(document.querySelectorAll('input,textarea,select,[contenteditable="true"]'))
            .filter(e => e.getClientRects().length && !e.disabled && e.type !== 'hidden')
            .map(e => ({tag:e.tagName, type:e.type||'', id:e.id||'', name:e.name||'',
              placeholder:e.getAttribute('placeholder')||'', ariaLabel:e.getAttribute('aria-label')||'',
              dataQf:e.getAttribute('data-qf')||'',
              labels:Array.from(e.labels||[]).map(x=>x.innerText.trim()).filter(Boolean).join(' | ')}));
        """)
        if not fields:
            raise RuntimeError("Biểu mẫu QTKT đã mở nhưng không tìm thấy ô nhập đang hiển thị. Kiểm tra lại giao diện website.")
        print(f"Đã tìm thấy {len(fields)} ô nhập đang hiển thị.")
        print(json.dumps(fields, ensure_ascii=False, indent=2))
        input("Nhấn Enter để đóng Chrome... ")
        raise SystemExit(0)
    current_step = "Điền các trường nội dung"
    filled, skipped, field_selectors = fill_fields(driver)
    current_step = "Chọn đơn vị thực hiện"
    choose_department(driver)
    current_step = "Chọn mã kỹ thuật"
    codes = choose_codes(driver)
    current_step = "Kiểm tra lại dữ liệu trước khi lưu"
    verify_fields(driver, filled, field_selectors)

    if skipped:
        print("Các trường chưa điền được (PHẢI KIỂM TRA THỦ CÔNG):")
        print("\n".join(f"- {x}" for x in skipped))

    print("Đã điền và kiểm tra trường:", ", ".join(filled))
    print("Mã PL1 đã chọn:", ", ".join(codes))
    if args.draft_preview:
        missing_clinical = [
            key for key in (
                "overview", "indications", "contraindications", "precautions", "performer",
                "support_personnel", "drugs", "supplies", "equipment", "patient",
                "records", "duration_hours", "location", "preprocedure_checks", "steps",
                "during_procedure_events", "post_procedure_events", "late_complications"
            ) if key in field_selectors and not str(values.get(key) or "").strip()
        ]
        if missing_clinical:
            print("CÁC MỤC CHƯA ĐỦ CĂN CỨ – ĐỂ TRỐNG, KHÔNG TỰ SUY DIỄN:")
            for key in missing_clinical:
                print("  -", key)
        print("Các trường trống KHÔNG được ghi đè vào biểu mẫu và không được xem là hoàn tất.")
    if not args.save:
        print("CHẾ ĐỘ XEM TRƯỚC: Chương trình KHÔNG bấm Lưu.")
        print("Kiểm tra lại tất cả trường còn trống, đối chiếu hồ sơ và tài liệu đã phê duyệt.")
        if args.draft_preview:
            # Additional UI safeguard; this is only a draft preview, not authorization to save.
            driver.execute_script("""
                const btn = document.querySelector('#qfLuu');
                if (btn) {
                    btn.disabled = true;
                    btn.title = 'Bản nháp chưa thẩm định: không được lưu';
                }
            """)
            report_draft_preview_state(driver, filled, field_selectors)
            print("BẢN NHÁP CHƯA THẨM ĐỊNH: đã vô hiệu hóa nút Lưu trong giao diện hiện tại.")
            print("KHÔNG LƯU dữ liệu lên cổng. Kiểm tra để chuẩn bị duyệt chuyên môn.")
        else:
            print("Bạn có thể tự lưu trong giao diện nếu đã xác minh đầy đủ.")
        input("Nhấn Enter khi đã kiểm tra xong và muốn đóng Chrome... ")
    else:
        if approved_package is not None:
            # Fail closed on any missing approved content or administrative field.
            must_fill = set(REQUIRED_FIELDS) - {"personnel", "references"}
            must_fill.update({"performer", "source", "decision_number", "issue_date", "approver"})
            missing_fields = sorted(must_fill - set(filled))
            if missing_fields:
                raise RuntimeError("Dừng lưu: chưa điền và xác minh đủ trường hồ sơ đã duyệt: " + ", ".join(missing_fields))
            if codes != [approved_package["catalog_code"]]:
                raise RuntimeError("Mã kỹ thuật trên biểu mẫu không khớp hồ sơ được phê duyệt.")
            if not driver.find_element(By.ID, "qfLuu").is_enabled():
                raise RuntimeError("Nút Lưu bị khóa hoặc tài khoản không có quyền thao tác.")
            print("Quyết định bệnh viện:", approved_package["approval"]["decision_number"])
            print("Người xác nhận đối chiếu:", approved_package["approval"]["attested_by"])
            print("Vui lòng đối chiếu trực tiếp tất cả các trường vừa nhập với PDF đã ký.")
            expected_confirmation = "LƯU " + item["id"]
        else:
            if procedure.get("requires_clinical_review", False):
                raise RuntimeError("Quy trình dự thảo chưa được bệnh viện thẩm định; KHÔNG cho phép tự động lưu.")
            if not procedure.get("approved_for_auto_save", False):
                raise RuntimeError("Chưa xác nhận hồ sơ đủ điều kiện lưu tự động; hãy kiểm tra và lưu thủ công.")
            expected_confirmation = "LƯU"
        if skipped:
            raise RuntimeError("Có trường bị bỏ qua; KHÔNG cho phép tự động lưu.")
        confirmation = input(f"Đã đối chiếu xong và đồng ý lưu lên cổng? Nhập đúng {expected_confirmation}: ").strip()
        if confirmation != expected_confirmation:
            print("Không lưu. Biểu mẫu vẫn mở để kiểm tra thủ công.")
            input("Nhấn Enter để đóng Chrome... ")
        else:
            current_step = "Bấm lưu quy trình (đã xác nhận)"
            click_unique(driver, "#qfLuu", "Lưu quy trình")
            current_step = "Chờ xác nhận lưu từ trang"
            message = wait_for_success(driver)
            if message != save_message:
                raise RuntimeError(f"Trang báo trạng thái khác dự kiến: {message}")
            print(message)
            print("Chrome vẫn mở để bạn kiểm tra bản đã lưu.")
            input("Nhấn Enter khi muốn đóng Chrome... ")
except Exception as exc:
    print(f"\nCHƯA XÁC NHẬN LƯU: {exc}")
    print(f"Bước gặp lỗi: {current_step}")
    debug_bundle = save_debug_bundle(driver, exc, current_step)
    if debug_bundle:
        print(f"Tệp chẩn đoán đã lưu tại: {debug_bundle}")
        print("Gồm error.txt, page.html, screenshot.png và browser_console.json; không ghi mật khẩu vào log.")
    print("Biểu mẫu được giữ mở trong Chrome để bạn kiểm tra hoặc sửa.")
    input("Nhấn Enter khi muốn đóng Chrome... ")
finally:
    driver.quit()
