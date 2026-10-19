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
    review_batch = "--all-for-review" in batch_args
    if approved_batch and review_batch:
        raise SystemExit("Chỉ chọn một chế độ: --all-approved hoặc --all-for-review.")
    if approved_batch or review_batch:
        batch_args.remove("--all-approved" if approved_batch else "--all-for-review")
        if any(arg in batch_args for arg in ("--draft-preview", "--id", "--approved-package", "--submit-for-review")):
            raise SystemExit("Chế độ hàng loạt không dùng cùng --draft-preview, --id, --approved-package, --submit-for-review.")
        if review_batch:
            if "--scope" in batch_args or "--init-templates" in batch_args or "--approved-dir" in batch_args:
                raise SystemExit("--all-for-review chỉ dùng cho 8 QTKT nắn bó bột; không cần mẫu hồ sơ đã duyệt.")
            batch_args.insert(0, "--for-review")
    if not (approved_batch or review_batch) or "--save" in batch_args:
        ensure_selenium()
    print("Bước 1/2: tạo/cập nhật file CSV dữ liệu...")
    run([sys.executable, str(ROOT / "prepare_data.py")])
    if approved_batch or review_batch:
        if review_batch:
            print("Bước 2/2: kiểm tra/nhập 8 QTKT chưa duyệt để chuyển người khác thẩm định...")
        else:
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
