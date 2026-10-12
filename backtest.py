#!/usr/bin/env python3
"""
Backtest Strategy: Rocket 10h VN M15 DCA
Logic:
  - At 10:00 AM VN Time (UTC+7):
    - Wait for M15 candle to close (10:15 AM VN).
    - If candle is Bearish (Close < Open) -> Open BUY #1 at Close price.
    - If candle is Bullish (Close > Open) -> Open SELL #1 at Close price.
  - At each subsequent M15 candle close:
    1. Check Take Profit: If total floating profit of the basket >= target_profit (e.g. 10 giá)
       -> Close ALL orders at Close price. Basket ends (WIN).
    2. If not closed:
       - If BUY basket & this M15 candle is Bearish (Close < Open):
           -> Open additional BUY order at Close price (if max_orders not reached).
       - If SELL basket & this M15 candle is Bullish (Close > Open):
           -> Open additional SELL order at Close price (if max_orders not reached).
       - (If candle is opposite color, hold and wait for next M15 close).
    3. Check Stop Loss (if enabled):
       - If basket floating loss exceeds max_loss -> Close ALL orders (LOSS).
"""

import os
import glob
import csv
from datetime import datetime, timezone, timedelta

# ============================
# CẤU HÌNH THAM SỐ (CONFIG)
# ============================
START_HOUR_VN = 10          # 10h sáng giờ VN
START_MINUTE_VN = 0         # Nến bắt đầu lúc 10:00 (đóng lúc 10:15 VN)
TARGET_PROFIT = 10.0        # Chốt lời >= 10 giá (100 pips) tính trên giá trung bình
MAX_ORDERS = 10             # Giới hạn số lệnh nhồi tối đa (đặt None nếu không giới hạn)
LOT_SIZE = 0.01             # Kích thước lot cơ bản
LOT_MULTIPLIER = 1.0        # Hệ số nhân lot (1.0 = đi đều lot, 1.5 = Martingale nhẹ)
MIN_STEP_PRICE = 0.0        # Khoảng cách tối thiểu giữa 2 lệnh (giá, 0.0 = không lọc)
HARD_SL_PRICE = None        # Cắt lỗ tổng rổ (VD: 30.0 giá tính từ giá trung bình, None = không cắt)

VN_TZ = timezone(timedelta(hours=7))

class Order:
    def __init__(self, order_type, open_price, lot, open_time):
        self.order_type = order_type  # 'BUY' or 'SELL'
        self.open_price = open_price
        self.lot = lot
        self.open_time = open_time

class Basket:
    def __init__(self, direction, start_date):
        self.direction = direction    # 'BUY' or 'SELL'
        self.start_date = start_date
        self.orders = []
        self.is_closed = False
        self.close_price = None
        self.close_time = None
        self.pnl_dollar = 0.0
        self.pnl_points = 0.0

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

    def get_floating_profit_price(self, current_price):
        """Tính số giá lãi/lỗ so với giá trung bình"""
        if self.direction == 'BUY':
            return current_price - self.avg_price
        else:
            return self.avg_price - current_price

    def get_floating_profit_dollar(self, current_price):
        """Vàng: 1 lot, biến động 1 giá = $100"""
        total_pnl = 0.0
        for o in self.orders:
            diff = (current_price - o.open_price) if o.order_type == 'BUY' else (o.open_price - current_price)
            total_pnl += diff * o.lot * 100.0
        return total_pnl

    def close(self, close_price, close_time):
        self.is_closed = True
        self.close_price = close_price
        self.close_time = close_time
        self.pnl_dollar = self.get_floating_profit_dollar(close_price)
        self.pnl_points = self.get_floating_profit_price(close_price)


def load_m15_data(data_dir):
    """Đọc và sắp xếp toàn bộ file CSV M15 theo timestamp"""
    files = sorted(glob.glob(os.path.join(data_dir, "XAUUSD_*_m15.csv")))
    if not files:
        print(f"Không tìm thấy file XAUUSD_*_m15.csv trong {data_dir}")
        return []

    print(f"Đang đọc {len(files)} file dữ liệu M15...")
    candles = []
    for filepath in files:
        filename = os.path.basename(filepath)
        with open(filepath, 'r', encoding='utf-8') as f:
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

    # Sắp xếp theo timestamp tăng dần
    candles.sort(key=lambda x: x[0])
    print(f"-> Tổng số nến M15 đã tải: {len(candles):,}")
    return candles


