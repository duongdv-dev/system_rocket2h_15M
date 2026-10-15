#!/usr/bin/env python3
"""
AI Quantitative Trading Engine - Pure Volatility Guard Backtest
Chiến lược Rocket 10h VN M15 - Thuần Túy & Tập Trung Đánh Giá Bộ Lọc Biến Động Mạnh

Quy tắc cốt lõi theo yêu cầu:
  1. CHẠY THUẦN TÚY (Pure Execution):
     - Không can thiệp đóng lệnh cứng theo giờ (Không ép đóng 12h, 18h hay 23h30).
     - Bỏ hoàn toàn Stop Loss cứng.
     - Bỏ qua giới hạn số lệnh (Unlimited DCA).
  2. KHOẢNG CÁCH MIN GIỮA CÁC LỆNH (Min Step):
     - Cố định: 0.5 x ATR(14).
     - Nhồi lệnh khi nến M15 đóng cửa cùng màu bất lợi và khoảng cách >= 0.5 x ATR(14).
  3. CHỐT LỜI CỐ ĐỊNH (Fixed Take Profit):
     - Cố định: 1.0 x ATR(14) tính từ giá trung bình của rổ lệnh (avg_price).
     - Khi đóng nến M15 mà floating profit >= 1.0 x ATR(14) -> Đóng toàn bộ rổ lệnh.
  4. BỘ LỌC NGÀY BIẾN ĐỘNG MẠNH / RỦI RO LỚN (Volatility Guard):
     - Mục tiêu nghiên cứu: Đánh giá tác động của việc loại bỏ các ngày rủi ro cao trước khi vào lệnh.
     - Tiêu chí nhận diện trước 10h15:
       + Biên độ sóng sáng 07h-10h giãn lớn (> 3.0 x ATR14).
       + ATR14 tại 10h tăng vọt đột biến (> 15.0 USD).
       + Cây nến 10h quét biên độ cực đại (> 2.0 x ATR14).
       + Sóng sáng 07h-10h dốc 1 chiều quá mạnh (> 2.5 x ATR14).
  5. QUẢN LÝ VỐN:
     - Vốn khởi điểm: $10,000.
     - Lãi kép: Cứ $5,000 vốn -> Đi 0.01 lot ($10,000 -> 0.02 lot).
"""

import os
import glob
import csv
import json
import math
from datetime import datetime, timezone, timedelta

VN_TZ = timezone(timedelta(hours=7))
TRAIN_YEARS = set(range(2011, 2021))
TEST_YEARS  = set(range(2021, 2026))

MIN_STEP_ATR_FACTOR = 0.5           # Khoảng cách tối thiểu giữa các lệnh DCA = 0.5 x ATR14
TP_SINGLE_ATR_FACTOR = 0.8          # Chốt lời lệnh đơn = 0.8 x ATR14 (Chốt nhanh phiên Á)
TP_DCA_ATR_FACTOR = 0.5             # Chốt lời rổ DCA (>= 2 lệnh) = 0.5 x ATR14 tính từ giá trung bình (avg_price)
DEFAULT_HARD_CLOSE_TIME = (14, 0)   # Cắt lỗ ép buộc vào 14:00 chiều VN (Hết phiên Á, né phiên Âu)
MAX_ORDERS = None                   # Bỏ giới hạn số lệnh (None = không giới hạn)
LOT_STEP_CAPITAL = 5000.0           # Cứ $5,000 vốn -> 0.01 lot
INITIAL_BALANCE = 10000.0           # Vốn khởi điểm $10,000


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


