# Gói sửa an toàn dự án `nhap_DMKT` (18/10/2026)

Gói này là **bản vá cần áp dụng vào thư mục clone GitHub**, không phải toàn bộ source của dự án. Không chứa dữ liệu đăng nhập. Bản vá **không tự đẩy mã lên GitHub** và **không xóa tệp `login.json` trên máy**.

## Sửa những gì?

1. Chuyển chế độ mặc định của `autofill_portal.py` sang **xem trước, không tự bấm Lưu**.
2. `--save` yêu cầu nhập `LƯU` và chỉ áp dụng khi hồ sơ không cần thẩm định, đã đặt `approved_for_auto_save=true` bằng quy trình kiểm soát nội bộ, không có trường bị bỏ qua.
3. Bổ sung lớp dữ liệu dự thảo riêng của 8 thủ thuật từ Word: 1. Đại cương đến 7.3. Biến chứng muộn, kèm nguồn. **Chưa tự đẩy nội dung chuyên môn dự thảo lên cổng**.
4. Thêm tài liệu nguồn QĐ 5728/QĐ-BYT cho kỹ thuật trật khớp khuỷu.
5. Giữ bí mật `login.json`, không còn Git theo dõi tệp này ở các commit tiếp theo; thêm `.gitignore` cho `debug/` và backup.
6. Xử lý ảnh chụp DOM lỗi nhằm tránh lưu bản HTML gốc chưa che thông tin đăng nhập.
7. Bổ sung bộ kiểm thử dữ liệu và GitHub Actions.

## Cài đặt (Windows / PowerShell)

Nếu chưa clone repo:

```powershell
git clone https://github.com/nldanh13/nhap_DMKT.git
cd nhap_DMKT
git switch -c fix/qtkt-safe-autofill
```

Giải nén `nhap_DMKT_fix_package.zip` sang thư mục bên cạnh, ví dụ `C:\Temp\nhap_DMKT_fix_package`.

```powershell
py C:\Temp\nhap_DMKT_fix_package\apply_fixes.py . --dry-run
py C:\Temp\nhap_DMKT_fix_package\apply_fixes.py .
py -m unittest discover -s tests -v
git status
git diff --stat
git diff --cached --stat
```

Đọc kỹ chênh lệch và xác nhận dữ liệu. Nếu ổn, tạo commit và đẩy lên một nhánh sửa đổi:

```powershell
git add -A
git commit -m "fix: safe preview and review-gated QTKT drafts"
git push -u origin fix/qtkt-safe-autofill
```

Mở Pull Request tới nhánh `main`, xem lại từng tệp và chỉ merge sau khi được kiểm tra. Tệp `login.json` vẫn tồn tại trên máy nhưng sẽ không còn được Git theo dõi; việc xóa khỏi commit mới không xóa bản cũ trong lịch sử công khai. **Đổi mật khẩu thật nếu đã từng lưu trong tệp đó và trao đổi với quản trị viên Git về xử lý lịch sử**. Không tự force-push làm mất lịch sử làm việc của người khác.

## Chạy chương trình sau khi sửa

```powershell
py run_all.py --id bot_trat_khuyu
```

Lệnh trên chỉ điền trường an toàn; nội dung chuyên môn dự thảo cần được phê duyệt và nhập/kiểm tra thủ công. `--inspect` dùng khi cần đối chiếu phần tử của giao diện hiện tại. Không dùng `--save` cho 8 dự thảo chưa thẩm định.

## Ghi chú giới hạn

- Dữ liệu dự thảo được trích từ bản Word đã tạo trong cuộc hội thoại này; bản Word **không phải** văn bản do Bộ Y tế ban hành.
- Quy trình trật khớp cổ chân chưa có nguồn nắn độc lập đã xác minh: hồ sơ vẫn yêu cầu thẩm định đặc biệt.
- Không đủ quyền vào cổng đích để chạy kiểm thử Selenium thật. Chỉ có thể kiểm tra cú pháp và tính nhất quán dữ liệu offline.
- Nếu `--dry-run` báo không nhận diện được đoạn mã, không sửa bằng cách đoán: nhánh GitHub đã thay đổi và bản vá cần đối chiếu lại.
- Script sao lưu mã nguồn trước khi sửa vào `.qtkt_fix_backup/` (bị Git bỏ qua).
