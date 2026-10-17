#!/usr/bin/env python3
"""
==============================================================================
MODULE: DAILY DEEP TRAINER (engine/daily_deep_trainer.py)
==============================================================================
Nhiệm vụ:
1. Duyệt qua từng ngày trong 10 năm huấn luyện (2011 - 2020, khoảng ~2,500 ngày).
2. Chạy thử nghiệm đồng thời 1,200 setups (Cartesian Grid: 8 x 6 x 5 x 5) trên từng ngày.
3. Tìm ra 1 setup có kết quả tốt nhất của ngày hôm đó (Max PnL, Min Drawdown, Min DCA).
4. Phân tích & trích xuất vector đặc trưng hình thái sóng sáng 07h-10h VN của ngày đó.
5. Xuất ra bảng dữ liệu tổng hợp 2,500 ngày đã được huấn luyện chuyên sâu.
==============================================================================
"""

import time
import math
from datetime import datetime, timezone
import zoneinfo
from concurrent.futures import ProcessPoolExecutor
import os

VN_TZ = zoneinfo.ZoneInfo("Asia/Ho_Chi_Minh")

# Siêu Lưới 2,688 setups may đo cho Sân Nhà Phiên Á (10h15 - 14h00 VN)
GRID_MIN_STEP_ATR = [0.30, 0.40, 0.50, 0.60, 0.75, 0.90, 1.10, 1.30]   # 8 mức
GRID_TP_SINGLE_ATR = [0.40, 0.60, 0.80, 1.00, 1.25, 1.50, 1.80, 2.20]  # 8 mức
GRID_TP_DCA_ATR = [0.25, 0.35, 0.45, 0.60, 0.75, 0.90]                 # 6 mức
GRID_HARD_EXITS = [
    (11, 30, '11:30'),
    (11, 45, '11:45'),
    (12, 0,  '12:00'),
    (12, 30, '12:30'),
    (13, 0,  '13:00'),
    (13, 30, '13:30'),
    (14, 0,  '14:00')
]  # 7 mốc chuẩn xác trong Sân Nhà Phiên Á (kết thúc hoàn toàn trước phiên Âu)
# Tổng số setups = 8 * 8 * 6 * 7 = 2,688 setups / ngày (quét nhanh & tối ưu triệt để)

ALL_SETUPS = []
for s in GRID_MIN_STEP_ATR:
    for tp_s in GRID_TP_SINGLE_ATR:
        for tp_d in GRID_TP_DCA_ATR:
            for h, m, h_str in GRID_HARD_EXITS:
                ALL_SETUPS.append((s, tp_s, tp_d, h, m, h_str))