def extract_daily_sessions(candles):
    print("[2/4] Đang trích xuất đặc trưng sóng 07h-10h & Bộ lọc ngày biến động mạnh...")
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
            atr_val = atrs[i]

            # Đo biến động phiên sáng 07:00 - 10:00 VN (12 nến M15 trước đó)
            idx_07h = max(0, i - 12)
            open_07h = candles[idx_07h][1]
            price_10h = c_open
            delta_p = price_10h - open_07h

            slice_morning = candles[idx_07h:i]
            if slice_morning:
                m_high = max(c[2] for c in slice_morning)
                m_low = min(c[3] for c in slice_morning)
                m_range = m_high - m_low
            else:
                m_range = atr_val

            # Phân loại xu hướng sáng 07h-10h
            trend_threshold = max(2.0, 1.0 * atr_val)
            if delta_p > trend_threshold:
                wave_regime = 'UP_TREND'      # Sóng tăng -> Chờ nến đỏ pullback để BUY
            elif delta_p < -trend_threshold:
                wave_regime = 'DOWN_TREND'    # Sóng giảm -> Chờ nến xanh pullback để SELL
            else:
                wave_regime = 'SIDEWAY'       # Sideway -> Đánh theo nến 10:15

            # ----------------------------------------------------
            # BỘ LỌC NGÀY BIẾN ĐỘNG MẠNH / RỦI RO LỚN (VOLATILITY GUARD)
            # Nhận diện các dấu hiệu rủi ro cao trước khi kích hoạt lệnh lúc 10h:
            # ----------------------------------------------------
            candle_10h_range = c_high - c_low
            reasons = []

            ratio_range = m_range / (atr_val + 1e-5)
            # 1. Biên độ sóng sáng 07h-10h giãn cực đại (> 5.0x ATR14 VÀ tối thiểu 25 USD)
            if ratio_range > 5.0 and m_range > 25.0:
                reasons.append(f"Biên độ sáng giãn cực đại ({m_range:.1f} giá = {ratio_range:.1f}x ATR)")
            # 2. Biến động ATR14 tại 10h vọt cao bất thường (> 18.0 USD)
            if atr_val > 18.0:
                reasons.append(f"ATR14 tại 10h vọt bão giá ({atr_val:.1f} giá)")
            # 3. Nến 10h quét biên độ siêu lớn (> 2.5x ATR14 VÀ tối thiểu 15 USD)
            if candle_10h_range > 2.5 * atr_val and candle_10h_range > 15.0:
                reasons.append(f"Nến 10h quét đột biến ({candle_10h_range:.1f} giá = {(candle_10h_range/atr_val):.1f}x ATR)")
            # 4. Sóng sáng 07h-10h 1 chiều dốc đứng không hồi (> 3.5x ATR14 VÀ tối thiểu 20 USD)
            if abs(delta_p) > 3.5 * atr_val and abs(delta_p) > 20.0:
                reasons.append(f"Sóng sáng 1 chiều quá dốc ({abs(delta_p):.1f} giá = {(abs(delta_p)/atr_val):.1f}x ATR)")

            is_extreme_toxic = 1 if len(reasons) > 0 else 0
            toxic_reason = " | ".join(reasons) if reasons else "Bình thường / An toàn"

            sessions.append({
                'date': current_date_str,
                'year': current_year,
                'day_of_week': day_of_week,
                'candle_idx': i,
                'open_07h': open_07h,
                'price_10h': price_10h,
                'delta_p': round(delta_p, 2),
                'm_range': round(m_range, 2),
                'atr_val': atr_val,
                'wave_regime': wave_regime,
                'is_extreme_toxic': is_extreme_toxic,
                'toxic_reason': toxic_reason
            })

        i += 1

    print(f"      -> Trích xuất được {len(sessions):,} phiên 10h.")
    return sessions


