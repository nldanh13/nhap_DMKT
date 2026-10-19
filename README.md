# Dữ liệu và công cụ điền trước quy trình kỹ thuật

Gói gồm 13 dịch vụ theo dữ liệu bạn cung cấp, người thực hiện được phân theo quy tắc bạn yêu cầu, nguồn Bộ Y tế, dự thảo có thể tham khảo, và đối chiếu danh mục kỹ thuật PL01/PL02. File Excel có 5 tab: `Dịch vụ`, `Dữ liệu biểu mẫu`, `Nguồn`, `Mã kỹ thuật`, `Tình trạng biểu mẫu`.

## Mức độ sẵn sàng

Dữ liệu hiện có **đủ để điền trước một số trường**, chưa đủ để hoàn thành và phê duyệt toàn bộ quy trình. Có thể điền tên dịch vụ, người thực hiện, chuyên khoa, gợi ý loại mẫu, nguồn tham khảo và một số nội dung dự thảo từ tài liệu Bộ Y tế. Các bước chỉ được điền khi có nội dung phù hợp với dịch vụ.

Công cụ chọn PL1, mẫu biểu, cơ quan ban hành và tên mục 6 theo các lựa chọn đã chốt; ghi tên kỹ thuật PL2 ở tab đối chiếu nhưng không tự điền ô PL2 vào hồ sơ hiện hành. Công cụ không chọn kỹ thuật trong cửa sổ danh mục `qfKT`, không tự điền thông tin bệnh viện còn thiếu, và mặc định bỏ chọn ô `Đang triển khai` vì chưa có quyết định phê duyệt phạm vi kỹ thuật. Sau khi chạy, phải kiểm tra dữ liệu và tự quyết định lưu.

### Các lựa chọn đã chốt để điền

- 2 dịch vụ xét nghiệm đường máu chọn mẫu **Xét nghiệm — QĐ 3376/QĐ-BYT**; 11 dịch vụ còn lại chọn **Lâm sàng — QĐ 3023/QĐ-BYT**, theo hướng dẫn ngay trên biểu mẫu. QĐ 3023 và QĐ 3376 là đề cương xây dựng quy trình, không thay thế quy trình thao tác cụ thể.
- Chọn **PL1** cho hồ sơ hiện hành. Theo TT25/2026/TT-BYT, PL1 áp dụng đến hết 31/12/2027; PL2 áp dụng từ 01/01/2028. Công cụ để trống ô chỉ dành cho tên PL2. Mã PL1 đề xuất cho từng dịch vụ được ghi ở cột `Đối chiếu PL01` của tab `Mã kỹ thuật`; mã vẫn cần chọn trong cửa sổ `qfKT`.
- Với dịch vụ thay băng/cắt chỉ **≤15 cm**, đề xuất chọn hai mã thành phần `15.303` và `15.302`. Không chọn `3.3911` để bao phủ cả trường hợp đúng 15 cm vì tên mã đó quy định chiều dài `<15 cm`.
- Chọn cơ quan ban hành **BỆNH VIỆN** vì đây là quy trình nội viện dựa trên tài liệu Bộ Y tế. Tên mục 6 chọn `CÁC BƯỚC TIẾN HÀNH` theo lựa chọn mặc định trên biểu mẫu.
- Công cụ luôn bỏ chọn `Đang triển khai` khi không có bằng chứng phê duyệt của cơ sở.

Các trường cần bệnh viện/khoa cung cấp hoặc xác nhận gồm: đơn vị trong danh mục nội bộ; số quyết định, ngày ban hành, số thứ tự; nhân lực hỗ trợ; thuốc, vật tư, thiết bị theo thực tế; người bệnh, hồ sơ bệnh án, thời gian và địa điểm; kiểm tra hồ sơ; ekip; nội dung tai biến/biến chứng theo mẫu; người viết, người kiểm tra, người phê duyệt và chức danh. Xem tab `Tình trạng biểu mẫu` để biết chi tiết theo từng nhóm ô.

## Chạy bằng Python trên Windows

1. Cài Python 3.10 trở lên và Google Chrome, rồi giải nén ZIP.
2. Mở Command Prompt hoặc PowerShell tại thư mục `qtkt_phanhieu_tool`.
3. Chạy toàn bộ luồng bằng một lệnh:

   ```powershell
   py run_all.py
   ```

   `run_all.py` cài Selenium nếu máy chưa có, tạo/cập nhật CSV, rồi mở Chrome và khởi động công cụ điền trước. Nếu muốn cài thư viện trước, chạy `py -m pip install -r requirements.txt`.
