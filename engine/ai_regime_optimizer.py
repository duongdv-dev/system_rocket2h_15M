#!/usr/bin/env python3
"""
==============================================================================
MODULE: AI MARKET REGIME OPTIMIZER (engine/ai_regime_optimizer.py)
==============================================================================
Hệ thống AI Tự Động Nhận Diện Hình Thái Thị Trường & Tối Ưu Tham Số Thích Ứng:
1. Phân loại hình thái phiên sáng (07h-10h VN):
   - 🧘 QUIET_SIDEWAY (Sóng Sáng Tích Lũy / Biên Hẹp)
   - 🌊 TREND_MOMENTUM (Sóng Sáng Đột Phá Xu Hướng Mạnh)
   - ⚡ WIDE_EXPANSION (Sóng Sáng Giằng Co Biên Rộng)
   - 🛡️ EXTREME_SHOCK (Bão Giá Cực Đại - Volatility Guard)
2. Huấn luyện (Training): Tự động quét không gian tham số (Auto-Tuning) trên 10 năm
   (2011-2020) để tìm bộ tham số "may đo" tối ưu riêng cho từng hình thái.
3. Dự báo & Thực thi (Inference): Áp dụng động bộ tham số riêng cho từng ngày,
   thay vì dùng 1 bộ tham số tĩnh cố định.
==============================================================================
"""

import time
from datetime import datetime, timezone
import zoneinfo

VN_TZ = zoneinfo.ZoneInfo("Asia/Ho_Chi_Minh")

# Định nghĩa các hình thái thị trường
REGIME_METADATA = {
    'QUIET_SIDEWAY': {
        'name': 'Sóng Sáng Tích Lũy / Biên Hẹp',
        'icon': '🧘',
        'tag': 'TÍCH LŨY',
        'color': '#38BDF8',
        'desc': 'Thị trường phiên Á dao động hẹp, không có tin tức. AI tự động tối ưu DCA bước nhỏ, TP gọn và cắt sớm để chốt lãi nhanh.',
        'param_space': {
            'min_step_atr': [0.35, 0.45, 0.55],
            'tp_single_atr': [0.4, 0.5, 0.65],
            'tp_dca_atr': [0.3, 0.4, 0.5],
            'hard_exit': ['12:30', '13:00', '13:30'],
            'risk_percent': [0.5, 0.7]
        }
    },
    'TREND_MOMENTUM': {
        'name': 'Sóng Sáng Đột Phá Xu Hướng',
        'icon': '🌊',
        'tag': 'TREND MẠNH',
        'color': '#818CF8',
        'desc': 'Phiên sáng có lực đẩy một chiều dứt khoát. AI tự động nới bước DCA lớn để né nhồi sớm và kỳ vọng TP lớn hơn khi giá hồi phục.',
        'param_space': {
            'min_step_atr': [0.55, 0.65, 0.75],
            'tp_single_atr': [0.8, 1.0, 1.2],
            'tp_dca_atr': [0.5, 0.6, 0.7],
            'hard_exit': ['13:30', '14:00', '14:30'],
            'risk_percent': [0.4, 0.5]
        }
    },
    'WIDE_EXPANSION': {
        'name': 'Sóng Sáng Giằng Co Biên Rộng',
        'icon': '⚡',
        'tag': 'GIẰNG CO',
        'color': '#F59E0B',
        'desc': 'Biên độ sáng lớn nhưng râu nến 2 chiều co giật mạnh. AI duy trì bước giá chuẩn và quản trị rủi ro chặt chẽ.',
        'param_space': {
            'min_step_atr': [0.45, 0.5, 0.6],
            'tp_single_atr': [0.65, 0.8, 0.95],
            'tp_dca_atr': [0.45, 0.5, 0.55],
            'hard_exit': ['13:30', '14:00', '14:30'],
            'risk_percent': [0.3, 0.5]
        }
    },
    'EXTREME_SHOCK': {
        'name': 'Bão Giá Cực Đại (Shock Filter)',
        'icon': '🛡️',
        'tag': 'NÉ BÃO',
        'color': '#EF4444',
        'desc': 'Biến động bất thường vượt ngưỡng an toàn. AI kích hoạt Volatility Guard né hoàn toàn phiên giao dịch.',
        'param_space': None
    }
}


