"""
==============================================================================
MODULE: MAIN CLI (pure_quant_system/run.py)
==============================================================================
Giao diện dòng lệnh chính (CLI) cho hệ thống Pure Quant DCA:
- mode=train: Tối ưu hóa tham số Quant Grid Search & Đánh giá In-Sample (2011-2020)
- mode=test: Kiểm định mù Out-of-Sample độc lập (2021-2025) bằng tham số đã đóng băng
- mode=all: Chạy song song và đối chiếu trực quan 10 năm Train vs 5 năm Test
==============================================================================
"""

import argparse
import sys
import os

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from pure_quant_system.config import (
    DEFAULT_CONFIG, TRAIN_YEARS, TEST_YEARS, OPTIMAL_PARAMS_FILE
)
from pure_quant_system.data_loader import load_m15_candles, compute_atr14, M1TradingWindowCache
from pure_quant_system.strategy import extract_sessions
from pure_quant_system.execution_engine import PureQuantExecutionEngine
from pure_quant_system.optimizer import PureQuantOptimizer, load_optimal_params
from pure_quant_system.metrics import calculate_metrics
from pure_quant_system.reporter import print_quant_report, export_json


def run_train_phase(config, m1_cache):
    """Giai đoạn 1: Quant Optimization & Đánh giá In-Sample (2011-2020)"""
    print("\n" + "=" * 88)
    print("🚀 [GIAI ĐOẠN 1: IN-SAMPLE 2011-2020] QUANT OPTIMIZATION & KIỂM THỬ 10 NĂM")
    print("=" * 88)

    # 1. Nạp nến M15
    print(f"[*] Đang nạp dữ liệu nến M15 các năm: {TRAIN_YEARS}...")
    candles_m15 = load_m15_candles(years=TRAIN_YEARS)
    print(f"    -> Đã nạp thành công: {len(candles_m15):,} nến M15.")

    print("[*] Đang tính toán chuỗi ATR(14)...")
    atrs = compute_atr14(candles_m15)

    print("[*] Đang phân tích sóng sáng 07h-10h & kiểm tra cầu chì bão giá...")
    sessions = extract_sessions(candles_m15, atrs, config)
    print(f"    -> Tổng số phiên 10h trích xuất: {len(sessions):,} ngày.")

    # 2. Chạy Quant Grid Search tìm tham số tối ưu
    print("\n" + "-" * 88)
    print("📐 BƯỚC 1: QUANT GRID SEARCH TỐI ƯU THAM SỐ TRÊN 2011-2020")
    print("-" * 88)
    optimizer = PureQuantOptimizer()
    best_params, top_results = optimizer.optimize_on_2011_2020(candles_m15, sessions, m1_cache=m1_cache)

    print("    -> TOP 3 CẤU HÌNH TỐI ƯU NHẤT QUA QUANT GRID SEARCH:")
    for rank, res in enumerate(top_results, 1):
        p = res["params"]
        print(f"       #{rank}: MinStep={p['min_dca_distance_atr']}x | SingleTP={p['tp_single_atr']}x | "
              f"BasketTP={p['tp_basket_atr']}x | MaxLayers={p['max_dca_layers']} | "
              f"WinRate={res['win_rate']}% | PF={res['profit_factor']} | MaxDD={res['max_dd_pct']}%")

    print(f"\n    [*] Đã chọn cấu hình tối ưu nhất và đóng băng vào: {OPTIMAL_PARAMS_FILE}")
    config.update(best_params)

    # 3. Chạy mô phỏng chi tiết có nến M1 trên 10 năm với cấu hình tối ưu
    print("\n" + "-" * 88)
    print("🎯 BƯỚC 2: CHẠY MÔ PHỎNG ĐA KHUNG (M15 SIGNAL + M1 REPLAY) TRÊN 2011-2020")
    print("-" * 88)
    engine = PureQuantExecutionEngine(config, m1_cache=m1_cache)
    trades, equity, circuit_skips = engine.run_simulation(candles_m15, sessions)

    metrics = calculate_metrics(trades, config["initial_balance"], len(sessions), circuit_skips)
    print_quant_report("HIỆU SUẤT IN-SAMPLE 2011 - 2020 (HUẤN LUYỆN & TỐI ƯU)", metrics, "2011-01-01 -> 2020-12-31")
    export_json(metrics, trades, "train_pure_quant_2011_2020.json")

    return metrics, config


