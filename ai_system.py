#!/usr/bin/env python3
"""
AI Quantitative Trading Engine for XAU/USD M15 Rocket Strategy
- Data: 2011 - 2025 (15 years)
- In-Sample Training: 2011 - 2020 (10 years)
- Out-of-Sample Validation: 2021 - 2025 (5 years)
- AI Model: Feature Engineering + Machine Learning Classifier (Trade Filter & Regime Detector)
- Generates: web_data.json for interactive Web Dashboard
"""

import os
import glob
import csv
import json
import math
from datetime import datetime, timezone, timedelta
from collections import Counter

VN_TZ = timezone(timedelta(hours=7))
TRAIN_YEARS = set(range(2011, 2021))
TEST_YEARS  = set(range(2021, 2026))

# Cấu hình chiến lược mặc định
DEFAULT_TARGET_PROFIT = 10.0  # 10 giá (100 pips)
DEFAULT_MAX_ORDERS = 8        # Tối đa 8 lệnh DCA
DEFAULT_LOT = 0.01
LOT_MULT = 1.0                # Đều lot
HARD_SL = 35.0                # Cắt lỗ tổng rổ 35 giá (bảo hiểm cháy tài khoản)


def load_candles(data_dir):
    files = sorted(glob.glob(os.path.join(data_dir, "XAUUSD_*_m15.csv")))
    if not files:
        raise FileNotFoundError(f"Không tìm thấy file XAUUSD_*_m15.csv trong {data_dir}")

    print(f"[1/4] Đang nạp dữ liệu từ {len(files)} files M15...")
    candles = []
    for fpath in files:
        with open(fpath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    ts = int(row['timestamp'])
                    o = float(row['open'])
                    h = float(row['high'])
                    l = float(row['low'])
                    c = float(row['close'])
                    v = float(row['volume'])
                    candles.append((ts, o, h, l, c, v))
                except (ValueError, KeyError):
                    continue

    candles.sort(key=lambda x: x[0])
    print(f"      -> Tổng cộng nạp thành công: {len(candles):,} nến M15.")
    return candles


# ==========================================
# FEATURE ENGINEERING & SIMULATION
# ==========================================
def extract_daily_features_and_trades(candles):
    """
    Duyệt qua chuỗi nến M15, nhận diện các phiên 10:00 VN hàng ngày.
    Tính toán các đặc trưng (features) ngay trước nến 10:00 và mô phỏng kết quả rổ lệnh.
    """
    print("[2/4] Đang trích xuất đặc trưng (Feature Engineering) & Mô phỏng rổ lệnh...")
    
    # 1. Tiền xử lý chỉ báo kỹ thuật trên chuỗi nến
    n = len(candles)
    closes = [c[4] for c in candles]
    highs = [c[2] for c in candles]
    lows = [c[3] for c in candles]

    # Tính ATR(14)
    trs = [highs[0] - lows[0]]
    for i in range(1, n):
        tr = max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))
        trs.append(tr)

    atrs = [0.0] * n
    period = 14
    running_tr = sum(trs[:period])
    atrs[period-1] = running_tr / period
    for i in range(period, n):
        running_tr = running_tr - trs[i-period] + trs[i]
        atrs[i] = running_tr / period

    # Tính EMA 20 & EMA 50
    ema20 = [closes[0]] * n
    ema50 = [closes[0]] * n
    k20 = 2.0 / (20 + 1)
    k50 = 2.0 / (50 + 1)
    for i in range(1, n):
        ema20[i] = closes[i] * k20 + ema20[i-1] * (1 - k20)
        ema50[i] = closes[i] * k50 + ema50[i-1] * (1 - k50)

    # 2. Duyệt tìm các điểm kích hoạt 10:00 AM VN
    sessions = []
    i = 0
    while i < n:
        ts, c_open, c_high, c_low, c_close, vol = candles[i]
        dt_utc = datetime.fromtimestamp(ts / 1000.0, tz=timezone.utc)
        dt_vn = dt_utc.astimezone(VN_TZ)

        # Nến 10:00 VN (mở 10:00, đóng 10:15)
        if dt_vn.hour == 10 and dt_vn.minute == 0 and i >= 30:
            current_year = dt_vn.year
            current_date_str = dt_vn.strftime('%Y-%m-%d')
            day_of_week = dt_vn.weekday()

            # --- TRÍCH XUẤT ĐẶC TRƯNG TRƯỚC VÀ TẠI 10h ---
            atr_val = atrs[i]
            ema_diff = (ema20[i] - ema50[i]) / (atr_val + 1e-5)
            candle_body = abs(c_close - c_open)
            candle_range = c_high - c_low
            body_ratio = candle_body / (candle_range + 1e-5)

            # Tính biên độ phiên Á (từ 06:00 đến 10:00 VN, khoảng 16 nến M15 trước đó)
            asian_slice = candles[max(0, i-16):i]
            if asian_slice:
                asian_high = max(c[2] for c in asian_slice)
                asian_low = min(c[3] for c in asian_slice)
                asian_range = asian_high - asian_low
                asian_open = asian_slice[0][1]
                asian_return = (c_close - asian_open) / (atr_val + 1e-5)
            else:
                asian_range = atr_val
                asian_return = 0.0

            # Hướng giao dịch theo quy tắc cơ bản:
            # Nến đỏ -> BUY, Nến xanh -> SELL
            direction = 'BUY' if c_close < c_open else ('SELL' if c_close > c_open else None)

            if direction is not None:
                # --- MÔ PHỎNG CHU KỲ LỆNH ---
                orders = [{'price': c_close, 'lot': DEFAULT_LOT, 'time': dt_vn.strftime('%H:%M')}]
                basket_closed = False
                close_price = c_close
                close_time = dt_vn
                max_layers_used = 1
                max_dd_price = 0.0
                j = i + 1

                while j < min(n, i + 96):  # Giới hạn tối đa trong vòng 24h (96 nến M15)
                    next_ts, n_open, n_high, n_low, n_close, _ = candles[j]
                    next_dt = datetime.fromtimestamp(next_ts / 1000.0, tz=timezone.utc).astimezone(VN_TZ)

                    # Tính giá trung bình
                    avg_price = sum(o['price'] * o['lot'] for o in orders) / sum(o['lot'] for o in orders)
                    floating_pnl_price = (n_close - avg_price) if direction == 'BUY' else (avg_price - n_close)

                    # Cập nhật drawdown lớn nhất trong chu kỳ
                    worst_price = (n_low - avg_price) if direction == 'BUY' else (avg_price - n_high)
                    if worst_price < max_dd_price:
                        max_dd_price = worst_price

                    # Kiểm tra Take Profit tại đóng nến
                    if floating_pnl_price >= DEFAULT_TARGET_PROFIT:
                        basket_closed = True
                        close_price = n_close
                        close_time = next_dt
                        break

                    # Kiểm tra Hard Stop Loss
                    if floating_pnl_price <= -HARD_SL:
                        basket_closed = True
                        close_price = n_close
                        close_time = next_dt
                        break

                    # Xét điều kiện nhồi lệnh DCA
                    if len(orders) < DEFAULT_MAX_ORDERS:
                        if direction == 'BUY' and n_close < n_open:
                            orders.append({'price': n_close, 'lot': DEFAULT_LOT, 'time': next_dt.strftime('%H:%M')})
                            max_layers_used = len(orders)
                        elif direction == 'SELL' and n_close > n_open:
                            orders.append({'price': n_close, 'lot': DEFAULT_LOT, 'time': next_dt.strftime('%H:%M')})
                            max_layers_used = len(orders)

                    j += 1

                # Nếu hết ngày chưa đóng, đóng tại nến cuối cùng
                if not basket_closed and j < n:
                    close_price = candles[j-1][4]
                    close_time = datetime.fromtimestamp(candles[j-1][0]/1000.0, tz=timezone.utc).astimezone(VN_TZ)

                # Tính tổng PnL $
                total_pnl_dollar = sum(
                    ((close_price - o['price']) if direction == 'BUY' else (o['price'] - close_price)) * o['lot'] * 100.0
                    for o in orders
                )

                # Gán nhãn cho AI:
                # 1 = Giao dịch an toàn (Lãi và số lệnh <= 4, DD < 15 giá)
                # 0 = Giao dịch rủi ro cao (Lỗ hoặc kẹt >= 5 lệnh hoặc DD > 15 giá)
                is_safe = 1 if (total_pnl_dollar > 0 and max_layers_used <= 4 and abs(max_dd_price) <= 15.0) else 0

                session_info = {
                    'date': current_date_str,
                    'year': current_year,
                    'day_of_week': day_of_week,
                    'direction': direction,
                    'features': [
                        round(atr_val, 3),
                        round(ema_diff, 3),
                        round(asian_range / (atr_val + 1e-5), 3),
                        round(asian_return, 3),
                        round(body_ratio, 3),
                        day_of_week
                    ],
                    'orders_count': max_layers_used,
                    'pnl_dollar': round(total_pnl_dollar, 2),
                    'pnl_price': round((close_price - orders[0]['price']) if direction == 'BUY' else (orders[0]['price'] - close_price), 2),
                    'max_dd_price': round(abs(max_dd_price), 2),
                    'is_win': total_pnl_dollar > 0,
                    'label_safe': is_safe,
                    'entry_price': round(orders[0]['price'], 2),
                    'close_price': round(close_price, 2),
                    'duration_bars': j - i
                }
                sessions.append(session_info)

        i += 1

    print(f"      -> Trích xuất được {len(sessions):,} chu kỳ giao dịch 10h.")
    return sessions


