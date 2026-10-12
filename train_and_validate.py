#!/usr/bin/env python3
"""
Framework: Train (In-Sample 2011-2020) & Test (Out-of-Sample 2021-2025)
Mục tiêu:
  - 10 năm đầu (2011 - 2020): Tập Training / Optimization để AI tìm kiếm bộ tham số / quy tắc tối ưu.
  - 5 năm sau (2021 - 2025): Tập Testing (Blind Out-of-Sample) để kiểm định độ vững chắc (Robustness),
    đánh giá xem chiến lược có bị "học vẹt" (Overfitting) hay không.
"""

import os
import glob
import csv
from datetime import datetime, timezone, timedelta
from collections import Counter

VN_TZ = timezone(timedelta(hours=7))

TRAIN_YEARS = set(range(2011, 2021))  # 2011 -> 2020 (10 năm)
TEST_YEARS  = set(range(2021, 2026))  # 2021 -> 2025 (5 năm)


def load_partitioned_data(data_dir):
    """Phân tách dữ liệu thành 2 tập riêng biệt: Train (10 năm) và Test (5 năm)"""
    train_candles = []
    test_candles = []

    files = sorted(glob.glob(os.path.join(data_dir, "XAUUSD_*_m15.csv")))
    print(f"-> Tìm thấy {len(files)} files M15. Đang nạp và phân tách dữ liệu...")

    for fpath in files:
        fname = os.path.basename(fpath)
        # Lấy năm từ tên file, ví dụ XAUUSD_2015_m15.csv -> 2015
        try:
            year = int(fname.split('_')[1])
        except (IndexError, ValueError):
            continue

        bucket = None
        if year in TRAIN_YEARS:
            bucket = train_candles
        elif year in TEST_YEARS:
            bucket = test_candles
        else:
            continue

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
                    bucket.append((ts, o, h, l, c, v))
                except (ValueError, KeyError):
                    continue

    train_candles.sort(key=lambda x: x[0])
    test_candles.sort(key=lambda x: x[0])

    print(f"   • Tập Training (2011 - 2020): {len(train_candles):,} nến M15")
    print(f"   • Tập Testing  (2021 - 2025): {len(test_candles):,} nến M15")
    return train_candles, test_candles


class Order:
    def __init__(self, order_type, open_price, lot, open_time):
        self.order_type = order_type
        self.open_price = open_price
        self.lot = lot
        self.open_time = open_time


class Basket:
    def __init__(self, direction, start_date):
        self.direction = direction
        self.start_date = start_date
        self.orders = []
        self.pnl_dollar = 0.0
        self.pnl_price = 0.0

    def add_order(self, price, lot, dt):
        self.orders.append(Order(self.direction, price, lot, dt))

    @property
    def total_lots(self):
        return sum(o.lot for o in self.orders)

    @property
    def avg_price(self):
        if not self.orders:
            return 0.0
        return sum(o.open_price * o.lot for o in self.orders) / self.total_lots

    @property
    def order_count(self):
        return len(self.orders)

    def get_floating_price(self, current_price):
        if self.direction == 'BUY':
            return current_price - self.avg_price
        else:
            return self.avg_price - current_price

    def close(self, close_price):
        total_pnl = 0.0
        for o in self.orders:
            diff = (close_price - o.open_price) if o.order_type == 'BUY' else (o.open_price - close_price)
            total_pnl += diff * o.lot * 100.0  # 1 lot Vàng 1 giá = $100
        self.pnl_dollar = total_pnl
        self.pnl_price = self.get_floating_price(close_price)


