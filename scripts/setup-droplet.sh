#!/bin/bash
# =============================================================================
# POS Application - DigitalOcean Droplet Initial Setup Script
# Run this script on a fresh Ubuntu 22.04/24.04 Droplet
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[SETUP]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

warn() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Verify Ubuntu
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$NAME
else
    error "Cannot detect OS"
    exit 1
fi

if [[ "$OS" != *"Ubuntu"* ]]; then
    error "This script is designed for Ubuntu. Detected: $OS"
    exit 1
fi

log "Detected OS: $OS"

# =============================================================================
# Step 1: System Updates
# =============================================================================
log "Updating system packages..."

sudo apt-get update && sudo apt-get upgrade -y

# =============================================================================
# Step 2: Install Docker
# =============================================================================
log "Installing Docker..."

sudo apt-get install -y apt-transport-https ca-certificates curl software-properties-common
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER

# =============================================================================
# Step 3: Install Docker Compose
# =============================================================================
log "Installing Docker Compose..."

DOCKER_COMPOSE_VERSION="v2.24.0"
sudo curl -L "https://github.com/docker/compose/releases/download/${DOCKER_COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify installation
docker-compose --version

# =============================================================================
# Step 4: Create Swap File (Important for Droplets with limited RAM)
# =============================================================================
log "Creating 1GB swap file..."

if [ ! -f /swapfile ]; then
    sudo fallocate -l 1G /swapfile
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile
    echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
    log "Swap file created and enabled"
else
    warn "Swap file already exists"
fi

# Verify swap
free -h

# =============================================================================
# Step 5: Install Additional Tools
# =============================================================================
log "Installing additional tools..."

sudo apt-get install -y git htop postgresql-client

# =============================================================================
# Step 6: Configure Firewall (UFW)
# =============================================================================
log "Configuring firewall..."

sudo ufw allow 22/tcp   # SSH
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS
sudo ufw --force enable
log "UFW firewall configured"

# =============================================================================
# Step 7: Create Application Directory
# =============================================================================
log "Creating application directory..."

APP_DIR="/opt/pos-app"
sudo mkdir -p $APP_DIR
sudo chown $USER:$USER $APP_DIR

log "Application directory created: $APP_DIR"

# =============================================================================
# Step 8: Set up Log Rotation for Docker
# =============================================================================
log "Configuring Docker log rotation..."

sudo mkdir -p /etc/docker
cat << EOF | sudo tee /etc/docker/daemon.json
{
    "log-driver": "json-file",
    "log-opts": {
        "max-size": "10m",
        "max-file": "3"
    }
}
EOF

sudo systemctl restart docker

# =============================================================================
# Step 9: Set up Daily Backup Cron Job
# =============================================================================
log "Setting up daily backup cron job..."

# Create backup script location
sudo mkdir -p /opt/scripts

# Add cron job for daily backup at 3 AM
(crontab -l 2>/dev/null | grep -v "backup.sh"; echo "0 3 * * * cd /opt/pos-app && ./scripts/backup.sh >> /var/log/pos-backup.log 2>&1") | crontab -

log "Backup cron job configured (runs daily at 3 AM)"

# =============================================================================
# Step 10: Install doctl (DigitalOcean CLI) - Optional
# =============================================================================
log "Installing doctl (DigitalOcean CLI)..."

DOCTL_VERSION="1.104.0"
curl -sL "https://github.com/digitalocean/doctl/releases/download/v${DOCTL_VERSION}/doctl-${DOCTL_VERSION}-linux-amd64.tar.gz" | sudo tar -xzv -C /usr/local/bin
warn "doctl installed. Run 'doctl auth init' to authenticate (optional, for Spaces backups)."

# =============================================================================
# Completion
# =============================================================================
log "=============================================="
log "Droplet setup completed successfully!"
log "=============================================="
log ""
log "Next steps:"
log "1. Log out and log back in for Docker group membership to take effect"
log "2. Clone your repository to /opt/pos-app"
log "3. Create .env.production file with your configuration"
log "4. Run: docker-compose -f docker-compose.prod.yml up -d"
log "5. Run: ./scripts/init-letsencrypt.sh <domain> <email>"
log ""
log "Useful commands:"
log "  View logs:      docker-compose -f docker-compose.prod.yml logs -f"
log "  Restart:        docker-compose -f docker-compose.prod.yml restart"
log "  Stop:           docker-compose -f docker-compose.prod.yml down"
log "  Check status:   docker-compose -f docker-compose.prod.yml ps"
log ""
warn "Remember to configure DigitalOcean Cloud Firewall to allow ports 22, 80, 443"
