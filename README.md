# Thực hành buổi 3 — Python với CoAP

Dự án mô phỏng ba bài IoT bằng Python và `aiocoap`: gửi thông điệp, giám sát cảm biến nhiệt độ/độ ẩm, và điều khiển đèn có CoAP Observe. Có đủ 7 chương trình theo cấu trúc đề bài. Thiết bị được mô phỏng bằng phần mềm, giao tiếp trực tiếp qua UDP; không cần phần cứng hay broker.

## Thông tin thực hiện

| Mục | Thông tin |
| --- | --- |
| Họ tên / tên nhóm | **Chưa cung cấp — điền trước khi nộp** |
| Mã sinh viên / thành viên | **Chưa cung cấp — điền trước khi nộp** |
| Nội dung | Lập trình Python với giao thức CoAP, buổi thực hành 3 |

`Nguyen Van A` và `B23DCCN001` trong các lệnh dưới đây là dữ liệu ví dụ của đề. Thay bằng thông tin của bạn khi chạy bài 1.

## Môi trường và cài đặt

- Python **3.10 trở lên**; môi trường kiểm tra local: **Python 3.12 trên Windows**.
- Thư viện duy nhất: **aiocoap 0.4.17**, cố định trong `requirements.txt`.
- Cổng mặc định **UDP 5683**, IP mặc định `127.0.0.1`.

Mở PowerShell tại thư mục gốc dự án:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -c "from importlib.metadata import version; print(version('aiocoap'))"
```

Không cần kích hoạt môi trường. Nếu máy có nhiều Python, có thể dùng `py -3.12 -m venv .venv`. Trên Linux/macOS, thay `.\.venv\Scripts\python.exe` bằng `./.venv/bin/python`.

Mỗi terminal bên dưới đều mở tại **thư mục gốc dự án**. Server của cả ba bài mặc định dùng cùng cổng, vì vậy **dừng server bài trước bằng Ctrl+C trước khi chạy bài tiếp theo**. Muốn chạy đồng thời, đặt `--port 5684`, `--port 5685` cho từng server và client tương ứng.

## Cấu trúc

```text
IOT - TH3/
├── bai1/
│   ├── coap_server_bai1.py
│   └── coap_client_bai1.py
├── bai2/
│   ├── sensor_server_bai2.py
│   └── monitor_client_bai2.py
├── bai3/
│   ├── light_server_bai3.py
│   ├── light_controller_bai3.py
│   └── light_monitor_bai3.py
├── coap_common.py
├── requirements.txt
├── tests/
├── tools/
├── docs/
├── evidence/
└── README.md
```

`coap_common.py` gom cấu hình kết nối, URI, xử lý JSON và timeout. Các script có `--help` để xem tham số.

## Bài 1 — Gửi và nhận thông điệp

Terminal 1:

```powershell
.\.venv\Scripts\python.exe bai1/coap_server_bai1.py
```

Terminal 2:

```powershell
.\.venv\Scripts\python.exe bai1/coap_client_bai1.py --name "Nguyen Van A" --student-id "B23DCCN001"
```

Client thực hiện GET rồi POST đến `coap://127.0.0.1:5683/iot/lab/message`. GET ban đầu trả `2.05 Content` và `Xin chao tu CoAP Server`. POST gửi lời chào kèm mã sinh viên, họ tên; server in payload và thời điểm nhận rồi xác nhận `2.04 Changed`, `Server da nhan thong diep`.

Mở rộng: gửi nhiều POST và kiểm tra GET trả thông điệp mới nhất:

```powershell
.\.venv\Scripts\python.exe bai1/coap_client_bai1.py --name "Nguyen Van A" --student-id "B23DCCN001" --count 3 --verify-get
```

Thử tài nguyên không tồn tại và server không hoạt động:

```powershell
.\.venv\Scripts\python.exe bai1/coap_client_bai1.py --name "Nguyen Van A" --student-id "B23DCCN001" --path /iot/lab/missing
.\.venv\Scripts\python.exe bai1/coap_client_bai1.py --name "Nguyen Van A" --student-id "B23DCCN001" --port 59999 --timeout 2
```

Trường hợp thứ nhất hiển thị `4.04 Not Found`; trường hợp thứ hai báo lỗi giao tiếp hoặc hết thời gian chờ và thoát với mã lỗi. Timeout giới hạn thời gian chờ ở client, không làm thay đổi trạng thái phía server.

## Bài 2 — Cảm biến nhiệt độ và độ ẩm

Terminal 1:

```powershell
.\.venv\Scripts\python.exe bai2/sensor_server_bai2.py
```

Terminal 2:

