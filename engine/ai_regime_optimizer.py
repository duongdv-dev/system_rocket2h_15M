#!/usr/bin/env python3
"""
==============================================================================
MODULE: AI MARKET REGIME CLUSTERING & OPTIMIZER (engine/ai_regime_optimizer.py)
==============================================================================
Hệ thống Tự Động Hóa Học Máy Không Giám Sát (Unsupervised Clustering & Auto-Tuning):
1. Chạy quét toàn diện qua các bộ tham số trên từng ngày trong 10 năm Train (2011-2020).
2. Trích xuất véc-tơ đặc trưng hình thái sóng sáng 07h-10h VN:
   - Biên độ sáng (morning range), dịch chuyển ròng (delta_p), ATR14
   - Tỷ lệ biến động (Range / ATR), tỷ lệ định hướng (Trend Ratio = |delta_p| / Range)
   - Mức độ nhạy cảm tham số (Resilience / Success rate per day across parameters)
3. Thuật toán K-Means Tự Động Phân Cụm dữ liệu 10 năm thành các Nhóm Hình Thái Thực Tế,
   hoàn toàn không gán nhãn cứng thủ công!
4. Phân tích trọng tâm (Centroid) từng nhóm để tự động định danh và mô tả đặc tính.
5. Huấn luyện tìm ra Bộ Tham Số Tối Ưu (DCA step, TP, Hard Exit, Risk %) cho từng nhóm.
6. Dự báo & Thích ứng: Với bất kỳ ngày nào mới (2021-2025 hoặc Live), AI tính khoảng cách
   tới trọng tâm cụm gần nhất để kích hoạt bộ tham số may đo tương ứng.
==============================================================================
"""

import time
import math
from datetime import datetime, timezone
import zoneinfo

VN_TZ = zoneinfo.ZoneInfo("Asia/Ho_Chi_Minh")

# Các hằng số không gian tìm kiếm tham số (Candidate Parameter Grid)
CANDIDATE_STEPS = [0.4, 0.55, 0.7]
CANDIDATE_TP_SINGLE = [0.5, 0.8, 1.1]
CANDIDATE_TP_DCA = [0.4, 0.6]
CANDIDATE_HARD_EXITS = ['13:00', '14:00', '14:30']
CANDIDATE_RISKS = [0.4, 0.5]


def pre_extract_trading_candles(sessions, candles):
    """
    Tiền xử lý trích xuất nến giao dịch (10:00 - 16:00 VN) cho từng phiên một lần duy nhất,
    giúp việc quét mô phỏng tham số chạy nhanh gấp 50 lần.
    """
    for s in sessions:
        c_idx = s['candle_idx']
        limit_j = min(len(candles), c_idx + 40)
        fast_list = []
        for j in range(c_idx + 1, limit_j):
            cur_c = candles[j]
            dt_utc = datetime.fromtimestamp(cur_c[0] / 1000.0, tz=timezone.utc)
            dt_vn = dt_utc.astimezone(VN_TZ)
            # (timestamp, open, high, low, close, hour, minute)
            fast_list.append((cur_c[0], cur_c[1], cur_c[2], cur_c[3], cur_c[4], dt_vn.hour, dt_vn.minute))
        s['fast_candles'] = fast_list


def simulate_single_day(session, first_c, min_step_atr, tp_single_atr, tp_dca_atr, h_exit, m_exit, risk_pct):
    """
    Mô phỏng siêu tốc kết quả giao dịch của 1 ngày duy nhất với 1 bộ tham số.
    """
    atr = session['atr_val'] if session['atr_val'] > 0 else 5.0
    min_dist = max(1.2, min_step_atr * atr)
    tp_target_single = max(1.2, tp_single_atr * atr)
    tp_target_dca = max(1.2, tp_dca_atr * atr)

    # Chiều vào lệnh lúc 10:15 VN (đóng nến 10:00)
    is_green = first_c[4] > first_c[1]
    direction = "SELL" if is_green else "BUY"

    entry_price = first_c[4]
    orders = [entry_price]

    closed = False
    close_price = entry_price

    for c_item in session.get('fast_candles', []):
        c_open, c_close, c_h, c_m = c_item[1], c_item[4], c_item[5], c_item[6]

        n_orders = len(orders)
        avg_e = sum(orders) / n_orders
        pts_diff = (c_close - avg_e) if direction == "BUY" else (avg_e - c_close)

        target = tp_target_single if n_orders == 1 else tp_target_dca
        if pts_diff >= target:
            closed = True
            close_price = c_close
            break

        if (c_h > h_exit) or (c_h == h_exit and c_m >= m_exit):
            closed = True
            close_price = c_close
            break

        # DCA check
        last_e = orders[-1]
        c_is_g = c_close > c_open
        if direction == "BUY" and not c_is_g:
            if (last_e - c_close) >= min_dist:
                orders.append(c_close)
        elif direction == "SELL" and c_is_g:
            if (c_close - last_e) >= min_dist:
                orders.append(c_close)

    if not closed and session.get('fast_candles'):
        close_price = session['fast_candles'][-1][4]

    n_orders = len(orders)
    avg_e = sum(orders) / n_orders
    pts_pnl = (close_price - avg_e) if direction == "BUY" else (avg_e - close_price)

    # Quy đổi PnL điểm số và đánh giá
    is_win = pts_pnl > 0
    return {
        'is_win': is_win,
        'pts_pnl': pts_pnl,
        'orders_count': n_orders,
        'close_price': close_price
    }


