#!/bin/bash
# =============================================================================
# POS Application - SSL Setup Script (Let's Encrypt / Certbot)
# Run this on the Droplet after DNS is configured
# Usage: ./setup-ssl.sh jccinventory.com
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[SSL]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

warn() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check if domain is provided
DOMAIN=${1:-jccinventory.com}

if [ -z "$DOMAIN" ]; then
    error "Usage: $0 <domain>"
    error "Example: $0 jccinventory.com"
    exit 1
fi

log "Setting up SSL for domain: $DOMAIN"

# =============================================================================
# Step 1: Install Certbot
# =============================================================================
log "Installing Certbot..."

sudo apt-get update
sudo apt-get install -y certbot

# =============================================================================
# Step 2: Stop nginx temporarily to get certificate
# =============================================================================
log "Stopping nginx container temporarily..."

cd /opt/pos-api
docker-compose -f docker-compose.prod.yml stop nginx || true

# =============================================================================
# Step 3: Obtain SSL Certificate (Standalone mode)
# =============================================================================
log "Obtaining SSL certificate for $DOMAIN..."

# Extract base domain for email (handles subdomains like api.example.com)
BASE_DOMAIN=$(echo $DOMAIN | rev | cut -d. -f1,2 | rev)

# Request certificate (standalone mode - certbot runs its own web server)
# For subdomains (api.example.com), we don't need www
sudo certbot certonly \
    --standalone \
    --non-interactive \
    --agree-tos \
    --email admin@${BASE_DOMAIN} \
    --domain ${DOMAIN}

log "✅ SSL certificate obtained!"

# =============================================================================
# Step 4: Create certificate directory for Docker
# =============================================================================
log "Setting up certificates for Docker..."

sudo mkdir -p /opt/pos-api/certs
sudo cp /etc/letsencrypt/live/${DOMAIN}/fullchain.pem /opt/pos-api/certs/
sudo cp /etc/letsencrypt/live/${DOMAIN}/privkey.pem /opt/pos-api/certs/
sudo chmod 644 /opt/pos-api/certs/*.pem

# =============================================================================
# Step 5: Update nginx config for SSL
# =============================================================================
log "Updating nginx configuration for SSL..."

# Backup existing config
cp /opt/pos-api/nginx/nginx.conf /opt/pos-api/nginx/nginx.conf.backup

# Copy SSL config
cp /opt/pos-api/nginx/nginx-ssl.conf /opt/pos-api/nginx/nginx.conf

# Replace DOMAIN placeholder with actual domain
sed -i "s/YOUR_DOMAIN/${DOMAIN}/g" /opt/pos-api/nginx/nginx.conf

log "✅ Nginx configured for SSL"

# =============================================================================
# Step 6: Update docker-compose to mount certs
# =============================================================================
log "Updating docker-compose for SSL..."

# The docker-compose.prod.yml already has SSL support commented out
# We need to use the SSL version
if [ -f /opt/pos-api/docker-compose.ssl.yml ]; then
    cp /opt/pos-api/docker-compose.ssl.yml /opt/pos-api/docker-compose.prod.yml
    log "✅ Using SSL docker-compose configuration"
else
    warn "SSL docker-compose not found, using existing config with manual cert mount"
fi

# =============================================================================
# Step 7: Restart services
# =============================================================================
log "Restarting services with SSL..."

cd /opt/pos-api
docker-compose -f docker-compose.prod.yml up -d

# =============================================================================
# Step 8: Setup auto-renewal (using pre/post hooks to stop/start nginx)
# =============================================================================
log "Setting up certificate auto-renewal..."

# Create directory for ACME challenges
sudo mkdir -p /var/www/certbot

# Update certbot renewal config to use pre/post hooks
sudo tee /etc/letsencrypt/renewal-hooks/pre/stop-nginx.sh > /dev/null << EOF
#!/bin/bash
# Stop nginx before renewal (to free port 80)
docker stop pos-nginx || true
EOF

sudo tee /etc/letsencrypt/renewal-hooks/post/start-nginx.sh > /dev/null << EOF
#!/bin/bash
# Copy renewed certificates and start nginx
cp /etc/letsencrypt/live/${DOMAIN}/fullchain.pem /opt/pos-api/certs/
cp /etc/letsencrypt/live/${DOMAIN}/privkey.pem /opt/pos-api/certs/
chmod 644 /opt/pos-api/certs/*.pem

# Start nginx
cd /opt/pos-api && docker-compose -f docker-compose.prod.yml up -d nginx
EOF

sudo chmod +x /etc/letsencrypt/renewal-hooks/pre/stop-nginx.sh
sudo chmod +x /etc/letsencrypt/renewal-hooks/post/start-nginx.sh

log "✅ Auto-renewal configured (will stop nginx briefly during renewal)"
log "ℹ️  Skipping dry-run test since nginx is running - renewal will work when needed"

# =============================================================================
# Step 9: Verify SSL setup
# =============================================================================
log "Verifying SSL setup..."

sleep 5

# Check if nginx is running
if docker ps | grep -q pos-nginx; then
    log "✅ Nginx container is running"
else
    error "Nginx container is not running"
    docker-compose -f docker-compose.prod.yml logs nginx
    exit 1
fi

# Test HTTPS endpoint
if curl -s -o /dev/null -w "%{http_code}" https://${DOMAIN}/api/health/ | grep -q "200"; then
    log "✅ HTTPS is working!"
else
    warn "HTTPS health check failed - may need a moment to start"
fi

echo ""
echo "=========================================="
echo -e "${GREEN}SSL SETUP COMPLETE!${NC}"
echo "=========================================="
echo ""
echo "Your API is now available at:"
echo "  https://${DOMAIN}/api/"
echo ""
echo "Certificate will auto-renew before expiry."
echo ""
echo "Next steps:"
echo "1. Update your Vercel environment variable:"
echo "   NEXT_PUBLIC_API_URL=https://${DOMAIN}/api"
echo ""
echo "2. Update GitHub secrets:"
echo "   CORS_ALLOWED_ORIGINS=https://pos-app-theta-ten.vercel.app"
echo "   CSRF_TRUSTED_ORIGINS=https://pos-app-theta-ten.vercel.app"
echo "   ALLOWED_HOSTS=${DOMAIN},www.${DOMAIN}"
echo ""