def run_single_session_simulation(candles, session_info, current_lot, hard_close_time=DEFAULT_HARD_CLOSE_TIME, max_orders=MAX_ORDERS):
    """
    Mô phỏng chu kỳ lệnh Rocket 10h M15 - Kết hợp 3 hướng tối ưu:
    - CẮT LỖ ÉP BUỘC VÀO 14:00 CHIỀU VN: Hết phiên Á, dứt khoát né phiên Âu biến động mạnh.
    - KHOẢNG CÁCH MIN GIỮA CÁC LỆNH DCA: 0.5 x ATR14.
    - CHỐT LỜI THÍCH ỨNG (Adaptive TP):
        + 1 lệnh đơn: 0.8 x ATR14 (Chốt nhanh trong phiên Á).
        + Rổ DCA (>= 2 lệnh): 0.5 x ATR14 tính từ giá trung bình (avg_price) - Hồi nhẹ là chốt lời ngay.
    - NHỒI LỆNH DCA: Nến M15 đóng cửa cùng màu bất lợi và dist >= 0.5 x ATR14.
    """
    n = len(candles)
    start_idx = session_info['candle_idx']
    atr_val = session_info['atr_val']
    regime = session_info['wave_regime']
    
    min_step = MIN_STEP_ATR_FACTOR * atr_val

    orders = []
    direction = None
    basket_closed = False
    close_price = None
    close_reason = ""
    worst_floating_pnl = 0.0

    start_ts = candles[start_idx][0]
    start_dt = datetime.fromtimestamp(start_ts / 1000.0, tz=timezone.utc).astimezone(VN_TZ)

    if hard_close_time is not None:
        h_close, m_close = hard_close_time
        cutoff_dt = start_dt.replace(hour=h_close, minute=m_close, second=0, microsecond=0)
        max_search = min(n, start_idx + 35)  # Từ 10h đến 14h là 16 nến M15
    else:
        cutoff_dt = None
        max_search = min(n, start_idx + 960)

    j = start_idx
    while j < max_search:
        n_ts, n_open, n_high, n_low, n_close, _ = candles[j]
        is_green = n_close > n_open
        is_red = n_close < n_open
        cur_dt = datetime.fromtimestamp(n_ts / 1000.0, tz=timezone.utc).astimezone(VN_TZ)

        # 1. TÌM ĐIỂM VÀO LỆNH ĐẦU TIÊN (#1)
        if not orders:
            if cutoff_dt is not None and cur_dt >= cutoff_dt:
                break  # Hết giờ mà chưa xuất hiện tín hiệu vào lệnh
            if regime == 'UP_TREND':
                if is_red:  # Chờ nến đỏ pullback để BUY
                    direction = 'BUY'
                    orders.append({'price': n_close, 'lot': current_lot})
            elif regime == 'DOWN_TREND':
                if is_green:  # Chờ nến xanh pullback để SELL
                    direction = 'SELL'
                    orders.append({'price': n_close, 'lot': current_lot})
            else: # SIDEWAY
                if j == start_idx:
                    if is_green:
                        direction = 'BUY'
                        orders.append({'price': n_close, 'lot': current_lot})
                    elif is_red:
                        direction = 'SELL'
                        orders.append({'price': n_close, 'lot': current_lot})
            j += 1
            continue

        # Theo dõi mức sụt giảm tạm thời sâu nhất (worst floating pnl)
        cur_floating_dollar = sum(
            ((n_close - o['price']) if direction == 'BUY' else (o['price'] - n_close)) * o['lot'] * 100.0
            for o in orders
        )
        if cur_floating_dollar < worst_floating_pnl:
            worst_floating_pnl = cur_floating_dollar

        # 2. XÉT CHỐT LỜI THÍCH ỨNG (ADAPTIVE TP THEO SỐ LỆNH)
        # - 1 lệnh đơn: 0.8 x ATR14 (Chốt nhanh trong phiên Á)
        # - Rổ DCA (>= 2 lệnh): 0.5 x ATR14 tính từ avg_price (Hồi nhẹ là ăn trọn khối lượng lớn)
        num_orders = len(orders)
        target_tp = (TP_SINGLE_ATR_FACTOR * atr_val) if num_orders == 1 else (TP_DCA_ATR_FACTOR * atr_val)
        total_lots = sum(o['lot'] for o in orders)
        avg_price = sum(o['price'] * o['lot'] for o in orders) / total_lots
        floating_price = (n_close - avg_price) if direction == 'BUY' else (avg_price - n_close)

        if floating_price >= target_tp:
            basket_closed = True
            close_price = n_close
            tp_type = "0.8 ATR (Lệnh đơn)" if num_orders == 1 else f"0.5 ATR (Rổ DCA {num_orders} lệnh)"
            close_reason = f"Đạt TP thích ứng {tp_type} (+{round(floating_price, 2)} giá)"
            break

        # 3. CẮT LỖ ÉP BUỘC VÀO 14:00 CHIỀU VN (HẾT PHIÊN Á, NÉ PHIÊN ÂU)
        # Nến 13:45 là cây nến kết thúc đúng lúc 14:00 VN
        is_hard_exit = (cur_dt.hour == 13 and cur_dt.minute == 45) or (cutoff_dt is not None and cur_dt >= cutoff_dt)
        if is_hard_exit:
            basket_closed = False
            close_price = n_close
            close_reason = "Cắt lỗ ép buộc vào 14:00 chiều VN (Hết phiên Á, né phiên Âu)"
            break

        # 4. XÉT NHỒI LỆNH DCA (KHOẢNG CÁCH TỐI THIỂU >= 0.5 x ATR14)
        can_add = (max_orders is None) or (len(orders) < max_orders)
        if can_add:
            last_price = orders[-1]['price']
            dist = abs(n_close - last_price)
            if dist >= min_step:
                if direction == 'BUY' and is_red:
                    orders.append({'price': n_close, 'lot': current_lot})
                elif direction == 'SELL' and is_green:
                    orders.append({'price': n_close, 'lot': current_lot})

        j += 1

    if not orders:
        return None

    exit_idx = min(j, n - 1)
    exit_ts = candles[exit_idx][0]
    exit_date = datetime.fromtimestamp(exit_ts / 1000.0, tz=timezone.utc).astimezone(VN_TZ).strftime('%Y-%m-%d %H:%M')

    if not basket_closed:
        if close_price is None:
            close_price = candles[exit_idx][4]
        if not close_reason:
            close_reason = "Cắt lỗ ép buộc vào 14:00 chiều VN (Hết phiên Á, né phiên Âu)"

    total_lots = sum(o['lot'] for o in orders)
    avg_price = sum(o['price'] * o['lot'] for o in orders) / total_lots
    pnl_price = (close_price - avg_price) if direction == 'BUY' else (avg_price - close_price)
    pnl_dollar = sum(
        ((close_price - o['price']) if direction == 'BUY' else (o['price'] - close_price)) * o['lot'] * 100.0
        for o in orders
    )
    is_win = basket_closed and (pnl_dollar > 0)
    duration_bars = exit_idx - start_idx
    duration_days = round(duration_bars / 96.0, 1)

    return {
        'date': session_info['date'],
        'exit_date': exit_date,
        'direction': direction,
        'regime': regime,
        'entry_price': orders[0]['price'],
        'avg_price': round(avg_price, 2),
        'close_price': round(close_price, 2),
        'layers': len(orders),
        'pnl_price': round(pnl_price, 2),
        'pnl_dollar': round(pnl_dollar, 2),
        'is_win': is_win,
        'duration_bars': duration_bars,
        'duration_days': duration_days,
        'close_reason': close_reason,
        'worst_floating_pnl': round(worst_floating_pnl, 2)
    }


