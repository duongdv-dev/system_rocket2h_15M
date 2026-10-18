"""
==============================================================================
MODULE: REPORTER (pure_quant_system/reporter.py)
==============================================================================
Báo cáo định lượng trực quan:
- In bảng ASCII chuyên nghiệp ra Terminal
- Báo cáo phân phối tầng nhồi DCA (Layers Distribution)
- Báo cáo hiệu suất bóc tách từng năm (2011 - 2025)
- Xuất file JSON chi tiết vào pure_quant_system/reports/
==============================================================================
"""

import os
import json
from typing import List, Dict, Any
from pure_quant_system.models import PerformanceMetrics, BasketTrade
from pure_quant_system.config import OUTPUT_DIR


def print_quant_report(
    title: str,
    metrics: PerformanceMetrics,
    period_str: str = ""
):
    sep = "=" * 88
    sub_sep = "-" * 88

    print(f"\n{sep}")
    print(f"📊 {title.upper()}")
    if period_str:
        print(f"🕒 Giai đoạn khảo sát: {period_str}")
    print(sep)

    print(f"  • Tổng số phiên khảo sát        : {metrics.total_days:>6} ngày")
    print(f"  • Số phiên vào lệnh thực tế     : {metrics.traded_days:>6} phiên ({metrics.traded_days/metrics.total_days*100:.1f}%)" if metrics.total_days > 0 else "")
    print(f"  • Số phiên CẦU CHÌ BÃO GIÁ ngắt : {metrics.circuit_skipped_days:>6} phiên ({metrics.circuit_skipped_days/metrics.total_days*100:.1f}%)" if metrics.total_days > 0 else "")
    print(f"  • Số phiên không có tín hiệu    : {metrics.no_signal_days:>6} phiên")
    print(sub_sep)
    print(f"  🎯 TỶ LỆ THẮNG RỔ LỆNH (WIN RATE): {metrics.win_rate:>6.2f} %  ({metrics.win_trades} Thắng / {metrics.loss_trades} Thua)")
    print(f"  ⚡ PROFIT FACTOR (PF)           : {metrics.profit_factor:>6.2f}")
    print(f"  💰 LỢI NHUẬN RÒNG (NET PROFIT)  : {metrics.net_profit_dollars:>+10,.2f} $  ({metrics.total_return_pct:>+.2f} %)")
    print(f"  🛡️ SỤT GIẢM TỐI ĐA (MAXDD)      : {metrics.max_drawdown_dollars:>10,.2f} $  ({metrics.max_drawdown_pct:.2f} %)")
    print(f"  ⚖️ HỆ SỐ CALMAR (RET / MDD)     : {metrics.calmar_ratio:>6.2f}")
    print(sub_sep)

    print("🪜 PHÂN PHỐI TẦNG NHỒI DCA (LAYERS DISTRIBUTION):")
    total_tr = metrics.traded_days or 1
    for layer in sorted(metrics.layer_distribution.keys()):
        cnt = metrics.layer_distribution[layer]
        pct = (cnt / total_tr) * 100.0
        print(f"  • Tầng {layer} ({'Lệnh đơn' if layer == 1 else f'Rổ {layer} lệnh'}): {cnt:>5} phiên ({pct:>5.1f}%)")

    print(sub_sep)
    print(f"  🎯 Chốt lời Lệnh Đơn (Single TP): {metrics.tp_single_count:>5} lần")
    print(f"  🎯 Chốt lời Rổ Nhồi (Basket TP) : {metrics.tp_basket_count:>5} lần")
    print(f"  ⏰ Thoát Hard Exit (14:00 VN)   : {metrics.hard_exit_count:>5} lần")
    print(sub_sep)

    print("\n📅 CHI TIẾT HIỆU SUẤT THEO TỪNG NĂM (YEARLY BREAKDOWN):")
    print(f"{'Năm':^6} | {'Số Phiên':^8} | {'Win Rate':^10} | {'Profit Factor':^14} | {'Net PnL ($)':^14} | {'Single/Basket/HardExit':^24}")
    print("-" * 88)

    for y, stats in sorted(metrics.yearly_breakdown.items()):
        detail_str = f"{stats['tp_single']} / {stats['tp_basket']} / {stats['hard_exit']}"
        print(f"{y:^6} | {stats['trades']:^8} | {stats['win_rate']:>8.1f} % | {stats['profit_factor']:>14.2f} | {stats['net_dollars']:>+12,.2f} $ | {detail_str:^24}")
    print(sep + "\n")


def export_json(
    metrics: PerformanceMetrics,
    trades: List[BasketTrade],
    filename: str
) -> str:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    fpath = os.path.join(OUTPUT_DIR, filename)

    data = {
        "summary": {
            "total_days": metrics.total_days,
            "traded_days": metrics.traded_days,
            "circuit_skipped_days": metrics.circuit_skipped_days,
            "win_rate": metrics.win_rate,
            "profit_factor": metrics.profit_factor,
            "net_profit_dollars": metrics.net_profit_dollars,
            "total_return_pct": metrics.total_return_pct,
            "max_drawdown_pct": metrics.max_drawdown_pct,
            "calmar_ratio": metrics.calmar_ratio,
            "layer_distribution": metrics.layer_distribution
        },
        "yearly": metrics.yearly_breakdown,
        "sample_trades": [
            {
                "date": t.date_str,
                "dir": t.direction,
                "regime": t.regime,
                "layers": t.layers_count,
                "total_lot": t.total_lot,
                "avg_entry": t.avg_entry_price,
                "exit_time": t.exit_time,
                "exit_price": t.exit_price,
                "exit_reason": t.exit_reason,
                "pnl_dollars": t.pnl_dollars,
                "balance": t.balance_after
            }
            for t in trades[:100]
        ]
    }

    with open(fpath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    return fpath
