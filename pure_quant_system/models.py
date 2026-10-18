"""
==============================================================================
MODULE: MODELS (pure_quant_system/models.py)
==============================================================================
Các đối tượng dữ liệu lõi cho hệ thống Pure Quant:
- Candle: Biểu diễn nến M15 / M1 chuẩn hóa
- SessionRegime: Enum hình thái sóng sáng (UPTREND, DOWNTREND, SIDEWAY)
- SessionData: Thông tin phiên 10h00
- Order: Từng lệnh trong rổ DCA
- BasketTrade: Bản ghi toàn bộ rổ lệnh trong ngày
- PerformanceMetrics: Tổng kết chỉ số định lượng
==============================================================================
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Dict, Any, Optional


class SessionRegime(Enum):
    UPTREND = "UPTREND"
    DOWNTREND = "DOWNTREND"
    SIDEWAY = "SIDEWAY"


@dataclass
class Candle:
    timestamp: int
    dt_vn: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float

    @property
    def is_green(self) -> bool:
        return self.close > self.open

    @property
    def is_red(self) -> bool:
        return self.close < self.open

    @property
    def body_size(self) -> float:
        return abs(self.close - self.open)


@dataclass
class SessionData:
    date_str: str
    year: int
    idx_10h: int
    open_07h: float
    open_10h: float
    delta_p: float
    atr14: float
    morning_range: float
    regime: SessionRegime
    is_safe: bool = True
    skip_reason: str = "Bình thường"


@dataclass
class Order:
    layer: int                  # Tầng 1, 2, 3...
    entry_time: str
    entry_price: float
    lot: float
    direction: str              # "BUY" / "SELL"


@dataclass
class BasketTrade:
    date_str: str
    year: int
    direction: str
    regime: str
    orders: List[Order] = field(default_factory=list)
    total_lot: float = 0.0
    avg_entry_price: float = 0.0
    layers_count: int = 0
    exit_time: str = ""
    exit_price: float = 0.0
    exit_reason: str = ""       # "TP_SINGLE", "TP_BASKET_AVG", "HARD_EXIT_TIME"
    pnl_dollars: float = 0.0
    pnl_pct: float = 0.0
    balance_after: float = 0.0
    duration_minutes: int = 0


@dataclass
class PerformanceMetrics:
    total_days: int = 0
    traded_days: int = 0
    circuit_skipped_days: int = 0
    no_signal_days: int = 0
    win_trades: int = 0
    loss_trades: int = 0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    net_profit_dollars: float = 0.0
    total_return_pct: float = 0.0
    max_drawdown_dollars: float = 0.0
    max_drawdown_pct: float = 0.0
    calmar_ratio: float = 0.0
    tp_single_count: int = 0
    tp_basket_count: int = 0
    hard_exit_count: int = 0
    layer_distribution: Dict[int, int] = field(default_factory=dict)
    yearly_breakdown: Dict[int, Dict[str, Any]] = field(default_factory=dict)
