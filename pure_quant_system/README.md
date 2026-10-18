# PURE_QUANT_SYSTEM: Hệ Thống Giao Dịch Định Lượng Thuần Túy Dynamic-ATR

`pure_quant_system` là cỗ máy giao dịch định lượng hoàn toàn minh bạch (100% White-box), được tối ưu hóa toàn diện cho chiến lược **Morning Wave M15 DCA Pullback** trên thị trường Vàng (XAU/USD).

Hệ thống được thiết kế riêng biệt để giải quyết bài toán **biên độ biến động bão giá của năm 2026** thông qua cơ chế chuẩn hóa 100% theo chỉ báo biến động $ATR(14)$ và mô phỏng khớp lệnh từng phút qua nến M1.

---

## 1. Bản Chất Chiến Lược & Cơ Chế Hoạt Động

### A. Nhận Diện Sóng Sáng (07:00 – 10:00 VN)
- Tính độ lệch: $\Delta P = Open_{10:00} - Open_{07:00}$.
- Ngưỡng Sideway: $\epsilon = 0.15 \times ATR_{14}$.
- **Sóng Tăng ($\Delta P > +\epsilon$):** Chờ nến M15 **ĐỎ** đóng cửa $\rightarrow$ **BUY Lệnh 1**.
- **Sóng Giảm ($\Delta P < -\epsilon$):** Chờ nến M15 **XANH** đóng cửa $\rightarrow$ **SELL Lệnh 1**.
- **Sideway ($|\Delta P| \le \epsilon$):** Xét nến 10:00 – 10:15: Đóng Xanh $\rightarrow$ **BUY**, Đóng Đỏ $\rightarrow$ **SELL**.

### B. Thuật Toán Nhồi Lệnh DCA Thuận Xu Hướng
- **Điều kiện nhồi:** Khi giá tiếp tục đi ngược và xuất hiện nến M15 cùng màu nhịp hồi (nến đỏ cho Buy, nến xanh cho Sell).
- **Khoảng cách nhồi tối thiểu:** $\text{Khoảng cách} \ge \mathbf{0.40 \times ATR_{14}}$ (Năm 2026 tự động dãn cách $5.6\$ - $6.5\$$ để chống dính chùm lệnh).
- **Khóa trần rủi ro:** Giới hạn tối đa **3 đến 4 tầng lệnh / rổ** (tuyệt đối không nhồi vô tận).

### C. Cơ Chế Chốt Lời Động (Basket Take Profit)
- **Khi chỉ có 1 Lệnh (Chưa nhồi):**
  - Chốt lời tại $Entry \pm (0.45 \times ATR_{14})$ (~ target $1\%$ vốn).
  - Khóa hòa vốn (Break-Even): Khi giá chạy được $50\%$ TP $\rightarrow$ Kéo SL về giá Entry.
- **Khi rổ đã nhồi ($\ge 2$ Lệnh):**
  - **Không tham gồng 1% nữa!**
  - Tính Giá Trung Bình của cả rổ lệnh.
  - Mục tiêu chốt lời toàn rổ: $\text{Avg\_Entry} \pm (0.15 \times ATR_{14})$ (chỉ cần vượt qua giá trung bình khoảng $1.0\$$ là đóng sạch toàn bộ rổ lệnh để bảo toàn vốn).
- **Hard Exit Lúc 14:00 VN:** Đúng 14:00 đóng sạch toàn bộ các lệnh còn lại theo giá nến M1 lúc 14:00 để né bão phiên Âu.

---

## 2. Cấu Trúc Thư Mục `pure_quant_system/`

```
pure_quant_system/
├── config.py                 # Cấu hình hệ thống & không gian tham số Quant Grid Search
├── models.py                 # Dataclasses: Candle, SessionData, Order, BasketTrade, PerformanceMetrics
├── data_loader.py            # Nạp nến M15 và trích xuất nến M1 khung giờ 10h-14h15
├── strategy.py               # Phân tích sóng 07h-10h, kiểm tra cầu chì bão giá, sinh tín hiệu M15
├── execution_engine.py       # Động cơ tua nến M1 từng phút để khớp lệnh, tính giá TB rổ và Hard Exit
├── optimizer.py              # Bộ máy Quant Grid Search tối ưu tham số trên 2011-2020
├── metrics.py                # Tính toán Winrate, Profit Factor, Max Drawdown, phân phối tầng DCA
├── reporter.py               # Xuất báo cáo Terminal bảng ASCII & file JSON chi tiết
├── run.py                    # Entrypoint CLI chính thức
└── pure_quant_optimal_params.json # Tham số Quant tối ưu đã đóng băng từ 2011-2020
```

---

## 3. Cách Vận Hành Qua Dòng Lệnh (CLI)

Chạy trực tiếp từ thư mục gốc dự án:

### Lựa Chọn 1: Chạy Tối Ưu Hóa & Đánh Giá 10 Năm In-Sample (2011 – 2020)
```bash
python3 pure_quant_system/run.py --mode train
```
> Hệ thống sẽ:
> 1. Chạy Quant Grid Search trên 2,500 ngày (2011–2020) để tìm bộ tham số tối ưu (Khoảng cách nhồi, TP đơn, TP rổ, Số tầng).
> 2. Đóng băng cấu hình tối ưu vào file `pure_quant_optimal_params.json`.
> 3. Xuất báo cáo hiệu suất chi tiết kèm phân phối tầng DCA của 10 năm In-Sample.

### Lựa Chọn 2: Kiểm Định Mù Out-of-Sample Trên 5 Năm Gần Nhất (2021 – 2025)
```bash
python3 pure_quant_system/run.py --mode test
```
> Hệ thống nạp bộ tham số đã đóng băng từ 2011-2020 để kiểm tra mù độc lập trên 5 năm gần nhất (2021-2025).

### Lựa Chọn 3: Chạy Song Song và In Bảng Đối Chiếu Toàn Diện
```bash
python3 pure_quant_system/run.py --mode all
```
> Chạy cả 2 giai đoạn và xuất bảng đối chiếu toàn diện các chỉ số: **Win Rate Rổ Lệnh**, **Profit Factor**, **Lợi Nhuận Ròng**, **Max Drawdown** và **Số Ngày Cầu Chì Bão Giá Ngắt**.
