"""
==============================================================================
MODULE: EXECUTION ENGINE (pure_quant_system/execution_engine.py)
==============================================================================
Động cơ mô phỏng khớp lệnh đa khung thời gian:
- Tín hiệu & Nhồi DCA: Quản lý theo từng đóng nến M15 (07h-12h30).
- Khớp lệnh, Break-Even & Thoát lệnh: Tua từng phút qua nến M1 (10h-14h).
- Chốt lời rổ nhồi: Thoát sạch khi giá vượt Giá Trung Bình + (0.15 x ATR).
- Hard Exit: Đúng 14:00:00 VN đóng sạch rổ lệnh.
==============================================================================
"""

from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime

from pure_quant_system.models import (
    Candle, SessionData, SessionRegime, Order, BasketTrade
)
from pure_quant_system.data_loader import M1TradingWindowCache


class PureQuantExecutionEngine:
    def __init__(self, config: Dict[str, Any], m1_cache: Optional[M1TradingWindowCache] = None):
        self.config = config
        self.m1_cache = m1_cache or M1TradingWindowCache()

    def run_simulation(
        self,
        candles_m15: List[Candle],
        sessions: List[SessionData]
    ) -> Tuple[List[BasketTrade], List[Dict[str, Any]], int]:
        """
        Mô phỏng khớp lệnh toàn bộ danh sách các phiên.
        Trả về: (danh sách BasketTrade, danh sách điểm trên Equity Curve, số phiên bị cầu chì ngắt)
        """
        initial_balance = float(self.config.get("initial_balance", 10000.0))
        risk_pct = float(self.config.get("risk_percent", 1.0))
        heat_buffer_mult = float(self.config.get("heat_buffer_atr", 5.0))
        
        sideway_ratio = float(self.config.get("sideway_atr_ratio", 0.15))
        min_dca_ratio = float(self.config.get("min_dca_distance_atr", 0.40))
        tp_single_ratio = float(self.config.get("tp_single_atr", 0.45))
        tp_basket_ratio = float(self.config.get("tp_basket_atr", 0.15))
        max_layers = int(self.config.get("max_dca_layers", 4))
        
        hard_exit_h = int(self.config.get("hard_exit_hour", 14))
        hard_exit_m = int(self.config.get("hard_exit_minute", 0))
        
        spread = float(self.config.get("spread_dollars", 0.25))
        slippage = float(self.config.get("slippage_dollars", 0.05))

        balance = initial_balance
        peak_balance = initial_balance
        trades: List[BasketTrade] = []
        equity_curve: List[Dict[str, Any]] = [{
            "date": sessions[0].date_str if sessions else "Start",
            "balance": balance,
            "drawdown_pct": 0.0
        }]

        circuit_skipped = 0
        n_m15 = len(candles_m15)

        for s in sessions:
            # 1. BỘ LỌC CẦU CHÌ BÃO GIÁ
            if not s.is_safe:
                circuit_skipped += 1
                continue

            atr = max(1.0, s.atr14)

            # 2. XÁC ĐỊNH HƯỚNG GIAO DỊCH (BUY hoặc SELL)
            c_10h_idx = s.idx_10h
            c_10h = candles_m15[c_10h_idx]

            if s.regime == SessionRegime.SIDEWAY:
                if c_10h.is_green:
                    direction = "BUY"
                elif c_10h.is_red:
                    direction = "SELL"
                else:
                    continue  # Doji đi ngang, bỏ qua
            elif s.regime == SessionRegime.UPTREND:
                direction = "BUY"
            else:
                direction = "SELL"

            # 3. TÍNH TOÁN LOT SIZE TỰ ĐỘNG THEO ATR
            risk_dollars = balance * (risk_pct / 100.0)
            heat_buffer = max(10.0, atr * heat_buffer_mult)
            base_lot = max(0.01, round(risk_dollars / (heat_buffer * 100.0), 2))

            # Ngưỡng khoảng cách tính theo ATR
            min_dca_dist = max(1.5, round(atr * min_dca_ratio, 2))
            tp_single_dist = max(1.5, round(atr * tp_single_ratio, 2))
            tp_basket_dist = max(0.8, round(atr * tp_basket_ratio, 2))

            # 4. NẠP NẾN M1 TRONG KHUNG GIAO DỊCH (10:00 - 14:15 VN)
            m1_bars = self.m1_cache.get_session_m1(s.year, s.date_str)
            if not m1_bars:
                # Nếu không có file M1 ngày đó, dùng nến M15 fallback
                continue

            # 5. MÔ PHỎNG CHI TIẾT TỪNG PHÚT M1
            orders: List[Order] = []
            trade_closed = False
            exit_reason = "--"
            exit_price = 0.0
            exit_time_str = ""
            is_break_even = False
            m1_start_time = 0

            # Quét từng nến M1
            for m1 in m1_bars:
                dt = m1.dt_vn
                h = dt.hour
                m = dt.minute

                # A. KIỂM TRA ĐIỀU KIỆN M15 ĐÓNG NẾN (đúng các phút 15, 30, 45, 00)
                if m in (0, 15, 30, 45):
                    # Tìm nến M15 vừa đóng
                    # Nếu chưa có lệnh nào mở (Chờ Lệnh 1)
                    if len(orders) == 0:
                        should_enter_layer1 = False

                        if s.regime == SessionRegime.SIDEWAY and h == 10 and m == 15:
                            should_enter_layer1 = True
                        elif s.regime == SessionRegime.UPTREND and (h < 12 or (h == 12 and m <= 30)):
                            # Nến M15 vừa đóng là nến ĐỎ
                            if m1.close < m1.open:
                                should_enter_layer1 = True
                        elif s.regime == SessionRegime.DOWNTREND and (h < 12 or (h == 12 and m <= 30)):
                            # Nến M15 vừa đóng là nến XANH
                            if m1.close > m1.open:
                                should_enter_layer1 = True

                        if should_enter_layer1:
                            if direction == "BUY":
                                e_price = round(m1.close + (spread / 2.0) + slippage, 3)
                            else:
                                e_price = round(m1.close - (spread / 2.0) - slippage, 3)

                            orders.append(Order(
                                layer=1,
                                entry_time=dt.strftime("%Y-%m-%d %H:%M"),
                                entry_price=e_price,
                                lot=base_lot,
                                direction=direction
                            ))
                            m1_start_time = m1.timestamp

                    # Nếu ĐÃ CÓ LỆNH và đang xem xét nhồi DCA (Tầng 2, 3, 4)
                    elif len(orders) < max_layers and (h < 13 or (h == 13 and m <= 30)):
                        last_order = orders[-1]
                        should_dca = False

                        if direction == "BUY":
                            # Nến M15 đóng nến Đỏ VÀ giá giảm cách lệnh trước ít nhất min_dca_dist
                            if m1.close < m1.open and (last_order.entry_price - m1.close) >= min_dca_dist:
                                should_dca = True
                        else:  # SELL
                            # Nến M15 đóng nến Xanh VÀ giá tăng cách lệnh trước ít nhất min_dca_dist
                            if m1.close > m1.open and (m1.close - last_order.entry_price) >= min_dca_dist:
                                should_dca = True

                        if should_dca:
                            if direction == "BUY":
                                e_price = round(m1.close + (spread / 2.0) + slippage, 3)
                            else:
                                e_price = round(m1.close - (spread / 2.0) - slippage, 3)

                            # Tăng nhẹ lot tầng nhồi để kéo giá trung bình nhanh hơn
                            next_lot = round(base_lot * (1.2 ** len(orders)), 2)
                            orders.append(Order(
                                layer=len(orders) + 1,
                                entry_time=dt.strftime("%Y-%m-%d %H:%M"),
                                entry_price=e_price,
                                lot=next_lot,
                                direction=direction
                            ))

                # B. KIỂM TRA ĐIỀU KIỆN CHỐT LỜI / THOÁT LỆNH TRONG TỪNG PHÚT M1
                if len(orders) > 0:
                    tot_lot = sum(o.lot for o in orders)
                    avg_entry = sum(o.entry_price * o.lot for o in orders) / tot_lot

                    # 1. KHI CHỈ CÓ 1 LỆNH (Lệnh đơn)
                    if len(orders) == 1:
                        single_o = orders[0]
                        if direction == "BUY":
                            # Kéo hòa vốn (BE) khi lãi 50% target
                            if m1.high >= single_o.entry_price + (tp_single_dist * 0.5):
                                is_break_even = True

                            # Chốt lời chạm TP Single
                            if m1.high >= single_o.entry_price + tp_single_dist:
                                trade_closed = True
                                exit_reason = "TP_SINGLE"
                                exit_price = single_o.entry_price + tp_single_dist
                                exit_time_str = dt.strftime("%Y-%m-%d %H:%M")
                                break

                            # Dính SL hòa vốn
                            if is_break_even and m1.low <= single_o.entry_price:
                                trade_closed = True
                                exit_reason = "BREAK_EVEN"
                                exit_price = single_o.entry_price
                                exit_time_str = dt.strftime("%Y-%m-%d %H:%M")
                                break

                        else:  # SELL
                            if m1.low <= single_o.entry_price - (tp_single_dist * 0.5):
                                is_break_even = True

                            if m1.low <= single_o.entry_price - tp_single_dist:
                                trade_closed = True
                                exit_reason = "TP_SINGLE"
                                exit_price = single_o.entry_price - tp_single_dist
                                exit_time_str = dt.strftime("%Y-%m-%d %H:%M")
                                break

                            if is_break_even and m1.high >= single_o.entry_price:
                                trade_closed = True
                                exit_reason = "BREAK_EVEN"
                                exit_price = single_o.entry_price
                                exit_time_str = dt.strftime("%Y-%m-%d %H:%M")
                                break

                    # 2. KHI RỔ ĐÃ NHỒI (>= 2 LỆNH)
                    else:
                        if direction == "BUY":
                            basket_tp = avg_entry + tp_basket_dist
                            if m1.high >= basket_tp:
                                trade_closed = True
                                exit_reason = "TP_BASKET_AVG"
                                exit_price = basket_tp
                                exit_time_str = dt.strftime("%Y-%m-%d %H:%M")
                                break
                        else:  # SELL
                            basket_tp = avg_entry - tp_basket_dist
                            if m1.low <= basket_tp:
                                trade_closed = True
                                exit_reason = "TP_BASKET_AVG"
                                exit_price = basket_tp
                                exit_time_str = dt.strftime("%Y-%m-%d %H:%M")
                                break

                    # 3. ĐIỀU KIỆN HARD EXIT ĐÚNG 14:00 VN
                    if (h > hard_exit_h) or (h == hard_exit_h and m >= hard_exit_m):
                        trade_closed = True
                        exit_reason = "HARD_EXIT_TIME"
                        exit_price = m1.close
                        exit_time_str = dt.strftime("%Y-%m-%d %H:%M")
                        break

            # 6. TỔNG KẾT KẾT QUẢ RỔ LỆNH NẾU CÓ VÀO LỆNH
            if len(orders) > 0 and trade_closed:
                tot_lot = sum(o.lot for o in orders)
                avg_entry = sum(o.entry_price * o.lot for o in orders) / tot_lot

                # Tính tổng PnL cho cả rổ lệnh
                pnl_dollars = 0.0
                for o in orders:
                    if direction == "BUY":
                        diff = exit_price - o.entry_price
                    else:
                        diff = o.entry_price - exit_price
                    pnl_dollars += diff * o.lot * 100.0

                pnl_dollars = round(pnl_dollars, 2)
                pnl_pct = round((pnl_dollars / balance) * 100.0, 2)
                balance = round(balance + pnl_dollars, 2)

                if balance > peak_balance:
                    peak_balance = balance
                dd_pct = round(((peak_balance - balance) / peak_balance) * 100.0, 2)

                duration = max(15, int((m1_bars[-1].timestamp - m1_start_time) / 60000)) if m1_start_time > 0 else 60

                trades.append(BasketTrade(
                    date_str=s.date_str,
                    year=s.year,
                    direction=direction,
                    regime=s.regime.value,
                    orders=orders,
                    total_lot=round(tot_lot, 2),
                    avg_entry_price=round(avg_entry, 3),
                    layers_count=len(orders),
                    exit_time=exit_time_str,
                    exit_price=exit_price,
                    exit_reason=exit_reason,
                    pnl_dollars=pnl_dollars,
                    pnl_pct=pnl_pct,
                    balance_after=balance,
                    duration_minutes=duration
                ))

                equity_curve.append({
                    "date": s.date_str,
                    "balance": balance,
                    "drawdown_pct": dd_pct
                })

        return trades, equity_curve, circuit_skipped
