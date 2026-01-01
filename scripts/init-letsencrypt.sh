#!/bin/bash
# =============================================================================
# POS Application - Let's Encrypt SSL Certificate Setup
# Run this script ONCE after initial deployment to obtain SSL certificates
# =============================================================================

set -e

# Configuration
DOMAIN="${1:-}"
EMAIL="${2:-}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" >&2
}

# Check arguments
if [ -z "$DOMAIN" ] || [ -z "$EMAIL" ]; then
    echo "Usage: $0 <domain> <email>"
    echo "Example: $0 pos.example.com admin@example.com"
    exit 1
fi

log "Setting up Let's Encrypt SSL for domain: ${DOMAIN}"

# Create required directories
log "Creating certificate directories..."
mkdir -p nginx/certbot/conf
mkdir -p nginx/certbot/www

# Step 1: Start services with initial nginx config (HTTP only)
log "Starting services with HTTP-only configuration..."
cp nginx/nginx-initial.conf nginx/nginx.conf

docker-compose -f docker-compose.prod.yml up -d nginx

# Wait for nginx to be ready
log "Waiting for nginx to start..."
sleep 10

# Step 2: Obtain certificates using certbot
log "Obtaining SSL certificates from Let's Encrypt..."

docker-compose -f docker-compose.prod.yml run --rm certbot certonly \
    --webroot \
    --webroot-path=/var/www/certbot \
    --email "$EMAIL" \
    --agree-tos \
    --no-eff-email \
    --force-renewal \
    -d "$DOMAIN"

# Check if certificate was obtained
if [ ! -f "nginx/certbot/conf/live/${DOMAIN}/fullchain.pem" ]; then
    error "Failed to obtain SSL certificate!"
    exit 1
fi

log "SSL certificate obtained successfully!"

# Step 3: Update nginx configuration for SSL
log "Updating nginx configuration for SSL..."

# Create the production nginx.conf with the domain
cat > nginx/nginx.conf << EOF
# Nginx Configuration for POS Application - SSL Enabled
user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 1024;
    use epoll;
    multi_accept on;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    log_format main '\$remote_addr - \$remote_user [\$time_local] "\$request" '
                    '\$status \$body_bytes_sent "\$http_referer" '
                    '"\$http_user_agent" "\$http_x_forwarded_for"';

    access_log /var/log/nginx/access.log main;

    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;

    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css text/xml application/json application/javascript 
               application/xml application/xml+rss text/javascript;

    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    limit_req_zone \$binary_remote_addr zone=api:10m rate=10r/s;
    limit_req_zone \$binary_remote_addr zone=login:10m rate=5r/m;

    upstream api_backend {
        server api:8000;
        keepalive 32;
    }

    upstream web_backend {
        server web:3000;
        keepalive 32;
    }

    # HTTP - Redirect to HTTPS
    server {
        listen 80;
        server_name ${DOMAIN};

        location /.well-known/acme-challenge/ {
            root /var/www/certbot;
        }

        location /health {
            access_log off;
            return 200 "healthy\n";
            add_header Content-Type text/plain;
        }

        location / {
            return 301 https://\$host\$request_uri;
        }
    }

    # HTTPS
    server {
        listen 443 ssl http2;
        server_name ${DOMAIN};

        ssl_certificate /etc/letsencrypt/live/${DOMAIN}/fullchain.pem;
        ssl_certificate_key /etc/letsencrypt/live/${DOMAIN}/privkey.pem;
        
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_prefer_server_ciphers off;
        ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
        ssl_session_timeout 1d;
        ssl_session_cache shared:SSL:50m;
        ssl_stapling on;
        ssl_stapling_verify on;

        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;

        client_max_body_size 10M;

        location /health {
            access_log off;
            return 200 "healthy\n";
            add_header Content-Type text/plain;
        }

        location /api/ {
            limit_req zone=api burst=20 nodelay;
            proxy_pass http://api_backend;
            proxy_http_version 1.1;
            proxy_set_header Host \$host;
            proxy_set_header X-Real-IP \$remote_addr;
            proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto \$scheme;
            proxy_set_header Connection "";
            proxy_connect_timeout 60s;
            proxy_send_timeout 120s;
            proxy_read_timeout 120s;
        }

        location /api/auth/login/ {
            limit_req zone=login burst=5 nodelay;
            proxy_pass http://api_backend;
            proxy_http_version 1.1;
            proxy_set_header Host \$host;
            proxy_set_header X-Real-IP \$remote_addr;
            proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto \$scheme;
        }

        location /admin/ {
            proxy_pass http://api_backend;
            proxy_set_header Host \$host;
            proxy_set_header X-Real-IP \$remote_addr;
            proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto \$scheme;
        }

        location /static/ {
            alias /var/www/static/;
            expires 30d;
            add_header Cache-Control "public, immutable";
        }

        location /media/ {
            alias /var/www/media/;
            expires 7d;
            add_header Cache-Control "public";
        }

        location /_next/static/ {
            proxy_pass http://web_backend;
            proxy_http_version 1.1;
            proxy_set_header Connection "";
            expires 365d;
            add_header Cache-Control "public, immutable";
        }

        location / {
            proxy_pass http://web_backend;
            proxy_http_version 1.1;
            proxy_set_header Host \$host;
            proxy_set_header X-Real-IP \$remote_addr;
            proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto \$scheme;
            proxy_set_header Upgrade \$http_upgrade;
            proxy_set_header Connection "upgrade";
        }
    }
}
EOF

# Step 4: Restart nginx with SSL configuration
log "Restarting nginx with SSL configuration..."
docker-compose -f docker-compose.prod.yml restart nginx

# Step 5: Set up auto-renewal cron job
log "Setting up SSL certificate auto-renewal..."

# Add cron job for certificate renewal (runs twice daily)
(crontab -l 2>/dev/null | grep -v "certbot renew"; echo "0 0,12 * * * cd $(pwd) && docker-compose -f docker-compose.prod.yml run --rm certbot renew --quiet && docker-compose -f docker-compose.prod.yml restart nginx") | crontab -

log "=============================================="
log "SSL setup completed successfully!"
log "=============================================="
log "Domain: https://${DOMAIN}"
log "Certificate location: nginx/certbot/conf/live/${DOMAIN}/"
log "Auto-renewal: Enabled (runs twice daily)"
log ""
log "Next steps:"
log "1. Update .env.production with:"
log "   ALLOWED_HOSTS=${DOMAIN}"
log "   CORS_ALLOWED_ORIGINS=https://${DOMAIN}"
log "   CSRF_TRUSTED_ORIGINS=https://${DOMAIN}"
log "   NEXT_PUBLIC_API_URL=https://${DOMAIN}/api"
log ""
log "2. Restart all services:"
log "   docker-compose -f docker-compose.prod.yml down"
log "   docker-compose -f docker-compose.prod.yml up -d"