def evaluate_setup_on_day(fast_candles, first_close, is_green, atr, setup, max_layers=8, sl_atr=None):
    """
    Mô phỏng siêu tốc 1 setup trên danh sách nến của 1 ngày.
    setup: (min_step_atr, tp_single_atr, tp_dca_atr, h_exit, m_exit, h_str)
    max_layers: số tầng DCA tối đa do AI khống chế (mặc định 8)
    sl_atr: Ngưỡng AI tự động ĐÓNG SỚM bảo vệ vốn khi giá đi ngược (tính theo ATR, mặc định None)
    """
    min_step_atr, tp_single_atr, tp_dca_atr, h_exit, m_exit, h_str = setup

    min_dist = max(1.2, min_step_atr * atr)
    tp_single = max(1.2, tp_single_atr * atr)
    tp_dca = max(1.2, tp_dca_atr * atr)
    sl_target = max(3.5, sl_atr * atr) if sl_atr is not None else None

    direction_is_sell = is_green
    orders = [first_close]
    orders_sum = first_close
    orders_cnt = 1
    last_order_p = first_close

    closed = False
    close_price = first_close
    worst_pts_dd = 0.0
    bars_held = 0

    for c_open, c_high, c_low, c_close, c_h, c_m in fast_candles:
        bars_held += 1
        avg_e = orders_sum / orders_cnt
        pts_diff = (avg_e - c_close) if direction_is_sell else (c_close - avg_e)

        # Tính floating drawdown
        if pts_diff < worst_pts_dd:
            worst_pts_dd = pts_diff

        # 1. Kiểm tra TP
        target = tp_single if orders_cnt == 1 else tp_dca
        if pts_diff >= target:
            closed = True
            close_price = c_close
            break

        # 2. CƠ CHẾ ĐÓNG SỚM KHẨN CẤP (AI Adaptive Invalidation Stop-Loss):
        # Nếu giá đi ngược vượt quá ngưỡng an toàn sl_target -> AI cắt lỗ đóng sớm ngay lập tức!
        if sl_target is not None and pts_diff <= -sl_target:
            closed = True
            close_price = c_close
            break

        # 3. Kiểm tra Hard Exit theo giờ (Giới hạn giữ lệnh tối đa trong ngày nếu an toàn)
        if (c_h > h_exit) or (c_h == h_exit and c_m >= m_exit):
            closed = True
            close_price = c_close
            break

        # 4. Kiểm tra nhồi lệnh DCA nếu chưa chạm trần max_layers
        if orders_cnt < max_layers:
            if direction_is_sell and (c_close > c_open):
                if (c_close - last_order_p) >= min_dist:
                    orders.append(c_close)
                    orders_sum += c_close
                    orders_cnt += 1
                    last_order_p = c_close
            elif (not direction_is_sell) and (c_close < c_open):
                if (last_order_p - c_close) >= min_dist:
                    orders.append(c_close)
                    orders_sum += c_close
                    orders_cnt += 1
                    last_order_p = c_close

    if not closed and fast_candles:
        close_price = fast_candles[-1][3]

    avg_e = orders_sum / orders_cnt
    final_pts = (avg_e - close_price) if direction_is_sell else (close_price - avg_e)

    # Hàm chấm điểm chất lượng của setup trên ngày này:
    # Ưu tiên thắng lớn, phạt nặng gồng lỗ sâu (drawdown), phạt số lệnh DCA nhiều và giữ lệnh lâu
    is_win = final_pts > 0
    day_score = final_pts + (abs(worst_pts_dd) * -0.5) - (orders_cnt * 0.8) - (bars_held * 0.05)

    return {
        'setup': {
            'min_step_atr': min_step_atr,
            'tp_single_atr': tp_single_atr,
            'tp_dca_atr': tp_dca_atr,
            'hard_exit': h_str,
            'hard_exit_hour': h_exit,
            'hard_exit_minute': m_exit
        },
        'day_score': day_score,
        'final_pts': round(final_pts, 2),
        'is_win': is_win,
        'orders_count': orders_cnt,
        'worst_dd_pts': round(worst_pts_dd, 2),
        'bars_held': bars_held,
        'close_price': round(close_price, 2)
    }