```powershell
.\.venv\Scripts\python.exe bai2/monitor_client_bai2.py
```

Server cập nhật độc lập mỗi 3 giây: nhiệt độ ngẫu nhiên trong 25–40°C, độ ẩm trong 30–70%. GET trả bản mới nhất, định dạng `application/json` (Content-Format 50):

```json
{"device_id":"sensor01","temperature":28.5,"humidity":65.2,"timestamp":"..."}
```

Client GET mỗi 3 giây, in mã thiết bị, nhiệt độ, độ ẩm và giờ nhận. Nhiệt độ **> 35°C** cảnh báo `CANH BAO: Nhiet do cao`; độ ẩm **< 40%** cảnh báo `CANH BAO: Do am thap`; nếu không có cảnh báo, in `Trang thai: Binh thuong`. Đúng 35°C và 40% không kích hoạt cảnh báo. Ctrl+C để dừng.

Để kiểm tra chắc chắn cả hai cảnh báo, dừng server cảm biến cũ rồi chạy:

```powershell
.\.venv\Scripts\python.exe bai2/sensor_server_bai2.py --temperature 36.1 --humidity 38.7
```

Ở terminal client, có thể chạy hữu hạn và lưu dữ liệu:

```powershell
.\.venv\Scripts\python.exe bai2/monitor_client_bai2.py --count 3 --csv logs/sensor.csv --jsonl logs/sensor.jsonl
```

Mở rộng nhiều cảm biến và chọn thiết bị:

```powershell
# Server (dừng server bài 2 cũ trước)
.\.venv\Scripts\python.exe bai2/sensor_server_bai2.py --devices sensor01 sensor02 sensor03
# Client
.\.venv\Scripts\python.exe bai2/monitor_client_bai2.py --device sensor02 --count 3
```

Mỗi cảm biến có URI `/iot/lab/<device_id>/data`. JSON có timestamp của server; log phía client ghi thời điểm nhận. Client thống kê số yêu cầu GET và thời gian phản hồi trung bình; thời gian trung bình chỉ tính các lần nhận phản hồi thành công. Khi mất kết nối hoặc nhận dữ liệu sai, client báo lỗi và tiếp tục ở chu kỳ tiếp theo.

## Bài 3 — Đèn thông minh và CoAP Observe

Terminal 1 — server:

```powershell
.\.venv\Scripts\python.exe bai3/light_server_bai3.py --log-file logs/light_changes.jsonl
```

Terminal 2 — giám sát:

```powershell
.\.venv\Scripts\python.exe bai3/light_monitor_bai3.py
```

Terminal 3 — điều khiển:

```powershell
.\.venv\Scripts\python.exe bai3/light_controller_bai3.py
```

Nhập `ON`, `STATUS`, `OFF`, `EXIT`, mỗi lệnh nhấn Enter. `ON`/`OFF` gửi PUT; `STATUS` gửi GET; `EXIT` kết thúc controller. Server bắt đầu với `OFF`. URI:

```text
coap://127.0.0.1:5683/iot/lab/light01/status
```

Payload PUT:

```json
{"device_id":"light01","command":"ON"}
```

GET và Observe trả JSON có `device_id`, `status`, `timestamp`. PUT hợp lệ trả `2.04 Changed`. Sai lệnh, JSON không hợp lệ, sai thiết bị hoặc sai Content-Format được trả mã lỗi CoAP phù hợp. Lệnh lặp lại trạng thái hiện tại vẫn được xác nhận nhưng **không phát thông báo Observe mới**.

Monitoring gửi **một GET có Observe=0**, nhận trạng thái ban đầu rồi chờ server đẩy thông báo qua cùng đăng ký. Không có vòng lặp GET định kỳ. Khi trạng thái thực sự đổi, server gọi `updated_state()` của `ObservableResource`, thông báo mọi client đang đăng ký. Mở thêm terminal giám sát để thử nhiều người quan sát; Ctrl+C để dừng từng client.

Chạy chuỗi điều khiển tự động:

```powershell
.\.venv\Scripts\python.exe bai3/light_controller_bai3.py --commands ON STATUS OFF
```

Mở rộng nhiều thiết bị:

```powershell
# Server (dừng server bài 3 cũ trước)
.\.venv\Scripts\python.exe bai3/light_server_bai3.py --devices light01 fan01 pump01 --log-file logs/devices.jsonl
# Các client chọn cùng device
.\.venv\Scripts\python.exe bai3/light_monitor_bai3.py --device fan01
.\.venv\Scripts\python.exe bai3/light_controller_bai3.py --device fan01
```

