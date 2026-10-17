#!/usr/bin/env python3
"""
==============================================================================
WEB SERVER & API PROVIDER (server/app.py)
==============================================================================
Nhiệm vụ chuyên trách:
  1. Phục vụ Web UI React (từ frontend/dist) hoặc dashboard.html dự phòng.
  2. Là nơi lưu trữ và quản lý toàn bộ lịch sử các lần chạy (server/history/).
  3. Cung cấp API cho Web UI:
     - GET  /api/status       : Kiểm tra sức khỏe server, run active, trạng thái chạy
     - GET  /api/history      : Lấy danh sách tóm tắt toàn bộ các lần chạy
     - GET  /api/runs/<id>    : Lấy chi tiết toàn bộ dữ liệu 1 bản chạy cụ thể
     - POST /api/run          : Nhận tham số từ Web UI, kích hoạt AI Engine tính toán và lưu lịch sử
     - POST /api/runs/select  : Chọn 1 bản chạy lịch sử làm Active
     - DELETE /api/runs/<id>  : Xóa 1 bản chạy khỏi lịch sử
     - GET  /api/data         : Lấy dữ liệu bản chạy active
==============================================================================
"""

import os
import sys
import json
import uuid
import threading
import argparse
from datetime import datetime
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

SERVER_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SERVER_DIR)
FRONTEND_DIST = os.path.join(PROJECT_ROOT, "frontend", "dist")
DASHBOARD_HTML = os.path.join(PROJECT_ROOT, "dashboard.html")

# Thêm đường dẫn project vào sys.path để import engine
sys.path.insert(0, PROJECT_ROOT)

from server.history_store import (
    init_store,
    list_runs,
    get_run,
    get_active_run,
    save_run,
    select_active,
    delete_run
)

# Khóa luồng kiểm soát tiến trình chạy Backtest
TRAINING_LOCK = threading.Lock()
IS_TRAINING = False


class QuantApiHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        base_dir = FRONTEND_DIST if os.path.isdir(FRONTEND_DIST) else PROJECT_ROOT
        super().__init__(*args, directory=base_dir, **kwargs)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()

    def do_GET(self):
        # 1. API: Trạng thái máy chủ
        if self.path == '/api/status':
            runs = list_runs()
            active_data = get_active_run()
            meta = active_data.get('metadata', {}) if active_data else {}
            active_run_id = meta.get('run_id', 'active_run')

            status_payload = {
                "server_status": "online",
                "is_training": IS_TRAINING,
                "active_run_id": active_run_id,
                "total_runs": len(runs),
                "ui_type": "react_production" if os.path.isdir(FRONTEND_DIST) else "fallback_html",
                "active_metadata": meta,
                "server_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            self.send_json_response(status_payload)
            return

        # 2. API: Lấy danh sách tóm tắt toàn bộ lịch sử các lần chạy
        if self.path in ('/api/history', '/api/runs'):
            runs = list_runs()
            active_data = get_active_run()
            active_run_id = active_data.get('metadata', {}).get('run_id') if active_data else None

            self.send_json_response({
                "status": "success",
                "active_run_id": active_run_id,
                "total_runs": len(runs),
                "runs": runs
            })
            return

        # 3. API: Lấy chi tiết một lần chạy cụ thể (/api/runs/<run_id>)
        if self.path.startswith('/api/runs/'):
            run_id = self.path.replace('/api/runs/', '').split('?')[0].strip('/')
            run_data = get_run(run_id)
            if run_data:
                self.send_json_response(run_data)
            else:
                self.send_json_error(f"Không tìm thấy bản chạy '{run_id}' trong lịch sử.", 404)
            return

        # 4. API: Lấy dữ liệu bản chạy active
        if self.path in ('/api/data', '/web_data.json'):
            active_data = get_active_run()
            if active_data:
                self.send_json_response(active_data)
            else:
                self.send_json_error("Chưa có dữ liệu nào trong lịch sử.", 404)
            return

        # 5. Phục vụ Web UI:
        if not os.path.isdir(FRONTEND_DIST):
            if self.path in ('/', '/index.html'):
                self.path = '/dashboard.html'
        else:
            # SPA Routing cho React
            requested_file = os.path.join(FRONTEND_DIST, self.path.lstrip('/'))
            if not os.path.exists(requested_file) and not self.path.startswith('/api'):
                self.path = '/index.html'

        return super().do_GET()

    def do_POST(self):
        global IS_TRAINING
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length).decode('utf-8')
        try:
            body = json.loads(post_data) if post_data else {}
        except Exception:
            body = {}

        # 1. API: Web UI gửi tham số -> Server gọi AI Engine tính toán và Server lưu lịch sử
        if self.path == '/api/run':
            if IS_TRAINING:
                self.send_json_error("Đang có một tiến trình huấn luyện đang chạy. Vui lòng đợi trong giây lát.", 409)
                return

            with TRAINING_LOCK:
                IS_TRAINING = True

            try:
                # Gọi engine tính toán
                from engine.backtest_ai import execute_backtest

                h_exit = int(body.get('hard_exit_hour', 14))
                m_exit = int(body.get('hard_exit_minute', 0))
                if 'hard_exit' in body and isinstance(body['hard_exit'], str) and ':' in body['hard_exit']:
                    parts = body['hard_exit'].split(':')
                    h_exit, m_exit = int(parts[0]), int(parts[1])

                config_params = {
                    'min_step_atr': float(body.get('min_step_atr', 0.5)),
                    'tp_single_atr': float(body.get('tp_single_atr', 0.8)),
                    'tp_dca_atr': float(body.get('tp_dca_atr', 0.5)),
                    'hard_exit_hour': h_exit,
                    'hard_exit_minute': m_exit,
                    'filter_ratio_range': float(body.get('filter_ratio_range', 5.0)),
                    'filter_range_min': 25.0,
                    'filter_atr_max': float(body.get('filter_atr_max', 18.0)),
                    'initial_balance': float(body.get('initial_balance', 10000.0)),
                    'sizing_mode': str(body.get('sizing_mode', 'atr_risk')),
                    'risk_percent': float(body.get('risk_percent', 0.5)),
                    'lot_step_capital': float(body.get('lot_step_capital', 5000.0))
                }

                # Engine thực thi trên dữ liệu nến
                stats = execute_backtest(config_params)

                # Server tạo Run ID và tự lưu trữ vào lịch sử của Server
                run_id = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:4]}"
                stats['metadata']['run_id'] = run_id
                save_run(run_id, stats, set_as_active=True)

                self.send_json_response({
                    "status": "success",
                    "message": "Chạy Backtest và Huấn Luyện AI thành công!",
                    "run_id": run_id,
                    "data": stats
                })
            except Exception as e:
                self.send_json_error(f"Lỗi thực thi: {str(e)}", 500)
            finally:
                with TRAINING_LOCK:
                    IS_TRAINING = False
            return

        # 2. API: Chọn 1 bản chạy lịch sử làm Active
        if self.path == '/api/runs/select':
            run_id = body.get('run_id')
            if not run_id:
                self.send_json_error("Thiếu tham số 'run_id'", 400)
                return

            data = select_active(run_id)
            if data:
                self.send_json_response({
                    "status": "success",
                    "message": f"Đã chọn bản chạy '{run_id}' làm dữ liệu hiển thị chính.",
                    "run_id": run_id,
                    "data": data
                })
            else:
                self.send_json_error(f"Không tìm thấy bản chạy '{run_id}'.", 404)
            return

        self.send_json_error(f"Endpoint POST '{self.path}' không tồn tại.", 404)

    def do_DELETE(self):
        # API: Xóa một bản chạy khỏi lịch sử
        if self.path.startswith('/api/runs/'):
            run_id = self.path.replace('/api/runs/', '').split('?')[0].strip('/')
            success = delete_run(run_id)
            if success:
                self.send_json_response({
                    "status": "success",
                    "message": f"Đã xóa thành công bản chạy '{run_id}'.",
                    "deleted_run_id": run_id
                })
            else:
                self.send_json_error(f"Không thể xóa bản chạy '{run_id}' (không tồn tại).", 404)
            return

        self.send_json_error(f"Endpoint DELETE '{self.path}' không tồn tại.", 404)

    def send_json_response(self, data, status_code=200):
        encoded = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(encoded)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, DELETE, OPTIONS')
        self.send_header('Cache-Control', 'no-cache')
        self.end_headers()
        self.wfile.write(encoded)

    def send_json_error(self, message, status_code=400):
        self.send_json_response({"status": "error", "message": message}, status_code=status_code)

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        super().end_headers()


