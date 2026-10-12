# Hệ Thống AI Quantitative Trading: Rocket 10h M15 (XAU/USD)

Hệ thống giao dịch định lượng kết hợp Trí tuệ Nhân tạo (Machine Learning) dành cho Vàng (XAU/USD), được kiểm chứng và tối ưu trên **15 năm dữ liệu nến M15 (2011 – 2025)**.

---

## 1. Cấu Trúc Hệ Thống

| File | Vai trò |
| :--- | :--- |
| **[`ai_system.py`](file:///Users/duongdv/Documents/Workspace/Personal/system_rocket2h_15M/ai_system.py)** | **Bộ não AI:** Trích xuất đặc trưng (ATR, Asian Range, EMA), huấn luyện mô hình AI trên 10 năm Train (2011-2020), kiểm định mù (Blind Test) trên 5 năm Test (2021-2025) và xuất ra file `web_data.json`. |
| **[`dashboard.html`](file:///Users/duongdv/Documents/Workspace/Personal/system_rocket2h_15M/dashboard.html)** | **Giao diện Web View:** Dashboard trực quan hóa hiệu suất, biểu đồ tăng trưởng vốn (Equity Curve), bảng đối đầu Train vs Test, và nhật ký từng lệnh. |
| **[`server.py`](file:///Users/duongdv/Documents/Workspace/Personal/system_rocket2h_15M/server.py)** | **Web Server:** Máy chủ HTTP nhẹ bằng Python tiêu chuẩn, tự động tạo dữ liệu và phục vụ dashboard trên cổng `8080` (chạy cả máy cá nhân lẫn VPS). |
| **[`deploy_vps.sh`](file:///Users/duongdv/Documents/Workspace/Personal/system_rocket2h_15M/deploy_vps.sh)** | **Script triển khai VPS:** Tự động cài đặt và biến dashboard thành dịch vụ chạy ngầm 24/7 (`systemd`). |

---

## 2. Cách Chạy Thử Nghiệm Trên Máy Cục Bộ (Local)

Chỉ với 1 lệnh duy nhất:

```bash
python3 server.py
```

- Server sẽ tự động kiểm tra, chạy `ai_system.py` để huấn luyện AI và tính toán kết quả nếu chưa có `web_data.json`.
- Mở trình duyệt và truy cập: **`http://localhost:8080`**

---

## 3. Cách Triển Khai Lên VPS (Ubuntu / Debian)

### Bước 1: Đẩy toàn bộ thư mục lên VPS
Bạn có thể dùng `rsync`, `scp` hoặc `git clone` để đưa thư mục mã nguồn lên VPS:
```bash
scp -r /path/to/system_rocket2h_15M root@<IP_VPS>:/root/
```

### Bước 2: Chạy script tự động triển khai
Đăng nhập SSH vào VPS và chạy:
```bash
cd /root/system_rocket2h_15M
chmod +x deploy_vps.sh
./deploy_vps.sh
```

Script sẽ tự động:
1. Mở cổng `8080` trên tường lửa `ufw`.
2. Tạo dịch vụ chạy ngầm `quant-dashboard.service` tự khởi động lại khi reboot.
3. Xuất đường link web dashboard trực tiếp qua IP của VPS: `http://<IP_VPS>:8080`.

### Quản lý dịch vụ trên VPS:
- Xem trạng thái: `sudo systemctl status quant-dashboard`
- Dừng dịch vụ: `sudo systemctl stop quant-dashboard`
- Khởi động lại: `sudo systemctl restart quant-dashboard`
- Xem log: `journalctl -u quant-dashboard -f`