def run_test_phase(config=None, m1_cache=None):
    """Giai đoạn 2: Kiểm định Mù Out-of-Sample trên 2021-2025"""
    print("\n" + "=" * 88)
    print("🧪 [GIAI ĐOẠN 2: OUT-OF-SAMPLE 2021-2025] KIỂM ĐỊNH MÙ ĐỘC LẬP")
    print("=" * 88)

    # 1. Nạp tham số đã đóng băng từ 2011-2020
    if config is None:
        config = dict(DEFAULT_CONFIG)
        saved_params = load_optimal_params()
        if saved_params:
            print(f"[*] Đang nạp tham số Quant tối ưu đã đóng băng từ: {OPTIMAL_PARAMS_FILE}")
            config.update(saved_params)
        else:
            print("[⚠️] Không tìm thấy file tham số tối ưu! Đang dùng cấu hình mặc định...")

    # 2. Nạp nến M15 các năm 2021 - 2025
    print(f"[*] Đang nạp dữ liệu nến M15 các năm kiểm định: {TEST_YEARS}...")
    candles_m15 = load_m15_candles(years=TEST_YEARS)
    print(f"    -> Đã nạp thành công: {len(candles_m15):,} nến M15.")

    atrs = compute_atr14(candles_m15)
    sessions = extract_sessions(candles_m15, atrs, config)
    print(f"    -> Tổng số phiên 10h trích xuất: {len(sessions):,} ngày.")

    # 3. Chạy mô phỏng mù hoàn toàn
    print("[*] Đang thực thi mô phỏng Out-of-Sample M15 + M1 Replay trên 2021-2025...")
    engine = PureQuantExecutionEngine(config, m1_cache=m1_cache)
    trades, equity, circuit_skips = engine.run_simulation(candles_m15, sessions)

    metrics = calculate_metrics(trades, config["initial_balance"], len(sessions), circuit_skips)
    print_quant_report("HIỆU SUẤT OUT-OF-SAMPLE 2021 - 2025 (KIỂM ĐỊNH MÙ THỰC TẾ)", metrics, "2021-01-01 -> 2025-12-31")
    export_json(metrics, trades, "test_pure_quant_2021_2025.json")

    return metrics


def main():
    parser = argparse.ArgumentParser(description="Hệ Thống PURE QUANT DCA M15/M1 Dynamic-ATR")
    parser.add_argument("--mode", choices=["train", "test", "all"], default="all",
                        help="train: Tối ưu Quant 2011-2020; test: Kiểm định mù 2021-2025; all: Chạy cả 2")
    args = parser.parse_args()

    cfg = dict(DEFAULT_CONFIG)
    m1_cache = M1TradingWindowCache()

    if args.mode == "train":
        run_train_phase(cfg, m1_cache)
    elif args.mode == "test":
        run_test_phase(m1_cache=m1_cache)
    elif args.mode == "all":
        train_m, opt_cfg = run_train_phase(cfg, m1_cache)
        test_m = run_test_phase(config=opt_cfg, m1_cache=m1_cache)

        # In bảng so sánh đối chiếu toàn diện
        print("\n" + "=" * 88)
        print("⚖️ TỔNG KẾT ĐỐI CHIẾU: PURE QUANT (IN-SAMPLE 2011-2020 VS OUT-OF-SAMPLE 2021-2025)")
        print("=" * 88)
        print(f"{'Chỉ Số Định Lượng':<32} | {'Train (2011-2020)':^22} | {'Test (2021-2025)':^22}")
        print("-" * 88)
        print(f"{'Win Rate Rổ Lệnh (%)':<32} | {train_m.win_rate:>20.2f} % | {test_m.win_rate:>20.2f} %")
        print(f"{'Profit Factor (PF)':<32} | {train_m.profit_factor:>22.2f} | {test_m.profit_factor:>22.2f}")
        print(f"{'Net Profit ($)':<32} | {train_m.net_profit_dollars:>20,.2f} $ | {test_m.net_profit_dollars:>20,.2f} $")
        print(f"{'Total Return (%)':<32} | {train_m.total_return_pct:>20.2f} % | {test_m.total_return_pct:>20.2f} %")
        print(f"{'Max Drawdown (%)':<32} | {train_m.max_drawdown_pct:>20.2f} % | {test_m.max_drawdown_pct:>20.2f} %")
        print(f"{'Calmar Ratio (Ret/MDD)':<32} | {train_m.calmar_ratio:>22.2f} | {test_m.calmar_ratio:>22.2f}")
        print(f"{'Số Phiên Cầu Chì Bão Giá Ngắt':<32} | {train_m.circuit_skipped_days:>22} | {test_m.circuit_skipped_days:>22}")
        print("=" * 88 + "\n")


if __name__ == "__main__":
    main()