def classify_session_regime(session):
    """
    Phân loại hình thái thị trường cụ thể cho một phiên 10:00 VN:
    Dựa trên:
    - Biến độ sóng sáng 07h-10h (m_range)
    - Mức độ dịch chuyển ròng (delta_p)
    - Tỷ lệ với độ co giãn ATR14
    """
    if session.get('is_extreme_toxic') == 1:
        return 'EXTREME_SHOCK'

    atr = session['atr_val'] if session['atr_val'] > 0 else 5.0
    ratio_range = session['m_range'] / atr
    ratio_delta = abs(session['delta_p']) / atr

    # 1. Nếu lực đẩy 1 chiều rõ rệt -> TREND_MOMENTUM
    if ratio_delta >= 1.4:
        return 'TREND_MOMENTUM'
    
    # 2. Nếu biên độ hẹp và biến động ít -> QUIET_SIDEWAY
    if ratio_range < 2.5 and ratio_delta < 1.0:
        return 'QUIET_SIDEWAY'
    
    # 3. Còn lại là biên độ lớn giằng co -> WIDE_EXPANSION
    return 'WIDE_EXPANSION'


def quick_simulate_regime_subset(sessions, candles, test_params):
    """Mô phỏng siêu tốc một tập con các phiên với 1 bộ tham số thử nghiệm."""
    min_step_atr = test_params['min_step_atr']
    tp_single_atr = test_params['tp_single_atr']
    tp_dca_atr = test_params['tp_dca_atr']
    h_exit, m_exit = [int(x) for x in test_params['hard_exit'].split(':')]
    risk_pct = test_params.get('risk_percent', 0.5)

    wins = 0
    total_pnl = 0.0
    gross_win = 0.0
    gross_loss = 0.0
    balance = 10000.0
    peak = 10000.0
    max_dd_dollars = 0.0

    for s in sessions:
        c_idx = s['candle_idx']
        atr = s['atr_val']
        min_dist = max(1.5, min_step_atr * atr)
        tp_target_single = max(1.5, tp_single_atr * atr)
        tp_target_dca = max(1.5, tp_dca_atr * atr)

        # Tính lot theo % risk co giãn theo ATR
        risk_dollars = balance * (risk_pct / 100.0)
        risk_points = max(12.0, atr * 5.0)
        lot_size = max(0.01, round(risk_dollars / (risk_points * 100.0), 2))

        first_c = candles[c_idx]
        is_green = first_c[4] > first_c[1]
        direction = "SELL" if is_green else "BUY"

        orders = [{
            'entry_price': first_c[4],
            'lot': lot_size
        }]

        closed = False
        close_price = 0.0

        j = c_idx + 1
        limit_j = min(len(candles), c_idx + 60)
        while j < limit_j:
            cur_c = candles[j]
            c_close = cur_c[4]
            dt_utc = datetime.fromtimestamp(cur_c[0] / 1000.0, tz=timezone.utc)
            dt_vn = dt_utc.astimezone(VN_TZ)

            tot_lot = sum(o['lot'] for o in orders)
            if direction == "BUY":
                avg_e = sum(o['entry_price'] * o['lot'] for o in orders) / tot_lot
                pts_diff = c_close - avg_e
            else:
                avg_e = sum(o['entry_price'] * o['lot'] for o in orders) / tot_lot
                pts_diff = avg_e - c_close

            # TP Check
            target = tp_target_single if len(orders) == 1 else tp_target_dca
            if pts_diff >= target:
                closed = True
                close_price = c_close
                break

            # Hard Exit Check
            if (dt_vn.hour > h_exit) or (dt_vn.hour == h_exit and dt_vn.minute >= m_exit):
                closed = True
                close_price = c_close
                break

            # DCA Check
            c_is_g = c_close > cur_c[1]
            last_p = orders[-1]['entry_price']
            if direction == "BUY" and not c_is_g:
                if (last_p - c_close) >= min_dist:
                    orders.append({'entry_price': c_close, 'lot': lot_size})
            elif direction == "SELL" and c_is_g:
                if (c_close - last_p) >= min_dist:
                    orders.append({'entry_price': c_close, 'lot': lot_size})

            j += 1

        if not closed:
            cur_c = candles[min(j, len(candles) - 1)]
            close_price = cur_c[4]

        tot_lot = sum(o['lot'] for o in orders)
        avg_e = sum(o['entry_price'] * o['lot'] for o in orders) / tot_lot
        pnl = (close_price - avg_e) * tot_lot * 100.0 if direction == "BUY" else (avg_e - close_price) * tot_lot * 100.0

        if pnl > 0:
            wins += 1
            gross_win += pnl
        else:
            gross_loss += abs(pnl)

        total_pnl += pnl
        balance += pnl
        if balance > peak:
            peak = balance
        dd = peak - balance
        if dd > max_dd_dollars:
            max_dd_dollars = dd

    total_t = len(sessions)
    win_rate = (wins / total_t * 100.0) if total_t > 0 else 0.0
    pf = (gross_win / (gross_loss + 1e-6)) if gross_loss > 0 else 9.99
    max_dd_pct = (max_dd_dollars / peak * 100.0) if peak > 0 else 0.0

    # Hàm mục tiêu AI: Tối đa hóa Win Rate & Profit Factor, phạt nặng Max Drawdown
    score = (win_rate * 0.45) + (min(pf, 5.0) * 15.0) - (max_dd_pct * 1.2) + (total_pnl / 2000.0)

    return {
        'score': score,
        'win_rate': round(win_rate, 2),
        'profit_factor': round(pf, 2),
        'total_pnl': round(total_pnl, 2),
        'max_dd_percent': round(max_dd_pct, 2),
        'total_trades': total_t
    }


