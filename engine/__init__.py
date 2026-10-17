"""
Package: engine
Chuyên trách xử lý dữ liệu nến, trích xuất đặc trưng, huấn luyện AI và Backtest định lượng.
"""

from .backtest_ai import execute_backtest, load_candles, extract_daily_sessions

__all__ = ['execute_backtest', 'load_candles', 'extract_daily_sessions']