# ==========================================
# AI MODEL (TRAIN TRÊN 2011-2020)
# ==========================================
class AIClassifier:
    """
    Bộ phân loại thông minh Machine Learning.
    Hỗ trợ scikit-learn (RandomForest / GradientBoosting) nếu có cài đặt.
    Tự động fallback về Ensemble Linear/Logistic Regression thuần Python nếu môi trường chưa cài sklearn.
    """
    def __init__(self):
        self.has_sklearn = False
        try:
            from sklearn.ensemble import RandomForestClassifier
            self.model = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42)
            self.has_sklearn = True
        except ImportError:
            self.weights = None
            self.bias = 0.0

    def fit(self, X, y):
        if self.has_sklearn:
            self.model.fit(X, y)
        else:
            # Huấn luyện Logistic Classifier thuần Python bằng Gradient Descent
            n_samples = len(X)
            n_features = len(X[0])
            self.weights = [0.0] * n_features
            self.bias = 0.0
            lr = 0.05
            epochs = 300

            for _ in range(epochs):
                for k in range(n_samples):
                    # z = sum(w * x) + b
                    z = sum(w * x for w, x in zip(self.weights, X[k])) + self.bias
                    pred = 1.0 / (1.0 + math.exp(-max(min(z, 20), -20)))
                    err = y[k] - pred
                    for f_idx in range(n_features):
                        self.weights[f_idx] += lr * err * X[k][f_idx] / n_samples
                    self.bias += lr * err / n_samples

    def predict_proba_safe(self, x):
        """Trả về xác suất [0.0 - 1.0] phiên này là an toàn (Safe)"""
        if self.has_sklearn:
            proba = self.model.predict_proba([x])[0]
            # proba của class 1
            classes = list(self.model.classes_)
            if 1 in classes:
                return float(proba[classes.index(1)])
            return 0.5
        else:
            z = sum(w * val for w, val in zip(self.weights, x)) + self.bias
            return 1.0 / (1.0 + math.exp(-max(min(z, 20), -20)))


