#!/usr/bin/env python3
"""
==============================================================================
MODULE: REGIME SYNTHESIZER & KNOWLEDGE BASE (engine/regime_synthesizer.py)
==============================================================================
Nhiệm vụ:
1. Nhận dữ liệu ~2,500 ngày huấn luyện chuyên sâu (từ daily_deep_trainer).
2. Dùng thuật toán K-Means Clustering tự động gom nhóm 10 năm thành các Hình Thái Cốt Lõi.
3. Rút trích đặc tính nhận diện (Centroid Profiling) cho từng hình thái.
4. May đo Bộ Setup Đại Diện Tối Thượng (Consensus Optimal Setup) cho từng hình thái.
5. Tính toán các chỉ số thực tế 100% trong 10 năm huấn luyện (Win Rate, PF, PnL, Drawdown).
6. Lưu trữ danh mục tri thức hình thái vào data/trained_morphology_catalog.json.
==============================================================================
"""

import os
import json
import time
import math
from datetime import datetime, timezone
import zoneinfo

VN_TZ = zoneinfo.ZoneInfo("Asia/Ho_Chi_Minh")

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
CATALOG_FILE = os.path.join(DATA_DIR, "trained_morphology_catalog.json")


def run_kmeans(vectors, k=4, max_iter=30):
    """K-Means clustering thuần Python với K-Means++ initialization."""
    n_samples = len(vectors)
    n_features = len(vectors[0])

    min_vals = [min(vectors[i][j] for i in range(n_samples)) for j in range(n_features)]
    max_vals = [max(vectors[i][j] for i in range(n_samples)) for j in range(n_features)]

    norm_vecs = []
    for row in vectors:
        norm_row = []
        for j in range(n_features):
            span = max_vals[j] - min_vals[j]
            norm_row.append((row[j] - min_vals[j]) / span if span > 1e-7 else 0.5)
        norm_vecs.append(norm_row)

    # K-Means++ init
    centroids = [norm_vecs[0]]
    for _ in range(1, k):
        dists = []
        for v in norm_vecs:
            min_d = min(sum((v[j] - c[j]) ** 2 for j in range(n_features)) for c in centroids)
            dists.append(min_d)
        total_d = sum(dists)
        if total_d > 0:
            target = total_d * 0.7
            cum = 0.0
            chosen = 0
            for idx, d in enumerate(dists):
                cum += d
                if cum >= target:
                    chosen = idx
                    break
            centroids.append(norm_vecs[chosen])
        else:
            centroids.append(norm_vecs[(len(centroids) * n_samples) // k])

    labels = [0] * n_samples
    for _ in range(max_iter):
        changed = False
        for i, v in enumerate(norm_vecs):
            best_c = 0
            best_d = float('inf')
            for c_idx, c in enumerate(centroids):
                d = sum((v[j] - c[j]) ** 2 for j in range(n_features))
                if d < best_d:
                    best_d = d
                    best_c = c_idx
            if labels[i] != best_c:
                labels[i] = best_c
                changed = True

        for c_idx in range(k):
            members = [norm_vecs[i] for i in range(n_samples) if labels[i] == c_idx]
            if members:
                for j in range(n_features):
                    centroids[c_idx][j] = sum(m[j] for m in members) / len(members)

        if not changed:
            break

    return {
        'k': k,
        'centroids': centroids,
        'min_vals': min_vals,
        'max_vals': max_vals,
        'labels': labels
    }


def find_consensus_setup_for_cluster(cluster_days, all_candidate_setups):
    """
    Tìm 1 bộ setup đồng thuận tối ưu nhất cho toàn bộ các ngày trong cụm.
    TỐI ƯU TOÀN DIỆN MỌI CHỈ SỐ: Min Step, TP Single/DCA, Giờ Cắt Lỗ, % Rủi Ro Vốn & Trần Tầng DCA.
    """
    from engine.daily_deep_trainer import evaluate_setup_on_day

    n = len(cluster_days)
    if n == 0:
        return {}, {}

    # Giai đoạn 1: Lọc nhanh Top 10 setups có tổng điểm PnL và tỷ lệ thắng tốt nhất
    sample_days = cluster_days if n <= 200 else cluster_days[::2]
    candidate_scores = []

    for setup in all_candidate_setups:
        tot_pts = 0.0
        wins = 0
        for day in sample_days:
            res = evaluate_setup_on_day(
                day['fast_candles'],
                day['first_candle'][4],
                day['direction'] == 'SELL',
                day['atr_val'],
                setup,
                max_layers=7
            )
            tot_pts += res['final_pts']
            if res['is_win']:
                wins += 1
        s_score = tot_pts + (wins / len(sample_days) * 100.0)
        candidate_scores.append((s_score, setup))

    candidate_scores.sort(key=lambda x: x[0], reverse=True)
    top_candidates = [x[1] for x in candidate_scores[:10]]

    # Giai đoạn 2: Tối ưu hóa sâu Quản Trị Vốn Tự Trị (100% Autonomous Risk & Lot Sizing)
    # AI tự học và quét qua các mức % rủi ro vốn và trần số tầng DCA tối đa
    GRID_RISK_PCT = [0.8, 1.0, 1.2, 1.5]
    GRID_MAX_LAYERS = [3, 4, 5, 7]

    best_score = -999999.0
    best_setup = None
    best_metrics = None

    for setup in top_candidates:
        for max_layers in GRID_MAX_LAYERS:
            for risk_pct in GRID_RISK_PCT:
                wins = 0
                gross_win = 0.0
                gross_loss = 0.0
                balance = 10000.0
                peak = 10000.0
                max_dd = 0.0
                total_layers = 0

                for day in cluster_days:
                    res = evaluate_setup_on_day(
                        day['fast_candles'],
                        day['first_candle'][4],
                        day['direction'] == 'SELL',
                        day['atr_val'],
                        setup,
                        max_layers=max_layers
                    )

                    # Quy đổi PnL dollar theo % rủi ro vốn thực tế
                    risk_dollars = balance * (risk_pct / 100.0)
                    risk_points = max(7.0, day['atr_val'] * 4.0)
                    lot = max(0.01, round(risk_dollars / (risk_points * 100.0), 2))
                    tot_lot = lot * res['orders_count']
                    pnl_d = res['final_pts'] * tot_lot * 100.0

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

                win_rate = (wins / n * 100.0)
                pf = (gross_win / (gross_loss + 1e-6)) if gross_loss > 0 else 9.99
                net_pnl = balance - 10000.0
                max_dd_pct = (max_dd / peak * 100.0) if peak > 0 else 0.0

                # Hàm mục tiêu Sharpe/Calmar lượng hóa rủi ro: ưu tiên PnL cao, winrate ổn định và khống chế DD
                score = (net_pnl * 0.4) - (max_dd_pct * 80.0) + (win_rate * 15.0) + (min(pf, 3.5) * 50.0)

                if score > best_score:
                    best_score = score
                    est_base_lot = max(0.02, round((10000.0 * (risk_pct / 100.0)) / (7.5 * 100.0), 2))
                    best_setup = {
                        'min_step_atr': setup[0],
                        'tp_single_atr': setup[1],
                        'tp_dca_atr': setup[2],
                        'hard_exit': setup[5],
                        'hard_exit_hour': setup[3],
                        'hard_exit_minute': setup[4],
                        'risk_percent': risk_pct,
                        'base_lot_per_10k': est_base_lot,
                        'max_dca_layers': max_layers
                    }
                    best_metrics = {
                        'win_rate': round(win_rate, 2),
                        'profit_factor': round(min(pf, 99.0), 2),
                        'total_pnl': round(net_pnl, 2),
                        'max_dd_percent': round(max_dd_pct, 2),
                        'avg_layers': round(total_layers / n, 2),
                        'total_trades': n,
                        'auto_risk_percent': risk_pct,
                        'auto_base_lot': est_base_lot,
                        'auto_max_layers': max_layers
                    }

    return best_setup, best_metrics


def synthesize_training_catalog(training_results, train_sessions, candles):
    """
    Gom cụm và tổng hợp Ma trận Hình Thái & Bộ Setup Tối Thượng từ kết quả 10 năm train.
    """
    t0 = time.time()
    day_records = training_results['day_records']
    n_days = len(day_records)

    # 1. Trích xuất vector đặc trưng đa chiều (bao gồm cả hướng xu hướng sóng sáng)
    feature_vectors = []
    for d in day_records:
        m = d['morphology']
        # Tính signed_trend: dương nếu sóng sáng tăng (nến xanh), âm nếu sóng sáng giảm (nến đỏ)
        s_trend = m['ratio_trend'] if d.get('delta_p', 0) >= 0 else -m['ratio_trend']
        # [ratio_range_atr, ratio_trend, s_trend, ratio_delta_atr, ratio_wick, atr_val]
        feature_vectors.append([
            m['ratio_range_atr'],
            m['ratio_trend'],
            s_trend,
            m['ratio_delta_atr'],
            m['ratio_wick'],
            m['atr_val']
        ])

    # 2. Phân cụm K-Means với K=8 nhóm hình thái chuyên sâu
    kmeans_res = run_kmeans(feature_vectors, k=8, max_iter=40)
    labels = kmeans_res['labels']

    # Gán nhãn cụm vào day_records
    for i, d in enumerate(day_records):
        d['cluster_id'] = labels[i]
        d['regime_id'] = f"MORPH_{labels[i]}"

    # Gắn thêm fast_candles vào để tính consensus setup (mở rộng tới 70 nến M15 = qua nửa đêm đến 24h)
    for i, s in enumerate(train_sessions):
        c_idx = s['candle_idx']
        fast_c = []
        for j in range(c_idx + 1, min(len(candles), c_idx + 70)):
            cur_c = candles[j]
            dt_utc = datetime.fromtimestamp(cur_c[0] / 1000.0, tz=timezone.utc)
            dt_vn = dt_utc.astimezone(VN_TZ)
            fast_c.append((cur_c[1], cur_c[2], cur_c[3], cur_c[4], dt_vn.hour, dt_vn.minute))
        day_records[i]['fast_candles'] = fast_c
        day_records[i]['first_candle'] = candles[c_idx]

    from engine.daily_deep_trainer import ALL_SETUPS

    morphology_catalog = {}
    cluster_summaries = []

    for c_id in range(kmeans_res['k']):
        c_days = [d for d in day_records if d['cluster_id'] == c_id]
        if not c_days:
            continue

        count = len(c_days)
        pct = round((count / n_days) * 100.0, 1)

        avg_range = sum(d['m_range'] for d in c_days) / count
        avg_atr = sum(d['atr_val'] for d in c_days) / count
        avg_range_atr = sum(d['morphology']['ratio_range_atr'] for d in c_days) / count
        avg_trend = sum(d['morphology']['ratio_trend'] for d in c_days) / count
        avg_signed = sum((d['morphology']['ratio_trend'] if d.get('delta_p', 0) >= 0 else -d['morphology']['ratio_trend']) for d in c_days) / count
        avg_wick = sum(d['morphology']['ratio_wick'] for d in c_days) / count

        # Tự động gán nhãn thực nghiệm dựa vào tỷ lệ định hướng, hướng nến (Bull/Bear) và biên độ:
        if avg_atr >= 3.8 or avg_range >= 13.0 or avg_range_atr >= 5.5:
            name = f"Hình Thái {c_id + 1}: Sóng Đột Biến & Bão Giá Rủi Ro Cao"
            tag = "BÃO GIÁ"
            icon = "🛡️"
            color = "#EF4444"
            desc = f"Biên độ sáng đột biến rất lớn (${avg_range:.2f}, {avg_range_atr:.1f}x ATR). Thị trường biến động dữ dội, AI tăng cường quản trị rủi ro tối đa."
        elif avg_trend >= 0.52 and avg_signed > 0.12:
            name = f"Hình Thái {c_id + 1}: Sóng Xu Hướng Tăng Mạnh Một Chiều"
            tag = "TREND TĂNG"
            icon = "📈"
            color = "#10B981"
            desc = f"Thân nến tăng áp đảo ({avg_trend*100:.1f}%), biên độ sáng ${avg_range:.2f}. Xung lực mua dốc đứng, AI giãn bước DCA và nới rộng TP."
        elif avg_trend >= 0.52 and avg_signed < -0.12:
            name = f"Hình Thái {c_id + 1}: Sóng Xu Hướng Giảm Mạnh Một Chiều"
            tag = "TREND GIẢM"
            icon = "📉"
            color = "#F43F5E"
            desc = f"Thân nến xả dốc chiếm {avg_trend*100:.1f}%, biên độ sáng ${avg_range:.2f}. Xung lực bán áp đảo, AI khống chế tầng DCA và nới TP theo đà rơi."
        elif avg_trend >= 0.35 and avg_signed > 0.06:
            name = f"Hình Thái {c_id + 1}: Sóng Đột Phá Mở Rộng Xu Hướng Tăng"
            tag = "BREAKOUT TĂNG"
            icon = "🚀"
            color = "#38BDF8"
            desc = f"Biên độ sáng ${avg_range:.2f} ({avg_range_atr:.1f}x ATR) thiên hướng tăng. Thị trường mở rộng biên độ, AI linh hoạt điểm hồi."
        elif avg_trend >= 0.35 and avg_signed < -0.06:
            name = f"Hình Thái {c_id + 1}: Sóng Đột Phá Mở Rộng Xu Hướng Giảm"
            tag = "BREAKDOWN GIẢM"
            icon = "💥"
            color = "#FB7185"
            desc = f"Biên độ sáng ${avg_range:.2f} ({avg_range_atr:.1f}x ATR) thiên hướng giảm. Áp lực bán lan tỏa, AI kiên nhẫn bắt nhịp hồi kỹ thuật."
        elif avg_trend <= 0.22 and avg_range <= 4.5:
            name = f"Hình Thái {c_id + 1}: Sóng Nén Tích Lũy / Doji Biên Hẹp"
            tag = "TÍCH LŨY"
            icon = "🧘"
            color = "#059669"
            desc = f"Biên độ sáng chỉ ${avg_range:.2f}, chủ yếu nến doji thân cực mỏng ({avg_trend*100:.1f}%). Sóng êm đềm, AI tự tin nâng volume thu hoạch lợi nhuận."
        elif avg_trend <= 0.28 and avg_wick >= 0.55:
            name = f"Hình Thái {c_id + 1}: Sóng Thanh Khoản Thấp Rút Râu Êm Đềm"
            tag = "TRÔI DẠT"
            icon = "🌙"
            color = "#6EE7B7"
            desc = f"Dao động nhỏ ${avg_range:.2f}, râu nến 2 đầu chiếm {avg_wick*100:.1f}%. Thị trường ít sóng, AI đi volume an toàn và chốt lời gọn."
        else:
            name = f"Hình Thái {c_id + 1}: Sóng Giằng Co Hai Chiều Rút Râu"
            tag = "GIẰNG CO"
            icon = "⚡"
            color = "#F59E0B"
            desc = f"Biên độ sáng ${avg_range:.2f}, râu nến 2 chiều co giật liên tục ({avg_wick*100:.1f}% râu). Thích hợp kiên nhẫn điểm hồi."

        # May đo bộ setup đại diện tối thượng cho cụm
        best_setup, best_metrics = find_consensus_setup_for_cluster(c_days, ALL_SETUPS)

        item = {
            'regime_id': f"MORPH_{c_id}",
            'cluster_index': c_id,
            'name': name,
            'tag': tag,
            'icon': icon,
            'color': color,
            'desc': desc,
            'sample_count': count,
            'sample_percent': pct,
            'centroid_metrics': {
                'avg_morning_range': round(avg_range, 2),
                'avg_atr': round(avg_atr, 2),
                'avg_range_to_atr': round(avg_range_atr, 2),
                'avg_trend_efficiency': round(avg_trend * 100, 1),
                'avg_wick_ratio': round(avg_wick * 100, 1)
            },
            'optimal_params': best_setup,
            'train_metrics': best_metrics
        }
        morphology_catalog[item['regime_id']] = item
        cluster_summaries.append(item)

    # Lưu metadata phân cụm để dự báo
    morphology_catalog['_clustering_meta'] = {
        'centroids': kmeans_res['centroids'],
        'min_vals': kmeans_res['min_vals'],
        'max_vals': kmeans_res['max_vals'],
        'k': kmeans_res['k']
    }

    # Bỏ trường fast_candles và first_candle khỏi day_records để file json nhẹ gàng
    clean_day_records = []
    for d in day_records:
        clean_day_records.append({
            'date': d['date'],
            'year': d['year'],
            'direction': d['direction'],
            'm_range': d['m_range'],
            'atr_val': d['atr_val'],
            'cluster_id': d['cluster_id'],
            'regime_id': d['regime_id'],
            'morphology': d['morphology'],
            'best_setup': d['best_setup'],
            'best_metrics': d['best_metrics'],
            'stats_across_1200_setups': d['stats_across_1200_setups']
        })

    full_catalog_data = {
        'metadata': {
            'generated_at': time.strftime('%Y-%m-%d %H:%M:%S'),
            'training_period': '2011 - 2020 (10 năm)',
            'total_training_days': n_days,
            'setups_evaluated_per_day': training_results['setups_per_day'],
            'total_simulations_executed': training_results['total_simulations'],
            'training_elapsed_seconds': training_results['elapsed_seconds'],
            'clusters_discovered': kmeans_res['k']
        },
        'morphology_catalog': morphology_catalog,
        'cluster_summaries': cluster_summaries,
        'sample_training_days': clean_day_records[:150],  # 150 ngày mẫu để tra cứu nhanh trên Web
        'total_records_count': len(clean_day_records)
    }

    # Lưu xuống ổ đĩa
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(CATALOG_FILE, 'w', encoding='utf-8') as f:
        json.dump(full_catalog_data, f, ensure_ascii=False, indent=2)

    elapsed = round(time.time() - t0, 2)
    print(f"[SYNTHESIZER] Đã tổng hợp xong Danh mục Hình Thái & Bộ Setup vào '{CATALOG_FILE}' ({elapsed}s).")

    return full_catalog_data


def load_saved_catalog():
    """Đọc catalog đã lưu từ trước nếu có."""
    if os.path.exists(CATALOG_FILE):
        try:
            with open(CATALOG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return None
    return None


def classify_session_with_catalog(session, catalog_dict):
    """
    Phân loại động cho một ngày bất kỳ (2021-2025 hoặc Live) bằng khoảng cách tới trọng tâm.
    """
    if not catalog_dict or 'morphology_catalog' not in catalog_dict:
        return 'MORPH_0'

    meta = catalog_dict['morphology_catalog'].get('_clustering_meta')
    if not meta:
        return 'MORPH_0'

    centroids = meta['centroids']
    min_vals = meta['min_vals']
    max_vals = meta['max_vals']

    m_range = max(session['m_range'], 0.1)
    atr = max(session['atr_val'], 0.5)
    delta_p = session['delta_p']

    v = [
        m_range / atr,
        min(1.0, abs(delta_p) / m_range),
        abs(delta_p) / atr,
        max(0.0, (m_range - abs(delta_p)) / m_range),
        atr
    ]

    norm_v = []
    for j in range(len(v)):
        span = max_vals[j] - min_vals[j]
        norm_v.append((v[j] - min_vals[j]) / span if span > 1e-7 else 0.5)

    best_c = 0
    best_d = float('inf')
    for c_idx, c in enumerate(centroids):
        d = sum((norm_v[j] - c[j]) ** 2 for j in range(len(v)))
        if d < best_d:
            best_d = d
            best_c = c_idx

    return f"MORPH_{best_c}"
