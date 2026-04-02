FROM python:3.13-slim

# Install OpenVPN and necessary tools
RUN apt-get update && apt-get install -y \
    openvpn \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy project files
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create startup script that connects to VPN first, then starts the API
RUN echo '#!/bin/bash\n\
# Create auth file from environment variables\n\
mkdir -p /etc/openvpn\n\
echo "$VPN_USER" > /etc/openvpn/auth.txt\n\
echo "$VPN_PASS" >> /etc/openvpn/auth.txt\n\
chmod 600 /etc/openvpn/auth.txt\n\
\n\
# Start OpenVPN in background\n\
openvpn --config /etc/openvpn/iiith.ovpn --auth-user-pass /etc/openvpn/auth.txt --daemon\n\
\n\
# Wait for VPN connection\n\
echo "Waiting for VPN connection..."\n\
sleep 10\n\
\n\
# Start Flask API\n\
exec python3 api_wrapper.py' > /start.sh && chmod +x /start.sh

EXPOSE 5000

CMD ["/start.sh"]
