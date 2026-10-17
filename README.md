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
4. **Cơ Chế Phân Bổ Khối Lượng Theo % Rủi Ro Co Giãn ATR (Cách 2 - Recommended):**
   - Khối lượng tự động thích ứng theo độ biến động thực tế của Vàng tại phiên 10h:
     - Ngày thị trường **bão giá (ATR tăng cao)**: Tự động **thu nhỏ lot** để bảo vệ tài khoản khỏi rung lắc sâu.
     - Ngày thị trường **sóng êm (ATR thấp)**: Tự động **nâng lot** để tối ưu hóa hiệu suất lợi nhuận.
     - Mặc định: Mức rủi ro **$0.5\%$ vốn / phiên** trên biên độ chịu nhiệt $5.0 \times ATR$ (hỗ trợ chuyển đổi linh hoạt sang chế độ cố định $5,000 vốn = 0.01 lot trên Web UI).
5. **Bỏ Qua Giới Hạn Số Lệnh (Unlimited DCA Layers):**
   - Không giới hạn số lệnh tối đa, cho phép rổ lệnh tự do DCA theo đóng nến M15 ngược màu để kéo giá trung bình nhanh nhất.
6. **Nhận Diện Sóng 07h-10h & Bộ Lọc Chống Dính Lệnh (Anti-Clustering):**
   - Sóng tăng: Chờ nến đỏ pullback để BUY.
   - Sóng giảm: Chờ nến xanh pullback để SELL.
   - Sideway: Đánh theo nến 10:15 (Xanh Buy, Đỏ Sell).
   - Khoảng cách nhồi tối thiểu: $\text{Min Distance} = \max(2.0, 0.4 \times ATR)$.

---

## 1. Cấu Trúc Hệ Thống (Phân Tách 4 Thư Mục Rõ Ràng)

```
system_rocket2h_15M/
├── data/                                 <-- Chứa TOÀN BỘ dữ liệu nến CSV (15 năm M15 & M1)
│   ├── XAUUSD_2011_m15.csv
│   └── ...
│
├── engine/                               <-- Hệ thống làm việc với nến: Backtest & Huấn Luyện AI
│   ├── __init__.py
│   ├── backtest_ai.py                    (Động cơ định lượng: Nạp nến, Volatility Guard, Train/Test)
│   └── run_cli.py                        (Script CLI chạy độc lập từ Terminal)
│
├── server/                               <-- Web Server: Cung cấp API cho Web UI & Lưu trữ Lịch sử
│   ├── __init__.py
│   ├── app.py                            (Máy chủ HTTP phục vụ Web UI & toàn bộ API)
│   ├── history_store.py                  (Quản lý lưu trữ index.json và từng run chi tiết)
│   └── history/                          (Thư mục lưu vĩnh viễn tất cả các lần chạy)
│       ├── index.json
│       └── run_*.json
│
└── frontend/                             <-- Web UI React (Vite + React 18)
    ├── src/
    │   ├── components/
    │   │   ├── ParameterControl.jsx      (Bộ nhập tham số + Nút Run trực tiếp)
    │   │   ├── RunHistory.jsx            (Xem lại toàn bộ lịch sử các lần chạy)
    │   │   ├── MetricsGrid.jsx           (6 chỉ số hiệu suất: Winrate, PnL, MaxDD...)
    │   │   ├── EquityChart.jsx           (Biểu đồ Canvas Equity Curve & Tầng DCA)
    │   │   └── ...
    │   └── services/api.js               (Giao tiếp API với server/app.py)
    └── package.json
```

| Thư mục | Chức năng chuyên biệt |
| :--- | :--- |
| **`data/`** | **Gom toàn bộ dữ liệu nến vào 1 nơi:** Chứa 15 năm nến M15 (2011 - 2025) và M1. Giữ cho thư mục gốc luôn sạch sẽ, gọn gàng. |
| **`engine/`** | **Hệ thống làm việc với dữ liệu nến:** Độc lập hoàn toàn. Chuyên trách nạp nến từ `data/`, đo sóng 07h-10h, áp dụng Volatility Guard, mô phỏng chiến lược và trả về kết quả định lượng. Có thể chạy độc lập qua CLI (`python3 engine/run_cli.py`) hoặc được gọi từ Web Server. |
| **`server/`** | **Web Server & Quản lý Lịch sử:** Chịu trách nhiệm trả API cho Web UI và là nơi duy nhất lưu trữ lịch sử các lần chạy vào thư mục `server/history/`. Phục vụ Web UI 24/7 ổn định trên VPS với lượng RAM siêu nhẹ (~15MB). |
| **`frontend/`** | **Web UI React:** Giao diện điều khiển cho phép đưa tham số đầu vào, nhấn nút Run trực tiếp, và xem lại toàn bộ lịch sử các lần chạy trong quá khứ. |

---

## 2. Hướng Dẫn Vận Hành

