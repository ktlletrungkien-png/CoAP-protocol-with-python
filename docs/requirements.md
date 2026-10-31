# Đối chiếu yêu cầu bài thực hành

Nguồn yêu cầu: tài liệu “Thực hành buổi 3 python coap.docx” do người dùng cung cấp. Bảng này phân biệt phần bắt buộc, gợi ý mở rộng và yêu cầu nộp bài. Tên, mã sinh viên trong ví dụ là dữ liệu minh họa, cần thay bằng thông tin người thực hiện.

## Phần bắt buộc

| Yêu cầu | Triển khai |
| --- | --- |
| Python và aiocoap, giao tiếp Client–Server qua UDP 5683 | `requirements.txt`, `coap_common.py`; IP/cổng có thể cấu hình |
| Bài 1 có 2 chương trình | `bai1/coap_server_bai1.py`, `bai1/coap_client_bai1.py` |
| Tài nguyên `/iot/lab/message` hỗ trợ GET/POST | `MessageResource` |
| GET trả lời chào, client hiển thị phản hồi | GET ban đầu trả `2.05 Content` và lời chào server |
| POST có họ tên, mã sinh viên, lời chào | Tham số `--name`, `--student-id`, `--message` |
| Server in thông điệp, giờ nhận, xác nhận | Log terminal; phản hồi `2.04 Changed` |
| Client thực hiện GET rồi POST | Luồng chạy mặc định của client bài 1 |
| Bài 2 có 2 chương trình | `bai2/sensor_server_bai2.py`, `bai2/monitor_client_bai2.py` |
| Sensor `/iot/lab/sensor01/data` cập nhật mỗi 3 giây | Tác vụ nền độc lập với GET |
| Nhiệt độ, độ ẩm ngẫu nhiên hợp lý | 25–40°C, 30–70% |
| GET trả dữ liệu mới nhất và JSON đúng Content-Format | `device_id`, `temperature`, `humidity`; Content-Format 50 |
| Monitor GET mỗi 3 giây và chạy đến Ctrl+C | `--interval` mặc định 3; không giới hạn nếu bỏ `--count` |
| Hiển thị thiết bị, nhiệt độ, độ ẩm, giờ nhận | Log terminal monitor |
| Cảnh báo nhiệt độ >35 và độ ẩm <40 | Hai điều kiện độc lập; trường hợp bằng ngưỡng không cảnh báo |
| Bài 3 có 3 chương trình | `bai3/light_server_bai3.py`, `light_controller_bai3.py`, `light_monitor_bai3.py` |
| Đèn `light01`, ban đầu OFF, URI `/iot/lab/light01/status` | `LightResource` |
| GET trạng thái và PUT điều khiển ON/OFF | JSON trạng thái và JSON `{device_id, command}`; PUT hợp lệ `2.04 Changed` |
| Observe bằng `ObservableResource` | Server gọi `updated_state()` khi trạng thái thực sự thay đổi |
| Controller nhập ON/OFF/STATUS/EXIT | Chế độ tương tác mặc định; STATUS thực hiện GET |
| Monitor nhận trạng thái đầu và các cập nhật, giờ nhận | Một đăng ký GET Observe=0; đọc luồng thông báo aiocoap |
| Không dùng GET định kỳ cho monitor đèn | Không có polling trong monitor bài 3; kiểm tra Observe qua UDP thật |
| Vừa điều khiển vừa giám sát | Controller và nhiều monitor chạy đồng thời |
| Xử lý đầu vào và lỗi giao tiếp cơ bản | Kiểm tra CLI, payload JSON, mã lỗi, timeout, dọn context khi thoát |

## Các gợi ý mở rộng đã đưa vào dự án

| Gợi ý của đề | Cách dùng |
| --- | --- |
| Bài 1 gửi nhiều POST | `--count N` |
| Bài 1 GET thông điệp gần nhất | Server lưu trong bộ nhớ; `--verify-get` kiểm tra lại |
| Truy cập tài nguyên không tồn tại | `--path /iot/lab/missing` → `4.04 Not Found` |
| Server không hoạt động | `--timeout N` giới hạn chờ, lỗi được hiển thị |
| Timestamp cảm biến | Trường `timestamp` trong JSON |
| Hai/ba cảm biến | Server `--devices sensor01 sensor02 sensor03` |
| Chọn cảm biến | Monitor `--device sensor02` |
| Ghi CSV hoặc JSON | Monitor `--csv file.csv`, `--jsonl file.jsonl`; JSON Lines là mỗi dòng một object JSON |
| Đếm GET, thời gian phản hồi trung bình | Thống kê lúc monitor cảm biến kết thúc |
| Lệnh điều khiển không hợp lệ | Server trả 4.xx, giữ nguyên trạng thái |
| Nhiều monitoring client Observe | Mở nhiều monitor; tất cả cùng nhận thông báo |
| Nhiều thiết bị đèn/quạt/bơm | `--devices light01 fan01 pump01`, client chọn `--device` |
| Timestamp trạng thái | Trường `timestamp` trong payload JSON |
| Nhật ký thay đổi trạng thái | Server `--log-file file.jsonl` |
| Thử Confirmable/Non-confirmable | Client `--mtype CON` hoặc `--mtype NON`; có kiểm tra thực tế |

## Yêu cầu nộp bài

| Yêu cầu | Tệp / trạng thái |
| --- | --- |
| Mã nguồn cả ba bài, cấu trúc thư mục theo đề | Đủ 7 script trong `bai1/`, `bai2/`, `bai3/` |
| README thông tin sinh viên/nhóm | Có mục riêng; người dùng chưa cung cấp nên để chỗ điền |
| Phiên bản Python/thư viện và cách cài đặt | README, requirements cố định phiên bản |
| Cách chạy từng chương trình, IP/cổng/URI | README có lệnh cho từng terminal và ví dụ hai máy |
| Kết quả từng bài | README và `docs/verification.md` |
| Hình ảnh hoặc log minh chứng | `evidence/` chứa log thực thi thật, không phải log viết sẵn |
| Nộp qua GitHub | Chuẩn bị local; người dùng tự tạo repo và đăng theo yêu cầu |

Trạng thái thiết bị và thông điệp gần nhất nằm trong bộ nhớ, được khởi tạo lại khi khởi động server. File nhật ký là lịch sử xuất ra, không dùng để khôi phục trạng thái.