Mọi thiết bị có tài nguyên `/iot/lab/<device_id>/status`, ban đầu `OFF`. File JSONL ghi các lần trạng thái thực sự thay đổi.

### Thử CON và NON

Mặc định client dùng bản tin Confirmable (`CON`). Thử `NON` bằng:

```powershell
.\.venv\Scripts\python.exe bai3/light_controller_bai3.py --command STATUS --mtype NON
.\.venv\Scripts\python.exe bai3/light_controller_bai3.py --command ON --mtype CON
.\.venv\Scripts\python.exe bai3/light_monitor_bai3.py --mtype NON
```

CON có cơ chế xác nhận và truyền lại của CoAP; NON không có xác nhận ở tầng thông điệp. `--mtype` chọn loại **yêu cầu gửi đi**; loại bản tin thông báo Observe do aiocoap quyết định. Thử nghiệm local thành công không chứng minh khả năng chịu mất gói của NON. `--timeout` áp dụng cho phản hồi đầu tiên; `--idle-timeout` ở monitor đèn là tùy chọn giới hạn chờ thông báo tiếp theo, mặc định theo dõi liên tục.

## Chạy trên hai máy

Server phải bind IP LAN **cụ thể của máy server**, ví dụ `192.168.1.10`:

```powershell
# Máy server
.\.venv\Scripts\python.exe bai3/light_server_bai3.py --host 192.168.1.10 --port 5683
# Máy client
.\.venv\Scripts\python.exe bai3/light_monitor_bai3.py --host 192.168.1.10 --port 5683
.\.venv\Scripts\python.exe bai3/light_controller_bai3.py --host 192.168.1.10 --port 5683
```

Thay IP ví dụ bằng IP thật. Cả hai máy cần kết nối được với nhau và tường lửa phía server cho phép **UDP 5683** (hoặc cổng tự chọn). Backend UDP dùng ở đây hỗ trợ Windows và yêu cầu địa chỉ bind cụ thể; không dùng `0.0.0.0`/`::`. `localhost` cũng dùng được cho client, nhưng nên dùng `127.0.0.1` để tránh khác biệt IPv4/IPv6. Các bài dùng CoAP UDP thông thường trong môi trường thực hành, chưa cấu hình DTLS.

## Kiểm tra và minh chứng

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Các kiểm tra tích hợp dùng UDP loopback thật và cổng tạm để không chiếm cổng mặc định. Xem [bảng đối chiếu yêu cầu](docs/requirements.md), [kết quả kiểm tra](docs/verification.md) và log thực thi trong [evidence](evidence/).

Kết quả trên môi trường local: **9/9 kiểm tra tích hợp đạt**. Cả 7 chương trình cũng đã chạy thành công trong kịch bản minh chứng. Có thể tạo lại log bằng `.\.venv\Scripts\python.exe tools/capture_evidence.py`.

## Lỗi thường gặp

| Hiện tượng | Cách xử lý |
| --- | --- |
| Không có module `aiocoap` | Cài requirements bằng đúng Python trong `.venv`. |
| Cổng đã được sử dụng | Dừng server bài trước hoặc đổi `--port` đồng bộ cả server và client. |
| Timeout / lỗi kết nối | Kiểm tra server đang chạy, IP/cổng giống nhau và tường lửa UDP. |
| `4.04 Not Found` | Kiểm tra URI và `--device` đã được tạo trong `--devices` phía server. |
| Observe chỉ hiện trạng thái ban đầu | Gửi lệnh đổi trạng thái thực sự từ controller; `OFF` khi đang `OFF` sẽ không phát cập nhật. |
| Theo dõi ngừng khi không đổi trạng thái | Bỏ `--idle-timeout` nếu muốn chờ vô hạn. |

## Đưa lên GitHub

Tạo repo từ **thư mục dự án này**. `.gitignore` loại môi trường `.venv`, cache và log cá nhân trong `logs/`; giữ mã nguồn, README, kiểm tra, tài liệu đối chiếu và `evidence/`. Điền thông tin sinh viên/nhóm ở đầu README trước khi nộp. Không cần đưa file Word đề bài lên repo.

## Tham khảo

- [aiocoap 0.4.17 trên PyPI](https://pypi.org/project/aiocoap/0.4.17/).
- [API ObservableResource của aiocoap](https://aiocoap.readthedocs.io/en/latest/module/aiocoap.resource.html).
- [Backend UDP và tính tương thích nền tảng](https://aiocoap.readthedocs.io/en/latest/faq.html).
- [RFC 7252 — CoAP](https://www.rfc-editor.org/rfc/rfc7252), [RFC 7641 — Observe](https://www.rfc-editor.org/rfc/rfc7641).