def analyze_single_day_worker(day_data):
    """
    Hàm worker độc lập để chạy song song trên đa nhân CPU.
    day_data: dict chứa thông tin nến và hình thái của ngày.
    """
    fast_candles = day_data['fast_candles']
    first_c = day_data['first_candle']
    is_green = first_c[4] > first_c[1]
    first_close = first_c[4]
    atr = max(0.5, day_data['atr_val'])

    best_score = -999999.0
    best_result = None
    win_count = 0
    total_pts = 0.0

    # Chạy quét toàn bộ 1,200 setups cho ngày này
    for setup in ALL_SETUPS:
        res = evaluate_setup_on_day(fast_candles, first_close, is_green, atr, setup)
        if res['is_win']:
            win_count += 1
        total_pts += res['final_pts']

        if res['day_score'] > best_score:
            best_score = res['day_score']
            best_result = res

    # Vector hình thái sóng sáng
    m_range = max(0.1, day_data['m_range'])
    delta_p = day_data['delta_p']
    ratio_range_atr = round(m_range / atr, 2)
    ratio_trend = round(min(1.0, abs(delta_p) / m_range), 2)
    ratio_delta_atr = round(abs(delta_p) / atr, 2)
    ratio_wick = round(max(0.0, (m_range - abs(delta_p)) / m_range), 2)

    return {
        'date': day_data['date'],
        'year': day_data['year'],
        'atr_val': round(atr, 2),
        'm_range': round(m_range, 2),
        'delta_p': round(delta_p, 2),
        'direction': "SELL" if is_green else "BUY",
        'morphology': {
            'ratio_range_atr': ratio_range_atr,
            'ratio_trend': ratio_trend,
            'ratio_delta_atr': ratio_delta_atr,
            'ratio_wick': ratio_wick,
            'atr_val': round(atr, 2),
            'm_range': round(m_range, 2)
        },
        'best_setup': best_result['setup'],
        'best_metrics': {
            'day_score': round(best_result['day_score'], 2),
            'pts_pnl': best_result['final_pts'],
            'is_win': best_result['is_win'],
            'orders_count': best_result['orders_count'],
            'worst_dd_pts': best_result['worst_dd_pts'],
            'bars_held': best_result['bars_held']
        },
        'stats_across_1200_setups': {
            'win_rate_percent': round((win_count / len(ALL_SETUPS)) * 100.0, 1),
            'avg_pts_pnl': round(total_pts / len(ALL_SETUPS), 2)
        }
    }


def train_10_years_deep(train_sessions, candles):
    """
    Thực thi quét 1,200 setups/ngày trên toàn bộ ~2,500 ngày của 10 năm train (2011-2020).
    Sử dụng tối đa các luồng CPU để hoàn thành 3,000,000 lượt tính toán trong vài giây.
    """
    t0 = time.time()
    n_days = len(train_sessions)
    total_simulations = n_days * len(ALL_SETUPS)
    print(f"[DEEP TRAINER] Khởi động quét sâu 10 Năm (2011 - 2020): {n_days} ngày x 1,200 setups = {total_simulations:,} lượt mô phỏng...")

    # Tiền xử lý dữ liệu phẳng cho từng ngày
    prepared_days = []
    for s in train_sessions:
        c_idx = s['candle_idx']
        first_c = candles[c_idx]

        fast_c = []
        limit_j = min(len(candles), c_idx + 20) # Giới hạn hoàn toàn trong phiên Á (tới 14h30 VN)
        for j in range(c_idx + 1, limit_j):
            cur_c = candles[j]
            dt_utc = datetime.fromtimestamp(cur_c[0] / 1000.0, tz=timezone.utc)
            dt_vn = dt_utc.astimezone(VN_TZ)
            fast_c.append((cur_c[1], cur_c[2], cur_c[3], cur_c[4], dt_vn.hour, dt_vn.minute))

        prepared_days.append({
            'date': s['date'],
            'year': s['year'],
            'atr_val': s['atr_val'],
            'm_range': s['m_range'],
            'delta_p': s['delta_p'],
            'candle_idx': c_idx,
            'first_candle': first_c,
            'fast_candles': fast_c
        })

    # Chạy song song trên các nhân CPU
    num_workers = min(os.cpu_count() or 4, 8)
    day_results = []
    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        for res in executor.map(analyze_single_day_worker, prepared_days, chunksize=25):
            day_results.append(res)

    elapsed = round(time.time() - t0, 2)
    print(f"[DEEP TRAINER] Hoàn tất {total_simulations:,} lượt mô phỏng trong {elapsed}s ({int(total_simulations/elapsed):,} ops/sec).")

    return {
        'total_days_analyzed': n_days,
        'setups_per_day': len(ALL_SETUPS),
        'total_simulations': total_simulations,
        'elapsed_seconds': elapsed,
        'day_records': day_results
    }
