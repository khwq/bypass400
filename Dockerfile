# Sử dụng image Python có sẵn mitmproxy
FROM mitmproxy/mitmproxy:latest

# Đặt thư mục làm việc
WORKDIR /app

# Copy toàn bộ source code vào container
COPY . /app

# Cài đặt các thư viện từ requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Lệnh chạy tool khi container khởi động
# Tool của bạn dùng mitmdump, trỏ tới file region_bypass.py và lắng nghe trên cổng 8080
CMD ["mitmdump", "-s", "region_bypass.py", "--listen-host", "0.0.0.0", "-p", "8080"]