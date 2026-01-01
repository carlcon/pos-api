#!/bin/bash

# POS System - Stop All Services
# This script stops Celery workers, Celery beat, and Redis

echo "🛑 Stopping POS System Services..."
echo ""

# Stop Celery workers
echo "⚙️  Stopping Celery workers..."
pkill -f "celery -A main worker"

# Stop Celery beat
echo "⏰ Stopping Celery beat..."
pkill -f "celery -A main beat"

# Stop Redis (if running as daemon)
echo "📦 Stopping Redis..."
redis-cli shutdown

# Stop Django server (if running)
echo "🌐 Stopping Django server..."
pkill -f "manage.py runserver"

echo ""
echo "✅ All services stopped"