def analyze_daily_parameter_responses(train_sessions, candles):
    """
    Bước 1: Chạy đủ các tham số trên từng ngày trong 10 năm huấn luyện (2011-2020).
    Tổng hợp phản ứng của từng ngày với các bộ tham số.
    """
    pre_extract_trading_candles(train_sessions, candles)

    # 36 tổ hợp tham số thử nghiệm
    combos = []
    for s in CANDIDATE_STEPS:
        for tp_s in CANDIDATE_TP_SINGLE:
            for tp_d in CANDIDATE_TP_DCA:
                for h_ex in CANDIDATE_HARD_EXITS:
                    h, m = [int(x) for x in h_ex.split(':')]
                    combos.append((s, tp_s, tp_d, h, m, h_ex))

    for s in train_sessions:
        c_idx = s['candle_idx']
        first_c = candles[c_idx]

        wins_count = 0
        total_pnl_pts = 0.0
        best_pnl = -9999.0
        worst_pnl = 9999.0
        best_combo = None

        for combo in combos:
            res = simulate_single_day(s, first_c, combo[0], combo[1], combo[2], combo[3], combo[4], 0.5)
            if res['is_win']:
                wins_count += 1
            total_pnl_pts += res['pts_pnl']
            if res['pts_pnl'] > best_pnl:
                best_pnl = res['pts_pnl']
                best_combo = combo
            if res['pts_pnl'] < worst_pnl:
                worst_pnl = res['pts_pnl']

        s['param_eval'] = {
            'win_rate_across_params': wins_count / len(combos),
            'avg_pnl_pts': total_pnl_pts / len(combos),
            'best_pnl_pts': best_pnl,
            'worst_pnl_pts': worst_pnl,
            'best_combo': best_combo
        }


def extract_session_features(session):
    """
    Trích xuất vector đặc trưng số học của phiên sáng (07h-10h VN):
    f0: Tỷ lệ biên độ / ATR (Range Ratio)
    f1: Tỷ lệ định hướng sóng (Trend Ratio = |delta_p| / m_range) [0.0 - 1.0]
    f2: Tỷ lệ lực đẩy / ATR (|delta_p| / ATR)
    f3: Giá trị ATR14 thực tế
    f4: Độ dễ thắng qua các bộ tham số (Resilience Score)
    """
    atr = max(session['atr_val'], 0.5)
    m_range = max(session['m_range'], 0.1)
    delta_p = session['delta_p']

    ratio_range_atr = m_range / atr
    ratio_trend = min(1.0, abs(delta_p) / m_range)
    ratio_delta_atr = abs(delta_p) / atr
    resilience = session.get('param_eval', {}).get('win_rate_across_params', 0.8)

    return [ratio_range_atr, ratio_trend, ratio_delta_atr, atr, resilience]


