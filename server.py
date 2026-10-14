#!/usr/bin/env python3
"""
Lightweight Production Web Server for XAU/USD Quant AI Dashboard
- Serves dashboard.html & web_data.json
- Automatically generates web_data.json if not present
- Ready for local testing and 24/7 background VPS deployment
"""

import os
import sys
import argparse
from http.server import HTTPServer, SimpleHTTPRequestHandler

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))


class QuantDashboardHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=CURRENT_DIR, **kwargs)

    def do_GET(self):
        # Mặc định mở dashboard.html khi truy cập trang chủ /
        if self.path in ('/', '/index.html'):
            self.path = '/dashboard.html'
        return super().do_GET()

    def end_headers(self):
        # Bổ sung Cache-Control để cập nhật dữ liệu mới nhất
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.send_header('Access-Control-Allow-Origin', '*')
        super().end_headers()


class ReusableHTTPServer(HTTPServer):
    allow_reuse_address = True


def ensure_data_ready():
    data_file = os.path.join(CURRENT_DIR, "web_data.json")
    if not os.path.exists(data_file):
        print("[!] Chưa tìm thấy web_data.json. Đang tự động chạy ai_system.py để huấn luyện và tính toán...")
        from ai_system import run_pipeline
        run_pipeline(CURRENT_DIR)
    else:
        print("[✓] Đã tìm thấy web_data.json sẵn sàng.")


def run_server(host='0.0.0.0', port=8080):
    ensure_data_ready()
    server_address = (host, port)
    try:
        httpd = ReusableHTTPServer(server_address, QuantDashboardHandler)
    except OSError as e:
        if e.errno == 98 or "already in use" in str(e).lower():
            alt_port = port + 1
            print(f"[!] Cổng {port} đang có tiến trình khác sử dụng. Tự động chuyển sang cổng {alt_port}...")
            server_address = (host, alt_port)
            httpd = ReusableHTTPServer(server_address, QuantDashboardHandler)
            port = alt_port
        else:
            raise e

    display_host = 'localhost' if host in ('0.0.0.0', '127.0.0.1') else host
    print("\n" + "="*65)
    print(" 🚀 XAU/USD QUANT AI WEB SERVER ĐANG CHẠY")
    print("="*65)
    print(f" • Mở xem trên trình duyệt   : http://{display_host}:{port}")
    print(f" • Truy cập từ ngoài qua VPS : http://<IP_VPS_CỦA_BẠN>:{port}")
    print(f" • Thư mục phục vụ           : {CURRENT_DIR}")
    print("="*65)
    print(" Nhấn Ctrl + C để dừng server.\n")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[!] Đã dừng server.")
        httpd.server_close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Chạy Web View Quant Dashboard")
    parser.add_argument('--host', default='0.0.0.0', help="Địa chỉ host (mặc định: 0.0.0.0)")
    parser.add_argument('--port', type=int, default=8080, help="Cổng mạng (mặc định: 8080)")
    args = parser.parse_args()
    run_server(host=args.host, port=args.port)
