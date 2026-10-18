"""
==============================================================================
MODULE: CONFIGURATION (pure_quant_system/config.py)
==============================================================================
HỆ THỐNG THUẦN QUANT ĐỘNG ATR (PURE QUANT DYNAMIC-ATR):
- Không dùng bất kỳ số giá $ cố định nào để thích ứng hoàn hảo chu kỳ 2026.
- Toàn bộ tham số co giãn theo ATR(14) tại nến 10:00 VN.
- Quản trị rủi ro cố định 1% vốn / phiên với biên độ chịu nhiệt 5.0 x ATR.
==============================================================================
"""

import os
from datetime import timezone, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
OUTPUT_DIR = os.path.join(BASE_DIR, "reports")
OPTIMAL_PARAMS_FILE = os.path.join(BASE_DIR, "pure_quant_optimal_params.json")

# Múi giờ Việt Nam (UTC+7)
VN_TZ = timezone(timedelta(hours=7))

# Phân tách tập dữ liệu nghiêm ngặt
TRAIN_YEARS = list(range(2011, 2021))  # 2011 - 2020: 10 năm In-Sample
TEST_YEARS  = list(range(2021, 2026))  # 2021 - 2025: 5 năm Out-of-Sample

# Cấu hình chuẩn hóa thích ứng độ biến động 2026
DEFAULT_CONFIG = {
    # Quản trị vốn & Rủi ro cố định
    "initial_balance": 10000.0,
    "risk_percent": 1.0,             # Mức rủi ro cố định: 1.0% vốn ($100 trên vốn $10,000)
    "heat_buffer_atr": 5.0,          # Biên độ chịu nhiệt: 5.0 x ATR để tính Lot size tự động
    "lot_step_capital": 5000.0,      # Dự phòng khi tính lot cố định
    "sizing_mode": "atr_risk",       # 'atr_risk' (tự co giãn theo biến động)
    
    # Nhận diện sóng 07h-10h VN
    "sideway_atr_ratio": 0.15,       # Ngưỡng sideway = 0.15 x ATR14
    
    # Cầu chì bão giá (Circuit Breaker)
    "circuit_stretch_ratio": 3.5,    # Sóng sáng giãn >= 3.5x ATR -> Bỏ qua
    "circuit_relative_atr_pct": 0.70,# ATR14 >= 0.70% giá trị Vàng 10h -> Bỏ qua bão giá
    
    # Thuật toán nhồi lệnh DCA
    "max_dca_layers": 4,             # Tối đa 4 tầng lệnh / rổ (tuyệt đối không nhồi vô tận)
    "min_dca_distance_atr": 0.40,    # Khoảng cách tối thiểu nhồi = 0.40 x ATR14 (chống dính chùm)
    "max_wait_bars": 10,             # Số nến M15 tối đa chờ nến pullback (tới 12:30 VN)
    
    # Chốt lời động theo ATR
    "tp_single_atr": 0.45,           # Lệnh đơn lẻ: Chốt lời tại 0.45 x ATR (~ target 1% vốn)
    "tp_basket_atr": 0.15,           # Rổ nhồi (>= 2 lệnh): Chốt sạch khi qua Giá TB + 0.15 x ATR
    "break_even_ratio": 0.50,        # Lệnh đơn chạy được 50% TP -> Kéo SL về hòa vốn
    
    # Thoát lệnh bắt buộc (Hard Exit)
    "hard_exit_hour": 14,            # Đúng 14:00 VN đóng sạch rổ lệnh né phiên Âu
    "hard_exit_minute": 0,
    
    # Chi phí giao dịch giả lập thực tế
    "spread_dollars": 0.25,          # Phí spread thực tế Vàng ($0.25 = 2.5 pips)
    "slippage_dollars": 0.05         # Trượt giá
}

# Không gian tìm kiếm tham số Quant Grid Search trên 2011-2020
QUANT_SEARCH_SPACE = {
    "min_dca_distance_atr": [0.30, 0.40, 0.50],
    "tp_single_atr": [0.35, 0.45, 0.55],
    "tp_basket_atr": [0.10, 0.15, 0.20],
    "max_dca_layers": [3, 4]
}
