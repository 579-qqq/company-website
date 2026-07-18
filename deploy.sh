#!/bin/bash
set -e
echo ">>> 安装依赖..."
apt update -qq && apt install -y -qq python3-pip nginx tesseract-ocr tesseract-ocr-chi-sim 2>/dev/null
echo ">>> 安装 Python 包..."
pip3 install -r /opt/website/requirements.txt -q
echo ">>> 初始化数据库..."
cd /opt/website
python3 database/init_db.py
python3 database/init_courses.py
python3 database/seed_courses.py
echo ">>> 配置 Nginx..."
cat > /etc/nginx/sites-available/website << 'NGINX'
server {
    listen 80;
    server_name _;
    location /static {
        alias /opt/website/static;
    }
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
NGINX
rm -f /etc/nginx/sites-enabled/default
ln -sf /etc/nginx/sites-available/website /etc/nginx/sites-enabled/
nginx -t && systemctl restart nginx
echo ">>> 启动服务..."
cat > /etc/systemd/system/website.service << 'SVC'
[Unit]
Description=Yaobo Website
After=network.target
[Service]
Type=simple
User=root
WorkingDirectory=/opt/website
ExecStart=/usr/bin/python3 /opt/website/app.py
Restart=always
[Install]
WantedBy=multi-user.target
SVC
systemctl daemon-reload
systemctl enable website
systemctl restart website
echo ">>> 完成！公网地址: http://$(curl -s ifconfig.me)"
