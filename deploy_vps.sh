#!/bin/bash
# ==============================================================================
# Script tự động triển khai Hệ thống AI Quant Dashboard trên VPS (Ubuntu/Debian)
# ==============================================================================

set -e

echo ">>> [1/4] Cập nhật hệ thống và kiểm tra Python 3..."
sudo apt-get update -y
sudo apt-get install -y python3 python3-pip git ufw

echo ">>> [2/4] Cài đặt các thư viện bổ trợ (tùy chọn để tăng tốc AI)..."
pip3 install scikit-learn numpy pandas --break-system-packages 2>/dev/null || pip3 install scikit-learn numpy pandas || true

echo ">>> [3/4] Mở cổng 8080 trên tường lửa (UFW)..."
sudo ufw allow 8080/tcp 2>/dev/null || true

echo ">>> [4/4] Khởi tạo systemd service để chạy ngầm 24/7..."
CURRENT_DIR=$(pwd)
SERVICE_FILE="/etc/systemd/system/quant-dashboard.service"

sudo bash -c "cat > $SERVICE_FILE" <<EOF
[Unit]
Description=XAUUSD Quant AI Dashboard Web Server
After=network.target

[Service]
Type=simple
User=$(whoami)
WorkingDirectory=$CURRENT_DIR
ExecStart=/usr/bin/python3 $CURRENT_DIR/server.py --host 0.0.0.0 --port 8080
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable quant-dashboard
sudo systemctl restart quant-dashboard

echo "===================================================================="
echo " [✓] TRIỂN KHAI THÀNH CÔNG!"
echo " • Web Dashboard đang chạy ngầm tại: http://$(curl -s ifconfig.me):8080"
echo " • Kiểm tra trạng thái: sudo systemctl status quant-dashboard"
echo " • Xem log thời gian thực: journalctl -u quant-dashboard -f"
echo "===================================================================="
