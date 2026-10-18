"""
==============================================================================
MODULE: DATA LOADER (pure_quant_system/data_loader.py)
==============================================================================
Nạp và chuẩn hóa dữ liệu đa khung thời gian:
1. M15 Loader: Nạp toàn bộ nến M15 để đo sóng sáng và tính ATR(14).
2. M1 Window Loader: Tối ưu bộ nhớ chỉ nạp các nến M1 trong khung giờ giao dịch
   (10:00 - 14:15 VN) của từng ngày để mô phỏng khớp lệnh chính xác từng phút.
==============================================================================
"""

import os
import glob
import csv
from datetime import datetime, timezone
from typing import List, Dict, Optional

from pure_quant_system.config import DATA_DIR, VN_TZ
from pure_quant_system.models import Candle


def load_m15_candles(years: Optional[List[int]] = None, data_dir: str = DATA_DIR) -> List[Candle]:
    """Nạp nến M15 của danh sách các năm được chỉ định"""
    if not os.path.isdir(data_dir):
        raise FileNotFoundError(f"Không tìm thấy thư mục data tại: {data_dir}")

    all_files = sorted(glob.glob(os.path.join(data_dir, "XAUUSD_*_m15.csv")))
    if not all_files:
        raise FileNotFoundError(f"Không tìm thấy file XAUUSD_*_m15.csv trong {data_dir}")

    target_files = []
    if years is not None:
        years_set = set(str(y) for y in years)
        for f in all_files:
            fname = os.path.basename(f)
            for y_str in years_set:
                if f"_{y_str}_" in fname or fname.startswith(f"XAUUSD_{y_str}"):
                    target_files.append(f)
                    break
    else:
        target_files = all_files

    raw_data = []
    for fpath in target_files:
        with open(fpath, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    ts = int(row["timestamp"])
                    o = float(row["open"])
                    h = float(row["high"])
                    l = float(row["low"])
                    c = float(row["close"])
                    v = float(row.get("volume", 0.0))
                    raw_data.append((ts, o, h, l, c, v))
                except (ValueError, KeyError):
                    continue

    raw_data.sort(key=lambda x: x[0])

    candles: List[Candle] = []
    for ts, o, h, l, c, v in raw_data:
        dt_utc = datetime.fromtimestamp(ts / 1000.0, tz=timezone.utc)
        dt_vn = dt_utc.astimezone(VN_TZ)
        candles.append(Candle(
            timestamp=ts,
            dt_vn=dt_vn,
            open=round(o, 3),
            high=round(h, 3),
            low=round(l, 3),
            close=round(c, 3),
            volume=v
        ))

    return candles


def compute_atr14(candles: List[Candle], period: int = 14) -> List[float]:
    """Tính toán chỉ báo ATR(14) trên khung M15"""
    n = len(candles)
    if n == 0:
        return []

    atrs = [0.0] * n
    trs = [candles[0].high - candles[0].low]

    for i in range(1, n):
        h = candles[i].high
        l = candles[i].low
        c_prev = candles[i - 1].close
        tr = max(h - l, abs(h - c_prev), abs(l - c_prev))
        trs.append(tr)

    if n < period:
        return [sum(trs) / len(trs)] * n

    running_tr = sum(trs[:period])
    atrs[period - 1] = running_tr / period

    for i in range(period, n):
        running_tr = running_tr - trs[i - period] + trs[i]
        atrs[i] = running_tr / period

    for i in range(period - 1):
        atrs[i] = atrs[period - 1]

    return atrs


class M1TradingWindowCache:
    """
    Trình nạp và lưu đệm nến M1 thông minh:
    Chỉ nạp và lưu các nến trong khung giờ giao dịch 10:00 - 14:15 VN của từng ngày.
    """
    def __init__(self, data_dir: str = DATA_DIR):
        self.data_dir = data_dir
        self.cached_years: Dict[int, Dict[str, List[Candle]]] = {}

    def get_session_m1(self, year: int, date_str: str) -> List[Candle]:
        """Lấy danh sách nến M1 (10:00 - 14:15 VN) của ngày date_str"""
        if year not in self.cached_years:
            self._load_year_m1(year)

        year_cache = self.cached_years.get(year, {})
        return year_cache.get(date_str, [])

    def _load_year_m1(self, year: int):
        fpath = os.path.join(self.data_dir, f"XAUUSD_{year}_m1.csv")
        if not os.path.isfile(fpath):
            self.cached_years[year] = {}
            return

        session_map: Dict[str, List[Candle]] = {}
        with open(fpath, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    ts = int(row["timestamp"])
                    dt_utc = datetime.fromtimestamp(ts / 1000.0, tz=timezone.utc)
                    dt_vn = dt_utc.astimezone(VN_TZ)

                    h = dt_vn.hour
                    m = dt_vn.minute
                    # Lưu nến từ 10:00 đến 14:15 VN
                    if (10 <= h < 14) or (h == 14 and m <= 15):
                        d_str = dt_vn.strftime("%Y-%m-%d")
                        c = Candle(
                            timestamp=ts,
                            dt_vn=dt_vn,
                            open=round(float(row["open"]), 3),
                            high=round(float(row["high"]), 3),
                            low=round(float(row["low"]), 3),
                            close=round(float(row["close"]), 3),
                            volume=float(row.get("volume", 0.0))
                        )
                        session_map.setdefault(d_str, []).append(c)
                except Exception:
                    continue

        for d_str in session_map:
            session_map[d_str].sort(key=lambda x: x.timestamp)

        self.cached_years[year] = session_map