# ==========================================
# ĐÁNH GIÁ VÀ XUẤT BÁO CÁO WEB
# ==========================================
def run_pipeline(data_dir):
    candles = load_candles(data_dir)
    sessions = extract_daily_features_and_trades(candles)

    # Chia Train (2011-2020) và Test (2021-2025)
    train_sessions = [s for s in sessions if s['year'] in TRAIN_YEARS]
    test_sessions  = [s for s in sessions if s['year'] in TEST_YEARS]

    print(f"\n[3/4] Huấn luyện AI Model trên 10 năm Train ({len(train_sessions):,} phiên)...")
    X_train = [s['features'] for s in train_sessions]
    y_train = [s['label_safe'] for s in train_sessions]

    ai = AIClassifier()
    ai.fit(X_train, y_train)

    # Dự đoán xác suất cho toàn bộ các phiên
    for s in sessions:
        s['ai_safe_prob'] = round(ai.predict_proba_safe(s['features']), 3)

    print("[4/4] Chạy đánh giá đối đầu: Chiến lược Gốc vs Chiến lược Có AI Lọc...")
    
    # Hàm tính toán số liệu thống kê cho 1 danh sách lệnh
    def calculate_stats(trade_list, initial_balance=10000.0):
        if not trade_list:
            return {
                'total_trades': 0, 'win_rate': 0, 'net_pnl': 0, 'profit_factor': 0,
                'max_dd_percent': 0, 'max_dd_dollar': 0, 'max_layers': 0, 'avg_layers': 0,
                'equity_curve': [{'date': 'Start', 'balance': initial_balance}]
            }

        total_trades = len(trade_list)
        wins = [t for t in trade_list if t['pnl_dollar'] > 0]
        losses = [t for t in trade_list if t['pnl_dollar'] <= 0]
        win_rate = (len(wins) / total_trades) * 100.0

        total_profit = sum(t['pnl_dollar'] for t in wins)
        total_loss = abs(sum(t['pnl_dollar'] for t in losses))
        net_pnl = total_profit - total_loss
        profit_factor = (total_profit / total_loss) if total_loss > 0 else 99.0

        # Equity Curve & Drawdown
        balance = initial_balance
        peak = balance
        max_dd_dollar = 0.0
        max_dd_pct = 0.0
        equity_curve = [{'date': 'Start', 'balance': round(balance, 2)}]

        for t in trade_list:
            balance += t['pnl_dollar']
            equity_curve.append({'date': t['date'], 'balance': round(balance, 2)})
            if balance > peak:
                peak = balance
            dd = peak - balance
            dd_pct = (dd / peak) * 100.0 if peak > 0 else 0
            if dd > max_dd_dollar:
                max_dd_dollar = dd
            if dd_pct > max_dd_pct:
                max_dd_pct = dd_pct

        max_layers = max(t['orders_count'] for t in trade_list)
        avg_layers = sum(t['orders_count'] for t in trade_list) / total_trades

        return {
            'total_trades': total_trades,
            'win_rate': round(win_rate, 2),
            'net_pnl': round(net_pnl, 2),
            'profit_factor': round(profit_factor, 2),
            'max_dd_percent': round(max_dd_pct, 2),
            'max_dd_dollar': round(max_dd_dollar, 2),
            'max_layers': max_layers,
            'avg_layers': round(avg_layers, 2),
            'equity_curve': equity_curve
        }

    # NGƯỠNG LỌC AI (AI Filter Threshold):
    # Chỉ mở lệnh nếu AI đánh giá xác suất an toàn >= 0.55
    AI_THRESHOLD = 0.55

    # 1. Tập Train (2011 - 2020)
    train_baseline_trades = train_sessions
    train_ai_trades = [s for s in train_sessions if s['ai_safe_prob'] >= AI_THRESHOLD]

    # 2. Tập Test (2021 - 2025) - KIỂM ĐỊNH MÙ OUT-OF-SAMPLE
    test_baseline_trades = test_sessions
    test_ai_trades = [s for s in test_sessions if s['ai_safe_prob'] >= AI_THRESHOLD]

    stats = {
        'metadata': {
            'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'total_years': 15,
            'train_period': '2011 - 2020 (10 năm)',
            'test_period': '2021 - 2025 (5 năm)',
            'ai_filter_threshold': AI_THRESHOLD,
            'target_profit': DEFAULT_TARGET_PROFIT,
            'max_orders': DEFAULT_MAX_ORDERS,
            'lot_size': DEFAULT_LOT,
            'hard_sl': HARD_SL
        },
        'train': {
            'baseline': calculate_stats(train_baseline_trades),
            'ai': calculate_stats(train_ai_trades)
        },
        'test': {
            'baseline': calculate_stats(test_baseline_trades),
            'ai': calculate_stats(test_ai_trades)
        },
        'all_time': {
            'baseline': calculate_stats(sessions),
            'ai': calculate_stats([s for s in sessions if s['ai_safe_prob'] >= AI_THRESHOLD])
        },
        'recent_trades': sessions[-200:] # 200 lệnh gần nhất để hiển thị bảng log
    }

    # Xuất ra web_data.json
    output_path = os.path.join(data_dir, "web_data.json")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    print(f"\n=======================================================")
    print(f" ĐÃ XUẤT DỮ LIỆU THÀNH CÔNG: {output_path}")
    print(f"=======================================================")
    print(f"TẬP TEST (2021 - 2025) - KẾT QUẢ ĐỐI ĐẦU:")
    print(f"• KHÔNG CÓ AI : Winrate {stats['test']['baseline']['win_rate']}% | PnL ${stats['test']['baseline']['net_pnl']:,.2f} | MaxDD {stats['test']['baseline']['max_dd_percent']}%")
    print(f"• CÓ AI LỌC   : Winrate {stats['test']['ai']['win_rate']}% | PnL ${stats['test']['ai']['net_pnl']:,.2f} | MaxDD {stats['test']['ai']['max_dd_percent']}%")
    print(f"=======================================================\n")

    return stats


if __name__ == '__main__':
    current_dir = os.path.dirname(os.path.abspath(__file__))
    run_pipeline(current_dir)
