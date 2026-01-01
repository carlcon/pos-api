#!/bin/bash

# POS System - Start All Services
# This script starts Redis, Celery worker, Celery beat, and Django server

echo "🚀 Starting POS System Services..."
echo ""

# Check if Redis is installed
if ! command -v redis-server &> /dev/null; then
    echo "❌ Redis not found. Please install Redis:"
    echo "   brew install redis"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please run:"
    echo "   python -m venv venv"
    echo "   source venv/bin/activate"
    echo "   pip install -r requirements.txt"
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Create reports directory if it doesn't exist
mkdir -p media/reports

# Start Redis in background if not running
if ! pgrep -x "redis-server" > /dev/null; then
    echo "📦 Starting Redis..."
    redis-server --daemonize yes
    sleep 2
else
    echo "✅ Redis already running"
fi

# Start Celery worker in background
echo "⚙️  Starting Celery worker..."
celery -A main worker -l info --logfile=logs/celery-worker.log --detach
sleep 2

# Start Celery beat in background
echo "⏰ Starting Celery beat..."
celery -A main beat -l info --logfile=logs/celery-beat.log --detach
sleep 2

# Start Django server
echo "🌐 Starting Django server..."
echo ""
echo "✅ All services started successfully!"
echo ""
echo "Services running:"
echo "  - Redis: localhost:6379"
echo "  - Celery Worker: Check logs/celery-worker.log"
echo "  - Celery Beat: Check logs/celery-beat.log"
echo "  - Django: http://localhost:8088"
echo ""
echo "To stop all services, run: ./stop_services.sh"
echo ""

python manage.py runserver 8088
