# Log minh chứng

Các file trong thư mục này được thu từ chương trình chạy thật, dùng UDP trên máy local. Tên sinh viên và mã sinh viên là dữ liệu ví dụ. Đọc [kết quả kiểm tra](../docs/verification.md) để xem từng kịch bản và file tương ứng.

- `automated_tests.txt`: kết quả 9 kiểm tra tích hợp.
- `bai1_*.txt`: GET/POST, thông điệp gần nhất, 4.04 và timeout.
- `bai2_*.txt`, `sensor.csv`, `sensor.jsonl`: cảm biến, ngưỡng cảnh báo, chọn thiết bị và lưu dữ liệu.
- `bai3_*.txt`, `transitions.jsonl`: điều khiển, hai client Observe, CON/NON và nhiều thiết bị.
- `environment.json`: phiên bản và thời điểm chạy.

Tạo lại minh chứng từ thư mục gốc:

```powershell
.\.venv\Scripts\python.exe tools/capture_evidence.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -v 2>&1 | Tee-Object -FilePath evidence/automated_tests.txt
```

Log dùng cổng tạm để tránh xung đột, còn ứng dụng mặc định cổng UDP 5683. Script minh chứng tự đóng các tiến trình server sau khi hoàn thành. Các dòng `Command:` là mô tả đối số đã chạy; dùng lệnh trong README chính để sao chép và chạy từng bài thủ công.
