#!/usr/bin/env python3
"""
==============================================================================
MODULE: BACKTEST & AI QUANTITATIVE ENGINE (engine/backtest_ai.py)
==============================================================================
Nhiệm vụ chuyên trách:
  1. Làm việc trực tiếp với dữ liệu nến XAU/USD trong thư mục data/.
  2. Trích xuất đặc trưng sóng 07h-10h sáng (Morning Wave & ATR14).
  3. Áp dụng Volatility Guard: Bộ lọc nhận diện bão giá cực đoan.
  4. Mô phỏng chiến lược giao dịch: DCA min step, TP thích ứng đóng nến M15, cắt lỗ ép buộc.
  5. Đánh giá song song: Train (2011-2020, 10 năm) vs Test (2021-2025, 5 năm) vs All-Time (15 năm).
  6. Trả về cấu trúc dữ liệu kết quả hoàn chỉnh cho Web Server hoặc CLI tiêu thụ.
==============================================================================
"""

import os
import glob
import csv
import math
import time
import shutil
from datetime import datetime, timezone, timedelta

ENGINE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(ENGINE_DIR)
DEFAULT_DATA_DIR = os.path.join(PROJECT_ROOT, "data")

VN_TZ = timezone(timedelta(hours=7))
TRAIN_YEARS = set(range(2011, 2021))
TEST_YEARS  = set(range(2021, 2026))


def load_candles(data_dir=None):
    """
    Nạp dữ liệu nến từ thư mục data/.
    Tự động gom nến từ root vào data/ nếu người dùng chưa chuyển.
    """
    if data_dir is None:
        data_dir = DEFAULT_DATA_DIR

    os.makedirs(data_dir, exist_ok=True)

    # Nếu có file CSV ở thư mục gốc, tự động chuyển vào data/ để gọn gàng
    root_csvs = glob.glob(os.path.join(PROJECT_ROOT, "XAUUSD_*.csv"))
    if root_csvs:
        print(f"[*] Đang gom {len(root_csvs)} file nến từ thư mục gốc vào {data_dir}...")
        for f in root_csvs:
            try:
                dest = os.path.join(data_dir, os.path.basename(f))
                shutil.move(f, dest)
            except Exception:
                pass

    # Tìm file M15 trong data/ hoặc data/candles/
    files = sorted(glob.glob(os.path.join(data_dir, "XAUUSD_*_m15.csv")))
    if not files:
        files = sorted(glob.glob(os.path.join(data_dir, "candles", "XAUUSD_*_m15.csv")))
    if not files:
        files = sorted(glob.glob(os.path.join(PROJECT_ROOT, "XAUUSD_*_m15.csv")))

    if not files:
        raise FileNotFoundError(f"Không tìm thấy file XAUUSD_*_m15.csv trong {data_dir}")

    target_dir = os.path.dirname(files[0])
    print(f"\n[1/4] Đang nạp dữ liệu từ {len(files)} files M15 (2011 - 2025) từ: {target_dir}...")
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


