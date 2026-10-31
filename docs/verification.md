# Kết quả kiểm tra thực tế

Kiểm tra ngày **31/10/2026**, trên **Windows 11**, **Python 3.12.0**, **aiocoap 0.4.17**. Các server và client là tiến trình riêng, trao đổi bằng **UDP thật trên 127.0.0.1**. Cổng tạm được chọn để không xung đột với server đang dùng cổng 5683. Khi chạy thông thường, mọi chương trình vẫn mặc định cổng 5683 theo đề.

## Kiểm tra tự động

Lệnh:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Kết quả cuối: **9/9 bài kiểm tra đạt**, thời gian **8.544 giây**. Log nguyên bản: [automated_tests.txt](../evidence/automated_tests.txt). Kiểm tra thư viện bằng `python -m pip check` cũng đạt.

| Nhóm | Nội dung đã xác nhận |
| --- | --- |
| Bài 1 | GET lời chào, POST nhận xác nhận, GET trả thông điệp gần nhất, POST rỗng bị từ chối, URI không tồn tại trả 4.04, CON/NON |
| Cảm biến | JSON Content-Format 50, chọn nhiều thiết bị, giá trị cố định để kiểm tra, dữ liệu cập nhật sau 3 giây dù không có GET ở giữa |
| Cảnh báo | Bình thường tại 35°C/40%, nhiệt độ cao độc lập, độ ẩm thấp độc lập, hai cảnh báo đồng thời, ghi log dữ liệu và thống kê |
| Dữ liệu lỗi | Monitor gặp JSON sai qua UDP thật vẫn báo lỗi và kết thúc hữu hạn đúng cấu hình |
| Điều khiển | PUT hợp lệ, JSON lỗi, object sai dạng, lệnh không hợp lệ, device_id không khớp và Content-Format sai |
| Observe | Hai client đăng ký đồng thời, trạng thái đầu OFF, cùng nhận ON rồi OFF; ON lặp không phát thông báo; monitor dòng lệnh nhận thông báo thật |
| Thiết bị mở rộng | Trạng thái light01, fan01, pump01 độc lập; nhật ký ghi đúng các lần thay đổi |
| Client | Timeout báo lỗi sạch, controller chạy chuỗi lệnh và trả trạng thái chính xác |

## Chạy toàn bộ bảy chương trình để lưu minh chứng

Lệnh tạo lại log:

```powershell
.\.venv\Scripts\python.exe tools/capture_evidence.py
```

Công cụ tự mở server/client cục bộ, kiểm tra đầu ra và ghi vào `evidence/`. Ba file dữ liệu `sensor.csv`, `sensor.jsonl`, `transitions.jsonl` trong thư mục đó được tạo lại mỗi lần chạy. Log bài 1 dùng họ tên/mã sinh viên ví dụ của đề, không phải thông tin cá nhân người thực hiện.

| Kịch bản | Minh chứng |
| --- | --- |
| GET → hai POST → GET thông điệp mới nhất | [Client bài 1](../evidence/bai1_client.txt), [server bài 1](../evidence/bai1_server.txt) |
| URI không tồn tại → 4.04, thoát mã 1 | [Tài nguyên không tồn tại](../evidence/bai1_missing.txt) |
| Server không phản hồi → timeout, thoát mã 1 | [Timeout](../evidence/bai1_timeout.txt) |
| 3 lần đọc cách nhau 3 giây ở 36.1°C/38.7% | [Hai cảnh báo](../evidence/bai2_monitor_alerts.txt), [CSV](../evidence/sensor.csv), [JSONL](../evidence/sensor.jsonl) |
| 35°C/40% không cảnh báo | [Đúng ngưỡng](../evidence/bai2_boundary.txt) |
| Chọn sensor02 và yêu cầu NON | [Sensor02 NON](../evidence/bai2_sensor02_non.txt) |
| Hai monitor đồng thời nhận OFF → ON → OFF | [Monitor 1](../evidence/bai3_observer1.txt), [monitor 2](../evidence/bai3_observer2.txt) |
| Nhập sai lệnh, sau đó ON và STATUS | [Controller tương tác](../evidence/bai3_controller_on.txt) |
| Lặp ON khi đã ON | [PUT ON lặp](../evidence/bai3_repeated_on.txt), đối chiếu hai log monitor |
| STATUS/OFF dùng NON | [Controller NON](../evidence/bai3_controller_non.txt) |
| Điều khiển thêm quạt, bơm | [Fan01](../evidence/bai3_fan01.txt), [pump01](../evidence/bai3_pump01.txt) |
| Server đăng ký Observe và phát cập nhật | [Log server bài 3](../evidence/bai3_server.txt), [nhật ký chuyển trạng thái](../evidence/transitions.jsonl) |

Metadata môi trường và thời điểm ghi log: [environment.json](../evidence/environment.json). Giờ nhận hiển thị theo múi giờ của máy; timestamp trong dữ liệu server dùng UTC với thông tin múi giờ.

## Phạm vi xác nhận

Các kiểm tra này xác nhận vận hành trên cùng máy qua UDP loopback. Hướng dẫn hai máy đã được viết trong README; chưa thử mạng LAN giữa hai máy hoặc điều kiện mất gói thực tế. Công cụ minh chứng và kiểm tra tự động dừng tiến trình server sau mỗi kịch bản; thao tác Ctrl+C thủ công không nằm trong bộ kiểm tra tự động. Các chương trình có khối dọn tài nguyên khi bị hủy hoặc thoát.

Nội dung bắt buộc và các gợi ý mở rộng được đối chiếu tại [requirements.md](requirements.md). Thông tin sinh viên/nhóm chưa được cung cấp nên vẫn để mục điền rõ ràng ở README.
