#!/usr/bin/env python3
"""
==============================================================================
CLI RUNNER: CHẠY BACKTEST ĐỘC LẬP TỪ TERMINAL (engine/run_cli.py)
==============================================================================
Cách dùng:
  python3 engine/run_cli.py --min-step 0.5 --tp-single 0.8 --tp-dca 0.5 --hard-exit 14:00
==============================================================================
"""

import os
import sys
import json
import argparse

# Thêm đường dẫn project vào sys.path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
sys.path.insert(0, PROJECT_ROOT)

from engine.backtest_ai import execute_backtest

def main():
    parser = argparse.ArgumentParser(description="Chạy Backtest & Huấn Luyện AI Định Lượng (XAU/USD)")
    parser.add_argument('--min-step', type=float, default=0.5, help="Khoảng cách min giữa các lệnh DCA (mặc định: 0.5 ATR)")
    parser.add_argument('--tp-single', type=float, default=0.8, help="TP khi chỉ có 1 lệnh (mặc định: 0.8 ATR)")
    parser.add_argument('--tp-dca', type=float, default=0.5, help="TP khi đã nhồi DCA (mặc định: 0.5 ATR)")
    parser.add_argument('--hard-exit', type=str, default="14:00", help="Giờ cắt lỗ ép buộc (VD: 14:00, 12:00, 15:00)")
    parser.add_argument('--filter-ratio', type=float, default=5.0, help="Ngưỡng lọc sóng sáng (mặc định: 5.0x ATR)")
    parser.add_argument('--filter-atr', type=float, default=18.0, help="Ngưỡng ATR bão giá (mặc định: 18.0 USD)")
    parser.add_argument('--balance', type=float, default=10000.0, help="Vốn khởi điểm (mặc định: 10,000 USD)")
    parser.add_argument('--sizing-mode', type=str, default='atr_risk', choices=['atr_risk', 'capital'], help="Chế độ tính lot: 'atr_risk' (% rủi ro ATR co giãn) hoặc 'capital' ($5k/0.01 lot)")
    parser.add_argument('--risk-pct', type=float, default=0.5, help="% Rủi ro vốn co giãn theo ATR (mặc định: 0.5%)")
    parser.add_argument('--lot-cap', type=float, default=5000.0, help="Vốn ứng với 0.01 lot nếu dùng chế độ capital (mặc định: 5,000 USD)")
    parser.add_argument('--data-dir', type=str, default=None, help="Thư mục chứa dữ liệu nến (mặc định: data/)")
    parser.add_argument('--output', type=str, default=None, help="File JSON xuất kết quả (tùy chọn)")
    args = parser.parse_args()

    h_exit, m_exit = [int(x) for x in args.hard_exit.split(':')]

    config_params = {
        'min_step_atr': args.min_step,
        'tp_single_atr': args.tp_single,
        'tp_dca_atr': args.tp_dca,
        'hard_exit_hour': h_exit,
        'hard_exit_minute': m_exit,
        'filter_ratio_range': args.filter_ratio,
        'filter_range_min': 25.0,
        'filter_atr_max': args.filter_atr,
        'initial_balance': args.balance,
        'sizing_mode': args.sizing_mode,
        'risk_percent': args.risk_pct,
        'lot_step_capital': args.lot_cap
    }

    stats = execute_backtest(config_params, data_dir=args.data_dir)

    test_b = stats['test']['baseline']
    test_ai = stats['test']['ai']
    meta = stats['metadata']
    filtered_days = stats['volatility_filter_analysis']['filtered_days']
    elapsed = meta.get('execution_time_seconds', 0.0)

    print("\n" + "="*85)
    print(" KẾT QUẢ KIỂM ĐỊNH TẬP TEST (2021-2025): BASELINE VS CÓ BỘ LỌC BIẾN ĐỘNG (FILTER)")
    print(f" (Quy tắc: DCA min = {args.min_step} ATR | TP: {args.tp_single}/{args.tp_dca} ATR | Cắt lỗ: {args.hard_exit} VN)")
    print("="*85)
    print(f"{'CHỈ SỐ':<26} | {'KHÔNG LỌC (BASELINE)':<24} | {'CÓ LỌC BIẾN ĐỘNG (FILTER)':<26}")
    print("-" * 85)
    print(f"{'Số ngày giao dịch':<26} | {test_b['total_trades']:>24} | {test_ai['total_trades']:>26}")
    print(f"{'Tỷ lệ thắng (Winrate)':<26} | {test_b['win_rate']:>23}% | {test_ai['win_rate']:>25}%")
    print(f"{'Lợi nhuận ròng (Net PnL)':<26} | ${test_b['net_pnl']:>23,.2f} | ${test_ai['net_pnl']:>25,.2f}")
    print(f"{'Vốn cuối kỳ ($10,000)':<26} | ${test_b['final_balance']:>23,.2f} | ${test_ai['final_balance']:>25,.2f}")
    print(f"{'Sụt giảm tối đa (Max DD)':<26} | {test_b['max_dd_percent']:>23}% | {test_ai['max_dd_percent']:>25}%")
    print(f"{'Profit Factor':<26} | {test_b['profit_factor']:>24} | {test_ai['profit_factor']:>26}")
    print(f"{'Số lệnh nhồi lớn nhất':<26} | {test_b['max_layers']:>21} lệnh | {test_ai['max_layers']:>23} lệnh")
    print(f"{'Số ngày bị lọc bỏ':<26} | {'0 ngày':>24} | {len(filtered_days):>21} ngày")
    print("="*85)
    print(f" ⏱️ Thời gian thực thi toàn bộ: {elapsed} giây.")

    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
        print(f" ✓ Đã xuất file kết quả ra: {args.output}")

    print("="*85 + "\n")

if __name__ == '__main__':
    main()