def run_server(host='0.0.0.0', port=8080):
    # Khởi tạo kho lưu trữ lịch sử
    init_store()

    server_address = (host, port)
    try:
        httpd = ThreadingHTTPServer(server_address, QuantApiHandler)
    except OSError as e:
        if e.errno == 98 or "already in use" in str(e).lower():
            alt_port = port + 1
            print(f"[!] Cổng {port} đang bận. Đang chuyển sang cổng {alt_port}...")
            server_address = (host, alt_port)
            httpd = ThreadingHTTPServer(server_address, QuantApiHandler)
            port = alt_port
        else:
            raise e

    display_host = 'localhost' if host in ('0.0.0.0', '127.0.0.1') else host
    mode_text = "React Production (frontend/dist)" if os.path.isdir(FRONTEND_DIST) else "Fallback HTML (dashboard.html)"
    runs_count = len(list_runs())

    print("\n" + "="*75)
    print(" 🌐 QUANT WEB SERVER & HISTORY MANAGER (server/app.py)")
    print("="*75)
    print(f" • Chế độ Phục Vụ        : {mode_text}")
    print(f" • Mở trên trình duyệt    : http://{display_host}:{port}")
    print(f" • Truy cập từ ngoài VPS : http://<IP_VPS_CỦA_BẠN>:{port}")
    print(f" • Thư mục lưu lịch sử   : server/history/ ({runs_count} bản chạy đã lưu)")
    print(f" • Thư mục dữ liệu nến   : data/ (Gom tập trung, độc lập)")
    print(f" • Module Backtest & AI  : engine/backtest_ai.py (Chuyên biệt)")
    print(f" • RAM máy chủ            : Siêu nhẹ (~15MB)")
    print("="*75)
    print(" API cung cấp cho Web UI:")
    print("   - GET    /api/status      : Kiểm tra trạng thái server")
    print("   - GET    /api/history     : Xem danh sách toàn bộ các lần chạy")
    print("   - GET    /api/runs/<id>   : Xem chi tiết 1 lần chạy bất kỳ")
    print("   - POST   /api/run         : Gửi tham số để chạy Backtest & AI")
    print("   - POST   /api/runs/select : Chọn 1 bản chạy làm Active")
    print("   - DELETE /api/runs/<id>   : Xóa 1 bản chạy khỏi lịch sử")
    print("="*75)
    print(" Nhấn Ctrl + C để dừng Web Server.\n")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[!] Đang tắt Web Server...")
        httpd.server_close()


def run_with_reloader(host, port):
    """
    Giám sát các file .py trong server/ và engine/.
    Tự động restart server khi phát hiện có file được chỉnh sửa (Hot Reload).
    """
    import subprocess
    import time

    print("\n" + "="*75)
    print(" ⚡ CHẾ ĐỘ AUTO-RELOAD (HOT RELOAD) ĐANG HOẠT ĐỘNG")
    print("="*75)
    print(" • Theo dõi thay đổi trong thư mục: server/ và engine/")
    print(" • Khi bạn lưu file, Web Server sẽ tự khởi động lại tức thì.")
    print("="*75 + "\n")

    def get_file_mtimes():
        mtimes = {}
        watch_dirs = [
            SERVER_DIR,
            os.path.join(PROJECT_ROOT, "engine")
        ]
        for folder in watch_dirs:
            if not os.path.isdir(folder):
                continue
            for root, _, files in os.walk(folder):
                # Bỏ qua history JSON và cache
                if "history" in root or "__pycache__" in root:
                    continue
                for f in files:
                    if f.endswith('.py'):
                        fpath = os.path.join(root, f)
                        try:
                            mtimes[fpath] = os.stat(fpath).st_mtime
                        except OSError:
                            pass
        return mtimes

    cmd = [sys.executable, os.path.abspath(__file__), '--host', host, '--port', str(port), '--worker']
    process = subprocess.Popen(cmd)
    last_mtimes = get_file_mtimes()

    try:
        while True:
            time.sleep(1)
            current_mtimes = get_file_mtimes()
            changed_file = None

            for fpath, mtime in current_mtimes.items():
                if fpath not in last_mtimes or mtime > last_mtimes[fpath]:
                    changed_file = fpath
                    break

            if changed_file:
                rel_path = os.path.relpath(changed_file, PROJECT_ROOT)
                print(f"\n[⚡ HOT RELOAD] Phát hiện thay đổi trong: {rel_path}")
                print("[⚡ HOT RELOAD] Đang khởi động lại Web Server...")
                process.terminate()
                process.wait()
                process = subprocess.Popen(cmd)
                last_mtimes = current_mtimes
    except KeyboardInterrupt:
        print("\n[!] Đang dừng chế độ Auto-Reload...")
        process.terminate()
        process.wait()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Chạy Máy Chủ Web & Quản Lý Lịch Sử")
    parser.add_argument('--host', default='0.0.0.0', help="Địa chỉ host (mặc định: 0.0.0.0)")
    parser.add_argument('--port', type=int, default=8080, help="Cổng mạng (mặc định: 8080)")
    parser.add_argument('--reload', action='store_true', help="Kích hoạt chế độ Hot Reload tự động cập nhật khi sửa code")
    parser.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()

    if args.reload and not args.worker:
        run_with_reloader(host=args.host, port=args.port)
    else:
        run_server(host=args.host, port=args.port)