def simulate(candles, params):
    """Chạy mô phỏng chiến lược với bộ tham số cho trước"""
    start_hour = params.get('start_hour', 10)
    start_minute = params.get('start_minute', 0)
    target_profit = params.get('target_profit', 10.0)
    max_orders = params.get('max_orders', 10)
    lot_size = params.get('lot_size', 0.01)
    lot_mult = params.get('lot_mult', 1.0)
    min_step = params.get('min_step', 0.0)
    hard_sl = params.get('hard_sl', None)

    baskets = []
    active_basket = None
    last_session_date = None

    for candle in candles:
        ts, c_open, c_high, c_low, c_close, vol = candle
        dt_utc = datetime.fromtimestamp(ts / 1000.0, tz=timezone.utc)
        dt_vn = dt_utc.astimezone(VN_TZ)

        date_key = dt_vn.date()
        hour = dt_vn.hour
        minute = dt_vn.minute

        # 1. Kiểm tra rổ lệnh đang mở tại đóng nến
        if active_basket is not None:
            floating_diff = active_basket.get_floating_price(c_close)

            # Chốt lời >= target
            if floating_diff >= target_profit:
                active_basket.close(c_close)
                baskets.append(active_basket)
                active_basket = None
            # Cắt lỗ cứng (nếu có)
            elif hard_sl is not None and floating_diff <= -hard_sl:
                active_basket.close(c_close)
                baskets.append(active_basket)
                active_basket = None
            else:
                # Nhồi lệnh DCA
                can_add = (max_orders is None) or (active_basket.order_count < max_orders)
                if can_add:
                    last_price = active_basket.orders[-1].open_price
                    if abs(c_close - last_price) >= min_step:
                        if active_basket.direction == 'BUY' and c_close < c_open:
                            next_lot = round(lot_size * (lot_mult ** active_basket.order_count), 2)
                            active_basket.add_order(c_close, next_lot, dt_vn)
                        elif active_basket.direction == 'SELL' and c_close > c_open:
                            next_lot = round(lot_size * (lot_mult ** active_basket.order_count), 2)
                            active_basket.add_order(c_close, next_lot, dt_vn)

        # 2. Kích hoạt vào lệnh mới lúc 10h sáng
        if active_basket is None:
            if hour == start_hour and minute == start_minute:
                if last_session_date != date_key:
                    last_session_date = date_key
                    if c_close < c_open:
                        active_basket = Basket('BUY', dt_vn)
                        active_basket.add_order(c_close, lot_size, dt_vn)
                    elif c_close > c_open:
                        active_basket = Basket('SELL', dt_vn)
                        active_basket.add_order(c_close, lot_size, dt_vn)

    if active_basket is not None:
        active_basket.close(candles[-1][4])
        baskets.append(active_basket)

    return baskets


def compute_metrics(baskets, initial_balance=10000.0):
    if not baskets:
        return None

    total_trades = len(baskets)
    wins = [b for b in baskets if b.pnl_dollar > 0]
    losses = [b for b in baskets if b.pnl_dollar <= 0]
    win_rate = (len(wins) / total_trades) * 100.0 if total_trades > 0 else 0

    total_profit = sum(b.pnl_dollar for b in wins)
    total_loss = abs(sum(b.pnl_dollar for b in losses))
    net_pnl = total_profit - total_loss
    profit_factor = (total_profit / total_loss) if total_loss > 0 else (99.0 if total_profit > 0 else 0.0)

    # Max Drawdown
    balance = initial_balance
    peak = balance
    max_dd = 0.0
    for b in baskets:
        balance += b.pnl_dollar
        if balance > peak:
            peak = balance
        dd = (peak - balance) / peak * 100.0 if peak > 0 else 0
        if dd > max_dd:
            max_dd = dd

    max_layers = max(b.order_count for b in baskets)
    avg_layers = sum(b.order_count for b in baskets) / total_trades

    # Điểm đánh giá chất lượng (Fitness Score): Càng cao càng tốt
    # Cân bằng giữa Lợi nhuận, Tỷ lệ thắng và khống chế Max Drawdown
    fitness = (net_pnl / initial_balance) * (win_rate / 100.0) / (1.0 + max_dd / 10.0)

    return {
        'total_trades': total_trades,
        'win_rate': win_rate,
        'net_pnl': net_pnl,
        'profit_factor': profit_factor,
        'max_dd_pct': max_dd,
        'max_layers': max_layers,
        'avg_layers': avg_layers,
        'fitness': fitness
    }