def train_regime_matrix(train_sessions, candles, base_params=None):
    """
    Huấn luyện AI trên tập dữ liệu lịch sử (10 năm: 2011 - 2020):
    Tìm ra bộ tham số tối ưu (best_params) độc lập cho từng hình thái thị trường.
    """
    t0 = time.time()
    print("[AI ENGINE] Đang huấn luyện và tối ưu bộ tham số thích ứng theo từng hình thái...")

    # Gán hình thái cho tập train
    for s in train_sessions:
        s['regime'] = classify_session_regime(s)

    regime_models = {}

    for regime_id in ['QUIET_SIDEWAY', 'TREND_MOMENTUM', 'WIDE_EXPANSION']:
        meta = REGIME_METADATA[regime_id]
        regime_sessions = [s for s in train_sessions if s['regime'] == regime_id]

        if not regime_sessions:
            continue

        space = meta['param_space']
        best_score = -999999
        best_params = None
        best_metrics = None

        # Grid search qua không gian tham số của hình thái này
        for step in space['min_step_atr']:
            for tp_s in space['tp_single_atr']:
                for tp_d in space['tp_dca_atr']:
                    for h_ex in space['hard_exit']:
                        for r_pct in space['risk_percent']:
                            candidate = {
                                'min_step_atr': step,
                                'tp_single_atr': tp_s,
                                'tp_dca_atr': tp_d,
                                'hard_exit': h_ex,
                                'risk_percent': r_pct
                            }
                            res = quick_simulate_regime_subset(regime_sessions, candles, candidate)
                            if res['score'] > best_score:
                                best_score = res['score']
                                best_params = candidate
                                best_metrics = res

        regime_models[regime_id] = {
            'regime_id': regime_id,
            'name': meta['name'],
            'icon': meta['icon'],
            'tag': meta['tag'],
            'color': meta['color'],
            'desc': meta['desc'],
            'optimal_params': best_params,
            'train_metrics': best_metrics,
            'train_sessions_count': len(regime_sessions)
        }

    # Bổ sung hình thái Extreme Shock (Né bão)
    regime_shock_sessions = [s for s in train_sessions if s['regime'] == 'EXTREME_SHOCK']
    regime_models['EXTREME_SHOCK'] = {
        'regime_id': 'EXTREME_SHOCK',
        'name': REGIME_METADATA['EXTREME_SHOCK']['name'],
        'icon': REGIME_METADATA['EXTREME_SHOCK']['icon'],
        'tag': REGIME_METADATA['EXTREME_SHOCK']['tag'],
        'color': REGIME_METADATA['EXTREME_SHOCK']['color'],
        'desc': REGIME_METADATA['EXTREME_SHOCK']['desc'],
        'optimal_params': {
            'min_step_atr': 0.5,
            'tp_single_atr': 0.8,
            'tp_dca_atr': 0.5,
            'hard_exit': '14:00',
            'risk_percent': 0.0,
            'action': 'SKIP_SESSION'
        },
        'train_metrics': {
            'win_rate': 0.0,
            'profit_factor': 0.0,
            'total_pnl': 0.0,
            'max_dd_percent': 0.0,
            'total_trades': 0
        },
        'train_sessions_count': len(regime_shock_sessions)
    }

    elapsed = round(time.time() - t0, 2)
    print(f"      -> Huấn luyện ma trận hình thái hoàn tất trong {elapsed}s.")
    return regime_models
