#!/usr/bin/env python3
"""
==============================================================================
MODULE: HISTORY STORE (server/history_store.py)
==============================================================================
Chuyên trách lưu trữ và quản lý toàn bộ lịch sử các lần chạy Backtest/AI:
- Lưu file chi tiết: server/history/<run_id>.json
- Lưu danh mục tóm tắt: server/history/index.json
- Cung cấp các thao tác CRUD cho Web Server.
==============================================================================
"""

import os
import json
import glob
from datetime import datetime

SERVER_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SERVER_DIR)
HISTORY_DIR = os.path.join(SERVER_DIR, "history")
INDEX_FILE = os.path.join(HISTORY_DIR, "index.json")
ACTIVE_DATA_FILE = os.path.join(SERVER_DIR, "active_data.json")
ROOT_WEB_DATA = os.path.join(PROJECT_ROOT, "web_data.json")

os.makedirs(HISTORY_DIR, exist_ok=True)


def init_store():
    """Khởi tạo kho lưu trữ lịch sử, nạp baseline ban đầu nếu có."""
    runs = list_runs()
    if not runs:
        # Kiểm tra file web_data.json cũ ở root hoặc history cũ
        source_file = None
        if os.path.exists(ROOT_WEB_DATA):
            source_file = ROOT_WEB_DATA
        elif os.path.exists(os.path.join(PROJECT_ROOT, "history", "index.json")):
            # Di chuyển history cũ nếu có
            old_history = os.path.join(PROJECT_ROOT, "history")
            for f in glob.glob(os.path.join(old_history, "*.json")):
                dest = os.path.join(HISTORY_DIR, os.path.basename(f))
                if not os.path.exists(dest):
                    try:
                        import shutil
                        shutil.copy2(f, dest)
                    except Exception:
                        pass
            return rebuild_index()

        if source_file:
            try:
                with open(source_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                run_id = "run_initial_baseline"
                save_run(run_id, data, set_as_active=True)
            except Exception as e:
                print(f"[!] Lỗi nạp baseline: {e}")


def list_runs():
    """Lấy danh sách tóm tắt tất cả các lần chạy đã lưu."""
    if os.path.exists(INDEX_FILE):
        try:
            with open(INDEX_FILE, 'r', encoding='utf-8') as f:
                index_data = json.load(f)
                if isinstance(index_data, list):
                    return index_data
        except Exception:
            pass

    return rebuild_index()


def rebuild_index():
    """Quét thư mục history và lập lại danh mục index.json."""
    os.makedirs(HISTORY_DIR, exist_ok=True)
    json_files = glob.glob(os.path.join(HISTORY_DIR, "run_*.json"))
    index_list = []

    for fpath in json_files:
        fname = os.path.basename(fpath)
        run_id = fname.replace('.json', '')
        try:
            size_mb = round(os.path.getsize(fpath) / (1024 * 1024), 2)
            with open(fpath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            meta = data.get('metadata', {})
            test_data = data.get('test', {}).get('ai', {})
            train_data = data.get('train', {}).get('ai', {})
            all_time_data = data.get('all_time', {}).get('ai', {})
            filtered_count = data.get('volatility_filter_analysis', {}).get('test_filtered_days_count', 0)

            index_list.append({
                'run_id': run_id,
                'created_at': meta.get('generated_at', datetime.fromtimestamp(os.path.getmtime(fpath)).strftime('%Y-%m-%d %H:%M:%S')),
                'strategy_name': meta.get('strategy_name', 'Rocket 10h M15'),
                'params': meta.get('active_params', {}),
                'test_summary': {
                    'win_rate': test_data.get('win_rate', 0.0),
                    'net_pnl': test_data.get('net_pnl', 0.0),
                    'final_balance': test_data.get('final_balance', 10000.0),
                    'max_dd_percent': test_data.get('max_dd_percent', 0.0),
                    'profit_factor': test_data.get('profit_factor', 0.0),
                    'total_trades': test_data.get('total_trades', 0),
                    'max_layers': test_data.get('max_layers', 0)
                },
                'train_summary': {
                    'win_rate': train_data.get('win_rate', 0.0),
                    'net_pnl': train_data.get('net_pnl', 0.0),
                    'max_dd_percent': train_data.get('max_dd_percent', 0.0),
                    'profit_factor': train_data.get('profit_factor', 0.0),
                    'total_trades': train_data.get('total_trades', 0),
                    'max_layers': train_data.get('max_layers', 0)
                },
                'all_time_summary': {
                    'win_rate': all_time_data.get('win_rate', 0.0),
                    'net_pnl': all_time_data.get('net_pnl', 0.0),
                    'max_dd_percent': all_time_data.get('max_dd_percent', 0.0),
                    'profit_factor': all_time_data.get('profit_factor', 0.0),
                    'total_trades': all_time_data.get('total_trades', 0),
                    'max_layers': all_time_data.get('max_layers', 0)
                },
                'filtered_days_count': filtered_count,
                'file_name': fname,
                'file_size_mb': size_mb
            })
        except Exception as e:
            print(f"[!] Bỏ qua file lỗi {fname}: {e}")

    # Sắp xếp mới nhất lên đầu
    index_list.sort(key=lambda x: x.get('created_at', ''), reverse=True)

    with open(INDEX_FILE, 'w', encoding='utf-8') as f:
        json.dump(index_list, f, ensure_ascii=False, indent=2)

    return index_list


def save_run(run_id, data, set_as_active=True):
    """Lưu bản chạy vào server/history/<run_id>.json và cập nhật index.json."""
    os.makedirs(HISTORY_DIR, exist_ok=True)
    fpath = os.path.join(HISTORY_DIR, f"{run_id}.json")

    if 'metadata' not in data:
        data['metadata'] = {}
    data['metadata']['run_id'] = run_id
    if 'generated_at' not in data['metadata']:
        data['metadata']['generated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    with open(fpath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    if set_as_active:
        with open(ACTIVE_DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        # Giữ đồng bộ cả ROOT_WEB_DATA để tương thích
        try:
            with open(ROOT_WEB_DATA, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    rebuild_index()
    return fpath


def get_run(run_id):
    """Lấy chi tiết một bản chạy từ history."""
    fpath = os.path.join(HISTORY_DIR, f"{run_id}.json")
    if not os.path.exists(fpath):
        if run_id in ('active', 'current') and os.path.exists(ACTIVE_DATA_FILE):
            fpath = ACTIVE_DATA_FILE
        elif run_id in ('active', 'current') and os.path.exists(ROOT_WEB_DATA):
            fpath = ROOT_WEB_DATA
        else:
            return None

    with open(fpath, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_active_run():
    """Lấy bản chạy active hiện tại."""
    if os.path.exists(ACTIVE_DATA_FILE):
        with open(ACTIVE_DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    elif os.path.exists(ROOT_WEB_DATA):
        with open(ROOT_WEB_DATA, 'r', encoding='utf-8') as f:
            return json.load(f)

    # Nếu chưa có active, lấy bản mới nhất trong history
    runs = list_runs()
    if runs:
        return get_run(runs[0]['run_id'])
    return None


def select_active(run_id):
    """Chọn 1 bản chạy lịch sử làm active."""
    data = get_run(run_id)
    if not data:
        return None

    with open(ACTIVE_DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    try:
        with open(ROOT_WEB_DATA, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

    return data


def delete_run(run_id):
    """Xóa 1 bản chạy khỏi history."""
    fpath = os.path.join(HISTORY_DIR, f"{run_id}.json")
    if os.path.exists(fpath):
        os.remove(fpath)
        rebuild_index()
        return True
    return False