### Bước 1: Bật Web Server (Phục vụ Web UI & Lưu trữ Lịch sử)
```bash
python3 server/app.py --host 0.0.0.0 --port 8080
```
- Mở trình duyệt tại: **`http://localhost:8080`** (hoặc `http://<IP_VPS>:8080` nếu trên VPS).
- Trên Web UI:
  - Tùy chỉnh các tham số đầu vào và nhấn nút **"🚀 CHẠY BACKTEST & TRAIN AI"** ngay trên trình duyệt.
  - Nhấn vào mục **"📜 Lịch Sử Chạy"** để xem danh sách tất cả các lần chạy trước đó, và bấm **"👁️ Xem Lại Bản Này"** để xem lại toàn bộ biểu đồ, chỉ số của bất kỳ bản chạy nào!

### Bước 2: Chạy Huấn Luyện AI Bằng Terminal (Tùy Chọn Khi Cần Chạy CLI Độc Lập)
Nếu muốn chạy trực tiếp bằng Terminal trên VPS mà không cần mở trình duyệt:
```bash
# Chạy tham số chuẩn
python3 engine/run_cli.py --min-step 0.5 --tp-single 0.8 --tp-dca 0.5 --hard-exit 14:00

# Hoặc cắt lỗ lúc 12:00
python3 engine/run_cli.py --min-step 0.6 --tp-single 0.6 --tp-dca 0.4 --hard-exit 12:00
```

### Bước 3: Triển Khai Chạy 24/7 Trên VPS (Ubuntu / Debian)
```bash
chmod +x deploy_vps.sh
./deploy_vps.sh
```
Script sẽ tự động kiểm tra `data/`, build React Frontend và khởi chạy dịch vụ `server/app.py` chạy ngầm 24/7 qua systemd.

---

## 3. Chạy Bằng Docker Tại Local Có Hot Reload (Khi Sửa Code)

Hệ thống đã được cấu hình file [`docker-compose.yml`](file:///Users/duongdv/Documents/Workspace/Personal/system_rocket2h_15M/docker-compose.yml) hỗ trợ **Hot Reload 100%**:
- **Khi sửa file React (`frontend/src/...`)**: Trình duyệt tự động cập nhật ngay lập tức (Vite HMR ~50ms).
- **Khi sửa file Python (`server/...` hoặc `engine/...`)**: Web server tự động restart tức thì (~100ms).

### Khởi động bằng 1 lệnh duy nhất:
```bash
docker compose up
```

- **Giao diện Web UI (chế độ phát triển Dev có Hot Reload):** `http://localhost:5173`
- **Máy chủ Backend API & History:** `http://localhost:8088` (hoặc `http://<IP_VPS>:8088`)
- Dữ liệu nến (`data/`) và lịch sử các lần chạy (`server/history/`) được mount trực tiếp nên sẽ được lưu vĩnh viễn trên máy của bạn.

### Dừng các container:
```bash
docker compose down
```

---

## 4. Bộ Công Cụ Chẩn Đoán Định Lượng Nâng Cấp (Quant Analytics Suite)

Hệ thống được nâng cấp bộ tính năng phân tích trực quan chuẩn Quỹ định lượng:
1. **Biểu đồ phân phối tầng DCA & Lý do thoát lệnh (DCA Distribution & Exit Reasons):**
   - Vòng tròn Donut SVG & thanh đo thời gian thực: Tầng 1 (Chốt ngay lệnh đầu 0.01 lot), Tầng 2-3 (Hồi nhẹ DCA), Tầng 4-5 (DCA sâu), Tầng 6+ (Bão giá).
   - Thống kê tỷ lệ chốt lời mục tiêu (TP hit) so với tỷ lệ cắt lỗ cưỡng bức 14:00 (Hard Exit) và tổng thiệt hại né được.
2. **Hiệu suất theo Ngày trong tuần (Day-of-Week Breakdown):**
   - Thống kê chi tiết từ Thứ Hai đến Thứ Sáu: Winrate %, Tổng PnL, PnL trung bình / lệnh, số lần gồng DCA sâu.
   - Gợi ý định hướng Feature Engineering để mô hình AI tự động tinh chỉnh volume hoặc nâng ngưỡng lọc vào ngày biến động cao.
3. **Lịch nhiệt hiệu suất 15 năm & Ma trận Tháng/Năm (Calendar Heatmap & Monthly Return Matrix):**
   - **Chế độ Ma trận Tháng/Năm:** Bảng 15 năm x 12 tháng hiển thị trực quan các tháng lãi (xanh lá) / lỗ (đỏ) và tổng PnL từng năm.
   - **Chế độ Lịch 365 Ngày:** Xem chi tiết từng ngày của năm được chọn, phân biệt ngày lãi lớn, lãi vừa, cắt lỗ 14:00, và các ngày được AI Shock Filter kích hoạt né bão an toàn (màu tím). Hover chuột để xem đầy đủ chi tiết phiên giao dịch.
4. **Biểu đồ nến Nhật M15 chi tiết từng ngày (Intraday Candlestick Chart):**
   - Bấm nút **"📈 Soi Nến"** ở bất kỳ dòng lệnh nào trong Nhật ký lệnh, hoặc click vào ô ngày trên Lịch nhiệt / Nhật ký ngày bão.
   - Hiển thị toàn bộ nến M15 của ngày đó: Vùng sóng sáng 07h-10h, các điểm vào lệnh L1, L2, L3..., đường giá trung bình rổ lệnh (Avg Entry), và điểm thoát lệnh (TP hoặc Cắt 14h) đi kèm con trỏ chữ thập (Crosshair) soi giá Open, High, Low, Close.


