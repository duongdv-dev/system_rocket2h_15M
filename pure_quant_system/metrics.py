"""
==============================================================================
MODULE: METRICS (pure_quant_system/metrics.py)
==============================================================================
Tính toán chỉ số hiệu suất định lượng của hệ thống Pure Quant DCA:
- Win Rate, Profit Factor, Net PnL, Max Drawdown
- Phân phối tầng nhồi DCA (Bao nhiêu % ngày chỉ cần 1 lệnh, bao nhiêu % ngày nhồi 2, 3 tầng)
- Bóc tách hiệu suất chi tiết theo từng năm (Yearly Breakdown)
==============================================================================
"""

from typing import List, Dict, Any
from pure_quant_system.models import BasketTrade, PerformanceMetrics


def calculate_metrics(
    trades: List[BasketTrade],
    initial_balance: float = 10000.0,
    total_days: int = 0,
    circuit_skipped_days: int = 0
) -> PerformanceMetrics:
    """Tổng hợp chỉ số hiệu suất định lượng cho rổ lệnh DCA"""
    m = PerformanceMetrics()
    m.total_days = total_days or len(trades)
    m.traded_days = len(trades)
    m.circuit_skipped_days = circuit_skipped_days
    m.no_signal_days = max(0, m.total_days - m.traded_days - m.circuit_skipped_days)

    if not trades:
        return m

    wins = [t for t in trades if t.pnl_dollars > 0]
    losses = [t for t in trades if t.pnl_dollars < 0]

    m.win_trades = len(wins)
    m.loss_trades = len(losses)
    m.win_rate = round((m.win_trades / m.traded_days) * 100.0, 2)

    total_win = sum(t.pnl_dollars for t in wins)
    total_loss = abs(sum(t.pnl_dollars for t in losses))

    m.profit_factor = round(total_win / total_loss, 2) if total_loss > 0 else (99.0 if total_win > 0 else 0.0)
    m.net_profit_dollars = round(total_win - total_loss, 2)

    final_bal = trades[-1].balance_after
    m.total_return_pct = round(((final_bal - initial_balance) / initial_balance) * 100.0, 2)

    # Max Drawdown
    peak = initial_balance
    max_dd_dollars = 0.0
    max_dd_pct = 0.0

    for t in trades:
        bal = t.balance_after
        if bal > peak:
            peak = bal
        diff = peak - bal
        pct = (diff / peak) * 100.0 if peak > 0 else 0.0

        if diff > max_dd_dollars:
            max_dd_dollars = diff
        if pct > max_dd_pct:
            max_dd_pct = pct

    m.max_drawdown_dollars = round(max_dd_dollars, 2)
    m.max_drawdown_pct = round(max_dd_pct, 2)
    m.calmar_ratio = round(m.total_return_pct / max_dd_pct, 2) if max_dd_pct > 0 else 99.0

    m.tp_single_count = sum(1 for t in trades if t.exit_reason in ("TP_SINGLE", "BREAK_EVEN"))
    m.tp_basket_count = sum(1 for t in trades if t.exit_reason == "TP_BASKET_AVG")
    m.hard_exit_count = sum(1 for t in trades if t.exit_reason == "HARD_EXIT_TIME")

    # Phân phối tầng nhồi DCA
    for t in trades:
        m.layer_distribution[t.layers_count] = m.layer_distribution.get(t.layers_count, 0) + 1

    # Bóc tách từng năm
    yearly_dict: Dict[int, List[BasketTrade]] = {}
    for t in trades:
        yearly_dict.setdefault(t.year, []).append(t)

    for y, y_trades in sorted(yearly_dict.items()):
        y_wins = [t for t in y_trades if t.pnl_dollars > 0]
        y_losses = [t for t in y_trades if t.pnl_dollars < 0]
        y_win_d = sum(t.pnl_dollars for t in y_wins)
        y_loss_d = abs(sum(t.pnl_dollars for t in y_losses))
        y_pf = round(y_win_d / y_loss_d, 2) if y_loss_d > 0 else (99.0 if y_win_d > 0 else 0.0)
        y_wr = round((len(y_wins) / len(y_trades)) * 100.0, 1)

        m.yearly_breakdown[y] = {
            "trades": len(y_trades),
            "win_rate": y_wr,
            "profit_factor": y_pf,
            "net_dollars": round(y_win_d - y_loss_d, 2),
            "tp_single": sum(1 for t in y_trades if t.exit_reason in ("TP_SINGLE", "BREAK_EVEN")),
            "tp_basket": sum(1 for t in y_trades if t.exit_reason == "TP_BASKET_AVG"),
            "hard_exit": sum(1 for t in y_trades if t.exit_reason == "HARD_EXIT_TIME")
        }

    return m