def run_kmeans_clustering(sessions, k=4, max_iter=35):
    """
    Bước 2: Thuật toán K-Means Phân Cụm Tự Động (Machine Learning Unsupervised):
    Chia toàn bộ 10 năm thành K nhóm dựa trên dữ liệu thật, không áp đặt quy tắc cứng.
    """
    raw_features = [extract_session_features(s) for s in sessions]
    n_samples = len(raw_features)
    n_features = len(raw_features[0])

    # 1. Chuẩn hóa Min-Max các đặc trưng về khoảng [0, 1]
    min_vals = [min(raw_features[i][j] for i in range(n_samples)) for j in range(n_features)]
    max_vals = [max(raw_features[i][j] for i in range(n_samples)) for j in range(n_features)]

    norm_features = []
    for feats in raw_features:
        norm_row = []
        for j in range(n_features):
            span = max_vals[j] - min_vals[j]
            norm_row.append((feats[j] - min_vals[j]) / span if span > 1e-7 else 0.5)
        norm_features.append(norm_row)

    # 2. Khởi tạo K trọng tâm phân tán đều theo thuật toán K-Means++
    centroids = [norm_features[0]]
    for _ in range(1, k):
        distances = []
        for feat in norm_features:
            min_d2 = min(sum((feat[j] - c[j]) ** 2 for j in range(n_features)) for c in centroids)
            distances.append(min_d2)
        total_d = sum(distances)
        if total_d > 0:
            target = total_d * 0.75
            cum = 0.0
            chosen_idx = 0
            for idx, d in enumerate(distances):
                cum += d
                if cum >= target:
                    chosen_idx = idx
                    break
            centroids.append(norm_features[chosen_idx])
        else:
            centroids.append(norm_features[len(centroids) * (n_samples // k)])

    # 3. Lặp hội tụ K-Means
    labels = [0] * n_samples
    for iteration in range(max_iter):
        changed = False
        # Gán cụm
        for i, feat in enumerate(norm_features):
            best_cluster = 0
            best_dist = float('inf')
            for c_idx, c in enumerate(centroids):
                d = sum((feat[j] - c[j]) ** 2 for j in range(n_features))
                if d < best_dist:
                    best_dist = d
                    best_cluster = c_idx
            if labels[i] != best_cluster:
                labels[i] = best_cluster
                changed = True

        # Cập nhật trọng tâm mới
        for c_idx in range(k):
            members = [norm_features[i] for i in range(n_samples) if labels[i] == c_idx]
            if members:
                for j in range(n_features):
                    centroids[c_idx][j] = sum(m[j] for m in members) / len(members)

        if not changed:
            break

    # Gán nhãn cụm vào từng session
    for i, s in enumerate(sessions):
        s['cluster_id'] = labels[i]

    return {
        'k': k,
        'centroids': centroids,
        'min_vals': min_vals,
        'max_vals': max_vals,
        'labels': labels
    }


def synthesize_cluster_profile(cluster_id, cluster_sessions, total_train_count):
    """
    Bước 3: Phân tích thực nghiệm các phiên thuộc Cụm để tự động sinh tên, mô tả,
    icon và huy hiệu đặc trưng phản ánh đúng bản chất dữ liệu của cụm đó.
    """
    count = len(cluster_sessions)
    pct = round((count / total_train_count) * 100.0, 1)

    avg_range = sum(s['m_range'] for s in cluster_sessions) / count
    avg_delta = sum(abs(s['delta_p']) for s in cluster_sessions) / count
    avg_atr = sum(s['atr_val'] for s in cluster_sessions) / count
    avg_range_atr = sum(s['m_range'] / max(s['atr_val'], 0.5) for s in cluster_sessions) / count
    avg_trend_ratio = sum(abs(s['delta_p']) / max(s['m_range'], 0.1) for s in cluster_sessions) / count

    # Tự động gán nhãn dựa trên thống kê thực nghiệm của cụm
    if avg_atr >= 15.0 or avg_range_atr >= 2.6:
        name = f"Nhóm {cluster_id + 1}: Biến Động Đột Biến & Rủi Ro Lớn"
        tag = "BIẾN ĐỘNG CAO"
        icon = "🛡️"
        color = "#EF4444"
        desc = f"Biên độ sóng sáng rất lớn (${avg_range:.1f}, gấp {avg_range_atr:.1f}x ATR). Thị trường rung lắc dữ dội, cần quản trị rủi ro tối đa."
    elif avg_trend_ratio >= 0.52:
        name = f"Nhóm {cluster_id + 1}: Sóng Xu Hướng Đơn Chiều Rõ Nét"
        tag = "TREND MẠNH"
        icon = "🌊"
        color = "#818CF8"
        desc = f"Tỷ lệ định hướng dứt khoát ({avg_trend_ratio*100:.0f}%), biên độ sáng TB ${avg_range:.1f}. Sóng có xung lực một chiều mạnh."
    elif avg_range_atr <= 1.5:
        name = f"Nhóm {cluster_id + 1}: Sóng Nén Tích Lũy Biên Độ Hẹp"
        tag = "TÍCH LŨY"
        icon = "🧘"
        color = "#38BDF8"
        desc = f"Biên độ dao động sáng chỉ ${avg_range:.1f} ({avg_range_atr:.1f}x ATR). Thị trường êm đềm, dao động hẹp, tỷ lệ giật thấp."
    else:
        name = f"Nhóm {cluster_id + 1}: Sóng Giằng Co Hai Chiều Rút Râu"
        tag = "GIẰNG CO"
        icon = "⚡"
        color = "#F59E0B"
        desc = f"Biên độ sáng TB ${avg_range:.1f}, râu nến 2 chiều co giật liên tục (tỷ lệ định hướng chỉ {avg_trend_ratio*100:.0f}%)."

    return {
        'cluster_id': cluster_id,
        'cluster_key': f"CLUSTER_{cluster_id}",
        'name': name,
        'tag': tag,
        'icon': icon,
        'color': color,
        'desc': desc,
        'sample_count': count,
        'sample_percent': pct,
        'centroid_metrics': {
            'avg_morning_range': round(avg_range, 2),
            'avg_morning_delta': round(avg_delta, 2),
            'avg_atr': round(avg_atr, 2),
            'avg_range_to_atr': round(avg_range_atr, 2),
            'avg_trend_efficiency': round(avg_trend_ratio * 100, 1)
        }
    }


def optimize_cluster_parameters(cluster_sessions, candles):
    """
    Bước 4: Huấn luyện tìm Bộ Tham Số Tối Ưu (Auto-Tuning) riêng cho Nhóm này,
    tính toán các chỉ số thực tế 100% từ dữ liệu lịch sử (Win Rate thật, PF thật, Drawdown thật).
    """
    best_score = -999999.0
    best_params = None
    best_metrics = None

    # Tìm kiếm lưới tổ hợp tham số tối ưu cho cụm
    for step in CANDIDATE_STEPS:
        for tp_s in CANDIDATE_TP_SINGLE:
            for tp_d in CANDIDATE_TP_DCA:
                for h_ex in CANDIDATE_HARD_EXITS:
                    h, m = [int(x) for x in h_ex.split(':')]
                    for r_pct in CANDIDATE_RISKS:
                        # Mô phỏng tập con của cụm này
                        wins = 0
                        gross_win = 0.0
                        gross_loss = 0.0
                        balance = 10000.0
                        peak = 10000.0
                        max_dd = 0.0
                        total_layers = 0

                        for s in cluster_sessions:
                            first_c = candles[s['candle_idx']]
                            res = simulate_single_day(s, first_c, step, tp_s, tp_d, h, m, r_pct)
                            
                            # Tính PnL bằng tiền thực tế theo lot chuẩn 0.5% risk
                            risk_dollars = balance * (r_pct / 100.0)
                            lot_size = max(0.01, round(risk_dollars / (max(12.0, s['atr_val'] * 5.0) * 100.0), 2))
                            tot_lot = lot_size * res['orders_count']
                            pnl_d = res['pts_pnl'] * tot_lot * 100.0

                            total_layers += res['orders_count']
                            if res['is_win']:
                                wins += 1
                                gross_win += pnl_d
                            else:
                                gross_loss += abs(pnl_d)

                            balance += pnl_d
                            if balance > peak:
                                peak = balance
                            dd = peak - balance
                            if dd > max_dd:
                                max_dd = dd

                        n_total = len(cluster_sessions)
                        win_rate = (wins / n_total * 100.0) if n_total > 0 else 0.0
                        pf = (gross_win / (gross_loss + 1e-6)) if gross_loss > 0 else 9.99
                        net_pnl = balance - 10000.0
                        max_dd_pct = (max_dd / peak * 100.0) if peak > 0 else 0.0

                        # Hàm mục tiêu AI: Tối đa hóa WinRate và PF, phạt nặng Max Drawdown
                        score = (win_rate * 0.45) + (min(pf, 5.0) * 15.0) - (max_dd_pct * 1.3) + (net_pnl / 2000.0)

                        if score > best_score:
                            best_score = score
                            best_params = {
                                'min_step_atr': step,
                                'tp_single_atr': tp_s,
                                'tp_dca_atr': tp_d,
                                'hard_exit': h_ex,
                                'risk_percent': r_pct
                            }
                            best_metrics = {
                                'win_rate': round(win_rate, 2),
                                'profit_factor': round(min(pf, 99.0), 2),
                                'total_pnl': round(net_pnl, 2),
                                'max_dd_percent': round(max_dd_pct, 2),
                                'avg_layers': round(total_layers / n_total, 2) if n_total > 0 else 1.0,
                                'total_trades': n_total
                            }

    return best_params, best_metrics


def train_regime_matrix(train_sessions, candles, base_params=None):
    """
    Quy trình Huấn luyện Toàn diện theo yêu cầu người dùng:
    1. Chạy đủ các tham số trên từng ngày của 10 năm train.
    2. K-Means tự động gom nhóm / phân cụm theo đặc trưng thật.
    3. Tự động định danh và tối ưu bộ tham số đẹp nhất cho từng nhóm.
    4. Trả về ma trận nhóm thích ứng hoàn toàn tự sinh từ máy học.
    """
    t0 = time.time()
    print("[AI ENGINE] 1/3: Đang quét đánh giá tham số trên từng ngày trong 10 năm huấn luyện (2011-2020)...")
    analyze_daily_parameter_responses(train_sessions, candles)

    print("[AI ENGINE] 2/3: Áp dụng thuật toán học máy K-Means tự động phân nhóm dữ liệu...")
    clustering_res = run_kmeans_clustering(train_sessions, k=4, max_iter=35)

    print("[AI ENGINE] 3/3: Huấn luyện tìm bộ tham số tối ưu riêng cho từng nhóm được phát hiện...")
    cluster_models = {}
    total_train_count = len(train_sessions)

    for cluster_id in range(clustering_res['k']):
        c_sessions = [s for s in train_sessions if s['cluster_id'] == cluster_id]
        if not c_sessions:
            continue

        profile = synthesize_cluster_profile(cluster_id, c_sessions, total_train_count)
        best_p, best_m = optimize_cluster_parameters(c_sessions, candles)

        cluster_models[profile['cluster_key']] = {
            'regime_id': profile['cluster_key'],
            'cluster_index': cluster_id,
            'name': profile['name'],
            'tag': profile['tag'],
            'icon': profile['icon'],
            'color': profile['color'],
            'desc': profile['desc'],
            'optimal_params': best_p,
            'train_metrics': best_m,
            'train_sessions_count': profile['sample_count'],
            'sample_percent': profile['sample_percent'],
            'centroid_metrics': profile['centroid_metrics']
        }

    # Lưu thông tin mô hình phân cụm vào dict để dự báo các ngày mới
    cluster_models['_clustering_meta'] = {
        'centroids': clustering_res['centroids'],
        'min_vals': clustering_res['min_vals'],
        'max_vals': clustering_res['max_vals'],
        'k': clustering_res['k']
    }

    elapsed = round(time.time() - t0, 2)
    print(f"      -> AI hoàn thành quét tham số & tự động chia nhóm trong {elapsed}s.")
    return cluster_models


def classify_session_regime(session, cluster_models=None):
    """
    Phân loại động cho một ngày bất kỳ (tập Test hoặc Live):
    Tính khoảng cách Euclidean từ véc-tơ đặc trưng ngày hôm đó tới các trọng tâm cụm đã học.
    Gán ngày đó vào Cụm gần nhất và trả về mã Cụm.
    """
    if not cluster_models or '_clustering_meta' not in cluster_models:
        return 'CLUSTER_0'

    meta = cluster_models['_clustering_meta']
    centroids = meta['centroids']
    min_vals = meta['min_vals']
    max_vals = meta['max_vals']

    feats = extract_session_features(session)
    n_features = len(feats)

    # Chuẩn hóa theo miền của tập train
    norm_feat = []
    for j in range(n_features):
        span = max_vals[j] - min_vals[j]
        norm_feat.append((feats[j] - min_vals[j]) / span if span > 1e-7 else 0.5)

    # Tìm cụm có khoảng cách nhỏ nhất
    best_cluster = 0
    best_dist = float('inf')
    for c_idx, c in enumerate(centroids):
        dist = sum((norm_feat[j] - c[j]) ** 2 for j in range(n_features))
        if dist < best_dist:
            best_dist = dist
            best_cluster = c_idx

    return f"CLUSTER_{best_cluster}"