4. Đăng nhập bằng tài khoản của bạn, mở biểu mẫu dịch vụ cần cập nhật. Chọn dịch vụ trong cửa sổ lệnh và kiểm tra nội dung được điền.
5. Chọn mã kỹ thuật trong danh mục `qfKT`, xác minh phạm vi phê duyệt của bệnh viện, rồi tự quyết định lưu.

Muốn kiểm tra các trường của biểu mẫu khi giao diện thay đổi, chạy `py run_all.py --inspect`. Trên macOS/Linux, dùng `python3` thay cho `py`.

## Phân công người thực hiện

Quy tắc phân công áp dụng theo yêu cầu của bạn: dịch vụ nắn chỉnh/bó bột ghi **Phan Văn Hiếu**; các dịch vụ còn lại ghi **BS. Hồ Điền**. Đây là dữ liệu phân công bạn cung cấp, không thay thế việc kiểm tra nhân sự, chức danh và phạm vi hành nghề của bệnh viện.

## Giới hạn nguồn chuyên môn và danh mục

- QĐ 199/QĐ-BYT có hướng dẫn bó bột/nắn chỉnh hình. Một số dịch vụ khớp chủ đề, một số chỉ liên quan kiểu gãy hoặc loại bột cụ thể; `match_status` trong dữ liệu nêu mức độ.
- QĐ 1904/QĐ-BYT có kỹ thuật thử đường máu mao mạch và quy trình thay băng trong phạm vi hồi sức-cấp cứu-chống độc. Phạm vi này không tự động áp dụng cho khoa ngoại.
- QĐ 3671/QĐ-BYT có hướng dẫn phòng ngừa nhiễm khuẩn vết mổ và lưu ý thay băng; đây không phải quy trình cắt chỉ độc lập.
- Chưa tìm thấy quy trình Bộ Y tế khớp trực tiếp cho dịch vụ cắt chỉ sau phẫu thuật và nắn trật khớp cổ chân. Công cụ không tự tạo bước thực hiện cho hai dịch vụ này.
- Tám dịch vụ nắn/bó bột có tên/mã danh mục tương ứng; hậu tố `[bột liền]` là mô tả dịch vụ của cơ sở. Dịch vụ đo đường máu có tên PL01 khớp nhưng chưa tìm thấy mục tương ứng PL02 trong tệp đã tra. Dịch vụ thay băng chiều dài `≤15cm` gần khớp các dòng `<15cm`; trường hợp đúng 15cm và dịch vụ gộp cắt chỉ cần đơn vị quản lý danh mục kỹ thuật xác định mã.
- Tại ngày 03/10/2026, theo TT25/2026/TT-BYT, PL01 tiếp tục áp dụng đến hết 31/12/2027, PL02 áp dụng từ 01/01/2028. Mã PL02 trong gói là dữ liệu đối chiếu cho danh mục tương lai, không chứng minh bệnh viện đã phê duyệt triển khai.

## Tự động điền

`run_all.py` điều phối tạo CSV và chạy `autofill_portal.py`; Selenium được cài nếu chưa có. `autofill_portal.py` chỉ điền các trường đã cấu hình; mặc định không tự lưu biểu mẫu. Dùng `--inspect` để kiểm tra nhãn/trường khi giao diện thay đổi.

Nếu Chrome không mở được, cập nhật Chrome và thử `py -m pip install --upgrade selenium`.

## Nguồn chính thức

