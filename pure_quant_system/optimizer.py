"""
==============================================================================
MODULE: OPTIMIZER (pure_quant_system/optimizer.py)
==============================================================================
Bộ máy Quant Grid Search tối ưu hóa tham số toán học trên 2011-2020:
- Quét lưới không gian tham số: min_dca_distance_atr, tp_single_atr, tp_basket_atr, max_layers
- Tìm bộ số mang lại: Maximize(Profit Factor * Winrate * (1 - MaxDD))
- Đóng băng cấu hình tối ưu vào pure_quant_optimal_params.json
==============================================================================
"""

import itertools
import json
import os
from typing import List, Dict, Any, Tuple, Optional
from pure_quant_system.models import Candle, SessionData
from pure_quant_system.execution_engine import PureQuantExecutionEngine
from pure_quant_system.metrics import calculate_metrics
from pure_quant_system.config import QUANT_SEARCH_SPACE, OPTIMAL_PARAMS_FILE, DEFAULT_CONFIG


from pure_quant_system.data_loader import M1TradingWindowCache


class PureQuantOptimizer:
    def __init__(self, search_space: Dict[str, List[Any]] = QUANT_SEARCH_SPACE):
        self.search_space = search_space

    def optimize_on_2011_2020(
        self,
        candles_m15: List[Candle],
        sessions: List[SessionData],
        m1_cache: Optional[M1TradingWindowCache] = None
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        if m1_cache is None:
            m1_cache = M1TradingWindowCache()

        keys = list(self.search_space.keys())
        values = list(self.search_space.values())
        combinations = list(itertools.product(*values))

        print(f"[*] Đang thực hiện Quant Grid Search qua {len(combinations)} tổ hợp tham số trên 2011-2020...")

        results = []
        for idx, combo in enumerate(combinations, 1):
            cfg = dict(DEFAULT_CONFIG)
            for k, v in zip(keys, combo):
                cfg[k] = v

            engine = PureQuantExecutionEngine(cfg, m1_cache=m1_cache)
            trades, _, circuit_skips = engine.run_simulation(candles_m15, sessions)
            m = calculate_metrics(trades, cfg["initial_balance"], len(sessions), circuit_skips)

            safety_factor = max(0.05, 1.0 - (m.max_drawdown_pct / 100.0))
            score = round(m.profit_factor * m.win_rate * safety_factor, 2)

            results.append({
                "params": {k: v for k, v in zip(keys, combo)},
                "win_rate": m.win_rate,
                "profit_factor": m.profit_factor,
                "net_profit": m.net_profit_dollars,
                "max_dd_pct": m.max_drawdown_pct,
                "score": score
            })

            # In tiến trình trực quan
            if idx % 3 == 0 or idx == len(combinations):
                print(f"    -> Đang quét [{idx:>2}/{len(combinations)} tổ hợp] | WR={m.win_rate:>5.1f}% | PF={m.profit_factor:>4.2f} | MaxDD={m.max_drawdown_pct:>4.1f}% | Điểm Quant={score:>6.1f}")

        results.sort(key=lambda x: x["score"], reverse=True)
        best = results[0]
        best_params = best["params"]

        # Lưu vào file JSON
        with open(OPTIMAL_PARAMS_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "best_params": best_params,
                "train_metrics": {
                    "win_rate": best["win_rate"],
                    "profit_factor": best["profit_factor"],
                    "net_profit": best["net_profit"],
                    "max_dd_pct": best["max_dd_pct"],
                    "quant_score": best["score"]
                },
                "period": "2011-2020 (10 năm In-Sample Quant Optimization)"
            }, f, indent=4, ensure_ascii=False)

        return best_params, results[:3]


def load_optimal_params() -> Optional[Dict[str, Any]]:
    """Nạp tham số đã tối ưu từ file JSON nếu có"""
    if os.path.isfile(OPTIMAL_PARAMS_FILE):
        try:
            with open(OPTIMAL_PARAMS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("best_params")
        except Exception:
            return None
    return None
