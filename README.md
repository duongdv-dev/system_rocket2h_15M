# Hệ Thống AI Quantitative Trading: Rocket 10h M15 (XAU/USD) v6.0 NO-SL CANDLE TP

Hệ thống giao dịch định lượng kết hợp Trí tuệ Nhân tạo (Machine Learning) dành cho Vàng (XAU/USD), được tối ưu hóa toàn diện trên **15 năm dữ liệu nến M15 (2011 – 2025)**.

### Bộ Quy Tắc Giao Dịch v6.0 (No-SL Candle TP & Volatility Guard):
1. **Bỏ Hoàn Toàn Stop Loss (No SL):**
   - Không cắt lỗ non; cho phép rổ lệnh hấp thụ rung lắc để chờ nhịp hồi tự nhiên của Vàng.
2. **Bộ Lọc Bão Giá Cực Đoan (Extreme Volatility Guard):**
   - Bắt buộc né 10% - 15% những ngày có tin tức sốc, ATR tăng vọt bất thường hoặc biên độ sáng giãn quá dài.
   - Đánh ~85% - 90% số ngày bình thường khi thị trường luôn có sóng hồi quy.
3. **Chốt Lời Động Theo Đóng Nến M15 (Candle-based TP):**
   - Không chờ cứng 10 giá; chốt ngay tại đóng nến M15 khi có lãi ròng đủ bù spread ($\ge 1.5 - 2.5$ giá).
   - Rổ nhồi ($\ge 2$ lệnh): Chỉ cần đóng nến M15 có lãi là đóng sạch toàn bộ rổ lệnh để bảo toàn vốn!
   - Lệnh đơn: Cho phép gồng tiếp nếu nến M15 đang bứt phá mạnh cùng chiều; chốt ngay khi nến rút râu hoặc đảo chiều.
4. **Hệ Số Volume Cơ Sở An Toàn:**
   - Cứ mỗi **$5,000 vốn** đi **0.01 lot** ($10k$ vốn đi $0.02$ lot khởi điểm; volume phân bổ nhẹ nhàng, tài khoản chịu được các đợt rung lắc mạnh).
5. **Bỏ Qua Giới Hạn Số Lệnh (Unlimited DCA Layers):**
   - Không giới hạn số lệnh tối đa, cho phép rổ lệnh tự do DCA theo đóng nến M15 ngược màu để kéo giá trung bình nhanh nhất.
6. **Nhận Diện Sóng 07h-10h & Bộ Lọc Chống Dính Lệnh (Anti-Clustering):**
   - Sóng tăng: Chờ nến đỏ pullback để BUY.
   - Sóng giảm: Chờ nến xanh pullback để SELL.
   - Sideway: Đánh theo nến 10:15 (Xanh Buy, Đỏ Sell).
   - Khoảng cách nhồi tối thiểu: $\text{Min Distance} = \max(2.0, 0.4 \times ATR)$.

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
