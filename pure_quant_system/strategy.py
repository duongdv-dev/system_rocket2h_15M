"""
==============================================================================
MODULE: STRATEGY (pure_quant_system/strategy.py)
==============================================================================
Hiện thực hóa logic phân tích sóng sáng và bộ lọc cầu chì:
1. Đo sóng sáng: Delta P = Open(10:00) - Open(07:00)
2. Bộ lọc cầu chì (Circuit Breaker):
   - Ngắt khi biên độ sáng giãn quá đà (>= 3.5x ATR)
   - Ngắt khi ATR đột biến so với thị giá 2026 (>= 0.70% thị giá)
3. Phân loại hình thái: UPTREND / DOWNTREND / SIDEWAY co giãn theo ATR
==============================================================================
"""

from typing import List, Dict, Any, Optional
from pure_quant_system.models import Candle, SessionRegime, SessionData


def extract_sessions(
    candles: List[Candle],
    atrs: List[float],
    config: Dict[str, Any]
) -> List[SessionData]:
    """Quét dữ liệu và phân tích các phiên 10:00 VN"""
    sessions: List[SessionData] = []
    n = len(candles)
    sideway_atr_ratio = float(config.get("sideway_atr_ratio", 0.15))
    stretch_limit = float(config.get("circuit_stretch_ratio", 3.5))
    relative_atr_limit = float(config.get("circuit_relative_atr_pct", 0.70))

    i = 0
    while i < n:
        c = candles[i]
        dt = c.dt_vn

        # Mốc 10:00 VN
        if dt.hour == 10 and dt.minute == 0 and i >= 20:
            cur_date = dt.strftime("%Y-%m-%d")
            cur_year = dt.year
            cur_atr = atrs[i] if atrs[i] > 0 else 4.0
            open_10h = c.open

            # Tìm nến 07:00 VN của cùng ngày
            idx_07h = None
            for back_step in range(8, 20):
                chk_idx = i - back_step
                if chk_idx >= 0:
                    chk_c = candles[chk_idx]
                    if chk_c.dt_vn.strftime("%Y-%m-%d") == cur_date and chk_c.dt_vn.hour == 7 and chk_c.dt_vn.minute == 0:
                        idx_07h = chk_idx
                        break

            if idx_07h is None:
                for back_step in range(16, 0, -1):
                    chk_idx = i - back_step
                    if chk_idx >= 0:
                        chk_c = candles[chk_idx]
                        if chk_c.dt_vn.strftime("%Y-%m-%d") == cur_date and chk_c.dt_vn.hour >= 7:
                            idx_07h = chk_idx
                            break

            if idx_07h is not None:
                open_07h = candles[idx_07h].open
                morning_candles = candles[idx_07h:i]
                if morning_candles:
                    m_high = max(mc.high for mc in morning_candles)
                    m_low = min(mc.low for mc in morning_candles)
                else:
                    m_high = c.high
                    m_low = c.low

                morning_range = round(m_high - m_low, 3)
                delta_p = round(open_10h - open_07h, 3)

                # 1. Kiểm tra cầu chì bão giá (Circuit Breaker)
                is_safe = True
                skip_reasons = []

                # A. Biên độ sáng giãn quá đà
                stretch_ratio = morning_range / cur_atr
                if stretch_ratio >= stretch_limit:
                    is_safe = False
                    skip_reasons.append(f"Sóng sáng giãn mạnh ({stretch_ratio:.1f}x ATR >= {stretch_limit}x)")

                # B. ATR đột biến so với thị giá (Thích ứng hoàn hảo mọi mức giá 2011 - 2026)
                rel_atr_pct = (cur_atr / open_10h) * 100.0
                if rel_atr_pct >= relative_atr_limit:
                    is_safe = False
                    skip_reasons.append(f"ATR bão giá cực đoan ({rel_atr_pct:.2f}% thị giá >= {relative_atr_limit}%)")

                reason_str = " | ".join(skip_reasons) if not is_safe else "Bình thường"

                # 2. Xác định hình thái sóng sáng
                threshold = max(0.5, round(sideway_atr_ratio * cur_atr, 3))
                if abs(delta_p) <= threshold:
                    regime = SessionRegime.SIDEWAY
                elif delta_p > threshold:
                    regime = SessionRegime.UPTREND
                else:
                    regime = SessionRegime.DOWNTREND

                sessions.append(SessionData(
                    date_str=cur_date,
                    year=cur_year,
                    idx_10h=i,
                    open_07h=open_07h,
                    open_10h=open_10h,
                    delta_p=delta_p,
                    atr14=cur_atr,
                    morning_range=morning_range,
                    regime=regime,
                    is_safe=is_safe,
                    skip_reason=reason_str
                ))

            i += 30
        else:
            i += 1

    return sessions