- Bộ Y tế, QĐ 3023/QĐ-BYT ngày 28/07/2023 — Đề cương quy trình kỹ thuật khám bệnh, chữa bệnh: [Sở Y tế Gia Lai](https://syt.gialai.gov.vn/vi/download/Thu-vien-Huong-dan-chan-doan-dieu-tri-Quy-trinh-ky-thuat-va-cac-Tai-lieu-chuyen-mon-kham-chua-benh/Quyet-dinh-so-3023-QD-BYT-ngay-28-07-2023-Ve-viec-ban-hanh-De-cuong-tai-lieu-chuyen-mon-Huong-dan-quy-trinh-ky-thuat-kham-benh-chua-benh.html).
- Bộ Y tế, QĐ 3376/QĐ-BYT ngày 30/08/2023 — Đề cương quy trình kỹ thuật xét nghiệm: [PDF tại Bệnh viện Đa khoa Sa Đéc](https://bvdksadec.vn/Uploads/files/XN-2023_%20QD%203376%20QD-BYT_2023_ban_hanh_De-cuong_quy_trinh_ky_thuat_xet_nghiem.pdf).
- Bộ Y tế, QĐ 199/QĐ-BYT ngày 16/01/2014 — Hướng dẫn quy trình kỹ thuật chuyên ngành Ngoại khoa, chuyên khoa Nắn chỉnh hình, bó bột: [PDF](https://kcb.vn/upload/2005611/20210723/B%C3%B3-B%E1%BB%99t.pdf).
- Bộ Y tế, QĐ 1904/QĐ-BYT ngày 30/05/2014 — Hướng dẫn quy trình kỹ thuật Hồi sức, Cấp cứu và Chống độc: [PDF](https://kcb.vn/upload/2005611/20210723//H%E1%BB%93i-s%E1%BB%A9c-c%E1%BA%A5p-c%E1%BB%A9u-Ch%E1%BB%91ng-%C4%91%E1%BB%99c.pdf).
- Bộ Y tế, QĐ 3671/QĐ-BYT ngày 27/09/2012 — Hướng dẫn phòng ngừa nhiễm khuẩn vết mổ: [PDF](https://kcb.vn/upload/2005611/20210723//H%C6%B0%E1%BB%9Bng-d%E1%BA%ABn-ph%C3%B2ng-ng%E1%BB%ABa-nhi%E1%BB%85m-khu%E1%BA%A9n-v%E1%BA%BFt-m%E1%BB%95.pdf).
- Bộ Y tế, TT 23/2024/TT-BYT — Danh mục kỹ thuật; [văn bản và Phụ lục 01/02](https://vanban.chinhphu.vn/?classid=1&docid=211508&pageid=27160).
- Bộ Y tế, TT 25/2026/TT-BYT — sửa thời điểm áp dụng TT23; [văn bản](https://vanban.chinhphu.vn/?classid=0&docid=218704&pageid=27160).

## Chẩn đoán lỗi Selenium

- Script in từng bước đang chạy và từng trường đã điền.
- Khi có lỗi, Chrome được giữ mở để kiểm tra; đồng thời tạo thư mục `debug/YYYYMMDD_HHMMSS/` cạnh script.
- Gói debug gồm `error.txt` (bước lỗi và traceback), `page.html` (DOM tại thời điểm lỗi), `screenshot.png` và `browser_console.json`.
- Không có mật khẩu trong log. Nếu cần gửi để kiểm tra, nén đúng thư mục thời gian vừa tạo trong `debug`.

### Giữ thông tin đăng nhập đã lưu

Gói cập nhật không kèm `login.json`. Khi chép bản mới vào máy, giữ nguyên `login.json` hiện có trong thư mục chương trình để bảo toàn tài khoản, đơn vị và mật khẩu đã mã hóa. Nếu đây là lần chạy đầu tiên, chương trình sẽ tự tạo tệp này sau khi nhập thông tin đăng nhập.


## Bản vá an toàn và dự thảo 8 QTKT (18/10/2026)

- Lệnh `py run_all.py` chỉ **điền trước và mở biểu mẫu để kiểm tra**, không tự bấm Lưu.
- `py run_all.py --save` chỉ cho phép lưu sau khi người dùng gõ `LƯU`, các trường được điền đã xác minh, dịch vụ **không** bị đánh dấu `requires_clinical_review` và **đã được đơn vị phê duyệt** qua `approved_for_auto_save=true`. Mặc định không dịch vụ nào được bật cờ này.
- Tám kỹ thuật nắn, bó bột có nội dung **dự thảo riêng** ở `data/clinical_drafts.json` và `data/procedures.json`. Các phần lâm sàng chưa được duyệt **không** tự điền vào cổng. Đề nghị bệnh viện thẩm định từng thủ thuật, duyệt định mức thuốc/vật tư và phê duyệt phạm vi kỹ thuật trước sử dụng.
- Trật khớp cổ chân chưa có quy trình nắn độc lập đã được xác minh trong bộ tài liệu; tuyệt đối không suy diễn động tác nắn từ quy trình bó bột.
- Chỉ các selector xác nhận trên giao diện mới được phép dùng. `--inspect` in thêm `data-qf` để phục vụ đối chiếu; không tự đoán selector cho các trường 5.1–5.9 và 7.1–7.3.
- Tệp `login.json` chỉ dùng trên máy cá nhân và được bỏ theo dõi Git (`git rm --cached login.json`); phải tự xử lý bản sao còn tồn tại trong lịch sử các commit cũ và cân nhắc đổi mật khẩu nếu từng đẩy thông tin xác thực lên repository công khai.
- Thư mục `debug/` chứa HTML, ảnh màn hình và log có khả năng lộ dữ liệu hồ sơ; không tải lên GitHub và không chia sẻ khi chưa ẩn thông tin người bệnh.
- Kiểm tra dữ liệu offline: `py -m unittest discover -s tests -v`.


## Kiểm tra dữ liệu trực tiếp từ PowerShell (không dùng Chrome DevTools)

Sau khi chạy `python run_all.py --id bot_trat_khuyu --draft-preview`, công cụ tự đọc giá trị `element.value` và trạng thái checkbox/nút Lưu trong DOM hiện tại. PowerShell sẽ in nhóm `KIỂM TRA TRỰC TIẾP TỪ CHROME` với **số ký tự** của các ô đã điền, `Đang triển khai: KHÔNG đánh dấu` và `Nút Lưu: ĐÃ VÔ HIỆU HÓA`. Công cụ không in nội dung chuyên môn ra báo cáo này và không lưu lên cổng. Các thông số này chỉ xác nhận thao tác nhập và trạng thái giao diện, không thay thế việc kiểm tra chuyên môn.

Không dán mã không hiểu vào Console để vượt cảnh báo bảo mật `Don't paste code`. Cảnh báo `favicon.ico: 404` chỉ liên quan biểu tượng website, không phản ánh kết quả tự động nhập. Cảnh báo `Chưa nhúng dữ liệu danh mục` do website phát ra, không thể khắc phục chỉ bằng sửa script Selenium; nếu tra mã kỹ thuật thất bại cần liên hệ quản trị cổng.

Mục 5.1 của 8 quy trình nháp ghi **cơ cấu nhân lực theo chức danh**, không tự động kèm tên người được phân công. Trong chế độ điền thông thường, trường nhân lực của 8 quy trình chưa thẩm định được để cho người rà soát hoàn thiện.

## Đối chiếu nguồn Bộ Y tế cho 8 QTKT (19/10/2026)

Các nội dung được đối chiếu với **QĐ 199/QĐ-BYT năm 2014**, **QĐ 5728/QĐ-BYT năm 2017**; **QĐ 3023/QĐ-BYT năm 2023** dùng để chuẩn hóa cấu trúc nhập biểu mẫu.

- PDF QĐ 199: https://kcb.vn/upload/2005611/20210723/B%C3%B3-B%E1%BB%99t.pdf
- Văn bản QĐ 5728: https://thuvienphapluat.vn/van-ban/The-thao-Y-te/Quyet-dinh-5728-QD-BYT-2017-quy-trinh-ky-thuat-Ngoai-khoa-chuyen-khoa-Chan-thuong-chinh-hinh-370394.aspx
- PDF đề cương QĐ 3023: https://static.luatvietnam.vn/uploaded/VIETLAWFILE/2023/8/3023_QD-BYT_020823144557.pdf

| ID | Nguồn phù hợp | Phạm vi đối chiếu |
| --- | --- | --- |
| `bot_hai_xuong_cang_tay_duoi` | QĐ 199, Bài 29 và 3 | Nắn gãy thân hai xương cẳng tay, bao gồm vị trí 1/3 dưới; bó bột cánh–cẳng–bàn tay |
| `bot_mot_xuong_cang_tay` | QĐ 199, Bài 3 | **Chỉ có nguồn bó bột**, chưa xác minh bài nắn riêng một xương |
| `bot_xuong_ban_chan` | QĐ 199, Bài 10 | **Chỉ có nguồn bó bột**, không tự nhận thao tác nắn đã được mô tả |
| `bot_xuong_chay` | QĐ 199, Bài 40 và 11 | Nắn và bó bột gãy cẳng chân có liên quan xương chày |
| `bot_xuong_got` | QĐ 199, Bài 41 | Nắn/bó gãy xương gót theo **từng dạng gãy**; có trường hợp chỉ băng ép, không nắn |
| `bot_xuong_ngon_chan` | QĐ 199, Bài 10 | **Chỉ có nguồn bó bột** cho gãy ngón, chưa xác minh bài nắn riêng |
| `bot_trat_co_chan` | QĐ 199, Bài 10 (bột); QĐ 5728, Bài 34 (khác tổn thương) | **Chưa có nguồn nắn trật khớp cổ chân đơn thuần trùng phương pháp**, giữ trống thao tác |
| `bot_trat_khuyu` | QĐ 5728, Bài 32; QĐ 199, Bài 18 | Nắn trật khớp khuỷu, nhân lực, vật tư và thời gian thực hiện |

Dữ liệu truy vết chi tiết tại `data/clinical_review_notes.json`, bao gồm loại độ phù hợp, số quyết định, bài, link và các phạm vi **chưa được chứng minh**. Nội dung QTKT được lưu ở `data/clinical_drafts.json`, đồng bộ vào `data/procedures.json` để xem trước trên DMKT.

Tài liệu Bộ Y tế **không tự động giải quyết việc phê duyệt quy trình nội viện**; Điều 2 QĐ 199 yêu cầu người đứng đầu cơ sở xây dựng và ban hành tài liệu phù hợp điều kiện đơn vị. Vì vậy cờ `requires_clinical_review` và khóa tự lưu được giữ nguyên đến khi có thẩm quyền quyết định.

Cách xem trước một quy trình **không tự lưu**:

```powershell
git pull --ff-only origin main
python -m unittest discover -s tests -v
python run_all.py --id bot_trat_khuyu --draft-preview
```

## Dành cho người được giao NHẬP QTKT, sau đó người khác duyệt

**Nếu quy trình làm việc trên cổng của bệnh viện là nhập → bấm Lưu → người có thẩm quyền kiểm tra/duyệt**, dùng chế độ `--all-for-review` thay vì `--all-approved`. Chế độ này dùng 8 bản dự thảo đã đối chiếu nguồn BYT, **không yêu cầu số quyết định phê duyệt của bệnh viện, không coi bản nháp là bản đã được phê duyệt**.

Kiểm tra xem 8 bản nháp đã đủ dữ liệu nhận diện chưa và đọc danh sách các mục còn thiếu (không mở Chrome, không lưu):

```powershell
cd E:\DMKT
git pull --ff-only origin main
python run_all.py --all-for-review
```

Khi đã xác nhận nút **Lưu** trên cổng **chỉ lưu dữ liệu để chuyển cho người khác duyệt** và bạn được giao nhập 8 bản đó, chạy:

```powershell
python run_all.py --all-for-review --save
```

Chương trình báo các mục thiếu của từng kỹ thuật; bạn xác nhận bằng cách nhập đúng `LƯU 8 BẢN NHÁP CHỜ DUYỆT` một lần. Selenium lần lượt đăng nhập, tạo QTKT, điền những trường có dữ liệu, chọn mã PL1, để **Đang triển khai** bỏ chọn, kiểm tra dữ liệu và bấm Lưu. Không tự điền số quyết định, ngày ban hành, người phê duyệt hoặc biến bản nháp thành bản được duyệt. Nếu cổng báo lỗi, nếu đã tồn tại quy trình cùng tên hoặc nếu một mục không lưu được, chương trình dừng để tránh trùng; báo cáo đặt tại `output/qtkt_batch_*.json`.

**Giới hạn nội dung:** ba QTKT gãy một xương cẳng tay, xương bàn chân, ngón chân mới xác minh rõ phần bó bột, còn thiếu nguồn nắn riêng; đặc biệt trật khớp cổ chân đang thiếu nội dung nắn, chỉ định và nhiều mục khác. Chế độ gửi duyệt để các chuyên gia hoàn thiện, không dùng như hướng dẫn điều trị chính thức. Trang có thể từ chối lưu nếu yêu cầu trường bắt buộc còn trống; chương trình không tự bịa để bỏ qua kiểm tra. Dữ liệu đã bấm Lưu **không tự động trở thành đã phê duyệt**; phải kiểm tra trạng thái tiếp nhận với người duyệt trên cổng. Nếu nút Lưu trên website lại công bố/ban hành ngay, **không sử dụng lệnh gửi duyệt**.

Xem trước một kỹ thuật mà không lưu vẫn dùng:

```powershell
python run_all.py --id bot_trat_khuyu --draft-preview
```

Không cần điền hoặc sửa 8 tệp `local_approved/*.approved-qtkt.json` được tạo trước đó để **gửi bản nháp cho người khác duyệt**; các tệp đó chỉ phục vụ chế độ lưu hồ sơ *đã phê duyệt thực tế*.

## Nhập hàng loạt QTKT bằng MỘT lệnh

Sau khi đã có **từng QTKT bệnh viện phê duyệt** ở thư mục cục bộ `local_approved/`, dùng `--all-approved` trên `run_all.py`. Mặc định nhóm `casts` là **8 kỹ thuật nắn, bó bột** đã biên tập. Công cụ không tự lấy bản nháp làm tài liệu đã phê duyệt và không bấm Lưu khi chưa đủ hồ sơ.

**Tạo 8 khung JSON trống (mỗi dịch vụ một tệp):**

```powershell
cd E:\DMKT
python run_all.py --all-approved --init-templates
```

Mỗi khung nằm ở `local_approved\\<ID>.approved-qtkt.json`, đã có đúng ID, mã PL1 và tên kỹ thuật. Trường nội dung ban đầu chỉ là **chỗ trống**: phải điền chính xác từ QTKT bệnh viện đã ký duyệt, bổ sung số/ngày quyết định, người ký, người đối chiếu và PDF nguồn. Không sử dụng nội dung nguồn `data/clinical_drafts.json` để tự đánh dấu đã phê duyệt. Chạy lần lượt `python approved_package.py local_approved\\<ID>.approved-qtkt.json --seal-checksums` sau khi đối chiếu PDF từng tệp.

**Kiểm tra đủ 8 hồ sơ trước khi đăng nhập (không lưu):**

```powershell
python run_all.py --all-approved
```

Nếu bất kỳ hồ sơ nào thiếu, sai mã danh mục, chưa có dấu vân tay hoặc tệp PDF thay đổi, chương trình **không chạy Chrome và không lưu bản nào**. Hãy sửa và thử lại.

**Nhập và lưu tự động cả 8 trong một lượt:**

```powershell
python run_all.py --all-approved --save
```

Khi cả 8 gói đạt kiểm tra ngoại tuyến, chương trình liệt kê đúng 8 dịch vụ và yêu cầu nhập **`LƯU TẤT CẢ 8`**. Sau một lần xác nhận, Selenium đăng nhập/mở biểu mẫu, nhập dữ liệu, đối chiếu từng trường và lưu lần lượt. Mỗi lần thành công chỉ được ghi nhận khi website báo đã thêm quy trình; Chrome tự đóng để chuyển sang kỹ thuật kế tiếp. Nếu gặp lỗi hay QTKT cùng tên đã tồn tại, chương trình **dừng ngay** và báo các mục chưa chạy; không âm thầm bỏ qua. Báo cáo cục bộ nằm trong `output/qtkt_batch_*.json` (Git ignore).

**Các phạm vi:**

- `--scope casts` (mặc định): 8 QTKT nắn, bó bột.
- `--scope clinical`: 11 QTKT mẫu lâm sàng; sẽ không lưu nếu thiếu bộ hồ sơ hoặc dịch vụ có nhiều mã PL1 chưa được giải quyết.
- `--scope all`: kiểm tra cả 13; **2 dịch vụ xét nghiệm dùng mẫu QĐ 3376 chưa được chức năng lưu đã duyệt hỗ trợ** nên phạm vi này sẽ báo không đủ điều kiện và không lưu. Không được ép xét nghiệm vào mẫu lâm sàng.

Cơ chế này không xác thực tính hợp pháp của chữ ký bệnh viện hoặc chứng minh văn bản sao chép đúng từ PDF: người phụ trách vẫn phải đối chiếu bộ hồ sơ chính thức. Không chạy thử với quyết định Bộ Y tế để giả làm quyết định bệnh viện. Nếu thao tác lưu trên cổng trả trạng thái bất định, kiểm tra danh mục trực tiếp trước khi chạy lại để tránh trùng.

## Tự động nhập và lưu QTKT đã được bệnh viện phê duyệt

**Không dùng dữ liệu nháp trong `data/clinical_drafts.json` để lưu.** Chế độ `--save` chỉ chấp nhận một gói JSON riêng được biên soạn **từ bản QTKT đã được bệnh viện ký duyệt**, kèm PDF quyết định và quy trình gốc, mã kỹ thuật PL1, số/ngày quyết định và thông tin người phê duyệt. Chương trình kiểm tra dữ liệu, checksum, trạng thái biểu mẫu và yêu cầu người phụ trách xác nhận riêng từng lần lưu.

1. Đặt PDF có **quyết định bệnh viện và nội dung QTKT đã duyệt** ở `E:\DMKT\local_approved\`. Đây là dữ liệu cá nhân của bệnh viện, **KHÔNG commit lên GitHub**.
2. Sao chép `examples/approved_qtkt.template.json` vào cùng thư mục với tên `bot_trat_khuyu.approved-qtkt.json`.
3. Sửa tất cả trường trong `approval`: số quyết định, ngày ban hành (`YYYY-MM-DD`), tên kỹ thuật trùng PL1, họ tên người phê duyệt, tên người đã đối chiếu nội dung, đường dẫn PDF đã ký. Có thể bổ sung số thứ tự trong quyết định (`serial_number`), người viết/kiểm tra và chức danh (`writer`, `writer_title`, `reviewer`, `reviewer_title`, `approver_title`) **khi những thông tin này có trong hồ sơ được duyệt**. Điền chính xác nội dung từng mục `content` theo QTKT bệnh viện đã phê duyệt; **không lấy nội dung dự thảo hiện có để điền tắt**. `drugs` và `support_personnel` có thể để trống nếu bản chính thức không quy định; các mục còn lại phải có nội dung. Tên chức danh/ê-kíp tại mục `personnel` không phải tên người nhận phân công.
4. Sau khi người phụ trách đã đối chiếu JSON với PDF bệnh viện, chạy lệnh kiểm tra checksum:

```powershell
cd E:\DMKT
python approved_package.py local_approved\bot_trat_khuyu.approved-qtkt.json --seal-checksums
```

5. Chạy tự động nhập và lưu:

```powershell
python run_all.py --id bot_trat_khuyu --approved-package local_approved\bot_trat_khuyu.approved-qtkt.json --save
```

Nếu hồ sơ hợp lệ và trên cổng chưa có quy trình cùng tên, Selenium sẽ đăng nhập, chọn kỹ thuật theo mã PL1, điền nội dung **từ gói được duyệt**, số và ngày quyết định, người phê duyệt, đối chiếu giá trị DOM. Bạn kiểm tra lần cuối trên Chrome và phải nhập **`LƯU bot_trat_khuyu`** trong PowerShell để chương trình bấm Lưu. Nếu cổng không báo thành công, chương trình không khẳng định đã lưu.

**Cảnh báo kỹ thuật:** SHA256 chỉ kiểm tra PDF/JSON **không bị sửa sau khi người phụ trách chốt**; không chứng thực chữ ký điện tử, thẩm quyền phê duyệt hoặc sự tương đồng giữa PDF và văn bản trích. Người nhập chịu trách nhiệm xác nhận hồ sơ thực sự đã được ký, có hiệu lực và nội dung JSON khớp chính xác. Công cụ không tự sinh một quyết định phê duyệt. Trên cổng nếu đã tồn tại QTKT cùng tên, chương trình dừng, không ghi đè vì cần kiểm tra phiên bản và quyền cập nhật.

Để nhập nhiều QTKT: chuẩn bị **một bộ PDF + JSON cho mỗi kỹ thuật**, lần lượt chạy với `--id` tương ứng và xác nhận từng bản. Không chạy `--save` với `--draft-preview`; khi chỉ dùng `--draft-preview` thì vẫn là xem nháp và không lưu. Trường “Đang triển khai” vẫn không được tự đánh dấu — trạng thái phê duyệt QTKT không đồng nghĩa bệnh viện đã phê duyệt triển khai danh mục kỹ thuật.

## Biên tập lại 8 nội dung QTKT và theo dõi thẩm định

Dữ liệu 8 quy trình nắn, bó bột trong `data/clinical_drafts.json` và `data/procedures.json` đã được tách thành nội dung nhập cổng và ghi chú thẩm định riêng trong `data/clinical_review_notes.json`.

- Nội dung QTKT tuân theo thứ tự các mục QĐ 3023/QĐ-BYT năm 2023: đại cương, chỉ định, chống chỉ định, thận trọng, chuẩn bị, tiến hành và theo dõi, xử trí tai biến. Các nguồn mô tả kỹ thuật chính là QĐ 199/QĐ-BYT năm 2014 và QĐ 5728/QĐ-BYT năm 2017 khi phù hợp.
- Không chèn các nhãn `[BỔ SUNG/ĐỀ XUẤT]`, `[KHUNG]`, `[CHỜ THẨM ĐỊNH]` vào nội dung QTKT. Các điểm chưa xác minh và dữ liệu gốc đã chuyển sang `data/clinical_review_notes.json`.
- Mục 5.2 không tự điền thuốc vô cảm, vì theo QĐ 3023 những thuốc và phương tiện này thuộc quy trình vô cảm riêng. Chỉ ghi thuốc trực tiếp cho kỹ thuật khi đã xác minh đủ thông tin.
- Mục 5.7 chỉ có thời gian dự kiến cho trật khớp khuỷu khi có nguồn hỗ trợ; các mục thời gian còn lại và mục địa điểm chưa xác định được để trống. Nhân lực hỗ trợ và định mức chưa xác minh không được tự tạo.
- Trật khớp cổ chân chưa có quy trình nắn đơn thuần được xác minh, nên nội dung kỹ thuật và định mức không tự bịa; cần chuyên gia hoàn thiện trước khi trình duyệt.
- Khi xem trước `--draft-preview`, chương trình chỉ điền trường đã có nội dung và **liệt kê các trường chưa có căn cứ**; không dùng `--save`.
- `make_clinical_drafts.py` là công cụ nhập lại bản Word cũ. Mặc định dừng để tránh ghi đè bản đã biên tập; chỉ sử dụng `--force-source-import` khi thật sự muốn thay thế dữ liệu và đã sao lưu.

Lệnh thử tại máy:

```powershell
git pull --ff-only origin main
python -m unittest discover -s tests -v
python run_all.py --id bot_trat_khuyu --draft-preview
```

**Lưu ý:** Chỉnh sửa văn phong và tự động điền biểu mẫu không đồng nghĩa thẩm định chuyên môn hay phê duyệt ban hành. Phải có xác nhận của chuyên khoa và bệnh viện trước khi lưu quy trình chính thức lên cổng.

## Xem trước nội dung 8 quy trình trên biểu mẫu (19/10/2026)

Sau khi đã thẩm định dữ liệu dự thảo, có thể dùng chế độ **xem trước có nhập dữ liệu vào biểu mẫu** để kiểm tra bố cục các ô. Chế độ này chỉ hiển thị nội dung chưa được duyệt trong phiên Chrome hiện tại, **không được bấm Lưu, không phải văn bản được phê duyệt**. Phải đóng biểu mẫu mà không lưu và không sử dụng nội dung dự thảo làm chỉ định lâm sàng.

```powershell
python run_all.py --id bot_trat_khuyu --draft-preview
```

Khi được yêu cầu, nhập đúng `XEM` để xác nhận đang kiểm tra bản nháp. Chương trình sử dụng các thuộc tính `data-qf` đã kiểm chứng từ `--inspect` để điền Đại cương, Chỉ định, Chống chỉ định, Thận trọng, hai nhóm nhân lực, thuốc, vật tư, thiết bị, người bệnh, hồ sơ, thời gian, địa điểm, kiểm tra hồ sơ, các bước thực hiện và ba nhóm tai biến/biến chứng. Các trường không có dữ liệu được để trống để người có thẩm quyền kiểm tra.

**Bảo vệ chống lưu nháp:** không thể ghép `--draft-preview` với `--save`; chương trình vô hiệu hóa nút Lưu trong giao diện đang xem sau khi điền. Nếu trang tự tải lại, trạng thái nút có thể thay đổi, nên người dùng vẫn phải tránh lưu. Cờ `requires_clinical_review` và danh sách trường cho phép tự điền ở chế độ thường không bị thay đổi. Chế độ `--inspect` tiếp tục chỉ đọc trường và không viết dữ liệu.

Cấu hình trường `selectors.json` dựa trên danh sách 46 ô trả về trực tiếp từ website trong phiên người dùng đã kiểm tra. Không dùng XPath vị trí dạng `tr[20]` hoặc `div[23]` vì giao diện có thể thay đổi. Mã dịch vụ được chọn bằng mã PL01 có kiểm tra trùng khớp; không dùng chuỗi click thủ công cố định.

Để chạy phiên chỉ điền thông tin đã được cho phép như trước, không thêm tùy chọn `--draft-preview`:

```powershell
python run_all.py --id bot_trat_khuyu
```

**Quan trọng:** Đối với kỹ thuật trật khớp cổ chân, bước nắn độc lập chưa có nguồn Bộ Y tế phù hợp được xác minh. Dù bản nháp được trình bày trên biểu mẫu, không được phê duyệt hoặc sử dụng nếu chưa có chuyên gia chuyên khoa thẩm định, bổ sung căn cứ.
