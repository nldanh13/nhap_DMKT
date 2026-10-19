"""Prepare the data, install Selenium if needed, then launch the form prefill tool."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def run(command: list[str]) -> None:
    subprocess.run(command, cwd=ROOT, check=True)


def ensure_selenium() -> None:
    try:
        import selenium  # noqa: F401
    except ImportError:
        print("Chưa có Selenium. Đang cài thư viện từ requirements.txt...")
        run([sys.executable, "-m", "pip", "install", "-r", str(ROOT / "requirements.txt")])


def main() -> int:
    batch_args = list(sys.argv[1:])
    approved_batch = "--all-approved" in batch_args
    if approved_batch:
        batch_args.remove("--all-approved")
        if "--draft-preview" in batch_args or "--id" in batch_args or "--approved-package" in batch_args:
            raise SystemExit("Chế độ --all-approved không dùng cùng --draft-preview, --id hoặc --approved-package.")
    if not approved_batch or "--save" in batch_args:
        ensure_selenium()
    print("Bước 1/2: tạo/cập nhật file CSV dữ liệu...")
    run([sys.executable, str(ROOT / "prepare_data.py")])
    if approved_batch:
        print("Bước 2/2: kiểm tra/lưu hàng loạt QTKT bệnh viện đã phê duyệt...")
        run([sys.executable, str(ROOT / "batch_portal.py"), *batch_args])
    else:
        print("Bước 2/2: mở công cụ điền trước biểu mẫu...")
        run([sys.executable, str(ROOT / "autofill_portal.py"), *batch_args])
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as exc:
        raise SystemExit(exc.returncode or 1)