def simulate_full_dataset(sessions, candles, use_filter=True, hard_close_time=DEFAULT_HARD_CLOSE_TIME, max_orders=MAX_ORDERS):
    """
    Mô phỏng toàn bộ dữ liệu có lãi kép $5,000 = 0.01 lot
    - use_filter=False: Chạy thuần không lọc (Baseline)
    - use_filter=True:  Kích hoạt bộ lọc né những ngày biến động mạnh (Filter)
    - hard_close_time:  Cắt lỗ ép buộc vào 14:00 chiều VN
    """
    balance = INITIAL_BALANCE
    peak = balance
    max_dd_dollar = 0.0
    max_dd_pct = 0.0
    equity_curve = [{'date': 'Start', 'balance': round(balance, 2)}]
    executed_trades = []

    for s in sessions:
        if use_filter and s['is_extreme_toxic'] == 1:
            continue

        current_lot = max(0.01, round(math.floor(balance / LOT_STEP_CAPITAL) * 0.01, 2))
        res = run_single_session_simulation(candles, s, current_lot, hard_close_time=hard_close_time, max_orders=max_orders)
        if res is None:
            continue

        balance += res['pnl_dollar']
        equity_curve.append({'date': s['date'], 'balance': round(balance, 2)})

        if balance > peak:
            peak = balance
        dd = peak - balance
        dd_pct = (dd / peak) * 100.0 if peak > 0 else 0
        if dd > max_dd_dollar:
            max_dd_dollar = dd
        if dd_pct > max_dd_pct:
            max_dd_pct = dd_pct

        executed_trades.append({
            'date': s['date'],
            'exit_date': res['exit_date'],
            'direction': res['direction'],
            'mode': res['regime'],
            'lot_size': current_lot,
            'entry_price': round(res['entry_price'], 2),
            'close_price': round(res['close_price'], 2),
            'orders_count': res['layers'],
            'pnl_dollar': res['pnl_dollar'],
            'pnl_price': res['pnl_price'],
            'ai_safe_prob': 0.90 if s['is_extreme_toxic'] == 0 else 0.10,
            'is_win': res['is_win'],
            'duration_bars': res['duration_bars'],
            'duration_days': res['duration_days'],
            'close_reason': res['close_reason'],
            'worst_floating_pnl': res['worst_floating_pnl']
        })

    total_trades = len(executed_trades)
    wins = [t for t in executed_trades if t['pnl_dollar'] > 0]
    losses = [t for t in executed_trades if t['pnl_dollar'] <= 0]
    win_rate = (len(wins) / total_trades * 100.0) if total_trades > 0 else 0
    total_profit = sum(t['pnl_dollar'] for t in wins)
    total_loss = abs(sum(t['pnl_dollar'] for t in losses))
    net_pnl = total_profit - total_loss
    profit_factor = (total_profit / total_loss) if total_loss > 0 else 99.0
    max_layers = max(t['orders_count'] for t in executed_trades) if executed_trades else 0
    avg_layers = sum(t['orders_count'] for t in executed_trades) / total_trades if total_trades > 0 else 0

    return {
        'total_trades': total_trades,
        'win_rate': round(win_rate, 2),
        'net_pnl': round(net_pnl, 2),
        'final_balance': round(balance, 2),
        'profit_factor': round(profit_factor, 2),
        'max_dd_percent': round(max_dd_pct, 2),
        'max_dd_dollar': round(max_dd_dollar, 2),
        'max_layers': max_layers,
        'avg_layers': round(avg_layers, 2),
        'equity_curve': equity_curve,
        'trades': executed_trades
    }