def run_training_and_testing():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    train_candles, test_candles = load_partitioned_data(current_dir)

    if not train_candles or not test_candles:
        print("Lỗi: Không đủ dữ liệu để chia tách Train/Test.")
        return

    print("\n" + "="*70)
    print(" BƯỚC 1: TRAINING / OPTIMIZATION TRÊN 10 NĂM ĐẦU (2011 - 2020)")
    print("="*70)
    print("Đang quét qua không gian tham số để AI tìm bộ quy tắc có Fitness cao nhất...")

    # Không gian tìm kiếm tham số (Search Space)
    candidates = []
    for tp in [5.0, 8.0, 10.0, 15.0]:               # Target profit (giá)
        for max_ord in [4, 6, 8, 10]:                # Số lệnh tối đa
            for mult in [1.0, 1.2]:                   # Hệ số nhân lot
                for step in [0.0, 2.0, 4.0]:          # Khoảng cách tối thiểu giữa 2 lệnh
                    candidates.append({
                        'start_hour': 10,
                        'start_minute': 0,
                        'target_profit': tp,
                        'max_orders': max_ord,
                        'lot_size': 0.01,
                        'lot_mult': mult,
                        'min_step': step,
                        'hard_sl': 35.0               # Bảo vệ vốn với mức SL 35 giá
                    })

    print(f"Tổng số bộ tham số cần thử nghiệm: {len(candidates)}")
    
    best_params = None
    best_train_metrics = None
    best_fitness = -float('inf')

    for i, p in enumerate(candidates):
        baskets = simulate(train_candles, p)
        metrics = compute_metrics(baskets)
        if metrics and metrics['fitness'] > best_fitness:
            best_fitness = metrics['fitness']
            best_params = p
            best_train_metrics = metrics

    print("\n[VÔ ĐỊCH TẬP TRAINING (2011-2020)]:")
    print(f"  • Target Profit   : {best_params['target_profit']} giá")
    print(f"  • Max Orders      : {best_params['max_orders']} lệnh")
    print(f"  • Lot Multiplier  : {best_params['lot_mult']}x")
    print(f"  • Min Step Price  : {best_params['min_step']} giá")
    print(f"  • Hard Stop Loss  : {best_params['hard_sl']} giá")

    print("\n" + "="*70)
    print(" BƯỚC 2: KIỂM ĐỊNH MÙ (BLIND TEST) TRÊN 5 NĂM SAU (2021 - 2025)")
    print("="*70)
    print("Áp dụng nguyên vẹn bộ tham số tốt nhất vào 5 năm dữ liệu chưa từng thấy...")

    test_baskets = simulate(test_candles, best_params)
    test_metrics = compute_metrics(test_baskets)

    # In bảng so sánh đối đầu
    print("\n" + "="*70)
    print("           BẢNG SO SÁNH HIỆU QUẢ: TRAINING vs TESTING")
    print("="*70)
    header = f"{'CHỈ SỐ':<25} | {'TRAIN (2011-2020)':<20} | {'TEST (2021-2025)':<20}"
    print(header)
    print("-" * 70)
    print(f"{'Thời gian':<25} | {'10 Năm':<20} | {'5 Năm':<20}")
    print(f"{'Số chu kỳ (Trades)':<25} | {best_train_metrics['total_trades']:<20,d} | {test_metrics['total_trades']:<20,d}")
    print(f"{'Tỷ lệ thắng (Winrate)':<25} | {best_train_metrics['win_rate']:<19.2f}% | {test_metrics['win_rate']:<19.2f}%")
    print(f"{'Lợi nhuận ròng':<25} | ${best_train_metrics['net_pnl']:<19,.2f} | ${test_metrics['net_pnl']:<19,.2f}")
    print(f"{'Profit Factor':<25} | {best_train_metrics['profit_factor']:<20.2f} | {test_metrics['profit_factor']:<20.2f}")
    print(f"{'Max Drawdown':<25} | {best_train_metrics['max_dd_pct']:<19.2f}% | {test_metrics['max_dd_pct']:<19.2f}%")
    print(f"{'Số lệnh nhồi tối đa':<25} | {best_train_metrics['max_layers']:<20d} | {test_metrics['max_layers']:<20d}")
    print(f"{'Số lệnh nhồi trung bình':<25} | {best_train_metrics['avg_layers']:<20.2f} | {test_metrics['avg_layers']:<20.2f}")
    print("="*70)

    # Đánh giá suy thoái (Degradation Analysis)
    wr_drop = best_train_metrics['win_rate'] - test_metrics['win_rate']
    print("\n[ĐÁNH GIÁ ĐỘ VỮNG CHẮC (ROBUSTNESS)]:")
    if test_metrics['profit_factor'] > 1.3 and wr_drop < 5.0:
        print("  -> CHIẾN LƯỢC ĐẠT CHUẨN VỮNG CHẮC: Hiệu quả trên tập 5 năm sau được duy trì tốt, không bị Overfitting!")
    else:
        print(f"  -> CẢNH BÁO SUY GIẢM: Winrate giảm {wr_drop:.1f}% hoặc Profit Factor thấp hơn kỳ vọng khi thị trường đổi pha.")
    print("="*70 + "\n")


if __name__ == '__main__':
    run_training_and_testing()