def get_candles_for_day(date_str, data_dir=None):
    """
    Trích xuất toàn bộ nến M15 của một ngày cụ thể (YYYY-MM-DD theo giờ VN).
    Phục vụ vẽ biểu đồ nến chi tiết phiên giao dịch cho Web UI.
    """
    if data_dir is None:
        data_dir = DEFAULT_DATA_DIR

    parts = date_str.split('-')
    if len(parts) != 3:
        return []

    year_str = parts[0]
    fpath = os.path.join(data_dir, f"XAUUSD_{year_str}_m15.csv")
    if not os.path.isfile(fpath):
        fpath = os.path.join(data_dir, "candles", f"XAUUSD_{year_str}_m15.csv")
    if not os.path.isfile(fpath):
        matches = glob.glob(os.path.join(data_dir, f"*{year_str}*.csv"))
        fpath = matches[0] if matches else None

    if not fpath or not os.path.isfile(fpath):
        return []

    day_candles = []
    with open(fpath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                ts = int(row['timestamp'])
                dt_utc = datetime.fromtimestamp(ts / 1000.0, tz=timezone.utc)
                dt_vn = dt_utc.astimezone(VN_TZ)
                cur_date = dt_vn.strftime('%Y-%m-%d')
                if cur_date == date_str:
                    day_candles.append({
                        'timestamp': ts,
                        'time': dt_vn.strftime('%H:%M'),
                        'datetime': dt_vn.strftime('%Y-%m-%d %H:%M'),
                        'open': round(float(row['open']), 2),
                        'high': round(float(row['high']), 2),
                        'low': round(float(row['low']), 2),
                        'close': round(float(row['close']), 2),
                        'volume': float(row.get('volume', 0))
                    })
            except Exception:
                continue

    day_candles.sort(key=lambda x: x['timestamp'])
    return day_candles


def extract_daily_sessions(candles, params):
    """
    Trích xuất đặc trưng từng phiên sáng (07h-10h VN):
    - Đo biên độ sóng sáng (morning_range)
    - Tính ATR14 tại nến 10:00 VN
    - Phân loại bão giá (Extreme Volatility Guard)
    """
    f_ratio_range = float(params.get('filter_ratio_range', 5.0))
    f_range_min = float(params.get('filter_range_min', 25.0))
    f_atr_max = float(params.get('filter_atr_max', 18.0))
    f_candle_10h_ratio = float(params.get('filter_candle_10h_ratio', 2.5))
    f_candle_10h_min = float(params.get('filter_candle_10h_min', 15.0))
    f_trend_ratio = float(params.get('filter_trend_ratio', 3.5))
    f_trend_min = float(params.get('filter_trend_min', 20.0))

    print("[2/4] Trích xuất sóng 07h-10h & Bộ lọc bão giá (Volatility Guard)...")
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
            cur_atr = atrs[i] if atrs[i] > 0 else 5.0

            # Quét nến phiên sáng từ 07:00 đến 10:00 VN (12 nến M15)
            start_m_idx = max(0, i - 12)
            m_high = max(candles[k][2] for k in range(start_m_idx, i + 1))
            m_low  = min(candles[k][3] for k in range(start_m_idx, i + 1))
            m_range = m_high - m_low
            p_07h = candles[start_m_idx][1]
            p_10h = c_close
            delta_p = p_10h - p_07h

            # Nến 10:00 VN
            candle_10h_body = abs(c_close - c_open)
            candle_10h_is_green = c_close > c_open

            # Kiểm tra các điều kiện bão giá
            cond_morning_stretch = (m_range >= f_ratio_range * cur_atr) and (m_range >= f_range_min)
            cond_atr_spike = cur_atr >= f_atr_max
            cond_candle_10h_giant = (candle_10h_body >= f_candle_10h_ratio * cur_atr) and (candle_10h_body >= f_candle_10h_min)
            cond_one_way_trend = (abs(delta_p) >= f_trend_ratio * cur_atr) and (abs(delta_p) >= f_trend_min)

            is_extreme = 1 if (cond_morning_stretch or cond_atr_spike or cond_candle_10h_giant or cond_one_way_trend) else 0

            reason = "Bình thường"
            if cond_morning_stretch:
                reason = f"Biên độ sáng giãn mạnh ({m_range:.1f}$ >= {f_ratio_range}x ATR)"
            elif cond_atr_spike:
                reason = f"ATR bão giá ({cur_atr:.1f}$ >= {f_atr_max}$)"
            elif cond_candle_10h_giant:
                reason = f"Nến 10h đột biến ({candle_10h_body:.1f}$)"
            elif cond_one_way_trend:
                reason = f"Trend 1 chiều sáng ({abs(delta_p):.1f}$)"

            sessions.append({
                'session_idx': len(sessions),
                'candle_idx': i,
                'timestamp': ts,
                'date': dt_vn.strftime('%Y-%m-%d'),
                'year': current_year,
                'atr_val': cur_atr,
                'm_range': m_range,
                'delta_p': delta_p,
                'c_10h_body': candle_10h_body,
                'c_10h_green': candle_10h_is_green,
                'is_extreme_toxic': is_extreme,
                'toxic_reason': reason
            })
            i += 40
        else:
            i += 1

    print(f"      -> Tổng số phiên 10h nhận diện: {len(sessions):,} ngày.")
    return sessions


def simulate_dataset(sessions, candles, use_filter=True, params=None, regime_models=None):
    """Mô phỏng giao dịch qua danh sách các phiên. Hỗ trợ cả chế độ tham số thủ công hoặc Dynamic AI theo hình thái."""
    if params is None:
        params = {}

    from engine.regime_synthesizer import classify_session_with_catalog

    min_step_atr = float(params.get('min_step_atr', 0.5))
    tp_single_atr = float(params.get('tp_single_atr', 0.8))
    tp_dca_atr = float(params.get('tp_dca_atr', 0.5))
    hard_exit_hour = int(params.get('hard_exit_hour', 14))
    hard_exit_min = int(params.get('hard_exit_minute', 0))
    initial_balance = float(params.get('initial_balance', 10000.0))
    lot_step_capital = float(params.get('lot_step_capital', 5000.0))
    sizing_mode = params.get('sizing_mode', 'atr_risk')
    risk_percent = float(params.get('risk_percent', 0.5))

    balance = initial_balance
    peak_balance = initial_balance
    max_dd_dollars = 0.0
    max_dd_pct = 0.0

    trades = []
    equity_curve = []
    layer_counts = {}

    for s in sessions:
        # Xác định nhóm hình thái phiên sáng qua mô hình phân cụm K-Means
        regime_id = s.get('regime') or classify_session_with_catalog(s, {'morphology_catalog': regime_models})
        s['regime'] = regime_id

        regime_info = regime_models.get(regime_id, {}) if regime_models else {}
        reg_params = regime_info.get('optimal_params', {}) if regime_models else {}

        # Nếu dùng bộ lọc bão giá hoặc hình thái Extreme Shock -> Bỏ qua
        if use_filter and (s['is_extreme_toxic'] == 1 or reg_params.get('action') == 'SKIP_SESSION'):
            continue

        # Áp dụng tham số động theo hình thái (nếu regime_models được bật)
        eff_min_step = reg_params.get('min_step_atr', min_step_atr) if regime_models else min_step_atr
        eff_tp_single = reg_params.get('tp_single_atr', tp_single_atr) if regime_models else tp_single_atr
        eff_tp_dca = reg_params.get('tp_dca_atr', tp_dca_atr) if regime_models else tp_dca_atr

        if regime_models and 'hard_exit' in reg_params and ':' in str(reg_params['hard_exit']):
            h_p = str(reg_params['hard_exit']).split(':')
            eff_h_exit = int(h_p[0])
            eff_m_exit = int(h_p[1])
        else:
            eff_h_exit = hard_exit_hour
            eff_m_exit = hard_exit_min

        eff_risk_pct = float(reg_params.get('risk_percent', risk_percent)) if regime_models else risk_percent
        eff_max_layers = int(reg_params.get('max_dca_layers', 7)) if regime_models else 7

        c_idx = s['candle_idx']
        atr = s['atr_val']
        min_dist = max(1.5, eff_min_step * atr)
        tp_target_single = max(1.5, eff_tp_single * atr)
        tp_target_dca = max(1.5, eff_tp_dca * atr)

        # Tính lot theo % rủi ro vốn do AI tự may đo cho hình thái này:
        if sizing_mode == 'atr_risk' or 'risk_percent' in params or regime_models:
            risk_dollars = balance * (eff_risk_pct / 100.0)
            risk_points = max(7.0, atr * 4.0)
            lot_size = max(0.01, round(risk_dollars / (risk_points * 100.0), 2))
        else:
            lot_size = max(0.01, round((balance / lot_step_capital) * 0.01, 2))

        # Nến 10:00 VN đóng lúc 10:15
        first_candle = candles[c_idx]
        is_green = first_candle[4] > first_candle[1]
        direction = "SELL" if is_green else "BUY"

        orders = [{
            'entry_price': first_candle[4],
            'lot': lot_size,
            'time': s['timestamp']
        }]

        worst_floating_pnl = 0.0
        closed = False
        close_reason = "--"
        close_price = 0.0
        close_time = 0
        bars_held = 0

        # Vòng lặp các nến M15 tiếp theo (hỗ trợ giữ lệnh tới 24h đêm)
        j = c_idx + 1
        while j < min(len(candles), c_idx + 70):
            cur_c = candles[j]
            c_open, c_high, c_low, c_close = cur_c[1], cur_c[2], cur_c[3], cur_c[4]
            bars_held += 1

            dt_utc = datetime.fromtimestamp(cur_c[0] / 1000.0, tz=timezone.utc)
            dt_vn = dt_utc.astimezone(VN_TZ)

            # Tính floating PnL của rổ lệnh
            total_lot = sum(o['lot'] for o in orders)
            if direction == "BUY":
                avg_entry = sum(o['entry_price'] * o['lot'] for o in orders) / total_lot
                pnl_dollars = (c_close - avg_entry) * total_lot * 100.0
                pts_diff = c_close - avg_entry
            else:
                avg_entry = sum(o['entry_price'] * o['lot'] for o in orders) / total_lot
                pnl_dollars = (avg_entry - c_close) * total_lot * 100.0
                pts_diff = avg_entry - c_close

            if pnl_dollars < worst_floating_pnl:
                worst_floating_pnl = pnl_dollars

            # 1. Điều kiện chốt lời tại đóng nến M15
            current_target = tp_target_single if len(orders) == 1 else tp_target_dca
            if pts_diff >= current_target:
                closed = True
                close_reason = f"TP đạt mục tiêu ({pts_diff:.1f} giá)"
                close_price = c_close
                close_time = cur_c[0]
                break

            # 2. Điều kiện cắt lỗ ép buộc theo giờ
            if (dt_vn.hour > eff_h_exit) or (dt_vn.hour == eff_h_exit and dt_vn.minute >= eff_m_exit):
                closed = True
                close_reason = f"Cắt lỗ ép buộc lúc {eff_h_exit:02d}:{eff_m_exit:02d} VN"
                close_price = c_close
                close_time = cur_c[0]
                break

            # 3. Xét nhồi lệnh DCA nếu nến cùng màu
            c_is_green = c_close > c_open
            last_entry = orders[-1]['entry_price']

            if direction == "BUY" and not c_is_green:
                if len(orders) < eff_max_layers and (last_entry - c_close) >= min_dist:
                    orders.append({
                        'entry_price': c_close,
                        'lot': lot_size,
                        'time': cur_c[0]
                    })
            elif direction == "SELL" and c_is_green:
                if len(orders) < eff_max_layers and (c_close - last_entry) >= min_dist:
                    orders.append({
                        'entry_price': c_close,
                        'lot': lot_size,
                        'time': cur_c[0]
                    })

            j += 1

        if not closed:
            cur_c = candles[min(j, len(candles) - 1)]
            close_price = cur_c[4]
            close_time = cur_c[0]
            close_reason = "Hết dữ liệu tìm kiếm"

        # Tính PnL cuối cùng của rổ lệnh
        final_total_lot = sum(o['lot'] for o in orders)
        avg_entry = sum(o['entry_price'] * o['lot'] for o in orders) / final_total_lot
        if direction == "BUY":
            final_pnl = (close_price - avg_entry) * final_total_lot * 100.0
        else:
            final_pnl = (avg_entry - close_price) * final_total_lot * 100.0

        is_win = final_pnl > 0
        balance += final_pnl
        if balance > peak_balance:
            peak_balance = balance
        dd_dollars = peak_balance - balance
        dd_pct = (dd_dollars / peak_balance * 100.0) if peak_balance > 0 else 0.0

        if dd_dollars > max_dd_dollars:
            max_dd_dollars = dd_dollars
        if dd_pct > max_dd_pct:
            max_dd_pct = dd_pct

        num_orders = len(orders)
        layer_counts[num_orders] = layer_counts.get(num_orders, 0) + 1

        meta_reg = regime_info if regime_info else {}
        trades.append({
            'trade_idx': len(trades) + 1,
            'date': s['date'],
            'direction': direction,
            'regime_id': regime_id,
            'regime_name': meta_reg.get('name', 'Bình thường'),
            'regime_icon': meta_reg.get('icon', '🎯'),
            'regime_tag': meta_reg.get('tag', 'CHUẨN'),
            'dynamic_params': {
                'min_step_atr': eff_min_step,
                'tp_single_atr': eff_tp_single,
                'tp_dca_atr': eff_tp_dca,
                'hard_exit': f"{eff_h_exit:02d}:{eff_m_exit:02d}",
                'risk_percent': eff_risk_pct,
                'max_dca_layers': eff_max_layers,
                'base_lot': lot_size
            },
            'ai_rationale': meta_reg.get('desc', ''),
            'orders_count': num_orders,
            'lot_size': lot_size,
            'total_lots': round(final_total_lot, 2),
            'first_entry': round(orders[0]['entry_price'], 2),
            'entry_price': round(orders[0]['entry_price'], 2),
            'avg_entry': round(avg_entry, 2),
            'close_price': round(close_price, 2),
            'close_time': close_time,
            'close_time_str': datetime.fromtimestamp(close_time / 1000.0, tz=timezone.utc).astimezone(VN_TZ).strftime('%H:%M') if close_time else '--',
            'pnl_dollar': round(final_pnl, 2),
            'worst_floating_pnl': round(worst_floating_pnl, 2),
            'balance_after': round(balance, 2),
            'is_win': is_win,
            'close_reason': close_reason,
            'bars_held': bars_held,
            'atr_at_entry': round(atr, 2),
            'orders': [{
                'layer': idx + 1,
                'entry_price': round(o['entry_price'], 2),
                'lot': o['lot'],
                'timestamp': o['time'],
                'time': datetime.fromtimestamp(o['time'] / 1000.0, tz=timezone.utc).astimezone(VN_TZ).strftime('%H:%M')
            } for idx, o in enumerate(orders)]
        })

        if len(trades) % 5 == 0 or len(trades) == len(sessions):
            equity_curve.append({
                'date': s['date'],
                'balance': round(balance, 2)
            })

    total_trades = len(trades)
    win_trades = sum(1 for t in trades if t['is_win'])
    loss_trades = total_trades - win_trades
    win_rate = round(win_trades / total_trades * 100.0, 2) if total_trades > 0 else 0.0
    net_pnl = round(balance - initial_balance, 2)

    total_gain = sum(t['pnl_dollar'] for t in trades if t['pnl_dollar'] > 0)
    total_loss = abs(sum(t['pnl_dollar'] for t in trades if t['pnl_dollar'] < 0))
    profit_factor = round(total_gain / total_loss, 2) if total_loss > 0 else (999.0 if total_gain > 0 else 0.0)

    max_layers = max(layer_counts.keys()) if layer_counts else 0
    total_layers_sum = sum(k * v for k, v in layer_counts.items())
    avg_layers = round(total_layers_sum / total_trades, 2) if total_trades > 0 else 0.0

    return {
        'initial_balance': initial_balance,
        'final_balance': round(balance, 2),
        'net_pnl': net_pnl,
        'win_rate': win_rate,
        'total_trades': total_trades,
        'win_trades': win_trades,
        'loss_trades': loss_trades,
        'profit_factor': profit_factor,
        'max_dd_dollars': round(max_dd_dollars, 2),
        'max_dd_dollar': round(max_dd_dollars, 2),
        'max_dd_percent': round(max_dd_pct, 2),
        'max_layers': max_layers,
        'avg_layers': avg_layers,
        'layer_distribution': layer_counts,
        'equity_curve': equity_curve,
        'trades': trades
    }


def analyze_filtered_days(test_sessions, baseline_trades):
    """Kiểm toán các ngày bị bộ lọc loại bỏ."""
    trade_map = {t['date']: t for t in baseline_trades}
    analysis = []
    for s in test_sessions:
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
    analysis.sort(key=lambda x: x['baseline_pnl'])
    return analysis


def execute_backtest(params, data_dir=None):
    """
    Hàm thực thi Backtest & Huấn Luyện AI chính:
    1. Trích xuất nến và đặc trưng sóng sáng 07h-10h
    2. Huấn luyện ma trận hình thái thị trường (AI Regime Optimizer 2011-2020)
    3. Mô phỏng so sánh:
       - Baseline Tĩnh (Static Baseline, không lọc)
       - Baseline Tĩnh Có Lọc (Static AI Volatility Guard)
       - Dynamic Adaptive AI (AI tự động chọn tham số theo hình thái từng ngày)
    4. Trả về thống kê toàn diện, ma trận tối ưu và so sánh độ cải thiện Alpha Lift
    """
    t0 = time.time()
    candles = load_candles(data_dir)
    sessions = extract_daily_sessions(candles, params)

    train_sessions = [s for s in sessions if s['year'] in TRAIN_YEARS]
    test_sessions  = [s for s in sessions if s['year'] in TEST_YEARS]

    # 1. Huấn luyện Sâu 10 Năm (2011-2020): Quét 1,200 setups/ngày & Gom cụm tự động
    from engine.regime_synthesizer import load_saved_catalog, synthesize_training_catalog, classify_session_with_catalog
    catalog_data = load_saved_catalog()
    if not catalog_data or params.get('force_retrain', False):
        from engine.daily_deep_trainer import train_10_years_deep
        training_results = train_10_years_deep(train_sessions, candles)
        catalog_data = synthesize_training_catalog(training_results, train_sessions, candles)

    regime_models = catalog_data.get('morphology_catalog', {})

    # Gán hình thái tự động học cho toàn bộ sessions
    for s in sessions:
        s['regime'] = classify_session_with_catalog(s, catalog_data)

    # 2. Mô phỏng kiểm định
    print("[3/4] Mô phỏng Tập Test (2021-2025): Baseline Tĩnh vs Dynamic AI...")
    test_baseline   = simulate_dataset(test_sessions, candles, use_filter=False, params=params)
    test_static_ai  = simulate_dataset(test_sessions, candles, use_filter=True, params=params)
    test_dynamic_ai = simulate_dataset(test_sessions, candles, use_filter=True, params=params, regime_models=regime_models)

    filtered_days_test = analyze_filtered_days(test_sessions, test_baseline['trades'])

    print("[4/4] Mô phỏng Tập Train (2011-2020) & Toàn bộ 15 Năm...")
    train_baseline   = simulate_dataset(train_sessions, candles, use_filter=False, params=params)
    train_static_ai  = simulate_dataset(train_sessions, candles, use_filter=True, params=params)
    train_dynamic_ai = simulate_dataset(train_sessions, candles, use_filter=True, params=params, regime_models=regime_models)

    all_baseline   = simulate_dataset(sessions, candles, use_filter=False, params=params)
    all_static_ai  = simulate_dataset(sessions, candles, use_filter=True, params=params)
    all_dynamic_ai = simulate_dataset(sessions, candles, use_filter=True, params=params, regime_models=regime_models)

    mode = params.get('mode', 'dynamic_ai') # 'dynamic_ai' (mặc định) hoặc 'manual'
    active_test = test_dynamic_ai if mode == 'dynamic_ai' else test_static_ai
    active_train = train_dynamic_ai if mode == 'dynamic_ai' else train_static_ai
    active_all = all_dynamic_ai if mode == 'dynamic_ai' else all_static_ai

    min_step = params.get('min_step_atr', 0.5)
    tp_single = params.get('tp_single_atr', 0.8)
    tp_dca = params.get('tp_dca_atr', 0.5)
    h_close = int(params.get('hard_exit_hour', 14))
    m_close = int(params.get('hard_exit_minute', 0))
    init_bal = float(params.get('initial_balance', 10000.0))
    lot_cap = float(params.get('lot_step_capital', 5000.0))

    elapsed = round(time.time() - t0, 2)

    stats = {
        'metadata': {
            'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'total_years': 15,
            'train_period': '2011 - 2020 (10 năm)',
            'test_period': '2021 - 2025 (5 năm)',
            'strategy_name': 'Rocket 10h VN M15 - Dynamic AI Adaptive Engine',
            'mode': mode,
            'dca_min_step_rule': 'AI Tự Động Chọn Theo Hình Thái' if mode == 'dynamic_ai' else f'{min_step} x ATR(14) giữa các lệnh DCA',
            'tp_rule': 'AI Tự Động Chọn Theo Hình Thái' if mode == 'dynamic_ai' else f'Thích ứng: {tp_single} ATR14 (lệnh đơn) / {tp_dca} ATR14 (rổ DCA >= 2 lệnh)',
            'stop_loss_rule': 'AI Tự Động Cắt Theo Hình Thái (12h30 - 14h30 VN)' if mode == 'dynamic_ai' else f'Cắt lỗ ép buộc vào {h_close:02d}:{m_close:02d} VN',
            'hard_close_rule': 'Tự động đóng theo hình thái nếu chưa chạm TP',
            'max_orders_rule': 'Không giới hạn số lệnh (Unlimited DCA)',
            'compounding_rule': f'{params.get("risk_percent", 0.5)}% rủi ro vốn co giãn theo biến động ATR(14) (Cách 2)' if params.get('sizing_mode', 'atr_risk') == 'atr_risk' or 'risk_percent' in params else f'${lot_cap:,.0f} vốn ứng với 0.01 lot',
            'initial_balance': init_bal,
            'active_params': params,
            'execution_time_seconds': elapsed
        },
        'mode': mode,
        'regime_matrix': regime_models,
        'training_catalog': catalog_data,
        'dynamic_ai_comparison': {
            'static_baseline': {
                'win_rate': test_static_ai['win_rate'],
                'net_pnl': test_static_ai['net_pnl'],
                'profit_factor': test_static_ai['profit_factor'],
                'max_dd_percent': test_static_ai['max_dd_percent'],
                'total_trades': test_static_ai['total_trades']
            },
            'dynamic_regime_ai': {
                'win_rate': test_dynamic_ai['win_rate'],
                'net_pnl': test_dynamic_ai['net_pnl'],
                'profit_factor': test_dynamic_ai['profit_factor'],
                'max_dd_percent': test_dynamic_ai['max_dd_percent'],
                'total_trades': test_dynamic_ai['total_trades']
            },
            'alpha_lift': {
                'win_rate_diff': round(test_dynamic_ai['win_rate'] - test_static_ai['win_rate'], 2),
                'pnl_diff': round(test_dynamic_ai['net_pnl'] - test_static_ai['net_pnl'], 2),
                'dd_diff': round(test_static_ai['max_dd_percent'] - test_dynamic_ai['max_dd_percent'], 2)
            }
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
            'ai': active_train
        },
        'test': {
            'baseline': test_baseline,
            'ai': active_test
        },
        'all_time': {
            'baseline': all_baseline,
            'ai': active_all
        },
        'losing_trades': [t for t in active_test['trades'] if not t['is_win']],
        'deep_dca_trades': [t for t in active_test['trades'] if t['orders_count'] >= 5],
        'recent_trades': active_test['trades']
    }

    return stats


def run_10_years_deep_training(data_dir=None):
    """
    Tiến trình độc lập Huấn luyện Chuyên sâu 10 Năm (2011-2020):
    1. Quét 1,200 setups/ngày trên toàn bộ ~2,500 ngày.
    2. Rút trích setup Top 1 và đặc trưng hình thái sóng sáng của từng ngày.
    3. Phân cụm K-Means và may đo bộ setup đại diện tối thượng cho từng hình thái.
    4. Trả về catalog dữ liệu để báo cáo kết quả trước khi chạy backtest kiểm định.
    """
    from engine.daily_deep_trainer import train_10_years_deep
    from engine.regime_synthesizer import synthesize_training_catalog

    candles = load_candles(data_dir)
    sessions = extract_daily_sessions(candles, {})
    train_sessions = [s for s in sessions if s['year'] in TRAIN_YEARS]

    training_results = train_10_years_deep(train_sessions, candles)
    catalog = synthesize_training_catalog(training_results, train_sessions, candles)
    return catalog