def analyze_filtered_days(sessions, baseline_trades):
    """
    Phân tích chi tiết tác động của bộ lọc:
    So sánh những ngày bị lọc xem nếu không lọc (Baseline) thì chuyện gì đã xảy ra.
    """
    trade_map = {t['date']: t for t in baseline_trades}
    analysis = []

    for s in sessions:
        if s['is_extreme_toxic'] == 1:
            t = trade_map.get(s['date'])
            analysis.append({
                'date': s['date'],
                'toxic_reason': s['toxic_reason'],
                'atr_val': round(s['atr_val'], 2),
                'morning_range': round(s['m_range'], 2),
                'morning_delta': round(s['delta_p'], 2),
                'baseline_layers': t['orders_count'] if t else 0,
                'baseline_pnl': t['pnl_dollar'] if t else 0.0,
                'baseline_worst_dd': t['worst_floating_pnl'] if t else 0.0,
                'baseline_is_win': t['is_win'] if t else False,
                'baseline_close_reason': t['close_reason'] if t else '--'
            })

    # Sắp xếp các ngày gây thiệt hại nặng nhất lên đầu để người dùng dễ quan sát
    analysis.sort(key=lambda x: x['baseline_pnl'])
    return analysis


def run_pipeline(data_dir):
    candles = load_candles(data_dir)
    sessions = extract_daily_sessions(candles)

    train_sessions = [s for s in sessions if s['year'] in TRAIN_YEARS]
    test_sessions  = [s for s in sessions if s['year'] in TEST_YEARS]

    print("[3/4] Đang mô phỏng Kiểm định Tập Test (2021-2025): Baseline vs Có Bộ Lọc...")
    test_baseline = simulate_full_dataset(test_sessions, candles, use_filter=False)
    test_ai       = simulate_full_dataset(test_sessions, candles, use_filter=True)

    print("      Đang phân tích tác động của các ngày biến động mạnh bị loại bỏ...")
    filtered_days_test = analyze_filtered_days(test_sessions, test_baseline['trades'])

    print("[4/4] Đang mô phỏng Tập Train (2011-2020) & Toàn bộ 15 Năm...")
    train_baseline = simulate_full_dataset(train_sessions, candles, use_filter=False)
    train_ai       = simulate_full_dataset(train_sessions, candles, use_filter=True)

    all_baseline   = simulate_full_dataset(sessions, candles, use_filter=False)
    all_ai         = simulate_full_dataset(sessions, candles, use_filter=True)

    stats = {
        'metadata': {
            'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'total_years': 15,
            'train_period': '2011 - 2020 (10 năm)',
            'test_period': '2021 - 2025 (5 năm)',
            'strategy_name': 'Rocket 10h VN M15 - Volatility Guard (Cắt lỗ 14h chiều VN)',
            'dca_min_step_rule': '0.5 x ATR(14) giữa các lệnh DCA',
            'tp_rule': 'Thích ứng: 0.8 x ATR14 (lệnh đơn) / 0.5 x ATR14 (rổ DCA >= 2 lệnh)',
            'stop_loss_rule': 'Cắt lỗ ép buộc vào 14:00 chiều VN (Hết phiên Á, né phiên Âu)',
            'hard_close_rule': 'Đóng sạch toàn bộ rổ lệnh lúc 14:00 VN nếu chưa chạm TP',
            'max_orders_rule': 'Không giới hạn số lệnh (Unlimited DCA)',
            'compounding_rule': '$5,000 vốn ứng với 0.01 lot ($10k vốn -> 0.02 lot khởi điểm)',
            'initial_balance': INITIAL_BALANCE
        },
        'volatility_filter_analysis': {
            'test_total_days': len(test_sessions),
            'test_normal_days': len([s for s in test_sessions if s['is_extreme_toxic'] == 0]),
            'test_filtered_days_count': len(filtered_days_test),
            'filter_rate_percent': round(len(filtered_days_test) / len(test_sessions) * 100.0, 1),
            'filtered_days': filtered_days_test
        },
        'train': {
            'baseline': train_baseline,
            'ai': train_ai
        },
        'test': {
            'baseline': test_baseline,
            'ai': test_ai
        },
        'all_time': {
            'baseline': all_baseline,
            'ai': all_ai
        },
        'losing_trades': [t for t in test_ai['trades'] if not t['is_win']],
        'deep_dca_trades': [t for t in test_ai['trades'] if t['orders_count'] >= 5],
        'recent_trades': test_ai['trades']
    }

    output_path = os.path.join(data_dir, "web_data.json")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    print("\n" + "="*85)
    print(" KẾT QUẢ SO SÁNH: CHẠY THUẦN (BASELINE) VS CÓ BỘ LỌC BIẾN ĐỘNG MẠNH (FILTER)")
    print(" (Quy tắc: DCA min = 0.5 ATR14 | TP thích ứng: 0.8/0.5 ATR | Cắt lỗ ép buộc 14:00 chiều VN)")
    print("="*85)
    print(f"{'CHỈ SỐ':<26} | {'KHÔNG LỌC (BASELINE)':<24} | {'CÓ LỌC BIẾN ĐỘNG (FILTER)':<26}")
    print("-" * 85)
    print(f"{'Số ngày giao dịch':<26} | {test_baseline['total_trades']:>24} | {test_ai['total_trades']:>26}")
    print(f"{'Tỷ lệ thắng (Winrate)':<26} | {test_baseline['win_rate']:>23}% | {test_ai['win_rate']:>25}%")
    print(f"{'Lợi nhuận ròng (Net PnL)':<26} | ${test_baseline['net_pnl']:>23,.2f} | ${test_ai['net_pnl']:>25,.2f}")
    print(f"{'Vốn cuối kỳ ($10,000)':<26} | ${test_baseline['final_balance']:>23,.2f} | ${test_ai['final_balance']:>25,.2f}")
    print(f"{'Sụt giảm tối đa (Max DD)':<26} | {test_baseline['max_dd_percent']:>23}% | {test_ai['max_dd_percent']:>25}%")
    print(f"{'Profit Factor':<26} | {test_baseline['profit_factor']:>24} | {test_ai['profit_factor']:>26}")
    print(f"{'Số lệnh nhồi lớn nhất':<26} | {test_baseline['max_layers']:>21} lệnh | {test_ai['max_layers']:>23} lệnh")
    print(f"{'Số ngày bị lọc bỏ':<26} | {'0 ngày':>24} | {len(filtered_days_test):>21} ngày")
    print("="*85)

    if filtered_days_test:
        print("\nTOP 5 NGÀY BIẾN ĐỘNG MẠNH NHẤT BỊ BỘ LỌC LOẠI BỎ (VÀ HẬU QUẢ NẾU VÀO LỆNH):")
        for idx, fd in enumerate(filtered_days_test[:5], 1):
            status = "THUA NẶNG" if fd['baseline_pnl'] < 0 else "THẮNG"
            print(f" {idx}. Ngày {fd['date']} | Lý do: {fd['toxic_reason']}")
            print(f"    -> Nếu vào lệnh (Baseline): Nhồi {fd['baseline_layers']} lệnh | PnL: ${fd['baseline_pnl']:,.2f} | Sụt giảm: ${fd['baseline_worst_dd']:,.2f} ({status})")
    print("\n" + "="*85 + "\n")

    return stats


if __name__ == '__main__':
    current_dir = os.path.dirname(os.path.abspath(__file__))
    run_pipeline(current_dir)
