# Hệ Thống AI Quantitative Trading: Rocket 10h M15 (XAU/USD) v5.0 WAVE REGIME

Hệ thống giao dịch định lượng kết hợp Trí tuệ Nhân tạo (Machine Learning) dành cho Vàng (XAU/USD), được tối ưu hóa toàn diện trên **15 năm dữ liệu nến M15 (2011 – 2025)**.

### Bộ Quy Tắc Giao Dịch v5.0 (Pullback Trend + Breakout Sideway):
1. **Nhận Diện Sóng 07:00 – 10:00 Sáng VN ($\Delta P = \text{Price}_{10h} - \text{Open}_{07h}$):**
   - **Kịch bản SÓNG TĂNG ($\Delta P > 1.0 \times ATR$):** Xác định chiều **BUY**. Chờ nến M15 đầu tiên đóng **ĐỎ** (Pullback giá hồi giảm) mới vào BUY 1 để được giá chiết khấu; các nến sau tiếp tục Đỏ $\rightarrow$ Nhồi thêm BUY.
   - **Kịch bản SÓNG GIẢM ($\Delta P < -1.0 \times ATR$):** Xác định chiều **SELL**. Chờ nến M15 đầu tiên đóng **XANH** (Pullback giật lên) mới vào SELL 1 để được giá cao; các nến sau tiếp tục Xanh $\rightarrow$ Nhồi thêm SELL.
   - **Kịch bản SIDEWAY ($\lvert \Delta P \rvert \le 1.0 \times ATR$):** Đánh thuận theo nến bứt phá 10:15: nến 10:15 XANH $\rightarrow$ Mở BUY 1; nến 10:15 ĐỎ $\rightarrow$ Mở SELL 1. Nhồi DCA khi nến sau đi ngược chiều.
2. **Bộ Lọc Chống Dính Lệnh (Anti-Clustering):**
   - Khoảng cách tối thiểu giữa 2 lệnh: $\text{Min Distance} = \max(2.0, 0.4 \times ATR_{15M})$.
   - Ngăn chặn việc gom 2 - 3 lệnh đè lên nhau tại các nến Doji/thân ngắn đi ngang.
3. **Cơ Chế Chốt Lời HYBRID Đa Tầng:**
   - 1 lệnh: Ăn dày theo con sóng ($1.0 - 1.5 \times ATR$, dao động 10 - 20 giá).
   - $\ge 3$ lệnh: Tự động co target lại ($0.5 \times ATR$, chỉ cần lãi 3.5 - 7 giá) để thoát sạch rổ lệnh ngay nến hồi đầu tiên.
   - Khóa lãi sớm theo nến M15 đảo chiều khi đã có lãi an toàn.
4. **Bảo Hiểm Rủi Ro (Circuit Breaker):**
   - Cắt lỗ cứng toàn bộ rổ lệnh khi chạm ngưỡng **$-50\%$ Balance** (cho rổ lệnh biên độ chịu rung lắc lớn để chờ nhịp hồi).
5. **Quản Lý Vốn Lãi Kép (Compounding):**
   - Cứ mỗi **$2,000 vốn** đi **0.01 lot** ($10k$ vốn khởi điểm 0.05 lot).

---

## 1. Cấu Trúc Hệ Thống

| File | Vai trò |
| :--- | :--- |
| **[`ai_system.py`](file:///Users/duongdv/Documents/Workspace/Personal/system_rocket2h_15M/ai_system.py)** | **Bộ não AI v5.0:** Đo sóng 07h-10h, phân loại Pullback Trend & Breakout Sideway, mô phỏng chốt lời Hybrid, lọc bão giá và xuất ra file `web_data.json`. |
| **[`dashboard.html`](file:///Users/duongdv/Documents/Workspace/Personal/system_rocket2h_15M/dashboard.html)** | **Giao diện Web View v5.0:** Dashboard trực quan hóa hiệu suất Lãi kép, biểu đồ tăng trưởng vốn (Equity Curve), bảng đối đầu Train vs Test, và nhật ký từng lệnh. |
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
