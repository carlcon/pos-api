# Quick Start Guide - Async Report Generation

## Prerequisites

- Redis installed (`brew install redis` on macOS)
- Python virtual environment activated
- All dependencies installed (`pip install -r requirements.txt`)

## Quick Start

### Option 1: Use the start script (Recommended)

```bash
cd pos-api
./start_services.sh
```

This will start:
- Redis (message broker)
- Celery worker (background tasks)
- Celery beat (scheduled tasks)
- Django server (API)

To stop all services:
```bash
./stop_services.sh
```

### Option 2: Manual start (for development/debugging)

Open 4 terminal windows:

**Terminal 1 - Redis:**
```bash
redis-server
```

**Terminal 2 - Celery Worker:**
```bash
cd pos-api
source venv/bin/activate
celery -A main worker -l info
```

**Terminal 3 - Celery Beat (optional):**
```bash
cd pos-api
source venv/bin/activate
celery -A main beat -l info
```

**Terminal 4 - Django:**
```bash
cd pos-api
source venv/bin/activate
python manage.py runserver 8088
```

**Terminal 5 - Frontend:**
```bash
cd pos-app
npm run dev
```

## Testing the System

1. Visit http://localhost:3000/reports
2. Click any report button (e.g., "📊 Daily Sales Report")
3. Watch the modal show generation progress
4. Download the PDF when ready
5. Or click the 📊 icon next to any report for CSV export

## Monitoring

View Celery tasks:
```bash
# See active tasks
celery -A main inspect active

# See registered tasks
celery -A main inspect registered

# See stats
celery -A main inspect stats
```

Check Redis connection:
```bash
redis-cli ping
# Should return: PONG
```

## Troubleshooting

**Reports not generating?**
1. Check Redis: `redis-cli ping`
2. Check Celery worker logs in `logs/celery-worker.log`
3. Check Django logs in terminal

**PDF errors?**
Install WeasyPrint dependencies:
```bash
brew install cairo pango gdk-pixbuf libffi
```

**Permission errors?**
```bash
chmod 755 media/reports
```

## What's New?

✅ **Async PDF Generation** - No more browser freezing while generating reports
✅ **Professional PDFs** - Beautiful, print-ready reports with proper formatting
✅ **Background Processing** - Celery handles long-running tasks
✅ **Progress Tracking** - Real-time status updates while report generates
✅ **CSV Export** - Still available with dedicated button per report
✅ **Auto Cleanup** - Old reports auto-deleted after 7 days

For more details, see [REPORTS_README.md](./REPORTS_README.md)