def run_backtest(candles, target_profit=TARGET_PROFIT, max_orders=MAX_ORDERS,
                 lot_size=LOT_SIZE, lot_mult=LOT_MULTIPLIER, min_step=MIN_STEP_PRICE,
                 hard_sl=HARD_SL_PRICE):
    baskets = []
    active_basket = None
    last_session_date = None

    for i, candle in enumerate(candles):
        ts, c_open, c_high, c_low, c_close, vol = candle
        # Quy đổi sang giờ VN
        dt_utc = datetime.fromtimestamp(ts / 1000.0, tz=timezone.utc)
        dt_vn = dt_utc.astimezone(VN_TZ)

        date_key = dt_vn.date()
        hour = dt_vn.hour
        minute = dt_vn.minute

        # ----------------------------------------------------
        # 1. KIỂM TRA ĐÓNG LỆNH CỦA BASKET ĐANG CHẠY TẠI ĐÓNG NẾN
        # ----------------------------------------------------
        if active_basket is not None:
            # Lãi theo giá so với giá trung bình
            floating_diff = active_basket.get_floating_profit_price(c_close)

            # Điều kiện Take Profit: Đóng nến M15 và đạt >= target
            if floating_diff >= target_profit:
                active_basket.close(c_close, dt_vn)
                baskets.append(active_basket)
                active_basket = None
            # Điều kiện Hard Stop Loss (nếu có cài đặt)
            elif hard_sl is not None and floating_diff <= -hard_sl:
                active_basket.close(c_close, dt_vn)
                baskets.append(active_basket)
                active_basket = None
            else:
                # Chưa chốt lời: Kiểm tra xem có nhồi lệnh thêm không
                can_add = (max_orders is None) or (active_basket.order_count < max_orders)
                if can_add:
                    last_order_price = active_basket.orders[-1].open_price
                    step_diff = abs(c_close - last_order_price)

                    if step_diff >= min_step:
                        # Quy tắc nhồi BUY: Nến M15 đóng Đỏ (Close < Open)
                        if active_basket.direction == 'BUY' and c_close < c_open:
                            next_lot = round(lot_size * (lot_mult ** active_basket.order_count), 2)
                            active_basket.add_order(c_close, next_lot, dt_vn)

                        # Quy tắc nhồi SELL: Nến M15 đóng Xanh (Close > Open)
                        elif active_basket.direction == 'SELL' and c_close > c_open:
                            next_lot = round(lot_size * (lot_mult ** active_basket.order_count), 2)
                            active_basket.add_order(c_close, next_lot, dt_vn)

        # ----------------------------------------------------
        # 2. KÍCH HOẠT VÀO LỆNH MỚI LÚC 10H VN (NẾU CHƯA CÓ BASKET)
        # ----------------------------------------------------
        # Nến 10:00 VN: mở lúc 10:00, đóng lúc 10:15
        if active_basket is None:
            if hour == START_HOUR_VN and minute == START_MINUTE_VN:
                # Mỗi ngày chỉ mở 1 chu kỳ vào khung 10h sáng
                if last_session_date != date_key:
                    last_session_date = date_key

                    # Nến Đỏ -> Mở BUY 1
                    if c_close < c_open:
                        active_basket = Basket('BUY', dt_vn)
                        active_basket.add_order(c_close, lot_size, dt_vn)

                    # Nến Xanh -> Mở SELL 1
                    elif c_close > c_open:
                        active_basket = Basket('SELL', dt_vn)
                        active_basket.add_order(c_close, lot_size, dt_vn)

    # Nếu còn basket chưa đóng ở cuối dữ liệu
    if active_basket is not None:
        last_candle = candles[-1]
        active_basket.close(last_candle[4], datetime.fromtimestamp(last_candle[0]/1000.0, tz=timezone.utc).astimezone(VN_TZ))
        baskets.append(active_basket)

    return baskets


def print_report(baskets, initial_balance=10000.0):
    if not baskets:
        print("Không có giao dịch nào được thực hiện.")
        return

    total_trades = len(baskets)
    wins = [b for b in baskets if b.pnl_dollar > 0]
    losses = [b for b in baskets if b.pnl_dollar <= 0]
    win_rate = (len(wins) / total_trades) * 100.0 if total_trades > 0 else 0

    total_profit = sum(b.pnl_dollar for b in wins)
    total_loss = abs(sum(b.pnl_dollar for b in losses))
    net_pnl = total_profit - total_loss
    profit_factor = (total_profit / total_loss) if total_loss > 0 else float('inf')

    # Thống kê số lượng lệnh trong chuỗi DCA
    order_counts = [b.order_count for b in baskets]
    max_layers = max(order_counts)
    avg_layers = sum(order_counts) / len(order_counts)

    # Tính Max Drawdown theo Balance/Equity sau mỗi basket
    balance = initial_balance
    peak = balance
    max_dd_dollar = 0.0
    max_dd_percent = 0.0

    for b in baskets:
        balance += b.pnl_dollar
        if balance > peak:
            peak = balance
        dd = peak - balance
        dd_pct = (dd / peak) * 100.0 if peak > 0 else 0
        if dd > max_dd_dollar:
            max_dd_dollar = dd
        if dd_pct > max_dd_percent:
            max_dd_percent = dd_pct

    print("\n" + "="*60)
    print("           KẾT QUẢ BACKTEST CHIẾN LƯỢC ROCKET 10H M15")
    print("="*60)
    print(f"Tổng số chu kỳ (Basket)        : {total_trades:,}")
    print(f"Tỷ lệ thắng (Winrate)          : {win_rate:.2f}% ({len(wins)} Win / {len(losses)} Loss)")
    print(f"Lợi nhuận ròng (Net Profit)    : ${net_pnl:,.2f}")
    print(f"Profit Factor                  : {profit_factor:.2f}")
    print(f"Max Drawdown (Sụt giảm lớn nhất): ${max_dd_dollar:,.2f} ({max_dd_percent:.2f}%)")
    print(f"Số lệnh DCA tối đa từng gặp    : {max_layers} lệnh")
    print(f"Số lệnh DCA trung bình         : {avg_layers:.1f} lệnh")
    print("-" * 60)
    print("Phân bố số lệnh nhồi trong các chu kỳ:")
    from collections import Counter
    dist = Counter(order_counts)
    for k in sorted(dist.keys()):
        pct = (dist[k] / total_trades) * 100.0
        bar = "█" * int(pct / 2)
        print(f"  • {k:2d} lệnh: {dist[k]:4d} chu kỳ ({pct:5.1f}%) {bar}")
    print("="*60 + "\n")


if __name__ == '__main__':
    current_dir = os.path.dirname(os.path.abspath(__file__))
    candles = load_m15_data(current_dir)
    if candles:
        baskets = run_backtest(candles)
        print_report(baskets)
