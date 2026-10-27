# Sử dụng image Python có sẵn mitmproxy
FROM mitmproxy/mitmproxy:latest

# Đặt thư mục làm việc
WORKDIR /app

# Copy toàn bộ source code vào container
COPY . /app

# Cài đặt các thư viện từ requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Lệnh chạy tool: Chạy file main.py để khởi động cả Bot và Proxy
CMD ["python", "main.py"]
