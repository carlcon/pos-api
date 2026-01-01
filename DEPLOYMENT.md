# POS System - AWS Deployment Guide

This guide walks you through deploying the POS system (Django API + Next.js Frontend) to AWS using EC2 Free Tier.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [AWS Account Setup](#aws-account-setup)
3. [EC2 Instance Setup](#ec2-instance-setup)
4. [Security Group Configuration](#security-group-configuration)
5. [IAM Role & Credentials](#iam-role--credentials)
6. [ECR Repository Setup](#ecr-repository-setup)
7. [GitHub Secrets Configuration](#github-secrets-configuration)
8. [First Deployment](#first-deployment)
9. [SSL Certificate Setup](#ssl-certificate-setup)
10. [DNS Configuration](#dns-configuration)
11. [Monitoring Setup](#monitoring-setup)
12. [Backup Configuration](#backup-configuration)
13. [Maintenance & Operations](#maintenance--operations)
14. [Troubleshooting](#troubleshooting)
15. [Rollback Procedures](#rollback-procedures)

---

## Prerequisites

- AWS Account (Free Tier eligible)
- GitHub repository with pos-api and pos-app code
- Domain name (optional, can use EC2 public IP initially)
- SSH client (Terminal on macOS/Linux, PuTTY on Windows)

---

## AWS Account Setup

1. **Create AWS Account** (if you don't have one):
   - Go to https://aws.amazon.com/free
   - Sign up for a free account
   - You'll have access to Free Tier services for 12 months

2. **Enable MFA** (recommended):
   - Go to IAM → Users → Your user
   - Security credentials → Assign MFA device

---

## EC2 Instance Setup

### Step 1: Launch EC2 Instance

1. Go to **EC2 Dashboard** → **Launch Instance**

2. **Name**: `pos-production`

3. **AMI**: Amazon Linux 2023 AMI (Free tier eligible)

4. **Instance Type**: `t3.micro` (Free tier: 750 hours/month for 12 months)
   > ⚠️ Note: t2.micro is also free tier but t3.micro has better performance

5. **Key Pair**:
   - Click "Create new key pair"
   - Name: `pos-production-key`
   - Type: RSA
   - Format: .pem (macOS/Linux) or .ppk (Windows/PuTTY)
   - Download and save securely!

6. **Network Settings** → Edit:
   - VPC: Default
   - Subnet: No preference (or pick one in your preferred AZ)
   - Auto-assign public IP: **Enable**
   - Create security group (see next section)

7. **Storage**: 
   - 20 GB gp3 (Free tier: 30GB total)

8. Click **Launch Instance**

### Step 2: Allocate Elastic IP (Recommended)

This gives you a static IP that doesn't change when instance restarts:

1. Go to **EC2** → **Elastic IPs**
2. Click **Allocate Elastic IP address**
3. Click **Allocate**
4. Select the IP → **Actions** → **Associate Elastic IP address**
5. Select your `pos-production` instance
6. Click **Associate**

> Note: Elastic IP is free as long as it's associated with a running instance

---

## Security Group Configuration

Create or edit the security group for your EC2 instance:

| Type        | Port Range | Source            | Description           |
|-------------|------------|-------------------|-----------------------|
| SSH         | 22         | Your IP           | SSH access            |
| HTTP        | 80         | 0.0.0.0/0         | Web traffic           |
| HTTPS       | 443        | 0.0.0.0/0         | Secure web traffic    |

### AWS CLI Command (alternative):
```bash
aws ec2 create-security-group \
  --group-name pos-production-sg \
  --description "POS Production Security Group"

aws ec2 authorize-security-group-ingress \
  --group-name pos-production-sg \
  --protocol tcp --port 22 --cidr YOUR.IP.ADDRESS/32

aws ec2 authorize-security-group-ingress \
  --group-name pos-production-sg \
  --protocol tcp --port 80 --cidr 0.0.0.0/0

aws ec2 authorize-security-group-ingress \
  --group-name pos-production-sg \
  --protocol tcp --port 443 --cidr 0.0.0.0/0
```

---

## IAM Role & Credentials

### Create IAM User for GitHub Actions

1. Go to **IAM** → **Users** → **Create user**

2. **User name**: `github-actions-pos`

3. **Permissions**:
   - Attach policies directly
   - Search and add:
     - `AmazonEC2ContainerRegistryPowerUser`
     - `CloudWatchAgentServerPolicy`

4. **Create custom policy** for S3 backups:
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": [
           "s3:PutObject",
           "s3:GetObject",
           "s3:DeleteObject",
           "s3:ListBucket"
         ],
         "Resource": [
           "arn:aws:s3:::your-backup-bucket-name",
           "arn:aws:s3:::your-backup-bucket-name/*"
         ]
       }
     ]
   }
   ```

5. **Create Access Key**:
   - Go to user → Security credentials
   - Create access key → CLI use case
   - Download CSV (save securely!)

### Create IAM Role for EC2

1. Go to **IAM** → **Roles** → **Create role**

2. **Trusted entity**: AWS service → EC2

3. **Permissions**:
   - `AmazonEC2ContainerRegistryReadOnly`
   - `CloudWatchAgentServerPolicy`
   - Your custom S3 backup policy

4. **Name**: `pos-ec2-role`

5. **Attach to EC2 instance**:
   - EC2 → Instances → Select instance
   - Actions → Security → Modify IAM role
   - Select `pos-ec2-role`

---

## ECR Repository Setup

Create ECR repositories for your Docker images:

```bash
# Set your region
export AWS_REGION=us-east-1

# Create repositories
aws ecr create-repository --repository-name pos-api --region $AWS_REGION
aws ecr create-repository --repository-name pos-app --region $AWS_REGION

# Get your ECR registry URL (note this for later)
aws ecr describe-repositories --query 'repositories[*].repositoryUri' --output table
```

The ECR URL format is: `123456789012.dkr.ecr.us-east-1.amazonaws.com`

---

## GitHub Secrets Configuration

Go to your GitHub repository → **Settings** → **Secrets and variables** → **Actions**

Add these secrets:

| Secret Name | Value | Description |
|-------------|-------|-------------|
| `AWS_ACCESS_KEY_ID` | From IAM user | AWS access key |
| `AWS_SECRET_ACCESS_KEY` | From IAM user | AWS secret key |
| `AWS_REGION` | `us-east-1` | Your AWS region |
| `EC2_HOST` | EC2 IP or domain | Your server address |
| `EC2_SSH_KEY` | Base64 encoded key | See below |
| `NEXT_PUBLIC_API_URL` | `https://api.yourdomain.com` | API URL |

### Encode SSH Key for GitHub Secret:

```bash
# On macOS/Linux
cat pos-production-key.pem | base64 | tr -d '\n'

# Copy the output and paste as EC2_SSH_KEY secret
```

---

## First Deployment

### Step 1: Connect to EC2

```bash
# Set permissions on key file
chmod 400 pos-production-key.pem

# Connect via SSH
ssh -i pos-production-key.pem ec2-user@YOUR_EC2_IP
```

### Step 2: Run Server Setup Script

```bash
# Create app directory
sudo mkdir -p /opt/pos-app
sudo chown ec2-user:ec2-user /opt/pos-app
cd /opt/pos-app

# Download and run setup script (or copy from your repo)
# Option 1: Clone your repo
git clone https://github.com/yourusername/pos-api.git .

# Option 2: Or create the setup script manually
nano scripts/setup-server.sh
# Paste the content from scripts/setup-server.sh
chmod +x scripts/setup-server.sh

# Run setup
sudo ./scripts/setup-server.sh
```

### Step 3: Configure Environment

```bash
cd /opt/pos-app

# Copy environment template
cp .env.production.example .env.production

# Edit with your values
nano .env.production
```

**Important values to set:**
- `SECRET_KEY`: Generate with `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`
- `DB_PASSWORD`: Strong random password
- `ALLOWED_HOSTS`: Your domain or EC2 IP
- `DJANGO_SUPERUSER_PASSWORD`: Admin password

### Step 4: Initial Docker Setup

```bash
# Login to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin YOUR_ECR_REGISTRY

# Pull images (after first GitHub Actions build)
docker-compose -f docker-compose.prod.yml pull

# Start services
docker-compose -f docker-compose.prod.yml up -d

# Run initial data setup
chmod +x scripts/init-data.sh
./scripts/init-data.sh
```

### Step 5: Verify Deployment

```bash
# Check all containers are running
docker-compose -f docker-compose.prod.yml ps

# Check logs
docker-compose -f docker-compose.prod.yml logs -f

# Test API
curl http://localhost/api/health/
```

---

## SSL Certificate Setup

### Option A: With Domain (Recommended)

```bash
cd /opt/pos-app

# Edit init-letsencrypt.sh with your domain and email
nano scripts/init-letsencrypt.sh

# Run Let's Encrypt setup
chmod +x scripts/init-letsencrypt.sh
sudo ./scripts/init-letsencrypt.sh
```

### Option B: Self-Signed Certificate (Testing Only)

```bash
# Generate self-signed certificate
mkdir -p nginx/ssl
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout nginx/ssl/privkey.pem \
  -out nginx/ssl/fullchain.pem \
  -subj "/CN=localhost"

# Update nginx.conf to use these certificates
```

---

## DNS Configuration

### If Using Route 53 (AWS DNS):

1. Go to **Route 53** → **Hosted zones**
2. Create or select your domain's hosted zone
3. Create records:

| Record Type | Name | Value |
|-------------|------|-------|
| A | yourdomain.com | Your Elastic IP |
| A | api.yourdomain.com | Your Elastic IP |
| A | www.yourdomain.com | Your Elastic IP |

### If Using External DNS Provider (GoDaddy, Namecheap, etc.):

1. Log into your DNS provider's dashboard
2. Find DNS settings for your domain
3. Add A records:

```
Type: A
Host: @
Points to: YOUR_ELASTIC_IP
TTL: 3600

Type: A  
Host: api
Points to: YOUR_ELASTIC_IP
TTL: 3600

Type: A
Host: www
Points to: YOUR_ELASTIC_IP
TTL: 3600
```

### Verify DNS Propagation:

```bash
# Check DNS resolution
dig yourdomain.com +short
dig api.yourdomain.com +short

# Or use online tool: https://dnschecker.org
```

> DNS propagation can take 15 minutes to 48 hours

---

## Monitoring Setup

CloudWatch basic monitoring is included in Free Tier:

### View Metrics:

1. Go to **CloudWatch** → **Metrics** → **EC2**
2. Select your instance
3. View: CPU Utilization, Network In/Out, Disk Read/Write

### Create Alarm (Optional):

1. **CloudWatch** → **Alarms** → **Create alarm**
2. Select metric: EC2 → Per-Instance → CPUUtilization
3. Condition: Greater than 80% for 5 minutes
4. Notification: Create SNS topic with your email

### View Docker Logs:

```bash
# All services
docker-compose -f docker-compose.prod.yml logs -f

# Specific service
docker-compose -f docker-compose.prod.yml logs -f api

# Last 100 lines
docker-compose -f docker-compose.prod.yml logs --tail=100 api
```

---

## Backup Configuration

### Setup S3 Bucket:

```bash
# Create bucket
aws s3 mb s3://your-pos-backups-bucket --region us-east-1

# Enable versioning (optional but recommended)
aws s3api put-bucket-versioning \
  --bucket your-pos-backups-bucket \
  --versioning-configuration Status=Enabled
```

### Setup Automated Backups:

```bash
# Edit backup script with your bucket name
nano scripts/backup.sh

# Make executable
chmod +x scripts/backup.sh

# Add to crontab (runs daily at 2 AM)
(crontab -l 2>/dev/null; echo "0 2 * * * /opt/pos-app/scripts/backup.sh >> /var/log/pos-backup.log 2>&1") | crontab -
```

### Manual Backup:

```bash
./scripts/backup.sh
```

### Restore from Backup:

```bash
# List available backups
aws s3 ls s3://your-pos-backups-bucket/

# Download backup
aws s3 cp s3://your-pos-backups-bucket/pos_backup_2024-01-15.sql.gz .

# Decompress
gunzip pos_backup_2024-01-15.sql.gz

# Restore (stop API first)
docker-compose -f docker-compose.prod.yml stop api celery celery-beat
cat pos_backup_2024-01-15.sql | docker-compose -f docker-compose.prod.yml exec -T db psql -U pos_user pos_db
docker-compose -f docker-compose.prod.yml start api celery celery-beat
```

---

## Maintenance & Operations

### Update Application:

Push to main branch triggers automatic deployment via GitHub Actions.

### Manual Update:

```bash
cd /opt/pos-app

# Pull latest images
docker-compose -f docker-compose.prod.yml pull

# Recreate containers
docker-compose -f docker-compose.prod.yml up -d

# Run migrations
docker-compose -f docker-compose.prod.yml exec api python manage.py migrate
```

### View Running Containers:

```bash
docker-compose -f docker-compose.prod.yml ps
```

### Restart Services:

```bash
# Restart all
docker-compose -f docker-compose.prod.yml restart

# Restart specific service
docker-compose -f docker-compose.prod.yml restart api
```

### Check Disk Space:

```bash
df -h
docker system df
```

### Clean Up Docker:

```bash
# Remove unused images
docker image prune -f

# Remove all unused resources
docker system prune -f
```

---

## Troubleshooting

### Container Won't Start:

```bash
# Check logs
docker-compose -f docker-compose.prod.yml logs api

# Check container status
docker-compose -f docker-compose.prod.yml ps

# Rebuild container
docker-compose -f docker-compose.prod.yml up -d --build api
```

### Database Connection Issues:

```bash
# Check if database is running
docker-compose -f docker-compose.prod.yml ps db

# Test connection
docker-compose -f docker-compose.prod.yml exec db psql -U pos_user -d pos_db -c "SELECT 1;"
```

### Out of Memory:

```bash
# Check memory usage
free -h
docker stats

# Add more swap (if not already done)
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### SSL Certificate Issues:

```bash
# Check certificate status
sudo certbot certificates

# Renew certificate manually
sudo certbot renew --dry-run
```

### 502 Bad Gateway:

```bash
# Check nginx logs
docker-compose -f docker-compose.prod.yml logs nginx

# Check if backend is running
docker-compose -f docker-compose.prod.yml ps api

# Restart nginx
docker-compose -f docker-compose.prod.yml restart nginx
```

### Permission Denied:

```bash
# Fix ownership
sudo chown -R ec2-user:ec2-user /opt/pos-app

# Fix Docker socket (if needed)
sudo usermod -aG docker ec2-user
# Log out and back in
```

---

## Rollback Procedures

### Rollback to Previous Image:

```bash
cd /opt/pos-app

# List available images
docker images

# Edit docker-compose.prod.yml to use previous tag
# Or set environment variable
export IMAGE_TAG=previous-commit-sha

# Pull and restart
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml up -d
```

### Rollback Database:

```bash
# Stop services
docker-compose -f docker-compose.prod.yml stop api celery celery-beat

# Restore from backup (see Backup section)
aws s3 cp s3://your-pos-backups-bucket/pos_backup_YYYY-MM-DD.sql.gz .
gunzip pos_backup_YYYY-MM-DD.sql.gz
cat pos_backup_YYYY-MM-DD.sql | docker-compose -f docker-compose.prod.yml exec -T db psql -U pos_user pos_db

# Start services
docker-compose -f docker-compose.prod.yml start api celery celery-beat
```

### Complete Rollback (Code + Database):

1. Revert git commit on main branch
2. GitHub Actions will deploy previous version
3. Restore database from backup matching that version

---

## Cost Estimation (Free Tier)

| Service | Free Tier | After Free Tier |
|---------|-----------|-----------------|
| EC2 t3.micro | 750 hrs/month (12 months) | ~$8/month |
| EBS 20GB | 30GB free (12 months) | ~$2/month |
| S3 (backups) | 5GB free | ~$0.50/month |
| ECR | 500MB free | ~$0.10/GB |
| Data Transfer | 100GB out free | $0.09/GB |
| **Total** | **$0/month** | **~$12/month** |

---

## Security Checklist

- [ ] MFA enabled on AWS root account
- [ ] SSH key secured (chmod 400)
- [ ] Strong database password
- [ ] Strong Django SECRET_KEY
- [ ] SSL certificate installed
- [ ] Security group restricts SSH to your IP
- [ ] Regular backups configured
- [ ] IAM user has minimal required permissions
- [ ] .env files not committed to git

---

## Support

For issues:
1. Check the [Troubleshooting](#troubleshooting) section
2. Review Docker logs: `docker-compose logs -f`
3. Check AWS CloudWatch metrics
4. Open an issue in the GitHub repository
